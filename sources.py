"""
Module de gestion des sources réelles d'offres de stage.
Aucun lien inventé : toutes les URLs proviennent directement des APIs interrogées.
"""

import html
import re
import requests
from typing import List, Dict, Any, Tuple

INTERNSHIP_KEYWORDS = [
    "stage", "stagiaire", "intern", "internship", "pfe", "werkstudent",
    "working student", "trainee", "praktik", "praktikum", "alternance",
    "apprenti", "apprentice", "student"
]

def clean_html(raw_html: str) -> str:
    """Nettoie les balises HTML et entités d'un texte."""
    if not raw_html:
        return ""
    clean = re.sub(r"<[^>]+>", " ", raw_html)
    clean = html.unescape(clean)
    return " ".join(clean.split())

def is_internship_match(title: str, description: str = "", job_types: List[str] = None, tags: List[str] = None) -> bool:
    """Vérifie si une offre correspond réellement à un stage ou contrat étudiant."""
    title_lower = (title or "").lower()
    desc_lower = (description or "").lower()
    types_lower = [str(t).lower() for t in (job_types or [])]
    tags_lower = [str(t).lower() for t in (tags or [])]
    
    # 1. Dans le titre (critère très fort)
    for kw in INTERNSHIP_KEYWORDS:
        # Correspondance par mot entier ou délimité
        if re.search(rf"\b{re.escape(kw)}\b", title_lower):
            return True
            
    # 2. Dans le type de contrat ou tags
    for kw in INTERNSHIP_KEYWORDS:
        if any(kw in t for t in types_lower) or any(kw in t for t in tags_lower):
            return True
            
    # 3. Dans la description si terme explicite en début de texte
    for kw in ["stage de fin d'études", "stage pfe", "internship position", "internship program", "sujet de stage"]:
        if kw in desc_lower:
            return True

    return False

def matches_query(text: str, query: str) -> bool:
    """Vérifie si un texte contient au moins l'un des mots-clés d'une requête."""
    terms = [w.lower() for w in re.findall(r"\w+", query) if len(w) > 2]
    text_lower = text.lower()
    return any(t in text_lower for t in terms)

