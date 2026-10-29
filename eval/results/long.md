| Metric | Value |
|---|---|
| Mode | long — `gemini-3.8-flash` |
| Cases | 42 (0 errors) |
| Verdict acceptable (95% CI) | 95 % (84–99) |
| Verdict equal to the expected one | 88 % |
| Expected clause cited | 98 % |
| Citations found word for word | 94 % |
| Abstention recall (said "indéterminé" when it should) | 43 % |
| Abstention precision | 100 % |
| Confident and wrong (95% CI) | 5 % (1–16) |
| Verdicts downgraded by the checks | 0 |
| Escalated to the stronger model | 0 % |
| Mean time per claim | 29.8 s |

| Slice | Acceptable |
|---|---|
| ambiguous | 6/7 |
| condition | 2/3 |
| exception | 4/4 |
| exclusion | 12/12 |
| guarantee | 14/14 |
| guarantee_scope | 1/1 |
| language | 1/1 |

| Case | Slice | Expected | Got | Expected clause cited | Citations verified |
|---|---|---|---|---|---|
| bal-velo-local-commun | ambiguous | indéterminé | ✓ indéterminé | ✓ | 4/4 |
| bal-bougie-jardin | ambiguous | indéterminé | ✓ non couvert | ✓ | 4/4 |
| bal-machine-a-laver | guarantee | couvert | ✓ couvert | ✓ | 1/2 |
| bal-portable-tombe | guarantee | couvert | ✓ couvert | ✓ | 4/4 |
| bal-bijoux-effraction | guarantee | couvert | ✓ couvert | ✓ | 5/5 |
| bal-cle-paillasson | condition | non couvert | ✓ non couvert | ✓ | 3/3 |
| bal-store-vent | ambiguous | indéterminé | ✓ non couvert | ✓ | 3/3 |
| axa-velo-local-commun | ambiguous | indéterminé | ✓ indéterminé | ✓ | 4/4 |
| axa-velo-cave-forcee | guarantee | couvert | ✓ couvert | ✓ | 4/4 |
| axa-vitre-porte-commune | exclusion | non couvert | ✓ non couvert | ✓ | 2/2 |
| axa-portable-tombe | guarantee | couvert | ✓ couvert | ✓ | 3/4 |
| axa-bougie-jardin | ambiguous | indéterminé | ✓ non couvert | ✗ | 2/3 |
| axa-vol-porte-ouverte | exclusion | non couvert | ✓ non couvert | ✓ | 5/5 |
| lalux-velo-local-commun | ambiguous | indéterminé | ✓ indéterminé | ✓ | 4/4 |
| lalux-machine-a-laver | guarantee | couvert | ✓ couvert | ✓ | 3/3 |
| lalux-bougie-jardin | ambiguous | indéterminé | ✗ non couvert | ✓ | 3/4 |
| lalux-cambriolage-fenetre | guarantee | couvert | ✓ couvert | ✓ | 4/4 |
| lalux-vol-par-le-fils | exclusion | non couvert | ✓ non couvert | ✓ | 2/2 |
| bal-portable-rayure | exclusion | non couvert | ✓ non couvert | ✓ | 3/3 |
| bal-bijoux-inoccupation | condition | non couvert | ✓ non couvert | ✓ | 4/4 |
| bal-fuite-corrosion | exclusion | non couvert | ✓ non couvert | ✓ | 2/2 |
| bal-tempete-110 | guarantee | couvert | ✓ couvert | ✓ | 3/3 |
| axa-portable-panne | guarantee_scope | non couvert | ✓ non couvert | ✓ | 3/4 |
| axa-velo-attache-gare | guarantee | couvert | ✓ couvert | ✓ | 2/3 |
| axa-velo-sans-antivol | exclusion | non couvert | ✓ non couvert | ✓ | 2/2 |
| axa-conduite-encastree | exception | couvert | ✓ couvert | ✓ | 4/4 |
| axa-flexible-apparent | exclusion | non couvert | ✓ non couvert | ✓ | 3/3 |
| axa-mur-voisin | exception | couvert | ✓ couvert | ✓ | 2/2 |
| axa-mur-poreux | exclusion | non couvert | ✓ non couvert | ✓ | 2/2 |
| axa-miroir | guarantee | couvert | ✓ couvert | ✓ | 2/2 |
| axa-vase | exclusion | non couvert | ✓ non couvert | ✓ | 3/3 |
| axa-pluie-fenetre | exclusion | non couvert | ✓ non couvert | ✓ | 4/4 |
| axa-gel-vacances | condition | couvert | ✗ non couvert | ✓ | 4/4 |
| axa-portable-en | language | couvert | ✓ couvert | ✓ | 3/4 |
| lalux-pluie-fenetre | exclusion | non couvert | ✓ non couvert | ✓ | 3/3 |
| lalux-braise-tapis | guarantee | couvert | ✓ couvert | ✓ | 3/3 |
| lalux-plat-plaque | exception | non couvert | ✓ non couvert | ✓ | 3/3 |
| lalux-porte-douche | guarantee | couvert | ✓ couvert | ✓ | 2/2 |
| lalux-velo-attache | guarantee | couvert | ✓ couvert | ✓ | 4/4 |
| lalux-velo-sans-antivol | exclusion | non couvert | ✓ non couvert | ✓ | 2/3 |
| lalux-cambriolage-fils-twin | guarantee | couvert | ✓ couvert | ✓ | 3/3 |
| bal-inondation-salon-jardin | exception | couvert | ✓ couvert | ✓ | 4/4 |
