#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OUANANICHE - socle statique (couche 1)
Extrait le « Bilan de l'exploitation du saumon au Quebec » (MELCCFP)
vers une base SQLite requetable : montaison par riviere, par annee.

Dependances Termux :
    pkg install python poppler curl

Usage :
    python ouananiche.py fetch    # telecharge le PDF
    python ouananiche.py text     # pdftotext -layout -> bilan.txt
    python ouananiche.py scan     # DIAGNOSTIC : montre la structure reelle
    python ouananiche.py parse    # tente le parse -> ouananiche.db + CSV

Roule fetch -> text -> scan AVANT parse. Le scan te dit si le PDF
est exploitable ou s'il faut passer a l'OCR.
"""

import os
import re
import sys
import csv
import sqlite3
import subprocess

BASE = os.path.dirname(os.path.abspath(__file__))
PDF = os.path.join(BASE, "bilan.pdf")
TXT = os.path.join(BASE, "bilan.txt")
DB = os.path.join(BASE, "ouananiche.db")
CSV_OUT = os.path.join(BASE, "montaisons.csv")
REJETS = os.path.join(BASE, "_non_parsees.txt")

URL = ("https://bibliotheque.cecile-rouleau.gouv.qc.ca/documents/"
       "archives/pgq/L6G48_B54/L6G48_B54_2025.pdf")

# Ancres de diagnostic seulement. PAS une whitelist : le parser
# ne s'en sert pas pour filtrer, juste pour reperer les bonnes pages.
ANCRES = [
    "Moisie", "Bonaventure", "Cascapedia", "Matapedia", "Matane",
    "Dartmouth", "York", "Madeleine", "Mitis", "Rimouski", "Ouelle",
    "Godbout", "Trinite", "Laval", "Pentecote", "Natashquan",
    "Romaine", "Magpie", "Jupiter", "Vaureal", "Becscie",
    "Escoumins", "Mars", "Patapedia", "Nouvelle", "Port-Daniel",
]

ANNEE_MIN, ANNEE_MAX = 1984, 2035


# ---------------------------------------------------------------- utilitaires

def sans_accents(s):
    table = str.maketrans("àâäéèêëîïôöùûüçÀÂÄÉÈÊËÎÏÔÖÙÛÜÇ",
                          "aaaeeeeiioouuucAAAEEEEIIOOUUUC")
    return s.translate(table)


def normaliser(ligne):
    """Espaces insecables -> espace, puis recolle les milliers (1 234 -> 1234)."""
    ligne = ligne.replace("\u00a0", " ").replace("\u202f", " ").replace("\t", "  ")
    avant = None
    while avant != ligne:
        avant = ligne
        ligne = re.sub(r"(?<=\d) (?=\d{3}(?!\d))", "", ligne)
    return ligne.rstrip()


def nombres(ligne):
    """Tokens numeriques d'une ligne, avec leur position de depart."""
    out = []
    for m in re.finditer(r"-?\d+(?:[.,]\d+)?", ligne):
        out.append((m.start(), m.group()))
    return out


def en_nombre(tok):
    tok = tok.replace(",", ".")
    try:
        v = float(tok)
    except ValueError:
        return None
    return int(v) if v == int(v) else v


def exiger(path, etape):
    if not os.path.exists(path):
        sys.exit("Manquant : %s  ->  roule d'abord : python ouananiche.py %s"
                 % (os.path.basename(path), etape))


# ---------------------------------------------------------------------- fetch

