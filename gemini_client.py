"""
Module d'intégration avec l'API Gemini.
Gestion de cascade de modèles, retry 503 (attente 3s puis 6s), bascule 429 (quota).
Protection stricte de la clé API et intégrité des liens d'offres.
"""

import json
import re
import time
from typing import Dict, Any, List, Tuple
import requests

# Cascade ordonnée demandée par l'utilisateur
GEMINI_MODELS = [
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
    "gemini-3.7-flash"
]

def clean_json_response(raw_text: str) -> str:
    """Nettoie le texte reçu pour isoler l'objet JSON valide."""
    text = raw_text.strip()
    # Supprimer les balises Markdown éventuelles ```json ... ```
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()

def call_gemini_with_fallback(
    api_key: str,
    prompt: str,
    system_instruction: str = "",
    require_json: bool = True
) -> Tuple[str, str]:
    """
    Appelle Gemini avec cascade automatique des modèles :
    1. gemini-3.6-flash
    2. gemini-3.5-flash-lite
    3. gemini-3.8-flash
    4. gemini-3.7-flash

    Gestion des erreurs :
    - 503 (Surcharge) : 3 tentatives (attente 3 s puis 6 s).
    - 429 (Quota) : bascule immédiate vers le modèle suivant.
    - Affiche l'erreur réelle à l'utilisateur si tout échoue.
    """
    if not api_key or not api_key.strip():
        raise ValueError("Clé API Gemini absente. Veuillez configurer GEMINI_API_KEY dans st.secrets.")

    headers = {"Content-Type": "application/json"}
    payload: Dict[str, Any] = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}]
            }
        ]
    }
    
    if system_instruction:
        payload["system_instruction"] = {
            "parts": [{"text": system_instruction}]
        }
        
    if require_json:
        payload["generationConfig"] = {
            "response_mime_type": "application/json",
            "temperature": 0.2
        }

    errors_log = []

    for model in GEMINI_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        
        # 3 tentatives en cas de surcharge 503
        for attempt in range(1, 4):
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=35)
                
                # Cas succès
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        if parts and "text" in parts[0]:
                            return parts[0]["text"], model
                    errors_log.append(f"{model}: Réponse vide ou structure inattendue.")
                    break # Passer au modèle suivant
                
                # Cas 503 (Surcharge)
                elif resp.status_code == 503:
                    err_msg = ""
                    try:
                        err_msg = resp.json().get("error", {}).get("message", resp.text)
                    except Exception:
                        err_msg = resp.text
                    errors_log.append(f"{model} (tentative {attempt}/3, HTTP 503): {err_msg}")
                    
                    if attempt < 3:
                        wait_sec = 3 if attempt == 1 else 6
                        time.sleep(wait_sec)
                        continue
                    else:
                        # Après 3 tentatives 503, basculer au modèle suivant
                        break
                        
                # Cas 429 (Quota dépassé)
                elif resp.status_code == 429:
                    err_msg = ""
                    try:
                        err_msg = resp.json().get("error", {}).get("message", resp.text)
                    except Exception:
                        err_msg = resp.text
                    errors_log.append(f"{model} (HTTP 429 Quota dépassé): {err_msg}")
                    # Basculer immédiatement au modèle suivant
                    break
                    
                # Erreur 400 (ex: mauvaise clé API)
                elif resp.status_code in [400, 401, 403]:
                    err_msg = ""
                    try:
                        err_msg = resp.json().get("error", {}).get("message", resp.text)
                    except Exception:
                        err_msg = resp.text
                    # Si clé invalide, inutile de tester d'autres modèles avec la même clé
                    if "API key" in err_msg or resp.status_code in [401, 403]:
                        raise RuntimeError(f"Erreur d'authentification Gemini ({resp.status_code}): {err_msg}")
                    errors_log.append(f"{model} (HTTP {resp.status_code}): {err_msg}")
                    break
                    
                # Autre code HTTP
                else:
                    errors_log.append(f"{model} (HTTP {resp.status_code}): {resp.text[:120]}")
                    break
                    
            except requests.exceptions.RequestException as e:
                errors_log.append(f"{model} (connexion): {str(e)}")
                if attempt < 3:
                    wait_sec = 3 if attempt == 1 else 6
                    time.sleep(wait_sec)
                else:
                    break

    # Si tous les modèles ont échoué, afficher la liste réelle des erreurs
    detailed_errors = " | ".join(errors_log)
    raise RuntimeError(
        f"Impossible d'obtenir une réponse de Gemini après bascule automatique sur les 4 modèles "
        f"({', '.join(GEMINI_MODELS)}). Détails réels : {detailed_errors}"
    )

