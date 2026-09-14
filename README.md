# OUANANICHE

Extraction du « Bilan de l'exploitation du saumon au Québec » (MELCCFP)
vers une base SQLite requêtable.

**111 rivières × 42 ans (1984-2025), 19 mesures par année.**

## Utilisation

    pkg install python poppler curl
    python ouananiche.py fetch     # télécharge le PDF (17 Mo, hors repo)
    python ouananiche.py text      # pdftotext -layout -> bilan.txt
    python fiches.py               # -> fiches.db + fiches.csv

`bilan.txt` n'est pas dans le repo : il faut rouler `fetch` puis `text`
avant `fiches.py` sur un clone frais. `fiches.db` est commité, donc les
données sont utilisables sans refaire l'extraction.

## Méthode

Les colonnes sont ancrées sur la ligne d'en-tête de **chaque page**
(biais mesuré, résidu max 2 caractères sur 89 pages de référence).
Un gabarit fixe ne marche pas : 34 mises en page distinctes.

Validé par cohérence interne : `cap_petit + cap_grand = cap_total` et
`mont_mad + mont_red = mont_total` — 0 ligne incohérente sur 4793.

## Colonnes

riviere, zone, no_riviere, seuil_optimal, seuil_demo, page, annee,
cap_petit, cap_grand, cap_total, remise_eau, jours_peche, succes,
succes_ajuste, taux_petit, taux_grand, taux_total, retrait,
prelevement, mont_mad, mont_red, mont_total, repro_mad, repro_red,
repro_total, oeufs_millions

Santé d'une rivière : `oeufs_millions / seuil_optimal`. Sous 1,0 = la
rivière ne dépose pas assez d'œufs pour se renouveler.

Attention aux homonymes (3 « Saint-Jean », 2 « Malbaie ») : grouper par
riviere + zone, jamais par riviere seul.

Source : https://bibliotheque.cecile-rouleau.gouv.qc.ca/documents/archives/pgq/L6G48_B54/L6G48_B54_2025.pdf
