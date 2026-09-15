# OUANANICHE

Base de données requêtable du saumon atlantique au Canada, extraite
de sources publiques dispersées.

**Québec : 114 rivières × 42 ans (1984-2025), 19 mesures par année.**
Plus le débit journalier, l'habitat d'Anticosti, et les décomptes des
Maritimes et de Terre-Neuve-Labrador comme référence comparative.

## Utilisation

    pkg install python poppler curl 7zip
    python ouananiche.py fetch     # PDF du bilan (17 Mo, hors repo)
    python ouananiche.py text      # pdftotext -layout -> bilan.txt
    python fiches.py && python autres.py
    python carte.py                # -> carte.html
    python ratio.py                # analyse mad/red

`bilan.txt` et `debit.db` ne sont pas dans le repo : il faut rouler
`fetch` puis `text` sur un clone frais. `fiches.db` est commité, donc
les données sont utilisables sans refaire l'extraction.

`fiches.py` recrée la base de zéro. Roule `autres.py` après, sinon la
table `autre_riviere` est perdue.

## Volets

**1 — Bilan du Québec** (`ouananiche.py`, `fiches.py`, `autres.py`)
Extraction du « Bilan de l'exploitation du saumon au Québec »
(MELCCFP). 110 rivières avec série historique, 4 avec seuils seulement.

**2 — Contexte** (`volet2/`)
Habitat de l'île d'Anticosti (25 rivières, UP + superficie m²),
correspondance unités désignables COSEPAC ↔ zones salmonicoles,
26 gestionnaires officiels (TFS), 45 mandats SEAO liés à l'habitat.

**3 — Hydrologie** (`volet2/cehq_saumon.json`)
589 577 mesures de débit journalier du CEHQ, 36 rivières, 1923-2025.
Régénérable : `debit.db` est hors repo.

**4 — Maritimes** (`volet2/asir_maritimes.csv`)
16 stations de comptage du MPO (ASIR), 9 rivières du N.-B. et de la N.-É.

**5 — Terre-Neuve-Labrador et Golfe** (`volet2/canada/`)
33 237 comptages journaliers d'adultes, 5 253 de smolts, 21 rivières
avec coordonnées. Estimations du Golfe (SFA15-18) de 1970 à 2025.

## Méthode

Les colonnes du bilan sont ancrées sur la ligne d'en-tête de **chaque
page** (biais mesuré, résidu max 2 caractères sur 89 pages de
référence). Un gabarit fixe ne marche pas : 34 mises en page distinctes.

Validé par cohérence interne : `cap_petit + cap_grand = cap_total` et
`mont_mad + mont_red = mont_total` — 0 ligne incohérente sur 4793.

## Colonnes principales (table `fiche`)

riviere, zone, no_riviere, seuil_optimal, seuil_demo, annee,
cap_petit, cap_grand, cap_total, remise_eau, jours_peche, succes,
succes_ajuste, taux_petit, taux_grand, taux_total, retrait,
prelevement, mont_mad, mont_red, mont_total, repro_mad, repro_red,
repro_total, oeufs_millions

Santé d'une rivière : `oeufs_millions / seuil_optimal`. Sous 1,0 = la
rivière ne dépose pas assez d'œufs pour se renouveler.

**Attention aux homonymes** (3 « Saint-Jean », 2 « Malbaie ») :
grouper par riviere + zone, jamais par riviere seul.

## Résultats

- **2025 : une seule rivière sur 35 atteint son seuil** (Causapscal).
- **La Gaspésie porte 91 %** de la reproduction du Québec.
- **Le déclin est réel, pas un artefact de financement.** Panel fixe
  de 20 rivières suivies les 42 ans : −29 %, pente −212 poissons/an
  (r = −0,52), avec cassure en 2024-2025.
- **Le débit de juin n'explique pas la montaison** : corrélations
  autour de zéro sur 19 rivières, 42 ans.
- **La structure d'âge n'a pas changé** : proportion de rédibermarins
  stable (pente +0,017 point/an, r = 0,02) sur le panel fixe.
- Les Maritimes s'effondrent en parallèle (Saint-Jean : 17 poissons en
  2025), tandis que Terre-Neuve tient avec d'énormes volumes de
  madeleineaux (Exploits : 66 500 en trois ans).

Ces trois résultats convergent : la cause n'est ni dans l'hydrologie
des rivières, ni dans un changement de structure de population.

## Limites

- Les superficies d'habitat ne sont publiées que pour Anticosti. Pour
  les 89 autres rivières, les données existent au ministère mais ne
  sont pas diffusées.
- 41 rivières (Est de la Côte-Nord, Nunavik) n'ont aucun décompte.
  Absence de donnée ≠ absence de saumon.
- 68 rivières sur 110 n'ont pas de coordonnées dans la carte.
- Les rivières dont le suivi a cessé l'ont peut-être été parce qu'elles
  allaient mal — le −29 % est probablement un plancher.

## Sources

- MELCCFP, Bilan de l'exploitation du saumon au Québec
- CEHQ, historique des débits journaliers
- Données Québec (CKAN), MRNF (WFS/WMS)
- MPO : ASIR, comptages TNL, estimations du Golfe
- SEAO, contrats publics
