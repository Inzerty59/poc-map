#!/usr/bin/env python3
"""POC: recuperer les offres d'emploi des SIAE filiales via l'API emplois.inclusion.

Usage: python3 scan_siaes.py <SIREN> [<SIREN> ...] [--departements 75,92,...]

Sans --departements, scanne tous les departements francais (long, respecte le
rate limit 12 req/min sans token).
"""
import argparse
import json
import sys
import time
import urllib.parse
import urllib.request

API_BASE = "https://emplois.inclusion.beta.gouv.fr/api/v1/siaes/"
RATE_LIMIT_SLEEP = 5.1  # 12 req/min sans token -> 1 req/5s min
GEOCODE_URL = "https://api-adresse.data.gouv.fr/search/"

METRO = [f"{d:02d}" for d in range(1, 96) if d != 20] + ["2A", "2B"]
DOM = ["971", "972", "973", "974", "975", "976"]
ALL_DEPARTEMENTS = METRO + DOM


def fetch_page(url, retries=3):
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                print(f"  429 rate limit, pause 15s...", file=sys.stderr)
                time.sleep(15)
                continue
            raise


def geocode(adresse, code_postal, ville):
    """Geocode via l'API adresse gouv (BAN). Retourne (lat, lon) ou (None, None)."""
    q = f"{adresse} {ville}".strip()
    params = urllib.parse.urlencode({"q": q, "postcode": code_postal, "limit": 1})
    try:
        with urllib.request.urlopen(f"{GEOCODE_URL}?{params}", timeout=15) as r:
            data = json.load(r)
        coords = data["features"][0]["geometry"]["coordinates"]
        return coords[1], coords[0]  # lat, lon
    except Exception as e:
        print(f"  geocodage echoue pour '{q}': {e}", file=sys.stderr)
        return None, None


def scan_departement(dep):
    """Retourne toutes les structures (avec pagination) pour un departement."""
    url = f"{API_BASE}?departement={dep}"
    structures = []
    while url:
        data = fetch_page(url)
        structures.extend(data["results"])
        url = data["next"]
        if url:
            time.sleep(RATE_LIMIT_SLEEP)
    return structures


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sirens", nargs="+", help="Liste de SIREN (9 chiffres) a matcher")
    ap.add_argument("--departements", help="Liste separee par des virgules, ex: 75,92")
    ap.add_argument("--output", help="Fichier JSON de sortie (defaut: stdout)")
    args = ap.parse_args()

    deps = args.departements.split(",") if args.departements else ALL_DEPARTEMENTS
    sirens = set(args.sirens)

    matches = []
    for i, dep in enumerate(deps):
        print(f"[{i+1}/{len(deps)}] departement {dep}...", file=sys.stderr)
        try:
            structures = scan_departement(dep)
        except Exception as e:
            print(f"  erreur dept {dep}: {e}", file=sys.stderr)
            continue
        for s in structures:
            siren = s["siret"][:9]
            if siren in sirens:
                offres = [p for p in s["postes"] if p.get("recrutement_ouvert") == "True"]
                lat, lon = geocode(s["addresse_ligne_1"], s["code_postal"], s["ville"])
                time.sleep(1)  # rate limit poli sur l'API de geocodage
                matches.append({
                    "siren": siren,
                    "siret": s["siret"],
                    "raison_sociale": s["raison_sociale"],
                    "enseigne": s.get("enseigne") or s["raison_sociale"],
                    "adresse": s.get("addresse_ligne_1", ""),
                    "code_postal": s.get("code_postal", ""),
                    "ville": s["ville"],
                    "departement": s["departement"],
                    "telephone": s.get("telephone", ""),
                    "site_web": s.get("site_web", ""),
                    "lat": lat,
                    "lon": lon,
                    "nb_postes_ouverts": len(offres),
                    "postes": [
                        {
                            "titre": p["appellation_modifiee"],
                            "type_contrat": p.get("type_contrat", ""),
                            "description": p.get("description", ""),
                            "lieu": (p.get("lieu") or {}).get("nom", s["ville"]),
                        }
                        for p in offres
                    ],
                })
        if i < len(deps) - 1:
            time.sleep(RATE_LIMIT_SLEEP)

    output = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "structures": matches}
    if args.output:
        with open(args.output, "w") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
    else:
        print(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"\n{len(matches)} structure(s) trouvee(s) pour {len(sirens)} SIREN(s)", file=sys.stderr)


if __name__ == "__main__":
    main()
