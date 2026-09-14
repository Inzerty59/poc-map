#!/usr/bin/env python3
"""POC: recupere la fiche entreprise via l'API officielle recherche-entreprises.api.gouv.fr
(gratuite, pas de cle). Un SIREN pointe le siege social ; un SIRET (14 chiffres)
pointe l'etablissement precis (agence/antenne).

Usage: python3 fetch_entreprises.py <SIREN|SIRET> [<SIREN|SIRET> ...] --output entreprises.json
"""
import argparse
import json
import time
import urllib.request

API_URL = "https://recherche-entreprises.api.gouv.fr/search"

# telephone/site web recuperes manuellement via l'API emplois.inclusion (non
# fournis par l'API SIRENE) pour enrichir la fiche quand on les connait.
CONTACTS = {
    "83508242100016": {"telephone": "03 20 61 70 70", "site_web": "https://inzerty.fr/"},
    "83508242100024": {"telephone": "06.47.23.20.32", "site_web": "http://inzerty.fr"},
}


def fetch_entreprise(identifiant):
    """identifiant: SIREN (9 chiffres, cible le siege) ou SIRET (14 chiffres,
    cible precisement cet etablissement, meme si ce n'est pas le siege)."""
    siren = identifiant[:9]
    url = f"{API_URL}?q={identifiant}"
    with urllib.request.urlopen(url, timeout=15) as r:
        data = json.load(r)
    results = [res for res in data.get("results", []) if res["siren"] == siren]
    if not results:
        return None
    e = results[0]

    is_siret = len(identifiant) == 14
    if is_siret and identifiant != e["siege"]["siret"]:
        matches = [m for m in e.get("matching_etablissements", []) if m["siret"] == identifiant]
        etab = matches[0] if matches else e["siege"]
    else:
        etab = e["siege"]

    siret = etab["siret"]
    contact = CONTACTS.get(siret, {})
    dirigeant_principal = next(
        (d for d in e.get("dirigeants", []) if d.get("type_dirigeant") == "personne morale"
         and "president" in (d.get("qualite") or "").lower().replace("é", "e")),
        None,
    )
    # matching_etablissements ne renvoie pas "departement" (contrairement a siege) ->
    # on le derive du code postal.
    code_postal = etab.get("code_postal", "")
    departement = etab.get("departement") or (
        code_postal[:3] if code_postal[:2] == "97" else code_postal[:2]
    )

    return {
        "siren": siren,
        "siret": siret,
        "nom": e.get("nom_raison_sociale") or e.get("nom_complet"),
        "enseigne": (etab.get("liste_enseignes") or [e.get("nom_raison_sociale")])[0],
        "adresse": etab.get("adresse", ""),
        "code_postal": code_postal,
        "ville": etab.get("libelle_commune", ""),
        "departement": departement,
        "lat": float(etab["latitude"]) if etab.get("latitude") else None,
        "lon": float(etab["longitude"]) if etab.get("longitude") else None,
        "activite": e.get("activite_principale", ""),
        "effectif_tranche": e.get("tranche_effectif_salarie", ""),
        "date_creation": e.get("date_creation", ""),
        "forme_juridique": e.get("nature_juridique", ""),
        "maison_mere": dirigeant_principal["denomination"] if dirigeant_principal else None,
        "telephone": contact.get("telephone", ""),
        "site_web": contact.get("site_web", ""),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sirens", nargs="+")
    ap.add_argument("--output", default="entreprises.json")
    args = ap.parse_args()

    entreprises = []
    for siren in args.sirens:
        e = fetch_entreprise(siren)
        if e:
            entreprises.append(e)
        else:
            print(f"  SIREN {siren} introuvable")
        time.sleep(0.5)

    output = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "entreprises": entreprises}
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"{len(entreprises)} entreprise(s) -> {args.output}")


if __name__ == "__main__":
    main()
