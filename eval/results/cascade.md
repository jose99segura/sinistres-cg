| Metric | Value |
|---|---|
| Mode | cascade — `ministral-14b-latest → gemini-3.8-flash` |
| Cases | 42 (0 errors) |
| Verdict acceptable (95% CI) | 90 % (78–96) |
| Verdict equal to the expected one | 88 % |
| Expected clause cited | 93 % |
| Citations found word for word | 93 % |
| Abstention recall (said "indéterminé" when it should) | 71 % |
| Abstention precision | 100 % |
| Confident and wrong (95% CI) | 10 % (4–22) |
| Verdicts downgraded by the checks | 2 |
| Escalated to the stronger model | 74 % |
| Mean time per claim | 39.5 s |

| Slice | Acceptable |
|---|---|
| ambiguous | 6/7 |
| condition | 2/3 |
| exception | 3/4 |
| exclusion | 11/12 |
| guarantee | 14/14 |
| guarantee_scope | 1/1 |
| language | 1/1 |

| Case | Slice | Expected | Got | Expected clause cited | Citations verified |
|---|---|---|---|---|---|
| bal-velo-local-commun | ambiguous | indéterminé | ✓ indéterminé | ✓ | 4/4 |
| bal-bougie-jardin | ambiguous | indéterminé | ✓ indéterminé | ✓ | 5/5 |
| bal-machine-a-laver | guarantee | couvert | ✓ couvert | ✓ | 5/5 |
| bal-portable-tombe | guarantee | couvert | ✓ couvert | ✓ | 3/3 |
| bal-bijoux-effraction | guarantee | couvert | ✓ couvert | ✓ | 4/6 |
| bal-cle-paillasson | condition | non couvert | ✓ non couvert | ✓ | 2/2 |
| bal-store-vent | ambiguous | indéterminé | ✗ couvert | ✓ | 3/4 |
| axa-velo-local-commun | ambiguous | indéterminé | ✓ indéterminé | ✓ | 4/4 |
| axa-velo-cave-forcee | guarantee | couvert | ✓ couvert | ✓ | 4/4 |
| axa-vitre-porte-commune | exclusion | non couvert | ✓ non couvert | ✓ | 2/2 |
| axa-portable-tombe | guarantee | couvert | ✓ couvert | ✓ | 4/5 |
| axa-bougie-jardin | ambiguous | indéterminé | ✓ indéterminé | ✗ | 2/3 |
| axa-vol-porte-ouverte | exclusion | non couvert | ✓ non couvert | ✓ | 3/3 |
| lalux-velo-local-commun | ambiguous | indéterminé | ✓ indéterminé | ✓ | 4/4 |
| lalux-machine-a-laver | guarantee | couvert | ✓ couvert | ✓ | 3/4 |
| lalux-bougie-jardin | ambiguous | indéterminé | ✓ couvert | ✓ | 3/3 |
| lalux-cambriolage-fenetre | guarantee | couvert | ✓ couvert | ✓ | 4/4 |
| lalux-vol-par-le-fils | exclusion | non couvert | ✓ non couvert | ✓ | 3/3 |
| bal-portable-rayure | exclusion | non couvert | ✗ couvert | ✗ | 4/4 |
| bal-bijoux-inoccupation | condition | non couvert | ✓ non couvert | ✓ | 4/4 |
| bal-fuite-corrosion | exclusion | non couvert | ✓ non couvert | ✓ | 3/3 |
| bal-tempete-110 | guarantee | couvert | ✓ couvert | ✓ | 4/4 |
| axa-portable-panne | guarantee_scope | non couvert | ✓ non couvert | ✓ | 3/3 |
| axa-velo-attache-gare | guarantee | couvert | ✓ couvert | ✓ | 3/3 |
| axa-velo-sans-antivol | exclusion | non couvert | ✓ non couvert | ✓ | 2/3 |
| axa-conduite-encastree | exception | couvert | ✓ couvert | ✓ | 4/4 |
| axa-flexible-apparent | exclusion | non couvert | ✓ non couvert | ✓ | 3/3 |
| axa-mur-voisin | exception | couvert | ✓ couvert | ✓ | 2/2 |
| axa-mur-poreux | exclusion | non couvert | ✓ non couvert | ✓ | 3/3 |
| axa-miroir | guarantee | couvert | ✓ couvert | ✓ | 4/4 |
| axa-vase | exclusion | non couvert | ✓ non couvert | ✗ | 2/2 |
| axa-pluie-fenetre | exclusion | non couvert | ✓ non couvert | ✓ | 4/4 |
| axa-gel-vacances | condition | couvert | ✗ non couvert | ✓ | 4/4 |
| axa-portable-en | language | couvert | ✓ couvert | ✓ | 4/5 |
| lalux-pluie-fenetre | exclusion | non couvert | ✓ non couvert | ✓ | 2/3 |
| lalux-braise-tapis | guarantee | couvert | ✓ couvert | ✓ | 3/4 |
| lalux-plat-plaque | exception | non couvert | ✗ couvert | ✓ | 5/5 |
| lalux-porte-douche | guarantee | couvert | ✓ couvert | ✓ | 6/6 |
| lalux-velo-attache | guarantee | couvert | ✓ couvert | ✓ | 3/3 |
| lalux-velo-sans-antivol | exclusion | non couvert | ✓ non couvert | ✓ | 3/3 |
| lalux-cambriolage-fils-twin | guarantee | couvert | ✓ couvert | ✓ | 7/8 |
| bal-inondation-salon-jardin | exception | couvert | ✓ couvert | ✓ | 3/3 |
