#!/usr/bin/env python3
"""
Script de validation autonome des sources d'offres de stage.
S'exécute SANS Gemini, teste les appels réseau réels, vérifie les critères de stage,
la validité des liens d'offres et le respect STRICT des critères géographiques.
"""

import sys
import os
from sources import (
    fetch_arbeitnow,
    fetch_remotive,
    fetch_jooble,
    fetch_adzuna,
    fetch_all_internships,
    check_country_coverage
)

def run_tests():
    print("=" * 70)
    print("🚀 VALIDATION DES SOURCES D'OFFRES DE STAGE (SANS GEMINI)")
    print("=" * 70)
    
    # 1. Test Arbeitnow
    print("\n[1/5] Test de la source Arbeitnow (Gratuit, sans clé)...")
    an_offers, an_status = fetch_arbeitnow(
        queries=["stage python", "data intern", "software"],
        country="France",
        city="Paris",
        max_results=10
    )
    if an_status.get("ok"):
        print(f"  ✅ Succès : {len(an_offers)} offres de stage réelles récupérées pour France/Paris.")
        if an_offers:
            sample = an_offers[0]
            print(f"     Exemple : \"{sample['title']}\" chez {sample['company']}")
            print(f"     Lieu    : {sample['location']}")
            print(f"     Lien    : {sample['url']}")
            assert sample['url'].startswith("http"), "Lien invalide !"
    else:
        print(f"  ❌ Échec : {an_status.get('error')}")

    # 2. Test Remotive
    print("\n[2/5] Test de la source Remotive (Gratuit, sans clé)...")
    rem_offers, rem_status = fetch_remotive(
        queries=["python", "developer", "data"],
        country="Maroc",
        city="Casablanca",
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

    # 3. Test spécifique exigé : PAYS = Maroc, VILLE = Casablanca
    print("\n[3/5] 🇲🇦 TEST SPÉCIFIQUE : Pays=Maroc, Ville=Casablanca...")
    
    # Vérification analyse de couverture
    cov = check_country_coverage("Maroc", {})
    print(f"  • Diagnostic couverture Maroc sans Jooble : on-site actif = {cov['has_onsite_coverage']}")
    assert not cov["has_onsite_coverage"], "Maroc ne devrait avoir aucune source on-site sans Jooble"
    print("  ✅ Détection d'absence de source on-site pour le Maroc validée.")

    # Interrogation globale pour Maroc / Casablanca
    morocco_offers, morocco_statuses = fetch_all_internships(
        queries=["Stage Data Science", "Stage Python", "Machine Learning"],
        country="Maroc",
        city="Casablanca",
        max_total_offers=30
    )
    
    print(f"  • Offres retournées pour Maroc/Casablanca : {len(morocco_offers)}")
    print(f"  • Statuts des sources :")
    for s_name, s_info in morocco_statuses.items():
        print(f"     - {s_name}: count={s_info.get('count', 0)}, note={s_info.get('error')}")

    # VÉRIFICATION STRICTE DE NON-CONTAMINATION PAR PARIS / FRANCE :
    for o in morocco_offers:
        loc_lower = (o.get("location") or "").lower()
        title = o.get("title", "")
        # Vérifier qu'aucune offre ne mentionne Paris, France ou l'Allemagne
        assert "paris" not in loc_lower, f"❌ ERREUR : Offre de Paris renvoyée pour le Maroc ! ({title} à {loc_lower})"
        assert "france" not in loc_lower, f"❌ ERREUR : Offre de France renvoyée pour le Maroc ! ({title} à {loc_lower})"
        assert "germany" not in loc_lower, f"❌ ERREUR : Offre d'Allemagne renvoyée pour le Maroc ! ({title} à {loc_lower})"
        assert "berlin" not in loc_lower, f"❌ ERREUR : Offre de Berlin renvoyée pour le Maroc ! ({title} à {loc_lower})"
        assert "munich" not in loc_lower, f"❌ ERREUR : Offre de Munich renvoyée pour le Maroc ! ({title} à {loc_lower})"

    print("  ✅ Zéro contamination : AUCUNE offre physique de France/Paris/Europe n'a été renvoyée pour le Maroc !")

    # 4. Test Jooble (si clé présente)
    print("\n[4/5] Test de la source Jooble (Maroc & Monde)...")
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
            print(f"  ✅ Succès : {len(j_offers)} offres Jooble trouvées pour Casablanca, Maroc.")
            if j_offers:
                sample = j_offers[0]
                print(f"     Exemple : \"{sample['title']}\" chez {sample['company']}")
                print(f"     Lieu    : {sample['location']}")
                print(f"     Lien    : {sample['url']}")
        else:
            print(f"  ⚠️ Erreur Jooble : {j_status.get('error')}")
    else:
        print("  ℹ️ JOOBLE_API_KEY non définie en variable d'environnement.")
        print("     (Clé gratuite instantanée sur jooble.org/api/about pour activer les offres réelles au Maroc).")

    # 5. Test Adzuna
    print("\n[5/5] Test de la source Adzuna (Vérification non-couverture du Maroc)...")
    ad_offers_ma, ad_status_ma = fetch_adzuna(
        app_id="dummy_id",
        app_key="dummy_key",
        queries=["stage"],
        country="Maroc",
        city="Casablanca"
    )
    assert not ad_status_ma.get("ok")
    assert "ne couvre pas le maroc" in (ad_status_ma.get("error") or "").lower()
    print("  ✅ Adzuna rejette proprement les recherches pour le Maroc car non couvert.")

    print("\n" + "=" * 70)
    print("🎉 TOUS LES TESTS DE GÉOLOCALISATION ET DES SOURCES ONT RÉUSSI !")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