def cmd_fetch():
    if os.path.exists(PDF):
        print("Deja la : %s (%d ko)" % (PDF, os.path.getsize(PDF) // 1024))
        print("Supprime-le pour retelecharger.")
        return
    print("Telechargement...")
    r = subprocess.run(["curl", "-sSL", "--fail", "-o", PDF, URL])
    if r.returncode != 0 or not os.path.exists(PDF):
        sys.exit("Echec du telechargement. Verifie l'URL dans un navigateur.")
    taille = os.path.getsize(PDF)
    print("OK : %d ko" % (taille // 1024))
    if taille < 50000:
        print("!! Fichier suspect (trop petit). Ouvre-le pour verifier.")


# ----------------------------------------------------------------------- text

def cmd_text():
    exiger(PDF, "fetch")
    r = subprocess.run(["pdftotext", "-layout", PDF, TXT])
    if r.returncode != 0:
        sys.exit("pdftotext a plante. pkg install poppler")
    with open(TXT, encoding="utf-8", errors="replace") as f:
        contenu = f.read()
    chiffres = sum(c.isdigit() for c in contenu)
    print("OK : %d caracteres, %d chiffres" % (len(contenu), chiffres))
    if chiffres < 500:
        print()
        print("!! Presque aucun chiffre extrait : le PDF est probablement")
        print("!! en images. Il faudra de l'OCR (pkg install tesseract).")


# ----------------------------------------------------------------------- scan

def cmd_scan():
    """Diagnostic. Ne produit rien, montre juste la structure reelle."""
    exiger(TXT, "text")
    with open(TXT, encoding="utf-8", errors="replace") as f:
        pages = f.read().split("\f")

    print("Pages : %d" % len(pages))
    print()

    ancres_bas = [sans_accents(a).lower() for a in ANCRES]
    interessantes = []

    for i, page in enumerate(pages, 1):
        pb = sans_accents(page).lower()
        hits = sum(1 for a in ancres_bas if a in pb)
        lignes_data = 0
        for ligne in page.splitlines():
            ligne = normaliser(ligne)
            nums = nombres(ligne)
            if len(nums) >= 4 and re.match(r"^\s*[A-Za-zÀ-ÿ]", ligne):
                lignes_data += 1
        if hits >= 2 or lignes_data >= 5:
            interessantes.append((i, hits, lignes_data))

    if not interessantes:
        print("Aucune page tabulaire detectee. Regarde bilan.txt a la main.")
        return

    print("Pages candidates (page / noms de rivieres / lignes de donnees) :")
    for i, h, d in interessantes:
        print("  p.%-4d  rivieres=%-3d  lignes=%d" % (i, h, d))
    print()

    best = max(interessantes, key=lambda t: t[2])[0]
    print("=" * 64)
    print("ECHANTILLON BRUT - page %d (colle-moi ca)" % best)
    print("=" * 64)
    for ligne in pages[best - 1].splitlines()[:30]:
        print(normaliser(ligne))
    print("=" * 64)


# ---------------------------------------------------------------------- parse

def annees_de_ligne(ligne):
    """Une ligne d'entete = plusieurs annees plausibles a la suite."""
    vals = [int(t) for _, t in nombres(ligne)
            if t.isdigit() and ANNEE_MIN <= int(t) <= ANNEE_MAX]
    if len(vals) < 3:
        return []
    # Un vrai entete est croissant et quasi consecutif. Sinon c'est une
    # ligne de decomptes dont les valeurs tombent par hasard dans 1984-2035.
    for a, b in zip(vals, vals[1:]):
        if not (1 <= b - a <= 2):
            return []
    return vals


def cmd_parse():
    exiger(TXT, "text")
    with open(TXT, encoding="utf-8", errors="replace") as f:
        pages = f.read().split("\f")

    lignes_ok = []      # (riviere, annee, valeur, page)
    rejets = []
    annees = []

    for num_page, page in enumerate(pages, 1):
        for brut in page.splitlines():
            ligne = normaliser(brut)
            if not ligne.strip():
                continue

            entete = annees_de_ligne(ligne)
            if entete:
                annees = entete
                continue

            nums = nombres(ligne)
            if len(nums) < 3:
                continue

            debut = nums[0][0]
            label = ligne[:debut].strip(" .-–—")
            label = re.sub(r"\s{2,}", " ", label)

            if len(re.findall(r"[A-Za-zÀ-ÿ]", label)) < 3:
                rejets.append("p.%d | %s" % (num_page, ligne))
                continue

            valeurs = [en_nombre(t) for _, t in nums]
            valeurs = [v for v in valeurs if v is not None]

            if not annees:
                rejets.append("p.%d | (aucune annee connue) %s" % (num_page, ligne))
                continue

            for i, v in enumerate(valeurs):
                if i < len(annees):
                    lignes_ok.append((label, annees[i], v, num_page))

    if not lignes_ok:
        print("Rien de parse. Roule `scan` et envoie l'echantillon.")
        _ecrire_rejets(rejets)
        return

    _ecrire_db(lignes_ok)
    _ecrire_csv(lignes_ok)
    _ecrire_rejets(rejets)

    rivieres = sorted({r for r, _, _, _ in lignes_ok})
    print("Parse : %d points, %d rivieres distinctes"
          % (len(lignes_ok), len(rivieres)))
    if annees:
        print("Dernier entete d'annees lu : %d -> %d (%d colonnes)"
              % (annees[0], annees[-1], len(annees)))
    print()
    print("Echantillon de noms detectes (VERIFIE-LES) :")
    for r in rivieres[:20]:
        print("   " + r)
    print()
    print("Rejets : %d lignes -> %s" % (len(rejets), os.path.basename(REJETS)))
    print("Sorties : ouananiche.db, montaisons.csv")


def _ecrire_db(rows):
    if os.path.exists(DB):
        os.remove(DB)
    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE montaison (
        riviere TEXT NOT NULL,
        annee   INTEGER NOT NULL,
        valeur  REAL,
        page    INTEGER
    )""")
    con.executemany("INSERT INTO montaison VALUES (?,?,?,?)", rows)
    con.execute("CREATE INDEX idx_riv ON montaison(riviere)")
    con.execute("CREATE INDEX idx_an ON montaison(annee)")
    con.commit()
    con.close()


def _ecrire_csv(rows):
    with open(CSV_OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["riviere", "annee", "valeur", "page"])
        w.writerows(rows)


def _ecrire_rejets(rejets):
    with open(REJETS, "w", encoding="utf-8") as f:
        f.write("\n".join(rejets))


# ------------------------------------------------------------------------ cli

def cmd_page():
    exiger(TXT, "text")
    if len(sys.argv) < 3:
        sys.exit("Usage : python ouananiche.py page 40 [45]")
    with open(TXT, encoding="utf-8", errors="replace") as f:
        pages = f.read().split("\f")
    debut = int(sys.argv[2])
    fin = int(sys.argv[3]) if len(sys.argv) > 3 else debut
    for n in range(debut, min(fin, len(pages)) + 1):
        print("=" * 64)
        print("PAGE %d / %d" % (n, len(pages)))
        print("=" * 64)
        print(pages[n - 1].rstrip())


def cmd_annexe():
    exiger(TXT, "text")
    with open(TXT, encoding="utf-8", errors="replace") as f:
        pages = f.read().split("\f")
    rx = re.compile(r"^\s*(?:19|20)\d{2}\b")
    stats = []
    for i, page in enumerate(pages, 1):
        n = sum(1 for l in page.splitlines() if rx.match(l))
        if n >= 5:
            stats.append((i, n))
    print("Pages a lignes-annee : %d" % len(stats))
    for i, n in stats[:40]:
        print("  p.%-4d  %d lignes" % (i, n))
    if stats:
        best = max(stats, key=lambda t: t[1])[0]
        print()
        print("=" * 64)
        print("PAGE %d" % best)
        print("=" * 64)
        for l in pages[best - 1].splitlines()[:28]:
            print(normaliser(l))


def cmd_titres():
    exiger(TXT, "text")
    with open(TXT, encoding="utf-8", errors="replace") as f:
        pages = f.read().split("\f")
    rx = re.compile(r"^\s*(Tableau|Annexe)\s", re.I)
    for i, page in enumerate(pages, 1):
        for l in page.splitlines():
            if rx.match(l):
                print("p.%-4d %s" % (i, " ".join(l.split())[:88]))


COMMANDES = {
    "fetch": cmd_fetch,
    "text": cmd_text,
    "scan": cmd_scan,
    "parse": cmd_parse,
    "page": cmd_page,
    "annexe": cmd_annexe,
    "titres": cmd_titres,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDES:
        print(__doc__)
        sys.exit(1)
    COMMANDES[sys.argv[1]]()
