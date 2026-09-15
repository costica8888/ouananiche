#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OUANANICHE - ratio madeleineaux / redibermarins, 1984-2025.
La proportion de GRANDS saumons baisse-t-elle avec le temps ?
    python ratio.py
"""

import sqlite3
import statistics

DB = "fiches.db"


def pente(paires):
    """Regression lineaire simple -> (pente par an, r)."""
    if len(paires) < 8:
        return None, None
    xs = [p[0] for p in paires]
    ys = [p[1] for p in paires]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    sxy = sum((x - mx) * (y - my) for x, y in paires)
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx == 0 or syy == 0:
        return None, None
    return sxy / sxx, sxy / (sxx * syy) ** 0.5


def main():
    c = sqlite3.connect(DB)

    print("=== 1. PROVINCIAL : part des redibermarins par annee ===")
    print("%6s %10s %10s %8s  %s" % ("ANNEE", "MAD.", "RED.", "% RED.", "RIV."))
    prov = []
    for r in c.execute("""
        SELECT CAST(annee AS INT), SUM(mont_mad), SUM(mont_red),
               COUNT(DISTINCT riviere)
        FROM fiche
        WHERE mont_mad IS NOT NULL AND mont_red IS NOT NULL
        GROUP BY annee ORDER BY annee"""):
        an, mad, red, n = r
        tot = (mad or 0) + (red or 0)
        if tot <= 0:
            continue
        pct = 100.0 * red / tot
        prov.append((an, pct))
        print("%6d %10.0f %10.0f %7.1f%%  %d" % (an, mad, red, pct, n))

    p, rr = pente(prov)
    if p is not None:
        print("\ntendance provinciale : %+.2f point de %% par an (r=%+.2f)"
              % (p, rr))
        print("soit %+.0f points sur 42 ans" % (p * 42))

    print("\n=== 2. PAR RIVIERE (>= 15 annees de donnees) ===")
    print("%-30s %4s %8s %8s %7s %6s"
          % ("RIVIERE", "N", "DEBUT", "FIN", "PENTE", "r"))
    res = []
    for (riv, zone) in c.execute("""
        SELECT riviere, zone FROM fiche
        WHERE mont_mad IS NOT NULL AND mont_red IS NOT NULL
        GROUP BY riviere, zone HAVING COUNT(*) >= 15"""):
        d = []
        for an, mad, red in c.execute("""
            SELECT CAST(annee AS INT), mont_mad, mont_red FROM fiche
            WHERE riviere=? AND zone=? AND mont_mad IS NOT NULL
              AND mont_red IS NOT NULL ORDER BY annee""", (riv, zone)):
            t = mad + red
            if t > 0:
                d.append((an, 100.0 * red / t))
        if len(d) < 15:
            continue
        pe, rr2 = pente(d)
        if pe is None:
            continue
        deb = statistics.mean(y for _, y in d[:5])
        fin = statistics.mean(y for _, y in d[-5:])
        res.append((riv, len(d), deb, fin, pe, rr2))

    for riv, n, deb, fin, pe, rr2 in sorted(res, key=lambda x: x[4]):
        print("%-30s %4d %7.1f%% %7.1f%% %+6.2f %+6.2f"
              % (riv[:30], n, deb, fin, pe, rr2))

    if res:
        baisse = sum(1 for x in res if x[4] < 0)
        print("\n%d rivieres sur %d en baisse de %% redibermarins"
              % (baisse, len(res)))
        print("pente mediane : %+.2f point par an"
              % statistics.median(x[4] for x in res))

    print("\n=== 3. AVANT / APRES le plan de gestion 2016 ===")
    for lab, cond in (("2006-2015", "annee BETWEEN 2006 AND 2015"),
                      ("2016-2025", "annee BETWEEN 2016 AND 2025")):
        r = c.execute("""SELECT SUM(mont_mad), SUM(mont_red) FROM fiche
                         WHERE mont_mad IS NOT NULL AND mont_red IS NOT NULL
                           AND %s""" % cond).fetchone()
        if r[0] and r[1]:
            t = r[0] + r[1]
            print("  %-10s mad=%8.0f  red=%8.0f  red=%5.1f%%"
                  % (lab, r[0], r[1], 100.0 * r[1] / t))


if __name__ == "__main__":
    main()
