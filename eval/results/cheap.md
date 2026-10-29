| Metric | Value |
|---|---|
| Mode | cheap — `ministral-14b-latest` |
| Cases | 42 (0 errors) |
| Verdict acceptable (95% CI) | 67 % (52–79) |
| Verdict equal to the expected one | 52 % |
| Expected clause cited | 74 % |
| Citations found word for word | 70 % |
| Abstention recall (said "indéterminé" when it should) | 43 % |
| Abstention precision | 21 % |
| Confident and wrong (95% CI) | 12 % (5–25) |
| Verdicts downgraded by the checks | 6 |
| Escalated to the stronger model | 0 % |
| Mean time per claim | 21.5 s |

| Slice | Acceptable |
|---|---|
| ambiguous | 7/7 |
| condition | 3/3 |
| exception | 1/4 |
| exclusion | 7/12 |
| guarantee | 8/14 |
| guarantee_scope | 1/1 |
| language | 1/1 |

| Case | Slice | Expected | Got | Expected clause cited | Citations verified |
|---|---|---|---|---|---|
| bal-velo-local-commun | ambiguous | indéterminé | ✓ non couvert | ✓ | 5/5 |
| bal-bougie-jardin | ambiguous | indéterminé | ✓ indéterminé | ✓ | 3/5 |
| bal-machine-a-laver | guarantee | couvert | ✓ couvert | ✓ | 4/4 |
| bal-portable-tombe | guarantee | couvert | ✗ indéterminé | ✓ | 5/5 |
| bal-bijoux-effraction | guarantee | couvert | ✓ couvert | ✓ | 4/5 |
| bal-cle-paillasson | condition | non couvert | ✓ non couvert | ✓ | 3/4 |
| bal-store-vent | ambiguous | indéterminé | ✓ non couvert | ✓ | 3/4 |
| axa-velo-local-commun | ambiguous | indéterminé | ✓ non couvert | ✓ | 5/6 |
| axa-velo-cave-forcee | guarantee | couvert | ✗ indéterminé | ✓ | 6/11 |
| axa-vitre-porte-commune | exclusion | non couvert | ✗ indéterminé | ✓ | 4/4 |
| axa-portable-tombe | guarantee | couvert | ✓ couvert | ✓ | 4/5 |
| axa-bougie-jardin | ambiguous | indéterminé | ✓ indéterminé | ✗ | 3/4 |
| axa-vol-porte-ouverte | exclusion | non couvert | ✓ non couvert | ✓ | 5/6 |
| lalux-velo-local-commun | ambiguous | indéterminé | ✓ indéterminé | ✓ | 4/5 |
| lalux-machine-a-laver | guarantee | couvert | ✓ couvert | ✓ | 3/5 |
| lalux-bougie-jardin | ambiguous | indéterminé | ✓ couvert | ✓ | 2/5 |
| lalux-cambriolage-fenetre | guarantee | couvert | ✗ indéterminé | ✓ | 4/5 |
| lalux-vol-par-le-fils | exclusion | non couvert | ✓ non couvert | ✓ | 3/4 |
| bal-portable-rayure | exclusion | non couvert | ✗ couvert | ✗ | 5/6 |
| bal-bijoux-inoccupation | condition | non couvert | ✓ non couvert | ✓ | 5/5 |
| bal-fuite-corrosion | exclusion | non couvert | ✓ non couvert | ✓ | 3/4 |
| bal-tempete-110 | guarantee | couvert | ✓ couvert | ✓ | 2/4 |
| axa-portable-panne | guarantee_scope | non couvert | ✓ non couvert | ✓ | 5/5 |
| axa-velo-attache-gare | guarantee | couvert | ✗ non couvert | ✗ | 3/5 |
| axa-velo-sans-antivol | exclusion | non couvert | ✓ non couvert | ✓ | 3/5 |
| axa-conduite-encastree | exception | couvert | ✗ indéterminé | ✗ | 1/4 |
| axa-flexible-apparent | exclusion | non couvert | ✗ indéterminé | ✗ | 1/4 |
| axa-mur-voisin | exception | couvert | ✓ indéterminé | ✗ | 1/4 |
| axa-mur-poreux | exclusion | non couvert | ✗ indéterminé | ✗ | 0/5 |
| axa-miroir | guarantee | couvert | ✓ couvert | ✓ | 4/5 |
| axa-vase | exclusion | non couvert | ✗ couvert | ✗ | 4/5 |
| axa-pluie-fenetre | exclusion | non couvert | ✓ non couvert | ✗ | 2/4 |
| axa-gel-vacances | condition | couvert | ✓ indéterminé | ✓ | 1/4 |
| axa-portable-en | language | couvert | ✓ couvert | ✓ | 5/6 |
| lalux-pluie-fenetre | exclusion | non couvert | ✓ non couvert | ✗ | 4/6 |
| lalux-braise-tapis | guarantee | couvert | ✓ couvert | ✓ | 2/4 |
| lalux-plat-plaque | exception | non couvert | ✗ couvert | ✓ | 3/4 |
| lalux-porte-douche | guarantee | couvert | ✓ couvert | ✓ | 4/4 |
| lalux-velo-attache | guarantee | couvert | ✗ indéterminé | ✓ | 4/5 |
| lalux-velo-sans-antivol | exclusion | non couvert | ✓ non couvert | ✓ | 4/4 |
| lalux-cambriolage-fils-twin | guarantee | couvert | ✗ indéterminé | ✓ | 6/7 |
| bal-inondation-salon-jardin | exception | couvert | ✗ non couvert | ✗ | 2/4 |
