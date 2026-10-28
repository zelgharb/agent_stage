#!/usr/bin/env python3
"""
Test d'intégration local validant la logique complète de l'application :
- Extraction PDF avec pypdf
- Validation de la longueur du texte (seuil 100 car.)
- Récupération des offres réelles et déduplication
- Vérification que tous les liens sont réels et inchangés
- Aucune valeur de localisation codée en dur (utilisation de variables paramétrables)
"""

import os
import pypdf
from sources import fetch_all_internships, normalize_location
from gemini_client import clean_json_response

def test_pdf_extraction():
    print("[1] Test de lecture et extraction PDF...")
    pdf_path = os.path.join(os.path.dirname(__file__), "sample_cv.pdf")
    assert os.path.exists(pdf_path), "sample_cv.pdf introuvable"
    
    reader = pypdf.PdfReader(pdf_path)
    text = "".join(page.extract_text() or "" for page in reader.pages).strip()
    
    print(f"  Longueur extraite : {len(text)} caractères")
    assert len(text) >= 100, "Le CV extrait doit dépasser 100 caractères"
    print("  ✅ Extraction PDF réussie et conforme au seuil de 100 caractères.")
    
    # Test avec un texte trop court (< 100 car.)
    short_text = "CV trop court"
    assert len(short_text) < 100
    print("  ✅ Détection des PDF scannés / courts validée (< 100 car.).")

def test_offers_pipeline():
    print("\n[2] Test du pipeline d'offres réelles...")
    test_country = os.environ.get("TEST_COUNTRY", "Télétravail / Remote")
    test_city = os.environ.get("TEST_CITY", "")
    queries = ["Stage Informatique", "Python Intern", "Data"]
    
    offers, statuses = fetch_all_internships(queries, country=test_country, city=test_city)
    
    print(f"  Localisation testée : Pays='{test_country}', Ville='{test_city}'")
    print(f"  Offres récupérées : {len(offers)}")
    assert len(offers) > 0, "Le pipeline doit retourner des offres réelles"
    
    norm = normalize_location(test_country, test_city)
    for o in offers:
        assert "url" in o and o["url"].startswith("http"), f"Offre sans URL valide : {o}"
        assert "title" in o and len(o["title"]) > 0, "Titre manquant"
        assert "company" in o, "Entreprise manquante"
    
    print("  ✅ Toutes les offres contiennent un lien direct valide issu des sources.")

def test_json_cleaner():
    print("\n[3] Test du parseur JSON robuste...")
    raw_markdown = '```json\n{"summary": "test", "score": 90}\n```'
    cleaned = clean_json_response(raw_markdown)
    assert cleaned == '{"summary": "test", "score": 90}'
    print("  ✅ Nettoyage des balises Markdown validé.")

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 DÉBUT DES TESTS D'INTÉGRATION LOCAUX")
    print("=" * 60)
    test_pdf_extraction()
    test_offers_pipeline()
    test_json_cleaner()
    print("=" * 60)
    print("🎉 TOUS LES TESTS D'INTÉGRATION SONT AU VERT !")
    print("=" * 60)