def analyze_cv(
    cv_text: str,
    country_city: str,
    domain: str,
    duration: str,
    api_key: str
) -> Dict[str, Any]:
    """
    Étape 2 : Analyse le CV et génère le profil ainsi que 3 à 5 requêtes de recherche.
    """
    truncated_cv = cv_text[:8000]
    
    system_instruction = (
        "Tu es un expert en recrutement et orientation professionnelle de haut niveau. "
        "Ton rôle est d'analyser le CV d'un candidat pour lui trouver des stages réels pertinents. "
        "Important : Détecte la langue principale du CV et réponds STRICTEMENT dans cette langue. "
        "Réponds UNIQUEMENT sous forme de JSON valide conforme au schéma demandé."
    )
    
    prompt = f"""
Voici le texte extrait du CV du candidat (tronqué à 8000 caractères) :
---
{truncated_cv}
---

Critères de recherche spécifiés par le candidat :
- Pays / Ville souhaités : {country_city if country_city else "Non spécifié"}
- Domaine souhaité : {domain if domain else "Non spécifié (à déduire du CV)"}
- Durée du stage souhaitée : {duration if duration else "Non spécifiée"}

Consignes :
1. Détecte la langue du CV (ex: 'fr', 'en', 'es', etc.).
2. Rédige un résumé du profil en EXACTEMENT 3 lignes dans la langue du CV.
3. Identifie le domaine principal et une liste de 5 à 8 compétences clés (hard & soft skills).
4. Génère entre 3 et 5 requêtes de recherche spécifiques pour trouver des STAGES (ex: 'Stage Data Science Paris', 'Internship Software Engineer', etc.), adaptées au pays demandé ({country_city}) et à la langue du marché.

Schéma JSON attendu :
{{
  "language": "fr",
  "summary": "Ligne 1 du résumé\\nLigne 2 du résumé\\nLigne 3 du résumé",
  "domain": "Domaine professionnel identifié",
  "key_skills": ["Compétence 1", "Compétence 2", "Compétence 3"],
  "search_queries": [
    "Requête de recherche stage 1",
    "Requête de recherche stage 2",
    "Requête de recherche stage 3"
  ]
}}
"""

    raw_response, model_used = call_gemini_with_fallback(
        api_key=api_key,
        prompt=prompt,
        system_instruction=system_instruction,
        require_json=True
    )
    
    cleaned_json = clean_json_response(raw_response)
    try:
        data = json.loads(cleaned_json)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Échec du décodage JSON de l'analyse du CV ({model_used}) : {str(e)}. Réponse brute : {raw_response[:200]}")

    data["model_used"] = model_used
    return data

def evaluate_offers(
    profile_data: Dict[str, Any],
    offers: List[Dict[str, Any]],
    cv_language: str,
    api_key: str
) -> Tuple[List[Dict[str, Any]], List[str], str]:
    """
    Étape 4 : Noter et justifier les offres trouvées + donner 3 conseils pour améliorer le CV.
    IMPORTANT : Les URLs NE SONT JAMAIS envoyées à Gemini pour éviter toute altération.
    Seuls les ID, titre, entreprise, lieu et description sont transmis.
    """
    if not offers:
        return [], ["Élargis tes critères géographiques.", "Ajoute des projets concrets sur ton CV.", "Précise tes outils techniques."], "aucun"

    # Préparer le payload anonymisé sans URL
    offers_payload = []
    for idx, o in enumerate(offers, 1):
        offers_payload.append({
            "id": idx,
            "title": o.get("title", ""),
            "company": o.get("company", ""),
            "location": o.get("location", ""),
            "snippet": o.get("snippet", "")[:250]
        })

    system_instruction = (
        "Tu es un recruteur expert. Tu évalues la correspondance entre le profil d'un candidat "
        "et une sélection d'offres de stage réelles. "
        f"Tu dois répondre STRICTEMENT dans la langue du CV : {cv_language}. "
        "Réponds UNIQUEMENT par un objet JSON valide conforme au schéma."
    )

    prompt = f"""
Profil du candidat :
- Résumé : {profile_data.get('summary', '')}
- Domaine : {profile_data.get('domain', '')}
- Compétences clés : {', '.join(profile_data.get('key_skills', []))}

Voici la liste des offres de stage à évaluer (identifiées par leur ID) :
{json.dumps(offers_payload, ensure_ascii=False, indent=2)}

Tâches :
1. Pour chaque offre (par son id), attribue :
   - 'score' : un score de correspondance réaliste entre 0 et 100.
   - 'justification' : EXACTEMENT une phrase courte et percutante expliquant pourquoi cette offre correspond au profil (ou ses limites).
2. Fournis exactement 3 conseils concrets et actionnables pour optimiser le CV du candidat par rapport aux opportunités visées.

Schéma JSON attendu :
{{
  "evaluations": [
    {{
      "id": 1,
      "score": 85,
      "justification": "Explication en une phrase."
    }}
  ],
  "tips": [
    "Conseil 1...",
    "Conseil 2...",
    "Conseil 3..."
  ]
}}
"""

    raw_response, model_used = call_gemini_with_fallback(
        api_key=api_key,
        prompt=prompt,
        system_instruction=system_instruction,
        require_json=True
    )

    cleaned_json = clean_json_response(raw_response)
    try:
        eval_data = json.loads(cleaned_json)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Échec du décodage JSON de l'évaluation ({model_used}) : {str(e)}. Réponse brute : {raw_response[:200]}")

    eval_map = {item["id"]: item for item in eval_data.get("evaluations", []) if "id" in item}
    
    # Rapprochement avec les offres d'origine : les vrais liens sont préservés à 100%
    scored_offers = []
    for idx, original_offer in enumerate(offers, 1):
        ev = eval_map.get(idx, {})
        score = ev.get("score")
        if score is None:
            score = 50
        try:
            score = int(score)
        except (ValueError, TypeError):
            score = 50
            
        justification = ev.get("justification", "Offre en lien avec votre domaine d'activité.")
        
        # Copie de l'offre originale
        scored_offer = dict(original_offer)
        scored_offer["score"] = score
        scored_offer["justification"] = justification
        scored_offers.append(scored_offer)

    # Tri décroissant par score
    scored_offers.sort(key=lambda x: x.get("score", 0), reverse=True)
    tips = eval_data.get("tips", [])
    if not tips:
        tips = [
            "Mets en avant tes projets personnels et GitHub sur ton CV.",
            "Quantifie tes réalisations lors de tes précédents stages ou projets académiques.",
            "Adapte tes compétences techniques aux mots-clés requis par chaque offre."
        ]

    return scored_offers, tips, model_used
