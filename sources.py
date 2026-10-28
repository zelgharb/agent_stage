"""
Module de gestion des sources réelles d'offres de stage.
Aucun lien inventé : toutes les URLs proviennent directement des APIs interrogées.
Filtrage géographique strict pour respecter le pays et la ville choisis.
"""

import html
import re
import requests
from typing import List, Dict, Any, Tuple

# Mots-clés stricts désignant des stages ou formations
INTERNSHIP_KEYWORDS = [
    "stage", "stagiaire", "intern", "internship", "pfe", "werkstudent",
    "working student", "trainee", "praktik", "praktikum", "alternance",
    "apprenti", "apprentice", "student"
]

# Pays européens couverts par Arbeitnow
ARBEITNOW_COUNTRIES = [
    "allemagne", "germany", "deutschland", "france", "suisse", "switzerland",
    "schweiz", "pays-bas", "netherlands", "nederland", "royaume-uni",
    "united kingdom", "uk", "autriche", "austria", "österreich",
    "belgique", "belgium", "belgië", "espagne", "spain", "italie", "italy",
    "irlande", "ireland", "europe"
]

# Codes pays supportés par l'API Adzuna (le Maroc n'en fait pas partie)
ADZUNA_COUNTRY_CODES = {
    "france": "fr", "fr": "fr",
    "royaume-uni": "gb", "united kingdom": "gb", "uk": "gb", "gb": "gb",
    "etats-unis": "us", "united states": "us", "usa": "us", "us": "us",
    "allemagne": "de", "germany": "de", "deutschland": "de", "de": "de",
    "canada": "ca", "ca": "ca",
    "belgique": "be", "belgium": "be", "be": "be",
    "suisse": "ch", "switzerland": "ch", "ch": "ch",
    "espagne": "es", "spain": "es", "es": "es",
    "italie": "it", "italy": "it", "it": "it",
    "pays-bas": "nl", "netherlands": "nl", "nl": "nl",
    "autriche": "at", "austria": "at", "at": "at",
    "australie": "au", "australia": "au", "au": "au",
    "bresil": "br", "brazil": "br", "br": "br",
    "inde": "in", "india": "in", "in": "in",
    "mexique": "mx", "mexico": "mx", "mx": "mx",
    "nouvelle-zelande": "nz", "new zealand": "nz", "nz": "nz",
    "pologne": "pl", "poland": "pl", "pl": "pl",
    "afrique du sud": "za", "south africa": "za", "za": "za"
}

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
        if re.search(rf"\b{re.escape(kw)}\b", title_lower):
            return True
            
    # 2. Dans le type de contrat ou tags
    for kw in INTERNSHIP_KEYWORDS:
        if any(kw in t for t in types_lower) or any(kw in t for t in tags_lower):
            return True
            
    # 3. Dans la description si terme explicite
    for kw in ["stage de fin d'études", "stage pfe", "internship position", "internship program", "sujet de stage"]:
        if kw in desc_lower:
            return True

    return False

def matches_query(text: str, query: str) -> bool:
    """Vérifie si un texte contient au moins un des mots-clés d'une requête."""
    terms = [w.lower() for w in re.findall(r"\w+", query) if len(w) > 2]
    text_lower = text.lower()
    return any(t in text_lower for t in terms)

