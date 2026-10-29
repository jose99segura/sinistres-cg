"""One function to call a model: `structured(system, user, Schema, model=...) -> Schema instance`.

Two providers behind the same call: Mistral (the cheap first stage) and Gemini (the stronger model the
cascade escalates to). Both are asked for JSON matching a Pydantic schema, and the answer is validated
by Pydantic again on our side: if it does not parse, it is an error, not a best effort.
"""

import json
import threading
import time
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from . import config

T = TypeVar("T", bound=BaseModel)

_client = httpx.Client(timeout=120)

# The free Mistral tier allows 30 requests a minute on ministral-14b: space calls out across threads
# rather than collecting 429s.
_lock = threading.Lock()
_next_slot = 0.0


def _throttle() -> None:
    global _next_slot
    with _lock:
        now = time.monotonic()
        wait = _next_slot - now
        _next_slot = max(now, _next_slot) + config.LLM_MIN_INTERVAL
    if wait > 0:
        time.sleep(wait)


class LLMError(RuntimeError):
    pass


def _mistral(system: str, user: str, schema: type[BaseModel], model: str, temperature: float) -> str:
    if not config.MISTRAL_API_KEY:
        raise LLMError("MISTRAL_API_KEY is not set")
    _throttle()
    r = _client.post(
        "https://api.mistral.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {config.MISTRAL_API_KEY}"},
        json={
            "model": model,
            "temperature": temperature,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": schema.__name__, "schema": schema.model_json_schema(), "strict": True},
            },
        },
    )
    if r.status_code == 429 or r.status_code >= 500:
        raise LLMError(f"Mistral {r.status_code}: {r.text[:200]}")
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def _gemini(system: str, user: str, schema: type[BaseModel], model: str, temperature: float) -> str:
    if not config.GEMINI_API_KEY:
        raise LLMError("GEMINI_API_KEY is not set")
    r = _client.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        headers={"x-goog-api-key": config.GEMINI_API_KEY},
        json={
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "temperature": temperature,
                "responseMimeType": "application/json",
                "responseJsonSchema": schema.model_json_schema(),
            },
        },
    )
    if r.status_code == 429 or r.status_code >= 500:
        raise LLMError(f"Gemini {r.status_code}: {r.text[:200]}")
    r.raise_for_status()
    parts = r.json()["candidates"][0]["content"]["parts"]
    return "".join(p.get("text", "") for p in parts if not p.get("thought"))


def structured(system: str, user: str, schema: type[T], *, model: str | None = None,
               temperature: float = 0.0, retries: int = 4) -> T:
    model = model or config.MISTRAL_MODEL
    call = _gemini if model.startswith("gemini") else _mistral
    last: Exception | None = None
    for attempt in range(retries):
        try:
            return schema.model_validate(json.loads(call(system, user, schema, model, temperature)))
        except (httpx.HTTPError, LLMError, ValidationError, json.JSONDecodeError, KeyError, IndexError) as e:
            last = e
            # Client errors other than rate limits will not get better by retrying.
            if isinstance(e, httpx.HTTPStatusError) and e.response.status_code < 500:
                break
            time.sleep(2 * 2**attempt)
    raise LLMError(f"{model} failed after {retries} attempts: {last}")
