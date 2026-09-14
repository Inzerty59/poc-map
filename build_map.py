#!/usr/bin/env python3
"""Genere france_map.html a partir de entreprises.json : carte de France (departements,
sans fond de rue), couleurs Vitamine T, clusters par departement (zoom -> pins),
popup = fiche entreprise (donnees SIRENE officielles, pas de fiche Google)."""
import json
import os

ORANGE = "#EF7D00"
LOGOS_DIR = "logos"

FORME_JURIDIQUE = {
    "5710": "SAS",
    "5720": "SASU",
    "5499": "SARL",
    "5498": "EURL",
    "5202": "SNC",
}

# tranches d'effectif salarie INSEE (code officiel -> libelle)
EFFECTIF = {
    "NN": "non employeuse",
    "00": "0 salarie",
    "01": "1 a 2 salaries",
    "02": "3 a 5 salaries",
    "03": "6 a 9 salaries",
    "11": "10 a 19 salaries",
    "12": "20 a 49 salaries",
    "21": "50 a 99 salaries",
    "22": "100 a 199 salaries",
    "31": "200 a 249 salaries",
    "32": "250 a 499 salaries",
    "41": "500 a 999 salaries",
    "42": "1000 a 1999 salaries",
    "51": "2000 a 4999 salaries",
    "52": "5000 a 9999 salaries",
    "53": "10000 salaries et plus",
}

TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>Fiches entreprises</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<style>
  html, body { margin: 0; height: 100%; font-family: -apple-system, Segoe UI, sans-serif; }
  #map { width: 100%; height: 100%; background: #ffffff; }
  .leaflet-container { background: #ffffff; }

  .dept-count {
    background: __ORANGE__;
    color: #fff;
    border: 2px solid #fff;
    border-radius: 50%;
    width: 34px; height: 34px;
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 0.9rem;
    box-shadow: 0 1px 4px rgba(0,0,0,.35);
    cursor: pointer;
  }

  .fiche { min-width: 240px; }
  .fiche h3 { margin: 0 0 4px; font-size: 1rem; }
  .fiche .adresse { color: #555; font-size: 0.85rem; margin-bottom: 6px; }
  .fiche .badge { display: inline-block; background: __ORANGE__; color: #fff; border-radius: 10px;
                  padding: 2px 8px; font-size: 0.75rem; margin-bottom: 6px; }
  .fiche table { font-size: 0.85rem; border-collapse: collapse; margin-top: 4px; }
  .fiche table td { padding: 1px 6px 1px 0; vertical-align: top; }
  .fiche table td:first-child { color: #777; white-space: nowrap; }
  .fiche a { color: __ORANGE__; }
  .fiche a.gmaps-btn {
    margin-top: 8px; display: block; width: 100%; box-sizing: border-box;
    background: __ORANGE__; color: #fff; border: none; border-radius: 4px;
    padding: 6px 8px; font-size: 0.8rem; cursor: pointer;
    text-align: center; text-decoration: none;
  }
  .gmaps-btn:hover { opacity: 0.9; }

  .logo-marker {
    width: 56px; height: 56px;
    border-radius: 50%;
    background: #fff;
    border: 3px solid __ORANGE__;
    box-shadow: 0 1px 4px rgba(0,0,0,.35);
    object-fit: contain;
    padding: 4px;
  }
</style>
</head>
<body>
<div id="map"></div>
<script>
const entreprises = __DATA__;
const ORANGE = "__ORANGE__";
const ZOOM_THRESHOLD = 8;

const map = L.map('map', { zoomControl: true, attributionControl: false });

const clusterLayer = L.layerGroup();
const pinLayer = L.layerGroup();

function deptStyle() {
  return { color: ORANGE, weight: 1, fillColor: '#ffffff', fillOpacity: 1 };
}

function makeFicheHtml(e) {
  const site = e.site_web ? `<div><a href="${e.site_web}" target="_blank" rel="noopener">${e.site_web}</a></div>` : '';
  const tel = e.telephone ? `<div>${e.telephone}</div>` : '';
  const mereRow = e.maison_mere ? `<tr><td>Maison mere</td><td>${e.maison_mere}</td></tr>` : '';
  const gmapsUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${e.enseigne} ${e.adresse} ${e.code_postal} ${e.ville}`)}`;
  return `
    <div class="fiche">
      <span class="badge">SIREN ${e.siren}</span>
      <h3>${e.enseigne}</h3>
      <div class="adresse">${e.adresse}<br>${e.code_postal} ${e.ville}</div>
      ${tel}${site}
      <table>
        <tr><td>Activite (NAF)</td><td>${e.activite}</td></tr>
        <tr><td>Effectif</td><td>${e.effectif_label}</td></tr>
        <tr><td>Creation</td><td>${e.date_creation}</td></tr>
        <tr><td>Forme juridique</td><td>${e.forme_juridique_label}</td></tr>
        ${mereRow}
      </table>
      <a class="gmaps-btn" href="${gmapsUrl}" target="_blank" rel="noopener">Voir sur Google Maps</a>
    </div>`;
}

// regroupe les entreprises qui partagent exactement la meme adresse (meme
// immeuble/siege) sous un seul marker, avec chaque fiche listee dans le popup
const byLocation = {};
entreprises.forEach(e => {
  if (!e.lat || !e.lon) return;
  const key = e.lat.toFixed(5) + ',' + e.lon.toFixed(5);
  (byLocation[key] = byLocation[key] || []).push(e);
});

Object.values(byLocation).forEach(list => {
  const html = list.map(makeFicheHtml).join('<hr style="margin:8px 0;border:none;border-top:1px solid #eee;">');
  // logo de la 1ere entreprise du lot si dispo, sinon pin bleu par defaut
  const logo = list.find(e => e.logo)?.logo;
  const options = logo ? {
    icon: L.icon({ iconUrl: logo, iconSize: [56, 56], iconAnchor: [28, 28], popupAnchor: [0, -28], className: 'logo-marker' })
  } : {};
  L.marker([list[0].lat, list[0].lon], options).bindPopup(html).addTo(pinLayer);
});

fetch('https://cdn.jsdelivr.net/gh/gregoiredavid/france-geojson@master/departements.geojson')
  .then(r => r.json())
  .then(geo => {
    // Corse retiree (pas utile pour ce POC) : filtre les departements 2A/2B
    geo.features = geo.features.filter(f => f.properties.code !== '2A' && f.properties.code !== '2B');

    const deptLayer = L.geoJSON(geo, {
      style: deptStyle,
      onEachFeature: (feature, layer) => {
        layer.on('mouseover', () => layer.setStyle({ fillColor: ORANGE, fillOpacity: 0.35 }));
        layer.on('mouseout', () => layer.setStyle(deptStyle()));
      }
    }).addTo(map);
    deptLayer.bringToBack();
    map.invalidateSize();
    map.fitBounds(deptLayer.getBounds());

    const byDept = {};
    entreprises.forEach(e => {
      if (!e.lat || !e.lon) return;
      (byDept[e.departement] = byDept[e.departement] || []).push(e);
    });

    deptLayer.eachLayer(layer => {
      const code = layer.feature.properties.code;
      const list = byDept[code];
      if (!list) return;
      const center = layer.getBounds().getCenter();
      const icon = L.divIcon({
        className: '',
        html: `<div class="dept-count">${list.length}</div>`,
        iconSize: [34, 34]
      });
      const marker = L.marker(center, { icon }).addTo(clusterLayer);
      marker.on('click', () => map.fitBounds(layer.getBounds(), { maxZoom: 10 }));
    });

    clusterLayer.addTo(map);
  });

map.on('zoomend', () => {
  const zoomedIn = map.getZoom() >= ZOOM_THRESHOLD;
  if (zoomedIn) {
    if (map.hasLayer(clusterLayer)) map.removeLayer(clusterLayer);
    if (!map.hasLayer(pinLayer)) map.addLayer(pinLayer);
  } else {
    if (map.hasLayer(pinLayer)) map.removeLayer(pinLayer);
    if (!map.hasLayer(clusterLayer)) map.addLayer(clusterLayer);
  }
});
</script>
</body>
</html>
"""


def find_logos():
    """Mappe SIRET ou SIREN -> chemin relatif du logo (logos/<siret-ou-siren>.<ext>),
    si present. Accepte les deux : un logo nomme par SIREN s'applique a tous
    les etablissements de cette entreprise."""
    if not os.path.isdir(LOGOS_DIR):
        return {}
    logos = {}
    for filename in os.listdir(LOGOS_DIR):
        key, ext = os.path.splitext(filename)
        if ext.lower() in (".png", ".jpg", ".jpeg", ".ico", ".svg"):
            logos[key] = f"{LOGOS_DIR}/{filename}"
    return logos


def main():
    data = json.load(open("entreprises.json"))
    entreprises = data["entreprises"]
    logos = find_logos()
    for e in entreprises:
        tranche = e.get("effectif_tranche") or ""
        e["effectif_label"] = EFFECTIF.get(tranche, tranche or "inconnu")
        e["forme_juridique_label"] = FORME_JURIDIQUE.get(e.get("forme_juridique"), e.get("forme_juridique") or "")
        e["logo"] = logos.get(e["siret"]) or logos.get(e["siren"])

    html = TEMPLATE.replace("__DATA__", json.dumps(entreprises, ensure_ascii=False))
    html = html.replace("__ORANGE__", ORANGE)
    with open("france_map.html", "w") as f:
        f.write(html)
    print(f"france_map.html genere ({len(entreprises)} entreprises)")


if __name__ == "__main__":
    main()