def fetch_arbeitnow(
    queries: List[str],
    country: str = "",
    city: str = "",
    max_results: int = 25
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Interroge l'API Arbeitnow (gratuite, sans clé requise).
    Excellente couverture pour l'Europe et le télétravail.
    """
    status = {"name": "Arbeitnow", "ok": False, "count": 0, "error": None}
    url = "https://www.arbeitnow.com/api/job-board-api"
    headers = {"User-Agent": "Mozilla/5.0 (InternshipAgent/1.0)"}
    
    try:
        resp = requests.get(url, headers=headers, timeout=12)
        if resp.status_code != 200:
            status["error"] = f"HTTP {resp.status_code}"
            return [], status
            
        data = resp.json().get("data", [])
        matched = []
        
        target_loc = f"{city} {country}".strip().lower()
        
        for item in data:
            title = item.get("title", "")
            raw_desc = item.get("description", "")
            snippet = clean_html(raw_desc)[:300]
            job_types = item.get("job_types", [])
            tags = item.get("tags", [])
            location = item.get("location", "Non spécifié")
            job_url = item.get("url", "")
            company = item.get("company_name", "Entreprise confidentielle")
            
            # Vérifier que l'URL existe
            if not job_url:
                continue
                
            # Filtrer pour ne garder que les stages
            if not is_internship_match(title, snippet, job_types, tags):
                continue
                
            # Filtrer par localisation si spécifiée
            loc_lower = location.lower()
            if target_loc:
                # Si localisation demandée, privilégier correspondance ou remote
                is_remote = item.get("remote", False) or "remote" in loc_lower or "télétravail" in loc_lower
                matches_loc = any(part in loc_lower for part in target_loc.split() if len(part) > 2)
                # Accepter si match direct de localisation OU si l'offre est remote
                if not (matches_loc or is_remote):
                    # Ne pas rejeter immédiatement si peu d'offres, mais baisser priorité
                    pass
            
            # Matching avec requêtes si fournies
            full_text = f"{title} {snippet} {' '.join(tags)}"
            if queries:
                if any(matches_query(full_text, q) for q in queries):
                    matched.append({
                        "title": title,
                        "company": company,
                        "location": location,
                        "url": job_url,
                        "snippet": snippet,
                        "source": "Arbeitnow"
                    })
            else:
                matched.append({
                    "title": title,
                    "company": company,
                    "location": location,
                    "url": job_url,
                    "snippet": snippet,
                    "source": "Arbeitnow"
                })
                
            if len(matched) >= max_results:
                break
                
        status["ok"] = True
        status["count"] = len(matched)
        return matched, status
        
    except Exception as e:
        status["error"] = str(e)
        return [], status

def fetch_remotive(
    queries: List[str],
    country: str = "",
    city: str = "",
    max_results: int = 15
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Interroge l'API Remotive (gratuite, sans clé requise).
    Idéal pour les opportunités remote mondiales.
    """
    status = {"name": "Remotive", "ok": False, "count": 0, "error": None}
    headers = {"User-Agent": "Mozilla/5.0 (InternshipAgent/1.0)"}
    matched = []
    
    # Extraire les mots-clés principaux des requêtes
    search_keywords = []
    for q in queries:
        for w in re.findall(r"\w+", q):
            w_lower = w.lower()
            if w_lower not in ["stage", "intern", "internship", "pour", "dans", "avec", "the", "and"] and len(w_lower) > 2:
                search_keywords.append(w_lower)
    search_keywords = list(dict.fromkeys(search_keywords))[:3]
    if not search_keywords:
        search_keywords = ["intern"]

    try:
        # Recherche ciblée sur les mots-clés
        for kw in search_keywords:
            url = f"https://remotive.com/api/remote-jobs?search={kw}"
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                jobs = resp.json().get("jobs", [])
                for j in jobs:
                    title = j.get("title", "")
                    job_url = j.get("url", "")
                    if not job_url:
                        continue
                    company = j.get("company_name", "Entreprise confidentielle")
                    location = j.get("candidate_required_location", "Remote / Télétravail")
                    snippet = clean_html(j.get("description", ""))[:300]
                    job_type = j.get("job_type", "")
                    tags = j.get("tags", [])
                    
                    # Vérifier stage ou profil junior/étudiant
                    if is_internship_match(title, snippet, [job_type], tags) or any(t in title.lower() for t in ["intern", "junior", "trainee", "student"]):
                        matched.append({
                            "title": title,
                            "company": company,
                            "location": f"Remote ({location})" if location else "Remote",
                            "url": job_url,
                            "snippet": snippet,
                            "source": "Remotive"
                        })
            if len(matched) >= max_results:
                break
                
        status["ok"] = True
        status["count"] = len(matched)
        return matched, status
        
    except Exception as e:
        status["error"] = str(e)
        return [], status

def fetch_jooble(
    api_key: str,
    queries: List[str],
    country: str = "",
    city: str = "",
    max_results: int = 20
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Interroge l'API Jooble (clé gratuite disponible sur jooble.org/api/about).
    Permet de couvrir le Maroc et plus de 70 pays.
    """
    status = {"name": "Jooble", "ok": False, "count": 0, "error": None}
    if not api_key:
        status["error"] = "Clé JOOBLE_API_KEY non configurée"
        return [], status
        
    # Choisir le point de terminaison adapté
    country_lower = country.lower().strip()
    if country_lower in ["maroc", "morocco", "ma"]:
        endpoint = f"https://ma.jooble.org/api/{api_key}"
    elif country_lower in ["france", "fr"]:
        endpoint = f"https://fr.jooble.org/api/{api_key}"
    else:
        endpoint = f"https://jooble.org/api/{api_key}"
        
    headers = {"Content-Type": "application/json"}
    matched = []
    
    # Construire la requête
    target_loc = f"{city} {country}".strip()
    search_terms = queries if queries else ["stage"]
    
    try:
        for q in search_terms[:3]:
            # S'assurer d'inclure le terme 'stage' ou 'intern'
            kw = q if any(k in q.lower() for k in ["stage", "intern"]) else f"stage {q}"
            payload = {
                "keywords": kw,
                "location": target_loc,
                "page": 1,
                "ResultOnPage": max_results
            }
            resp = requests.post(endpoint, json=payload, headers=headers, timeout=12)
            if resp.status_code == 200:
                jobs = resp.json().get("jobs", [])
                for j in jobs:
                    title = j.get("title", "")
                    job_url = j.get("link", "")
                    if not job_url:
                        continue
                    company = j.get("company", "Entreprise confidentielle")
                    location = j.get("location", target_loc or "Non spécifié")
                    snippet = clean_html(j.get("snippet", ""))[:300]
                    
                    matched.append({
                        "title": title,
                        "company": company,
                        "location": location,
                        "url": job_url,
                        "snippet": snippet,
                        "source": "Jooble"
                    })
            elif resp.status_code in [401, 403]:
                status["error"] = f"Clé Jooble invalide ou quota atteint (HTTP {resp.status_code})"
                return [], status
                
            if len(matched) >= max_results:
                break
                
        status["ok"] = True
        status["count"] = len(matched)
        return matched, status
        
    except Exception as e:
        status["error"] = str(e)
        return [], status

def fetch_adzuna(
    app_id: str,
    app_key: str,
    queries: List[str],
    country: str = "France",
    city: str = "",
    max_results: int = 20
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Interroge l'API Adzuna (clé gratuite sur developer.adzuna.com).
    Couvre: France (fr), UK (gb), USA (us), Allemagne (de), etc. (ne couvre pas le Maroc).
    """
    status = {"name": "Adzuna", "ok": False, "count": 0, "error": None}
    if not (app_id and app_key):
        status["error"] = "Identifiants Adzuna non configurés"
        return [], status
        
    # Mapping pays
    country_map = {
        "france": "fr", "fr": "fr",
        "uk": "gb", "royaume-uni": "gb", "gb": "gb",
        "usa": "us", "etats-unis": "us", "us": "us",
        "germany": "de", "allemagne": "de", "de": "de",
        "canada": "ca", "ca": "ca",
        "belgique": "be", "be": "be",
        "suisse": "ch", "ch": "ch",
        "espagne": "es", "es": "es",
        "italie": "it", "it": "it"
    }
    
    code = country_map.get(country.lower().strip(), "fr")
    base_url = f"https://api.adzuna.com/v1/api/jobs/{code}/search/1"
    matched = []
    
    try:
        search_terms = queries if queries else ["stage"]
        for q in search_terms[:2]:
            kw = q if "stage" in q.lower() or "intern" in q.lower() else f"stage {q}"
            params = {
                "app_id": app_id,
                "app_key": app_key,
                "what": kw,
                "where": city,
                "results_per_page": max_results
            }
            resp = requests.get(base_url, params=params, timeout=12)
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                for r in results:
                    title = r.get("title", "")
                    job_url = r.get("redirect_url", "")
                    if not job_url:
                        continue
                    company = r.get("company", {}).get("display_name", "Entreprise confidentielle")
                    location = r.get("location", {}).get("display_name", city or country)
                    snippet = clean_html(r.get("description", ""))[:300]
                    
                    matched.append({
                        "title": title,
                        "company": company,
                        "location": location,
                        "url": job_url,
                        "snippet": snippet,
                        "source": "Adzuna"
                    })
            else:
                status["error"] = f"HTTP {resp.status_code}"
                return [], status
                
            if len(matched) >= max_results:
                break
                
        status["ok"] = True
        status["count"] = len(matched)
        return matched, status
        
    except Exception as e:
        status["error"] = str(e)
        return [], status

def fetch_all_internships(
    queries: List[str],
    country: str = "",
    city: str = "",
    domain: str = "",
    secrets: Dict[str, Any] = None,
    max_total_offers: int = 30
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Combine toutes les sources disponibles, déduplique et filtre les offres.
    Ne conserve que les offres valides avec lien direct.
    """
    if secrets is None:
        secrets = {}
        
    all_offers = []
    sources_status = {}
    
    # 1. Arbeitnow (toujours actif, sans clé)
    an_offers, an_status = fetch_arbeitnow(queries, country, city, max_results=25)
    sources_status["Arbeitnow"] = an_status
    all_offers.extend(an_offers)
    
    # 2. Remotive (toujours actif, sans clé)
    rem_offers, rem_status = fetch_remotive(queries, country, city, max_results=15)
    sources_status["Remotive"] = rem_status
    all_offers.extend(rem_offers)
    
    # 3. Jooble (actif si clé présente)
    jooble_key = secrets.get("JOOBLE_API_KEY")
    if jooble_key:
        j_offers, j_status = fetch_jooble(jooble_key, queries, country, city, max_results=20)
        sources_status["Jooble"] = j_status
        all_offers.extend(j_offers)
    else:
        sources_status["Jooble"] = {
            "name": "Jooble",
            "ok": False,
            "count": 0,
            "error": "Clé non configurée (optionnelle pour étendre la couverture pays)"
        }
        
    # 4. Adzuna (actif si id et clé présents)
    adzuna_id = secrets.get("ADZUNA_APP_ID")
    adzuna_key = secrets.get("ADZUNA_APP_KEY")
    if adzuna_id and adzuna_key:
        ad_offers, ad_status = fetch_adzuna(adzuna_id, adzuna_key, queries, country, city, max_results=20)
        sources_status["Adzuna"] = ad_status
        all_offers.extend(ad_offers)
    else:
        sources_status["Adzuna"] = {
            "name": "Adzuna",
            "ok": False,
            "count": 0,
            "error": "Clés non configurées (optionnelle pour France/UK/USA)"
        }

    # Déduplication stricte par URL et par (titre normalisé, entreprise normalisée)
    seen_urls = set()
    seen_keys = set()
    deduped_offers = []
    
    for offer in all_offers:
        url = offer.get("url", "").strip()
        if not url:
            continue
            
        # Normaliser pour déduplication
        norm_title = re.sub(r"[^\w\s]", "", offer.get("title", "").lower()).strip()
        norm_company = re.sub(r"[^\w\s]", "", offer.get("company", "").lower()).strip()
        offer_key = (norm_title, norm_company)
        
        if url in seen_urls or (norm_title and offer_key in seen_keys):
            continue
            
        seen_urls.add(url)
        if norm_title:
            seen_keys.add(offer_key)
            
        deduped_offers.append(offer)
        
        if len(deduped_offers) >= max_total_offers:
            break
            
    return deduped_offers, sources_status
