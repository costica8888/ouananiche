#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OUANANICHE - carte des rivieres a saumon.
Genere carte.html : Leaflet + fond hydrographique GRHQ (WMS du MRNF).
    python carte.py
"""

import os
import json
import sqlite3

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "fiches.db")
OUT = os.path.join(BASE, "carte.html")

WMS = ("https://servicescarto.mrnf.gouv.qc.ca/pes/services/Territoire/"
       "GRHQ_WMS/MapServer/WMSServer")


def donnees():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    rows = c.execute("""
        SELECT co.riviere, co.zone, co.lat, co.lon,
               f.seuil_optimal, f.oeufs_millions, f.mont_total,
               f.repro_total, f.jours_peche
        FROM coord co
        LEFT JOIN fiche f
          ON f.riviere = co.riviere AND f.zone = co.zone AND f.annee = 2025
    """).fetchall()

    moy = {}
    for r in c.execute("""
        SELECT riviere, zone,
               AVG(oeufs_millions * 100.0 / seuil_optimal) p, COUNT(*) n
        FROM fiche WHERE annee >= 2021 AND oeufs_millions IS NOT NULL
          AND seuil_optimal > 0
        GROUP BY riviere, zone"""):
        moy[(r[0], r[1])] = (r[2], r[3])

    out = []
    for r in rows:
        d = dict(r)
        so, oe = d.get("seuil_optimal"), d.get("oeufs_millions")
        d["pct"] = round(100.0 * oe / so, 1) if (so and oe) else None
        m = moy.get((d["riviere"], d["zone"]))
        d["pct5"] = round(m[0], 1) if m and m[0] else None
        out.append(d)
    return out


HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>OUANANICHE - rivieres a saumon du Quebec</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  html,body{margin:0;height:100%%;font-family:system-ui,-apple-system,sans-serif}
  #map{height:100%%}
  .legende{background:#fff;padding:9px 11px;border-radius:5px;
           box-shadow:0 1px 6px rgba(0,0,0,.35);font-size:12px;line-height:1.7}
  .legende b{display:block;margin-bottom:5px;font-size:13px}
  .pastille{display:inline-block;width:11px;height:11px;border-radius:50%%;
            margin-right:7px;border:1px solid #333;vertical-align:-1px}
  .popup h3{margin:0 0 6px;font-size:14px}
  .popup table{border-collapse:collapse;font-size:12px}
  .popup td{padding:1px 9px 1px 0}
  .popup td:last-child{text-align:right;font-variant-numeric:tabular-nums}
</style>
</head>
<body>
<div id="map"></div>
<script>
var RIV = %s;

function couleur(p){
  if (p === null) return '#9e9e9e';
  if (p >= 100) return '#1a9850';
  if (p >= 60)  return '#a6d96a';
  if (p >= 30)  return '#fdae61';
  return '#d73027';
}
function rayon(m){ return m ? Math.max(6, Math.min(20, Math.sqrt(m)/3)) : 6; }
function n(v, d){ return (v === null || v === undefined) ? '\\u2014' : v.toFixed(d); }

var map = L.map('map').setView([49.0, -66.0], 6);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; OpenStreetMap', maxZoom: 14
}).addTo(map);

var hydro = L.tileLayer.wms('%s', {
  layers: '1', format: 'image/png', transparent: true,
  version: '1.3.0', attribution: 'GRHQ / MRNF', opacity: 0.75
});

RIV.forEach(function(r){
  var m = L.circleMarker([r.lat, r.lon], {
    radius: rayon(r.mont_total), fillColor: couleur(r.pct),
    color: '#222', weight: 1, fillOpacity: 0.82
  }).addTo(map);
  m.bindPopup(
    '<div class="popup"><h3>' + r.riviere + '</h3><table>' +
    '<tr><td>Zone</td><td>' + (r.zone || '\\u2014') + '</td></tr>' +
    '<tr><td>Montaison 2025</td><td>' + n(r.mont_total, 0) + '</td></tr>' +
    '<tr><td>Reproducteurs</td><td>' + n(r.repro_total, 0) + '</td></tr>' +
    '<tr><td>\\u0152ufs (M)</td><td>' + n(r.oeufs_millions, 2) + '</td></tr>' +
    '<tr><td>Seuil optimal (M)</td><td>' + n(r.seuil_optimal, 2) + '</td></tr>' +
    '<tr><td><b>%% du seuil 2025</b></td><td><b>' +
      (r.pct === null ? '\\u2014' : r.pct + ' %%') + '</b></td></tr>' +
    '<tr><td>Moyenne 2021-2025</td><td>' +
      (r.pct5 === null ? '\\u2014' : r.pct5 + ' %%') + '</td></tr>' +
    '<tr><td>Jours-peche</td><td>' + n(r.jours_peche, 0) + '</td></tr>' +
    '</table></div>');
  m.bindTooltip(r.riviere, {direction: 'top'});
});

L.control.layers(null, {'R\\u00e9seau hydrographique (GRHQ)': hydro},
                 {collapsed: false}).addTo(map);

var lg = L.control({position: 'bottomright'});
lg.onAdd = function(){
  var d = L.DomUtil.create('div', 'legende');
  d.innerHTML =
    '<b>%% du seuil de conservation (2025)</b>' +
    '<span class="pastille" style="background:#1a9850"></span>100 %% et plus<br>' +
    '<span class="pastille" style="background:#a6d96a"></span>60 \\u2013 99 %%<br>' +
    '<span class="pastille" style="background:#fdae61"></span>30 \\u2013 59 %%<br>' +
    '<span class="pastille" style="background:#d73027"></span>moins de 30 %%<br>' +
    '<span class="pastille" style="background:#9e9e9e"></span>sans donn\\u00e9e<br>' +
    '<i>Taille du cercle = montaison 2025</i>';
  return d;
};
lg.addTo(map);
</script>
</body>
</html>
"""


def main():
    riv = donnees()
    html = HTML % (json.dumps(riv, ensure_ascii=False), WMS)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    avec = sum(1 for r in riv if r["pct"] is not None)
    print("carte.html genere : %d rivieres, %d avec %% du seuil 2025"
          % (len(riv), avec))


if __name__ == "__main__":
    main()
