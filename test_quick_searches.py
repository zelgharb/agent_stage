#!/usr/bin/env python3
"""
Test unitaire et d'intégration validant la génération des liens de Recherches Rapides :
- LinkedIn
- Google ciblé (rekrute.com, emploi.ma, indeed.com)
- Respect strict de l'absence de valeurs par défaut
- Encodage conforme avec urllib.parse.quote_plus
- Gestion des caractères accentués et caractères spéciaux
- Absence totale de scraping et d'appel réseau serveur
"""

import urllib.parse
from sources import build_quick_search_keywords, generate_quick_search_urls

def test_standard_generation():
    print("[1] Test du cas standard (Maroc, Casablanca, Data Science, Python/SQL)...")
    country = "Maroc"
    city = "Casablanca"
    domain = "Data Science"
    skills = ["Python", "SQL", "Machine Learning"]
    
    res = generate_quick_search_urls(country, city, domain, skills)
    
    assert res["keywords"] == "Data Science Python", f"Mots-clés inattendus: {res['keywords']}"
    assert res["location"] == "Casablanca, Maroc"
    
    # Vérification LinkedIn
    expected_linkedin = "https://www.linkedin.com/jobs/search/?keywords=Data+Science+Python+stage&location=Casablanca%2C+Maroc"
    assert res["linkedin"] == expected_linkedin, f"LinkedIn invalide: {res['linkedin']}"
    
    # Vérification Google ciblés
    expected_rekrute = "https://www.google.com/search?q=stage+Data+Science+Python+Casablanca+site:rekrute.com"
    expected_emploi_ma = "https://www.google.com/search?q=stage+Data+Science+Python+Casablanca+site:emploi.ma"
    expected_indeed = "https://www.google.com/search?q=stage+Data+Science+Python+Casablanca+site:indeed.com"
    
    assert res["google"]["rekrute.com"] == expected_rekrute, f"Rekrute invalide: {res['google']['rekrute.com']}"
    assert res["google"]["emploi.ma"] == expected_emploi_ma, f"Emploi.ma invalide: {res['google']['emploi.ma']}"
    assert res["google"]["indeed.com"] == expected_indeed, f"Indeed invalide: {res['google']['indeed.com']}"
    
    print("  ✅ URLs générées conformes au format attendu pour LinkedIn et Google ciblé.")

def test_no_defaults():
    print("\n[2] Test strict 'Aucune valeur par défaut' (champs vides)...")
    res = generate_quick_search_urls("", "", "", [])
    
    assert res["keywords"] == "", f"Les mots-clés doivent être vides mais valent: {repr(res['keywords'])}"
    assert res["location"] == "", f"La localisation doit être vide mais vaut: {repr(res['location'])}"
    
    # Vérification qu'aucune valeur factice (Paris, France, Informatique, etc.) n'est injectée
    assert res["linkedin"] == "https://www.linkedin.com/jobs/search/?keywords=stage&location="
    assert res["google"]["rekrute.com"] == "https://www.google.com/search?q=stage+site:rekrute.com"
    assert res["google"]["emploi.ma"] == "https://www.google.com/search?q=stage+site:emploi.ma"
    assert res["google"]["indeed.com"] == "https://www.google.com/search?q=stage+site:indeed.com"
    
    print("  ✅ Aucune valeur par défaut injectée lorsque les critères sont absents.")

def test_encoding_accents_and_special_chars():
    print("\n[3] Test de l'encodage urllib.parse.quote_plus (accents, espaces, caractères spéciaux)...")
    country = "France"
    city = "Montréal" # test accent dans ville
    domain = "Ingénierie & Systèmes" # test & et accents
    skills = ["C++", "Réseaux"] # test + et accent
    
    res = generate_quick_search_urls(country, city, domain, skills)
    
    # Vérifier que les espaces sont bien des +, que & est %26, + est %2B, é est %C3%A9
    linkedin = res["linkedin"]
    assert " " not in linkedin, "L'URL LinkedIn ne doit contenir aucun espace brut"
    assert "Montr%C3%A9al" in linkedin, "L'accent de Montréal doit être encodé en %C3%A9"
    assert "%26" in linkedin, "Le & doit être encodé en %26"
    assert "%2B%2B" in linkedin, "Le C++ doit être encodé en C%2B%2B"
    assert "France" in linkedin
    
    for site, g_url in res["google"].items():
        assert " " not in g_url, f"L'URL Google ({site}) ne doit contenir aucun espace brut"
        assert f"site:{site}" in g_url, f"L'opérateur site:{site} doit être préservé sans altération"
        assert "Montr%C3%A9al" in g_url
        
    print("  ✅ Encodage correct validé pour les accents, espaces et caractères spéciaux.")

def test_missing_city_or_country():
    print("\n[4] Test de résilience : pays seul ou ville seule...")
    # Pays seul (ex: Maroc sans ville)
    res_country = generate_quick_search_urls("Maroc", "", "Marketing", ["SEO"])
    assert res_country["location"] == "Maroc"
    assert "location=Maroc" in res_country["linkedin"]
    assert "stage+Marketing+SEO+Maroc+site:rekrute.com" in res_country["google"]["rekrute.com"]
    
    # Ville seule (ex: Casablanca sans pays)
    res_city = generate_quick_search_urls("", "Casablanca", "Comptabilité", ["Excel"])
    assert res_city["location"] == "Casablanca"
    assert "location=Casablanca" in res_city["linkedin"]
    assert "stage+Comptabilit%C3%A9+Excel+Casablanca+site:emploi.ma" in res_city["google"]["emploi.ma"]
    
    print("  ✅ Gestion propre et sans erreur pour ville seule ou pays seul.")

def test_duplicate_keywords_removal():
    print("\n[5] Test d'élimination des doublons entre domaine et compétences clés...")
    domain = "Machine Learning"
    skills = ["Machine Learning", "Python", "Deep Learning"]
    keywords = build_quick_search_keywords(domain, skills)
    
    # Ne doit pas contenir "Machine Learning Machine Learning"
    assert keywords.count("Machine Learning") == 1
    assert "Python" in keywords
    print(f"  Mots-clés filtrés : '{keywords}'")
    print("  ✅ Pas de duplication des termes.")

def test_zero_network_calls():
    print("\n[6] Test de performance & zéro appel réseau serveur...")
    import time
    start = time.time()
    for _ in range(100):
        generate_quick_search_urls("Maroc", "Rabat", "DevOps", ["Kubernetes", "Docker"])
    elapsed = time.time() - start
    print(f"  100 générations exécutées en {elapsed*1000:.2f} ms")
    assert elapsed < 0.1, "L'exécution doit être instantanée en mémoire sans scraping ni réseau"
    print("  ✅ Exécution locale pure validée (aucune requête réseau côté serveur, aucune clé requise).")

if __name__ == "__main__":
    print("=" * 70)
    print("🧪 DÉBUT DES TESTS DES RECHERCHES RAPIDES")
    print("=" * 70)
    test_standard_generation()
    test_no_defaults()
    test_encoding_accents_and_special_chars()
    test_missing_city_or_country()
    test_duplicate_keywords_removal()
    test_zero_network_calls()
    print("=" * 70)
    print("🎉 TOUS LES TESTS DE GÉNÉRATION D'URLS SONT VALIDÉS AVEC SUCCÈS !")
    print("=" * 70)
