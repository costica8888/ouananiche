import re, sqlite3
pages = open('bilan.txt', encoding='utf-8', errors='replace').read().split('\f')
RX = re.compile(r"^\s*(.+?)\s*\((\d{8})\)\s+([\d,]+)\s+([\d,]+)\s*$")
nb = lambda s: float(s.replace(',', '.'))

rows = []
for i, p in enumerate(pages, 1):
    if "Seuils de conservation pour les autres" not in p:
        continue
    z = re.search(r"zone\s+(Q\d+)", p)
    for l in p.splitlines():
        m = RX.match(l)
        if m:
            rows.append((m.group(1).strip(), z.group(1) if z else None,
                         m.group(2), nb(m.group(3)), nb(m.group(4)), i))

c = sqlite3.connect('fiches.db')
c.execute("DROP TABLE IF EXISTS autre_riviere")
c.execute("""CREATE TABLE autre_riviere (riviere TEXT, zone TEXT,
             no_riviere TEXT, seuil_optimal REAL, seuil_demo REAL, page INTEGER)""")
c.executemany("INSERT INTO autre_riviere VALUES (?,?,?,?,?,?)", rows)
c.commit()
for r in rows:
    print("  %-22s %-4s %s  opt=%.3f" % (r[0], r[1], r[2], r[3]))
print("\n%d rivieres ajoutees (sans serie historique)" % len(rows))
print("total nomme :", c.execute(
    "SELECT COUNT(DISTINCT riviere) FROM fiche WHERE riviere NOT LIKE '%autres%'"
    ).fetchone()[0] + len(rows))
