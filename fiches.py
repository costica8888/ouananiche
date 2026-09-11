#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OUANANICHE - parser des fiches par riviere (p.72 a 302 du bilan).
Parse par POSITION de colonne, pas par ordre.
    python fiches.py
"""

import os
import re
import csv
import sqlite3

BASE = os.path.dirname(os.path.abspath(__file__))
TXT = os.path.join(BASE, "bilan.txt")
DB = os.path.join(BASE, "fiches.db")
CSV_OUT = os.path.join(BASE, "fiches.csv")
SUSPECTS = os.path.join(BASE, "_suspects.txt")

COLONNES = [
    "annee", "cap_petit", "cap_grand", "cap_total", "remise_eau",
    "jours_peche", "succes", "succes_ajuste",
    "taux_petit", "taux_grand", "taux_total",
    "retrait", "prelevement",
    "mont_mad", "mont_red", "mont_total",
    "repro_mad", "repro_red", "repro_total",
    "oeufs_millions",
]
N_COL = len(COLONNES)
TOL = 4

# Positions figees (medianes de 52 pages propres, ecart max 3 car.)
GABARIT = [4, 12, 21, 29, 38, 48, 57, 65, 71, 77,
           82, 92, 101, 108, 117, 125, 132, 139, 147, 157]

RX_TITRE = re.compile(
    r"Sommaire de l'exploitation sportive de \d{4} à \d{4}\s+"
    r"(?:de la |du |de l'|dans les |des )?(.+?)\s+Optimal\s*:\s*([\d,]*)")
RX_ZONE = re.compile(r"Zone salmonicole\s*:\s*(\S+)")
RX_NO = re.compile(r"No\.\s*rivière\s*:\s*(\S+)")
RX_DEMO = re.compile(r"Démographique\s*:\s*([\d,]+)")
RX_ANNEE = re.compile(r"^\s*(?:19|20)\d{2}\b")


# --- ancrage des colonnes sur l'en-tete de CHAQUE page ---
# residu max mesure : 2 caracteres sur 89 pages de reference

SPEC = [(1, "Petit", 1), (1, "Grand", 1), (1, "Total", 1), (2, "à l'eau", 1),
        (2, "pêche", 1), (2, "(Cap./j-p.)", 1), (2, "ajusté", 1),
        (2, "Petit", 1), (2, "Grand", 1), (2, "Total", 1), (1, "Retrait", 1),
        (2, "vement", 1), (1, "Mad.", 1), (1, "Réd.", 1), (1, "Total", 2),
        (1, "Mad.", 2), (1, "Réd.", 2), (1, "Total", 3), (1, "Oeufs", 1)]

BIAIS = [-2, -1, -1, -2, -1, -3, -2, -2, -2, -3, -3, -1, -1, 0, -1, -1, -1, -1, 3]

RX_MOYENNE = re.compile(r"^\s*\d{4}\s*-\s*\d{4}")


def ancres(page):
    """Bords droits attendus des 19 colonnes (sans l'annee), ou None."""
    ls = page.splitlines()
    h1 = h2 = None
    for k, l in enumerate(ls):
        if "Année" in l and "Petit" in l and "Grand" in l:
            h1 = l
            for m in ls[k + 1:k + 3]:
                if "ajusté" in m:
                    h2 = m
            break
    if h1 is None or h2 is None:
        return None
    out = []
    for idx, (src, mot, occ) in enumerate(SPEC):
        h = h1 if src == 1 else h2
        pos = -1
        for _ in range(occ):
            k = h.find(mot, pos + 1)
            if k < 0:
                return None
            pos = k
        out.append(pos + len(mot) + BIAIS[idx])
    return out


def nb(tok):
    try:
        return float(tok.replace(" ", "").replace(",", "."))
    except ValueError:
        return None


def jetons(ligne):
    """Nombres -> [(bord_droit, valeur)]. Recolle 1 757 -> 1757 en gardant
    le bord droit d'origine, qui est ce qui aligne les colonnes."""
    bruts = [(m.start(), m.end(), m.group())
             for m in re.finditer(r"\d+(?:,\d+)?", ligne)]
    out = []
    i = 0
    while i < len(bruts):
        d, f, t = bruts[i]
        while (i + 1 < len(bruts)
               and bruts[i + 1][0] == f + 1
               and re.fullmatch(r"\d{3}", bruts[i + 1][2])
               and "," not in t):
            t += bruts[i + 1][2]
            f = bruts[i + 1][1]
            i += 1
        out.append((f, nb(t)))
        i += 1
    return out


def colonnes_de_page(lignes_jetons):
    bords = sorted(b for js in lignes_jetons for b, _ in js)
    if not bords:
        return []
    grappes = [[bords[0]]]
    for b in bords[1:]:
        if b - grappes[-1][-1] <= TOL:
            grappes[-1].append(b)
        else:
            grappes.append([b])
    return [round(sum(g) / len(g)) for g in grappes]


def entete(pages, i):
    for p in (i, i - 1):
        if p < 1:
            continue
        plat = "\n".join(" ".join(l.split())
                         for l in pages[p - 1].splitlines())
        m = RX_TITRE.search(plat)
        if m:
            return {
                "riviere": m.group(1).strip(),
                "seuil_optimal": nb(m.group(2)) if m.group(2) else None,
                "zone": (RX_ZONE.search(plat).group(1)
                         if RX_ZONE.search(plat) else None),
                "no_riviere": (RX_NO.search(plat).group(1)
                               if RX_NO.search(plat) else None),
                "seuil_demo": (nb(RX_DEMO.search(plat).group(1))
                               if RX_DEMO.search(plat) else None),
            }
    return None


def main():
    if not os.path.exists(TXT):
        raise SystemExit("bilan.txt manquant : python ouananiche.py text")
    with open(TXT, encoding="utf-8", errors="replace") as f:
        pages = f.read().split("\f")

    lignes = []
    suspects = []
    courant = None
    page_titre = -9
    hors = 0

    for i in range(1, len(pages) + 1):
        plat = "\n".join(" ".join(l.split())
                         for l in pages[i - 1].splitlines())
        meta = entete(pages, i)
        if meta and RX_TITRE.search(plat):
            courant = meta
            page_titre = i
        if courant is None or i > page_titre + 1:
            continue

        brutes = [l for l in pages[i - 1].splitlines()
                  if RX_ANNEE.match(l) and not RX_MOYENNE.match(l)]
        if not brutes:
            continue

        anc = ancres(pages[i - 1])
        if anc is None:
            suspects.append("p.%-4d %-32s en-tete illisible" % (i, courant["riviere"][:32]))
            continue
        cols = anc
        js = [jetons(l) for l in brutes]

        for j in js:
            if not j:
                continue
            vals = {"annee": j[0][1]}
            for bord, v in j[1:]:
                k = min(range(19), key=lambda c: abs(cols[c] - bord))
                if abs(cols[k] - bord) <= TOL:
                    vals[COLONNES[k + 1]] = v
                else:
                    hors += 1
            ligne = dict(courant)
            ligne["page"] = i
            for c in COLONNES:
                ligne[c] = vals.get(c)
            ligne["annee"] = int(ligne["annee"])
            lignes.append(ligne)

    champs = (["riviere", "zone", "no_riviere", "seuil_optimal",
               "seuil_demo", "page"] + COLONNES)

    with open(CSV_OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=champs)
        w.writeheader()
        w.writerows(lignes)

    if os.path.exists(DB):
        os.remove(DB)
    con = sqlite3.connect(DB)
    con.execute("CREATE TABLE fiche (%s)" % ", ".join(
        "%s %s" % (c, "TEXT" if c in ("riviere", "zone", "no_riviere")
                   else "REAL")
        for c in champs))
    con.executemany(
        "INSERT INTO fiche VALUES (%s)" % ",".join("?" * len(champs)),
        [tuple(l[c] for c in champs) for l in lignes])
    con.execute("CREATE INDEX i1 ON fiche(riviere)")
    con.execute("CREATE INDEX i2 ON fiche(annee)")
    con.commit()
    con.close()

    with open(SUSPECTS, "w", encoding="utf-8") as f:
        f.write("\n".join(suspects))

    rivieres = {l["riviere"] for l in lignes}
    annees = [l["annee"] for l in lignes]
    print("Lignes   : %d" % len(lignes))
    print("Rivieres : %d" % len(rivieres))
    if annees:
        print("Annees   : %d -> %d" % (min(annees), max(annees)))
    print("Pages rejetees : %d -> %s"
          % (len(suspects), os.path.basename(SUSPECTS)))
    print("Jetons hors gabarit (ignores) : %d" % hors)
    manque = sum(1 for l in lignes if l["mont_total"] is None)
    print("Lignes sans montaison totale : %d" % manque)


if __name__ == "__main__":
    main()
