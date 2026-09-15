#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OUANANICHE - taux de survie en mer (Terre-Neuve-Labrador).
  survie madeleineaux = grilse(X+1) / smolts(X)
Le Quebec ne compte pas ses smolts ; Terre-Neuve oui.
    python survie.py
"""

import os
import sqlite3
import statistics

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tnl.db")


def pente(d):
    if len(d) < 8:
        return None, None
    xs = [x for x, _ in d]
    ys = [y for _, y in d]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    sxy = sum((x - mx) * (y - my) for x, y in d)
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx == 0 or syy == 0:
        return None, None
    return sxy / sxx, sxy / (sxx * syy) ** 0.5


def main():
    c = sqlite3.connect(DB)

    smolt = {}
    for code, an, n in c.execute("""
        SELECT code, CAST(substr(date,1,4) AS INT), SUM(n)
        FROM smolt WHERE n IS NOT NULL GROUP BY code, 2"""):
        smolt[(code, an)] = n

    grilse, large = {}, {}
    for code, an, g, l in c.execute("""
        SELECT code, CAST(substr(date,1,4) AS INT),
               SUM(COALESCE(grilse,0)), SUM(COALESCE(large,0))
        FROM adulte GROUP BY code, 2"""):
        grilse[(code, an)] = g
        large[(code, an)] = l

    noms = dict(c.execute("SELECT code, nom FROM riviere"))

    print("=== survie 1HM par riviere (grilse X+1 / smolts X) ===")
    print("%-30s %4s %8s %8s %8s" % ("RIVIERE", "N", "MED.", "MIN", "MAX"))
    par_riv, global_ = {}, {}
    for (code, an), s in smolt.items():
        if s and s > 50:
            g = grilse.get((code, an + 1))
            if g:
                par_riv.setdefault(code, []).append((an, 100.0 * g / s))
                global_.setdefault(an, []).append(100.0 * g / s)

    for code, d in sorted(par_riv.items(),
                          key=lambda x: -statistics.median(y for _, y in x[1])):
        if len(d) < 5:
            continue
        v = [y for _, y in d]
        print("%-30s %4d %7.1f%% %7.1f%% %7.1f%%"
              % ((noms.get(code) or code)[:30], len(d),
                 statistics.median(v), min(v), max(v)))

    print("\n=== tendance globale de la survie ===")
    print("%6s %8s %5s" % ("ANNEE", "SURVIE", "RIV."))
    serie = []
    for an in sorted(global_):
        v = global_[an]
        m = statistics.median(v)
        serie.append((an, m))
        print("%6d %7.1f%% %5d" % (an, m, len(v)))

    p, r = pente(serie)
    if p is not None:
        print("\npente : %+.3f point/an   r = %+.2f" % (p, r))
        d5 = statistics.mean(y for _, y in serie[:5])
        f5 = statistics.mean(y for _, y in serie[-5:])
        print("5 premieres annees : %.1f%%" % d5)
        print("5 dernieres annees : %.1f%%" % f5)
        if d5:
            print("variation : %+.0f%%" % (100 * (f5 / d5 - 1)))

    print("\n=== volumes : smolts descendus vs adultes revenus ===")
    print("%6s %10s %10s %10s" % ("ANNEE", "SMOLTS", "GRILSE", "LARGE"))
    for an in range(2000, 2026):
        s = sum(v for (cc, aa), v in smolt.items() if aa == an and v)
        g = sum(v for (cc, aa), v in grilse.items() if aa == an and v)
        l = sum(v for (cc, aa), v in large.items() if aa == an and v)
        if s or g:
            print("%6d %10.0f %10.0f %10.0f" % (an, s, g, l))


if __name__ == "__main__":
    main()