def check_country_coverage(country: str, secrets: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyse quelles sources actives couvrent le pays demandé.
    """
    c_lower = country.strip().lower()
    has_jooble = bool(secrets.get("JOOBLE_API_KEY"))
    has_adzuna = bool(secrets.get("ADZUNA_APP_ID") and secrets.get("ADZUNA_APP_KEY"))
    
    is_morocco = c_lower in ["maroc", "morocco", "ma"]
    is_europe = any(ec in c_lower for ec in ARBEITNOW_COUNTRIES)
    is_adzuna_country = c_lower in ADZUNA_COUNTRY_CODES
    
    active_onsite_sources = []
    inactive_potential_sources = []
    
    if is_morocco:
        if has_jooble:
            active_onsite_sources.append("Jooble (Maroc)")
        else:
            inactive_potential_sources.append("Jooble (clé manquante)")
    elif is_europe:
        active_onsite_sources.append("Arbeitnow (Europe)")
        if has_adzuna and is_adzuna_country:
            active_onsite_sources.append("Adzuna")
        if has_jooble:
            active_onsite_sources.append("Jooble")
    else:
        if has_jooble:
            active_onsite_sources.append("Jooble")
        if has_adzuna and is_adzuna_country:
            active_onsite_sources.append("Adzuna")

    return {
        "is_morocco": is_morocco,
        "is_europe": is_europe,
        "has_onsite_coverage": len(active_onsite_sources) > 0,
        "active_sources": active_onsite_sources,
        "missing_sources": inactive_potential_sources
    }

def fetch_arbeitnow(
    queries: List[str],
    country: str = "",
    city: str = "",
    max_results: int = 25
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Interroge l'API Arbeitnow (gratuite, sans clé requise).
    Couverture RÉELLE : Allemagne, France, Suisse, Pays-Bas, UK, et Remote européen.
    NE COUVRE PAS : Le Maroc ou les pays hors Europe sur site physique.
    """
    status = {
        "name": "Arbeitnow",
        "ok": False,
        "count": 0,
        "error": None,
        "coverage_desc": "Europe & Télétravail (Ne couvre pas le Maroc sur site)"
    }
    
    target_country = country.strip().lower()
    target_city = city.strip().lower()
    is_target_morocco = target_country in ["maroc", "morocco", "ma"]
    is_target_europe = any(ec in target_country for ec in ARBEITNOW_COUNTRIES)
    
    # Si le pays demandé est explicitement le Maroc (ou hors Europe), Arbeitnow n'a pas d'offres sur site
    if is_target_morocco:
        status["ok"] = True
        status["count"] = 0
        status["error"] = "Arbeitnow ne couvre pas le Maroc (réservé à l'Europe)"
        return [], status

    url = "https://www.arbeitnow.com/api/job-board-api"
    headers = {"User-Agent": "Mozilla/5.0 (InternshipAgent/1.0)"}
    
    try:
        resp = requests.get(url, headers=headers, timeout=12)
        if resp.status_code != 200:
            status["error"] = f"HTTP {resp.status_code}"
            return [], status
            
        data = resp.json().get("data", [])
        matched = []
        
        for item in data:
            title = item.get("title", "")
            raw_desc = item.get("description", "")
            snippet = clean_html(raw_desc)[:300]
            job_types = item.get("job_types", [])
            tags = item.get("tags", [])
            location = item.get("location", "Non spécifié")
            job_url = item.get("url", "")
            company = item.get("company_name", "Entreprise confidentielle")
            
            if not job_url:
                continue
                
            # Filtrer strictement les stages
            if not is_internship_match(title, snippet, job_types, tags):
                continue
                
            loc_lower = location.lower()
            is_job_remote = bool(item.get("remote")) or "remote" in loc_lower or "télétravail" in loc_lower
            
            # FILTRAGE GÉOGRAPHIQUE STRICT
            if target_country or target_city:
                matches_city = bool(target_city and target_city in loc_lower)
                matches_country = bool(target_country and target_country in loc_lower)
                
                # Si l'utilisateur a ciblé une ville ou un pays :
                if matches_city or matches_country:
                    # Match géographique direct !
                    pass
                elif is_job_remote and (is_target_europe or not target_country):
                    # Accepter le télétravail européen si recherche Europe
                    pass
                else:
                    # REJET STRICT : ne jamais renvoyer une offre physique non correspondante
                    continue

            # Matching par mot-clé / requête
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
    Couverture RÉELLE : 100% télétravail international (Remote mondial).
    Ne propose AUCUNE offre physique sur site.
    """
    status = {
        "name": "Remotive",
        "ok": False,
        "count": 0,
        "error": None,
        "coverage_desc": "100% Télétravail mondial (Remote)"
    }
    headers = {"User-Agent": "Mozilla/5.0 (InternshipAgent/1.0)"}
    matched = []
    
    # Extraire les mots-clés principaux
    search_keywords = []
    for q in queries:
        for w in re.findall(r"\w+", q):
            w_lower = w.lower()
            if w_lower not in ["stage", "intern", "internship", "maroc", "france", "paris", "casablanca", "pour", "dans", "avec", "the", "and"] and len(w_lower) > 2:
                search_keywords.append(w_lower)
    search_keywords = list(dict.fromkeys(search_keywords))[:3]
    if not search_keywords:
        search_keywords = ["intern"]

    target_country = country.strip().lower()

    try:
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
                    req_loc = j.get("candidate_required_location", "Worldwide")
                    req_loc_lower = (req_loc or "").lower()
                    
                    # FILTRAGE GÉOGRAPHIQUE REMOTIVE :
                    # Si une offre requiert un pays spécifique incompatible (ex: USA only alors qu'on est au Maroc)
                    is_worldwide = any(w in req_loc_lower for w in ["worldwide", "anywhere", "all", "global"])
                    is_loc_match = bool(target_country and target_country in req_loc_lower)
                    
                    if not (is_worldwide or is_loc_match):
                        # Exclure les offres restreintes à d'autres zones (ex: USA Only, UK Only)
                        continue

                    snippet = clean_html(j.get("description", ""))[:300]
                    job_type = j.get("job_type", "")
                    tags = j.get("tags", [])
                    
                    if is_internship_match(title, snippet, [job_type], tags) or any(t in title.lower() for t in ["intern", "junior", "trainee", "student"]):
                        matched.append({
                            "title": title,
                            "company": company,
                            "location": f"Remote ({req_loc})" if req_loc else "Remote (Worldwide)",
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
    Couverture RÉELLE : Le Maroc (via ma.jooble.org), la France (fr.jooble.org), et 70+ pays.
    Prend en compte le paramètre 'location' (ville et pays).
    """
    status = {
        "name": "Jooble",
        "ok": False,
        "count": 0,
        "error": None,
        "coverage_desc": "Maroc & International (70+ pays)"
    }
    if not api_key:
        status["error"] = "Clé JOOBLE_API_KEY absente (requise pour rechercher au Maroc)"
        return [], status
        
    country_lower = country.lower().strip()
    # Sélection de l'endpoint adapté
    if country_lower in ["maroc", "morocco", "ma"]:
        endpoint = f"https://ma.jooble.org/api/{api_key}"
    elif country_lower in ["france", "fr"]:
        endpoint = f"https://fr.jooble.org/api/{api_key}"
    else:
        endpoint = f"https://jooble.org/api/{api_key}"
        
    headers = {"Content-Type": "application/json"}
    matched = []
    
    target_loc = f"{city} {country}".strip()
    search_terms = queries if queries else ["stage"]
    
    try:
        for q in search_terms[:3]:
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
                status["error"] = f"Clé Jooble invalide ou expirée (HTTP {resp.status_code})"
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
    Couverture RÉELLE : 20 pays dont France, UK, USA, Allemagne, Canada.
    NE COUVRE PAS LE MAROC.
    """
    status = {
        "name": "Adzuna",
        "ok": False,
        "count": 0,
        "error": None,
        "coverage_desc": "France, UK, USA, Allemagne... (Ne couvre pas le Maroc)"
    }
    
    country_lower = country.lower().strip()
    if country_lower in ["maroc", "morocco", "ma"]:
        status["error"] = "Adzuna ne couvre pas le Maroc (non disponible dans leur catalogue)"
        return [], status
        
    code = ADZUNA_COUNTRY_CODES.get(country_lower)
    if not code:
        status["error"] = f"Pays '{country}' non supporté par l'API Adzuna"
        return [], status

    if not (app_id and app_key):
        status["error"] = "Identifiants ADZUNA_APP_ID / ADZUNA_APP_KEY non configurés"
        return [], status
        
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
    Combine toutes les sources disponibles, déduplique et filtre strictement les offres.
    Respecte scrupuleusement la localisation demandée.
    """
    if secrets is None:
        secrets = {}
        
    all_offers = []
    sources_status = {}
    
    target_country = country.strip()
    target_city = city.strip()
    
    # 1. Arbeitnow (Europe / Remote)
    an_offers, an_status = fetch_arbeitnow(queries, target_country, target_city, max_results=25)
    sources_status["Arbeitnow"] = an_status
    all_offers.extend(an_offers)
    
    # 2. Remotive (100% Télétravail mondial)
    rem_offers, rem_status = fetch_remotive(queries, target_country, target_city, max_results=15)
    sources_status["Remotive"] = rem_status
    all_offers.extend(rem_offers)
    
    # 3. Jooble (Maroc & 70+ pays, actif si clé présente)
    jooble_key = secrets.get("JOOBLE_API_KEY", "")
    if jooble_key:
        j_offers, j_status = fetch_jooble(jooble_key, queries, target_country, target_city, max_results=20)
        sources_status["Jooble"] = j_status
        all_offers.extend(j_offers)
    else:
        sources_status["Jooble"] = {
            "name": "Jooble",
            "ok": False,
            "count": 0,
            "error": "Clé JOOBLE_API_KEY non configurée (requise pour le Maroc)",
            "coverage_desc": "Maroc & International (70+ pays)"
        }
        
    # 4. Adzuna (France, UK, USA...)
    adzuna_id = secrets.get("ADZUNA_APP_ID", "")
    adzuna_key = secrets.get("ADZUNA_APP_KEY", "")
    if adzuna_id and adzuna_key:
        ad_offers, ad_status = fetch_adzuna(adzuna_id, adzuna_key, queries, target_country, target_city, max_results=20)
        sources_status["Adzuna"] = ad_status
        all_offers.extend(ad_offers)
    else:
        sources_status["Adzuna"] = {
            "name": "Adzuna",
            "ok": False,
            "count": 0,
            "error": "Clés non configurées" if target_country.lower() not in ["maroc", "morocco", "ma"] else "Adzuna ne couvre pas le Maroc",
            "coverage_desc": "France, UK, USA... (Ne couvre pas le Maroc)"
        }

    # Déduplication stricte par URL et par (titre normalisé, entreprise normalisée)
    seen_urls = set()
    seen_keys = set()
    deduped_offers = []
    
    for offer in all_offers:
        url = offer.get("url", "").strip()
        if not url:
            continue
            
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
