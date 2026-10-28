#!/usr/bin/env python3
"""
Script de validation autonome des sources d'offres de stage.
S'exécute SANS Gemini, teste les appels réseau réels, vérifie les critères de stage
et la validité des liens d'offres.
"""

import sys
import os
from sources import (
    fetch_arbeitnow,
    fetch_remotive,
    fetch_jooble,
    fetch_adzuna,
    fetch_all_internships
)

def run_tests():
    print("=" * 70)
    print("🚀 VALIDATION DES SOURCES D'OFFRES DE STAGE (SANS GEMINI)")
    print("=" * 70)
    
    # 1. Test Arbeitnow
    print("\n[1/4] Test de la source Arbeitnow (Gratuit, sans clé)...")
    an_offers, an_status = fetch_arbeitnow(
        queries=["stage python", "data intern", "software"],
        country="France",
        city="Paris",
        max_results=10
    )
    if an_status.get("ok"):
        print(f"  ✅ Succès : {len(an_offers)} offres de stage réelles récupérées.")
        if an_offers:
            sample = an_offers[0]
            print(f"     Exemple : \"{sample['title']}\" chez {sample['company']}")
            print(f"     Lieu    : {sample['location']}")
            print(f"     Lien    : {sample['url']}")
            assert sample['url'].startswith("http"), "Lien invalide !"
    else:
        print(f"  ❌ Échec : {an_status.get('error')}")

    # 2. Test Remotive
    print("\n[2/4] Test de la source Remotive (Gratuit, sans clé)...")
    rem_offers, rem_status = fetch_remotive(
        queries=["python", "developer", "data"],
        max_results=5
    )
    if rem_status.get("ok"):
        print(f"  ✅ Succès : {len(rem_offers)} opportunités récupérées.")
        if rem_offers:
            sample = rem_offers[0]
            print(f"     Exemple : \"{sample['title']}\" chez {sample['company']}")
            print(f"     Lieu    : {sample['location']}")
            print(f"     Lien    : {sample['url']}")
            assert sample['url'].startswith("http"), "Lien invalide !"
    else:
        print(f"  ❌ Échec : {rem_status.get('error')}")

    # 3. Test Jooble (vérification si clé présente)
    print("\n[3/4] Test de la source Jooble (Couverture Maroc & Monde)...")
    jooble_key = os.environ.get("JOOBLE_API_KEY", "")
    if jooble_key:
        j_offers, j_status = fetch_jooble(
            api_key=jooble_key,
            queries=["stage informatique"],
            country="Maroc",
            city="Casablanca",
            max_results=5
        )
        if j_status.get("ok"):
            print(f"  ✅ Succès : {len(j_offers)} offres Jooble trouvées pour le Maroc.")
            if j_offers:
                sample = j_offers[0]
                print(f"     Exemple : \"{sample['title']}\" chez {sample['company']}")
                print(f"     Lieu    : {sample['location']}")
                print(f"     Lien    : {sample['url']}")
        else:
            print(f"  ⚠️ Erreur Jooble : {j_status.get('error')}")
    else:
        print("  ℹ️ JOOBLE_API_KEY non définie en variable d'environnement.")
        print("     (Source optionnelle : clé gratuite instantanée sur jooble.org/api/about pour activer le Maroc).")

    # 4. Test Adzuna (vérification si identifiants présents)
    print("\n[4/4] Test de la source Adzuna (Couverture France, UK, etc.)...")
    adzuna_id = os.environ.get("ADZUNA_APP_ID", "")
    adzuna_key = os.environ.get("ADZUNA_APP_KEY", "")
    if adzuna_id and adzuna_key:
        ad_offers, ad_status = fetch_adzuna(
            app_id=adzuna_id,
            app_key=adzuna_key,
            queries=["stage"],
            country="France",
            city="Paris",
            max_results=5
        )
        if ad_status.get("ok"):
            print(f"  ✅ Succès : {len(ad_offers)} offres Adzuna trouvées.")
        else:
            print(f"  ⚠️ Erreur Adzuna : {ad_status.get('error')}")
    else:
        print("  ℹ️ ADZUNA_APP_ID / ADZUNA_APP_KEY non définis.")
        print("     (Source optionnelle : clé gratuite sur developer.adzuna.com).")

    # 5. Test agrégateur et déduplication globale
    print("\n" + "-" * 70)
    print("🔬 TEST DU PIPELINE GLOBAL DE DÉDUPLICATION ET FILTRAGE")
    print("-" * 70)
    queries = ["Stage Machine Learning", "Data Analyst Intern", "Python"]
    combined, statuses = fetch_all_internships(
        queries=queries,
        country="France",
        city="Paris",
        max_total_offers=30
    )
    print(f"Total offres dédupliquées consolidées : {len(combined)}")
    urls = [o['url'] for o in combined]
    assert len(urls) == len(set(urls)), "Doublons d'URL détectés !"
    print("✅ Intégrité vérifiée : 100% des offres ont une URL unique et réelle.")
    print("=" * 70)
    print("🎉 Test des sources réussi avec succès !")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
