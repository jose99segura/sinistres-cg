| Metric | Value |
|---|---|
| Mode | strong — `gemini-3.8-flash` |
| Cases | 42 (0 errors) |
| Verdict acceptable (95% CI) | 93 % (81–98) |
| Verdict equal to the expected one | 88 % |
| Expected clause cited | 90 % |
| Citations found word for word | 95 % |
| Abstention recall (said "indéterminé" when it should) | 71 % |
| Abstention precision | 83 % |
| Confident and wrong (95% CI) | 5 % (1–16) |
| Verdicts downgraded by the checks | 2 |
| Escalated to the stronger model | 0 % |
| Mean time per claim | 32.6 s |

| Slice | Acceptable |
|---|---|
| ambiguous | 7/7 |
| condition | 1/3 |
| exception | 4/4 |
| exclusion | 11/12 |
| guarantee | 14/14 |
| guarantee_scope | 1/1 |
| language | 1/1 |

| Case | Slice | Expected | Got | Expected clause cited | Citations verified |
|---|---|---|---|---|---|
| bal-velo-local-commun | ambiguous | indéterminé | ✓ indéterminé | ✓ | 3/4 |
| bal-bougie-jardin | ambiguous | indéterminé | ✓ indéterminé | ✓ | 5/5 |
| bal-machine-a-laver | guarantee | couvert | ✓ couvert | ✓ | 2/3 |
| bal-portable-tombe | guarantee | couvert | ✓ couvert | ✓ | 4/4 |
| bal-bijoux-effraction | guarantee | couvert | ✓ couvert | ✓ | 5/5 |
| bal-cle-paillasson | condition | non couvert | ✗ indéterminé | ✗ | 1/2 |
| bal-store-vent | ambiguous | indéterminé | ✓ non couvert | ✓ | 3/3 |
| axa-velo-local-commun | ambiguous | indéterminé | ✓ indéterminé | ✓ | 3/3 |
| axa-velo-cave-forcee | guarantee | couvert | ✓ couvert | ✓ | 4/4 |
| axa-vitre-porte-commune | exclusion | non couvert | ✓ non couvert | ✓ | 2/2 |
| axa-portable-tombe | guarantee | couvert | ✓ couvert | ✓ | 2/3 |
| axa-bougie-jardin | ambiguous | indéterminé | ✓ indéterminé | ✗ | 2/3 |
| axa-vol-porte-ouverte | exclusion | non couvert | ✓ non couvert | ✓ | 4/4 |
| lalux-velo-local-commun | ambiguous | indéterminé | ✓ indéterminé | ✓ | 4/4 |
| lalux-machine-a-laver | guarantee | couvert | ✓ couvert | ✓ | 3/3 |
| lalux-bougie-jardin | ambiguous | indéterminé | ✓ couvert | ✓ | 3/3 |
| lalux-cambriolage-fenetre | guarantee | couvert | ✓ couvert | ✓ | 4/4 |
| lalux-vol-par-le-fils | exclusion | non couvert | ✓ non couvert | ✓ | 2/2 |
| bal-portable-rayure | exclusion | non couvert | ✗ couvert | ✗ | 4/4 |
| bal-bijoux-inoccupation | condition | non couvert | ✓ non couvert | ✓ | 2/2 |
| bal-fuite-corrosion | exclusion | non couvert | ✓ non couvert | ✓ | 3/3 |
| bal-tempete-110 | guarantee | couvert | ✓ couvert | ✓ | 4/4 |
| axa-portable-panne | guarantee_scope | non couvert | ✓ non couvert | ✓ | 2/2 |
| axa-velo-attache-gare | guarantee | couvert | ✓ couvert | ✓ | 3/3 |
| axa-velo-sans-antivol | exclusion | non couvert | ✓ non couvert | ✓ | 3/3 |
| axa-conduite-encastree | exception | couvert | ✓ couvert | ✓ | 4/4 |
| axa-flexible-apparent | exclusion | non couvert | ✓ non couvert | ✓ | 3/3 |
| axa-mur-voisin | exception | couvert | ✓ couvert | ✓ | 2/2 |
| axa-mur-poreux | exclusion | non couvert | ✓ non couvert | ✓ | 2/2 |
| axa-miroir | guarantee | couvert | ✓ couvert | ✓ | 2/2 |
| axa-vase | exclusion | non couvert | ✓ non couvert | ✗ | 2/2 |
| axa-pluie-fenetre | exclusion | non couvert | ✓ non couvert | ✓ | 4/4 |
| axa-gel-vacances | condition | couvert | ✗ non couvert | ✓ | 4/4 |
| axa-portable-en | language | couvert | ✓ couvert | ✓ | 2/3 |
| lalux-pluie-fenetre | exclusion | non couvert | ✓ non couvert | ✓ | 3/3 |
| lalux-braise-tapis | guarantee | couvert | ✓ couvert | ✓ | 2/2 |
| lalux-plat-plaque | exception | non couvert | ✓ non couvert | ✓ | 2/2 |
| lalux-porte-douche | guarantee | couvert | ✓ couvert | ✓ | 2/2 |
| lalux-velo-attache | guarantee | couvert | ✓ couvert | ✓ | 4/4 |
| lalux-velo-sans-antivol | exclusion | non couvert | ✓ non couvert | ✓ | 3/3 |
| lalux-cambriolage-fils-twin | guarantee | couvert | ✓ couvert | ✓ | 4/4 |
| bal-inondation-salon-jardin | exception | couvert | ✓ couvert | ✓ | 3/3 |
