"""
Module de gestion des sources réelles d'offres de stage.
Aucun lien inventé : toutes les URLs proviennent directement des APIs interrogées.
Filtrage géographique strict pour respecter le pays et la ville choisis.
"""

import html
import re
import unicodedata
import requests
from typing import List, Dict, Any, Tuple

# Mots-clés désignant des stages, alternances ou contrats étudiants
INTERNSHIP_KEYWORDS = [
    "stage", "stagiaire", "intern", "internship", "pfe", "alternance",
    "apprentissage", "apprenti", "apprentice", "trainee", "student",
    "etudiant", "werkstudent", "working student", "praktik", "praktikum"
]

# Pays européens couverts par Arbeitnow
ARBEITNOW_COUNTRIES = [
    "allemagne", "germany", "deutschland", "france", "suisse", "switzerland",
    "schweiz", "pays-bas", "netherlands", "nederland", "royaume-uni",
    "united kingdom", "uk", "autriche", "austria", "österreich",
    "belgique", "belgium", "belgië", "espagne", "spain", "italie", "italy",
    "irlande", "ireland", "europe", "pologne", "poland", "portugal"
]

# Codes pays supportés par l'API Adzuna
ADZUNA_COUNTRY_CODES = {
    "france": "fr", "fr": "fr",
    "royaume-uni": "gb", "united kingdom": "gb", "uk": "gb", "gb": "gb",
    "etats-unis": "us", "united states": "us", "usa": "us", "us": "us",
    "allemagne": "de", "germany": "de", "deutschland": "de", "de": "de",
    "canada": "ca", "ca": "ca",
    "belgique": "be", "belgium": "be", "be": "be",
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

# Base de connaissances géographique et équivalences normalisées
KNOWN_COUNTRIES = {
    "maroc": {
        "canonical_name": "Maroc",
        "aliases": ["maroc", "morocco", "ma", "marrocos", "marokko", "al maghrib", "maghreb", "royaume du maroc"],
        "iso_code": "ma",
        "jooble_domain": "ma.jooble.org",
        "adzuna_code": None,
        "is_europe": False,
        "is_remote": False,
    },
    "france": {
        "canonical_name": "France",
        "aliases": ["france", "fr", "fra", "republique francaise", "french republic"],
        "iso_code": "fr",
        "jooble_domain": "fr.jooble.org",
        "adzuna_code": "fr",
        "is_europe": True,
        "is_remote": False,
    },
    "belgique": {
        "canonical_name": "Belgique",
        "aliases": ["belgique", "belgium", "be", "belgie", "belgien"],
        "iso_code": "be",
        "jooble_domain": "be.jooble.org",
        "adzuna_code": "be",
        "is_europe": True,
        "is_remote": False,
    },
    "suisse": {
        "canonical_name": "Suisse",
        "aliases": ["suisse", "switzerland", "ch", "schweiz", "svizzera", "confederation suisse"],
        "iso_code": "ch",
        "jooble_domain": "ch.jooble.org",
        "adzuna_code": None,
        "is_europe": True,
        "is_remote": False,
    },
    "canada": {
        "canonical_name": "Canada",
        "aliases": ["canada", "ca", "can"],
        "iso_code": "ca",
        "jooble_domain": "ca.jooble.org",
        "adzuna_code": "ca",
        "is_europe": False,
        "is_remote": False,
    },
    "allemagne": {
        "canonical_name": "Allemagne",
        "aliases": ["allemagne", "germany", "de", "deutschland", "deu"],
        "iso_code": "de",
        "jooble_domain": "de.jooble.org",
        "adzuna_code": "de",
        "is_europe": True,
        "is_remote": False,
    },
    "espagne": {
        "canonical_name": "Espagne",
        "aliases": ["espagne", "spain", "es", "espana", "esp"],
        "iso_code": "es",
        "jooble_domain": "es.jooble.org",
        "adzuna_code": "es",
        "is_europe": True,
        "is_remote": False,
    },
    "royaume-uni": {
        "canonical_name": "Royaume-Uni",
        "aliases": ["royaume-uni", "royaume uni", "united kingdom", "uk", "gb", "great britain", "angleterre", "england"],
        "iso_code": "gb",
        "jooble_domain": "uk.jooble.org",
        "adzuna_code": "gb",
        "is_europe": True,
        "is_remote": False,
    },
    "etats-unis": {
        "canonical_name": "États-Unis",
        "aliases": ["etats-unis", "etats unis", "united states", "usa", "us", "u s a", "u s"],
        "iso_code": "us",
        "jooble_domain": "jooble.org",
        "adzuna_code": "us",
        "is_europe": False,
        "is_remote": False,
    },
    "tunisie": {
        "canonical_name": "Tunisie",
        "aliases": ["tunisie", "tunisia", "tn"],
        "iso_code": "tn",
        "jooble_domain": None,
        "adzuna_code": None,
        "is_europe": False,
        "is_remote": False,
    },
    "algerie": {
        "canonical_name": "Algérie",
        "aliases": ["algerie", "algeria", "dz"],
        "iso_code": "dz",
        "jooble_domain": None,
        "adzuna_code": None,
        "is_europe": False,
        "is_remote": False,
    },
    "senegal": {
        "canonical_name": "Sénégal",
        "aliases": ["senegal", "sn"],
        "iso_code": "sn",
        "jooble_domain": None,
        "adzuna_code": None,
        "is_europe": False,
        "is_remote": False,
    },
    "cote d'ivoire": {
        "canonical_name": "Côte d'Ivoire",
        "aliases": ["cote d'ivoire", "cote d ivoire", "cote divoire", "ivory coast", "ci"],
        "iso_code": "ci",
        "jooble_domain": "ci.jooble.org",
        "adzuna_code": None,
        "is_europe": False,
        "is_remote": False,
    },
    "italie": {
        "canonical_name": "Italie",
        "aliases": ["italie", "italy", "it", "italia"],
        "iso_code": "it",
        "jooble_domain": "it.jooble.org",
        "adzuna_code": "it",
        "is_europe": True,
        "is_remote": False,
    },
    "pays-bas": {
        "canonical_name": "Pays-Bas",
        "aliases": ["pays-bas", "pays bas", "netherlands", "nl", "nederland", "hollande", "holland"],
        "iso_code": "nl",
        "jooble_domain": "nl.jooble.org",
        "adzuna_code": "nl",
        "is_europe": True,
        "is_remote": False,
    },
    "autriche": {
        "canonical_name": "Autriche",
        "aliases": ["autriche", "austria", "at", "osterreich"],
        "iso_code": "at",
        "jooble_domain": "at.jooble.org",
        "adzuna_code": "at",
        "is_europe": True,
        "is_remote": False,
    },
    "australie": {
        "canonical_name": "Australie",
        "aliases": ["australie", "australia", "au"],
        "iso_code": "au",
        "jooble_domain": "au.jooble.org",
        "adzuna_code": "au",
        "is_europe": False,
        "is_remote": False,
    },
    "bresil": {
        "canonical_name": "Brésil",
        "aliases": ["bresil", "brazil", "br", "brasil"],
        "iso_code": "br",
        "jooble_domain": "br.jooble.org",
        "adzuna_code": "br",
        "is_europe": False,
        "is_remote": False,
    },
    "inde": {
        "canonical_name": "Inde",
        "aliases": ["inde", "india", "in"],
        "iso_code": "in",
        "jooble_domain": "in.jooble.org",
        "adzuna_code": "in",
        "is_europe": False,
        "is_remote": False,
    },
    "mexique": {
        "canonical_name": "Mexique",
        "aliases": ["mexique", "mexico", "mx"],
        "iso_code": "mx",
        "jooble_domain": "mx.jooble.org",
        "adzuna_code": "mx",
        "is_europe": False,
        "is_remote": False,
    },
    "pologne": {
        "canonical_name": "Pologne",
        "aliases": ["pologne", "poland", "pl", "polska"],
        "iso_code": "pl",
        "jooble_domain": "pl.jooble.org",
        "adzuna_code": "pl",
        "is_europe": True,
        "is_remote": False,
    },
    "portugal": {
        "canonical_name": "Portugal",
        "aliases": ["portugal", "pt"],
        "iso_code": "pt",
        "jooble_domain": "pt.jooble.org",
        "adzuna_code": None,
        "is_europe": True,
        "is_remote": False,
    },
    "afrique du sud": {
        "canonical_name": "Afrique du Sud",
        "aliases": ["afrique du sud", "south africa", "za"],
        "iso_code": "za",
        "jooble_domain": "za.jooble.org",
        "adzuna_code": "za",
        "is_europe": False,
        "is_remote": False,
    },
    "remote": {
        "canonical_name": "Télétravail / Remote",
        "aliases": ["teletravail / remote", "teletravail remote", "teletravail", "remote", "distanciel", "en ligne", "worldwide", "mondial", "anywhere"],
        "iso_code": "REMOTE",
        "jooble_domain": "jooble.org",
        "adzuna_code": None,
        "is_europe": False,
        "is_remote": True,
    }
}

# Construction de la table de correspondance inversée normalisée
ALIAS_TO_COUNTRY: Dict[str, Dict[str, Any]] = {}
for _key, _data in KNOWN_COUNTRIES.items():
    for _alias in _data["aliases"]:
        _norm_alias = "".join(
            c for c in unicodedata.normalize("NFKD", _alias.lower().strip())
            if not unicodedata.combining(c)
        )
        _norm_alias = re.sub(r"[^\w\s-]", " ", _norm_alias)
        _norm_alias = re.sub(r"\s+", " ", _norm_alias).strip()
        ALIAS_TO_COUNTRY[_norm_alias] = _data

def strip_accents(text: str) -> str:
    """Supprime les accents et diacritiques d'une chaîne de caractères."""
    nfkd = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in nfkd if not unicodedata.combining(c))

def normalize_text(text: str) -> str:
    """Minuscules, suppression des accents et des caractères parasites."""
    s = strip_accents(text or "").lower().strip()
    s = re.sub(r"[^\w\s-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def normalize_location(country: str, city: str = "") -> Dict[str, Any]:
    """
    Normalise la saisie utilisateur (minuscules, accents, espaces, équivalences).
    Exemples d'équivalences : maroc = Maroc = Morocco = MA.
    Retourne les paramètres unifiés pour les différentes APIs.
    """
    norm_c = normalize_text(country)
    norm_city = (city or "").strip()
    
    match = ALIAS_TO_COUNTRY.get(norm_c)
    if match:
        canonical_name = match["canonical_name"]
        iso_code = match["iso_code"]
        jooble_domain = match["jooble_domain"]
        adzuna_code = match["adzuna_code"]
        is_europe = match["is_europe"]
        is_remote = match["is_remote"]
    elif "remote" in norm_c or "teletravail" in norm_c or norm_c == "distanciel":
        canonical_name = "Télétravail / Remote"
        iso_code = "REMOTE"
        jooble_domain = "jooble.org"
        adzuna_code = None
        is_europe = False
        is_remote = True
    elif not country or not country.strip():
        canonical_name = ""
        iso_code = ""
        jooble_domain = "jooble.org"
        adzuna_code = None
        is_europe = False
        is_remote = False
    else:
        # Saisie libre ("Autre pays")
        canonical_name = country.strip()
        iso_code = norm_c[:2] if len(norm_c) == 2 else None
        adzuna_code = ADZUNA_COUNTRY_CODES.get(norm_c)
        is_europe = any(ec in norm_c for ec in ARBEITNOW_COUNTRIES)
        jooble_domain = f"{iso_code}.jooble.org" if (iso_code and len(iso_code) == 2) else "jooble.org"
        is_remote = False

    # Combinaison pour le champ 'location' (ville et pays, ou pays seul si ville vide)
    if is_remote:
        jooble_location = "Remote"
    elif norm_city and canonical_name:
        jooble_location = f"{norm_city}, {canonical_name}"
    elif norm_city:
        jooble_location = norm_city
    elif canonical_name:
        jooble_location = canonical_name
    else:
        jooble_location = ""

    display_loc = f"{norm_city + ', ' if norm_city else ''}{canonical_name}".strip()

    return {
        "raw_country": country,
        "raw_city": city,
        "canonical_name": canonical_name,
        "city": norm_city,
        "iso_code": iso_code,
        "jooble_domain": jooble_domain,
        "adzuna_code": adzuna_code,
        "is_europe": is_europe,
        "is_remote": is_remote,
        "jooble_location": jooble_location,
        "display_location": display_loc
    }

def clean_html(raw_html: str) -> str:
    """Nettoie les balises HTML et entités d'un texte."""
    if not raw_html:
        return ""
    clean = re.sub(r"<[^>]+>", " ", raw_html)
    clean = html.unescape(clean)
    return " ".join(clean.split())

def is_internship_match(title: str, description: str = "", job_types: List[str] = None, tags: List[str] = None) -> bool:
    """
    Vérifie si une offre correspond réellement à un stage, alternance ou contrat étudiant.
    Filtre élargi : stage, stagiaire, internship, intern, PFE, alternance, apprentissage.
    """
    title_lower = (title or "").lower()
    desc_lower = (description or "").lower()
    types_lower = [str(t).lower() for t in (job_types or [])]
    tags_lower = [str(t).lower() for t in (tags or [])]
    
    # 1. Dans le titre (critère fort avec gestion singulier/pluriel)
    for kw in INTERNSHIP_KEYWORDS:
        if re.search(rf"\b{re.escape(kw)}s?\b", title_lower):
            return True
            
    # 2. Dans le type de contrat ou tags
    for kw in INTERNSHIP_KEYWORDS:
        if any(re.search(rf"\b{re.escape(kw)}s?\b", t) for t in types_lower) or any(re.search(rf"\b{re.escape(kw)}s?\b", t) for t in tags_lower):
            return True
            
    # 3. Dans la description si expressions explicites
    explicit_phrases = [
        "stage de fin d'études", "stage pfe", "stage de pré-embauche",
        "internship position", "internship program", "sujet de stage",
        "contrat d'apprentissage", "contrat d'alternance", "contrat pro",
        "offre de stage", "pfe internship"
    ]
    if any(p in desc_lower for p in explicit_phrases):
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
    Ne s'appuie sur aucune valeur codée en dur.
    """
    norm = normalize_location(country)
    has_jooble = bool(secrets.get("JOOBLE_API_KEY"))
    has_adzuna = bool(secrets.get("ADZUNA_APP_ID") and secrets.get("ADZUNA_APP_KEY"))
    
    active_sources = []
    missing_sources = []
    
    if norm["is_remote"]:
        active_sources.append("Remotive (100% Télétravail)")
        active_sources.append("Arbeitnow (Télétravail)")
        if has_jooble:
            active_sources.append("Jooble (Télétravail)")
    else:
        if norm["is_europe"]:
            active_sources.append("Arbeitnow (Europe)")
            if has_adzuna and norm["adzuna_code"]:
                active_sources.append("Adzuna")
            elif not has_adzuna and norm["adzuna_code"]:
                missing_sources.append("Adzuna (clés manquantes)")
        else:
            if has_adzuna and norm["adzuna_code"]:
                active_sources.append("Adzuna")
            elif not has_adzuna and norm["adzuna_code"]:
                missing_sources.append("Adzuna (clés manquantes)")
                
        if has_jooble:
            active_sources.append("Jooble")
        else:
            missing_sources.append("Jooble (clé manquante)")

    has_onsite = any(s in active_sources for s in ["Arbeitnow (Europe)", "Adzuna", "Jooble"])

    return {
        "country": norm["canonical_name"],
        "is_remote": norm["is_remote"],
        "is_europe": norm["is_europe"],
        "has_onsite_coverage": has_onsite,
        "active_sources": active_sources,
        "missing_sources": missing_sources,
        "has_jooble": has_jooble,
        "has_adzuna": has_adzuna
    }

def fetch_arbeitnow(
    queries: List[str],
    country: str = "",
    city: str = "",
    max_results: int = 25
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Interroge l'API Arbeitnow (gratuite, sans clé requise).
    Couverture RÉELLE : Pays européens et Remote européen.
    NE COUVRE PAS les pays hors Europe sur site physique.
    """
    norm = normalize_location(country, city)
    status = {
        "name": "Arbeitnow",
        "ok": False,
        "count": 0,
        "http_status": "N/A",
        "error": None,
        "coverage_desc": "Europe & Télétravail"
    }
    
    # Si le pays n'est ni européen ni remote, Arbeitnow ne couvre pas
    if norm["canonical_name"] and not norm["is_europe"] and not norm["is_remote"]:
        status["ok"] = True
        status["count"] = 0
        status["http_status"] = "N/A (Hors couverture)"
        status["error"] = f"Arbeitnow ne couvre pas {norm['canonical_name']} sur site (réservé à l'Europe & Remote)"
        return [], status

    url = "https://www.arbeitnow.com/api/job-board-api"
    headers = {"User-Agent": "Mozilla/5.0 (InternshipAgent/1.0)"}
    
    try:
        resp = requests.get(url, headers=headers, timeout=12)
        status["http_status"] = f"HTTP {resp.status_code}"
        if resp.status_code != 200:
            status["error"] = f"HTTP {resp.status_code}"
            return [], status
            
        data = resp.json().get("data", [])
        matched = []
        target_city_lower = norm["city"].lower()
        target_country_lower = norm["canonical_name"].lower()
        
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
                
            # Filtrer les offres de stage
            if not is_internship_match(title, snippet, job_types, tags):
                continue
                
            loc_lower = location.lower()
            is_job_remote = bool(item.get("remote")) or "remote" in loc_lower or "télétravail" in loc_lower
            
            # Filtrage géographique strict
            if norm["is_remote"]:
                if not is_job_remote:
                    continue
            elif target_city_lower or target_country_lower:
                matches_city = bool(target_city_lower and target_city_lower in loc_lower)
                matches_country = bool(target_country_lower and target_country_lower in loc_lower)
                
                if matches_city or matches_country:
                    pass
                elif is_job_remote and norm["is_europe"]:
                    pass
                else:
                    continue

            # Matching par requête
            full_text = f"{title} {snippet} {' '.join(tags)}"
            if queries:
                if any(matches_query(full_text, q) for q in queries):
                    matched.append({
                        "title": title,
                        "company": company,
                        "location": location,
                        "url": job_url,
                        "snippet": snippet,
                        "source": "Arbeitnow",
                        "is_confirmed_stage": True
                    })
            else:
                matched.append({
                    "title": title,
                    "company": company,
                    "location": location,
                    "url": job_url,
                    "snippet": snippet,
                    "source": "Arbeitnow",
                    "is_confirmed_stage": True
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
    """
    norm = normalize_location(country, city)
    status = {
        "name": "Remotive",
        "ok": False,
        "count": 0,
        "http_status": "N/A",
        "error": None,
        "coverage_desc": "100% Télétravail mondial (Remote)"
    }
    headers = {"User-Agent": "Mozilla/5.0 (InternshipAgent/1.0)"}
    matched = []
    unconfirmed_fallback = []
    
    # Mots vides dynamiques : exclut les termes de localisation de l'utilisateur
    loc_words = set(re.findall(r"\w+", f"{country} {city}".lower()))
    stopwords = {"stage", "intern", "internship", "pour", "dans", "avec", "the", "and", "sur", "for", "with"}.union(loc_words)
    
    search_keywords = []
    for q in queries:
        for w in re.findall(r"\w+", q):
            w_lower = w.lower()
            if w_lower not in stopwords and len(w_lower) > 2:
                search_keywords.append(w_lower)
    search_keywords = list(dict.fromkeys(search_keywords))[:3]
    if not search_keywords:
        search_keywords = ["intern"]

    target_country_lower = norm["canonical_name"].lower()

    try:
        last_code = None
        for kw in search_keywords:
            url = f"https://remotive.com/api/remote-jobs?search={kw}"
            resp = requests.get(url, headers=headers, timeout=10)
            last_code = resp.status_code
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
                    
                    is_worldwide = any(w in req_loc_lower for w in ["worldwide", "anywhere", "all", "global"])
                    is_loc_match = bool(target_country_lower and target_country_lower in req_loc_lower)
                    
                    # Si une offre requiert un pays spécifique et incompatible, on l'exclut
                    if not norm["is_remote"] and target_country_lower:
                        if not (is_worldwide or is_loc_match):
                            continue

                    snippet = clean_html(j.get("description", ""))[:300]
                    job_type = j.get("job_type", "")
                    tags = j.get("tags", [])
                    
                    offer_item = {
                        "title": title,
                        "company": company,
                        "location": f"Remote ({req_loc})" if req_loc else "Remote (Worldwide)",
                        "url": job_url,
                        "snippet": snippet,
                        "source": "Remotive",
                        "is_confirmed_stage": True,
                        "stage_status": "Confirmé"
                    }

                    if is_internship_match(title, snippet, [job_type], tags) or any(t in title.lower() for t in ["intern", "junior", "trainee", "student"]):
                        matched.append(offer_item)
                    elif queries and any(matches_query(f"{title} {snippet} {' '.join(tags)}", q) for q in queries):
                        # Offre brute pertinente avec mention stage non confirmé
                        unconf_item = dict(offer_item)
                        unconf_item["is_confirmed_stage"] = False
                        unconf_item["stage_status"] = "Stage non confirmé"
                        unconf_item["title"] = f"{title} (stage non confirmé)"
                        unconfirmed_fallback.append(unconf_item)
            if len(matched) >= max_results:
                break
                
        if matched:
            final_offers = matched[:max_results]
            status["unconfirmed_fallback"] = False
        elif unconfirmed_fallback:
            final_offers = unconfirmed_fallback[:max_results]
            status["unconfirmed_fallback"] = True
        else:
            final_offers = []
            status["unconfirmed_fallback"] = False

        status["ok"] = True
        status["http_status"] = f"HTTP {last_code}" if last_code else "200 OK"
        status["count"] = len(final_offers)
        return final_offers, status
        
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
    Interroge l'API Jooble (clé gratuite sur jooble.org/api/about).
    Couverture RÉELLE : 70+ pays via domaines régionaux ou jooble.org.
    Paramètres : keywords et location (combine ville et pays choisis, ou pays seul si ville vide).
    Filtre stage élargi avec bascule sur offres brutes (« stage non confirmé ») si aucune offre ne passe le filtre.
    Sécurité : N'affiche et ne logge JAMAIS la clé API.
    """
    norm = normalize_location(country, city)
    target_loc = norm["jooble_location"]
    norm_country = norm["canonical_name"]

    status = {
        "name": "Jooble",
        "ok": False,
        "count": 0,
        "http_status": "N/A",
        "total_count": 0,
        "raw_count": 0,
        "filtered_count": 0,
        "unconfirmed_fallback": False,
        "endpoint_masked": "N/A",
        "keywords_used": "N/A",
        "location_used": target_loc,
        "error": None,
        "coverage_desc": f"Jooble ({norm_country or 'International'})"
    }

    if not api_key or not api_key.strip():
        status["error"] = "Clé JOOBLE_API_KEY absente des secrets (requise pour rechercher sur Jooble)"
        return [], status

    # Liste ordonnée d'endpoints Jooble : domaine régional puis jooble.org en fallback
    endpoints_to_try = []
    if norm.get("jooble_domain"):
        endpoints_to_try.append(f"https://{norm['jooble_domain']}/api/{api_key.strip()}")
    base_endpoint = f"https://jooble.org/api/{api_key.strip()}"
    if base_endpoint not in endpoints_to_try:
        endpoints_to_try.append(base_endpoint)

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (InternshipAgent/1.0)"
    }

    # Préparation des requêtes / mots-clés
    search_terms = []
    if queries:
        for q in queries[:3]:
            kw = q if any(k in q.lower() for k in INTERNSHIP_KEYWORDS) else f"stage {q}"
            search_terms.append(kw)
    else:
        search_terms = ["stage"]

    status["keywords_used"] = ", ".join(search_terms)

    raw_jobs_collected = []
    seen_job_links = set()
    total_count_reported = 0
    last_http_code = None
    successful_endpoint_masked = "N/A"

    for endpoint in endpoints_to_try:
        masked_ep = re.sub(r"/api/[^/]+", "/api/••••••••", endpoint)
        endpoint_failed = False

        for kw in search_terms:
            payload = {
                "keywords": kw,
                "location": target_loc,
                "page": 1,
                "ResultOnPage": max_results
            }

            try:
                resp = requests.post(endpoint, json=payload, headers=headers, timeout=12)
                last_http_code = resp.status_code
                status["http_status"] = f"HTTP {resp.status_code}"

                if resp.status_code == 200:
                    successful_endpoint_masked = masked_ep
                    data = resp.json()
                    tc = int(data.get("totalCount", 0))
                    if tc > total_count_reported:
                        total_count_reported = tc

                    jobs = data.get("jobs", [])
                    for j in jobs:
                        link = j.get("link", "").strip()
                        if link and link not in seen_job_links:
                            seen_job_links.add(link)
                            raw_jobs_collected.append(j)

                    if len(raw_jobs_collected) >= max_results:
                        break

                elif resp.status_code in [401, 403]:
                    status["error"] = f"Clé API Jooble invalide ou non autorisée pour cette région (HTTP {resp.status_code})"
                    endpoint_failed = True
                    break

                elif resp.status_code == 429:
                    status["error"] = "Quota de requêtes Jooble dépassé pour aujourd'hui (HTTP 429)"
                    endpoint_failed = True
                    break

                elif resp.status_code >= 500:
                    status["error"] = f"Le serveur Jooble a rencontré une erreur technique (HTTP {resp.status_code})"
                    endpoint_failed = True
                    break

                else:
                    status["error"] = f"Réponse inattendue de Jooble (HTTP {resp.status_code})"

            except requests.exceptions.Timeout:
                status["http_status"] = "Timeout"
                status["error"] = "Le serveur Jooble n'a pas répondu à temps (délai d'attente dépassé)"
                endpoint_failed = True
                break
            except requests.exceptions.RequestException as e:
                status["http_status"] = "Erreur réseau"
                status["error"] = f"Erreur de communication avec Jooble : {str(e)}"
                endpoint_failed = True
                break

        # Si le premier endpoint a réussi (HTTP 200), pas besoin de tenter le suivant
        if last_http_code == 200:
            break
        # Si échec d'authentification sur le domaine régional, le fallback jooble.org sera tenté
        if endpoint_failed and len(endpoints_to_try) > 1 and endpoint == endpoints_to_try[0]:
            continue

    status["endpoint_masked"] = successful_endpoint_masked if successful_endpoint_masked != "N/A" else re.sub(r"/api/[^/]+", "/api/••••••••", endpoints_to_try[0])
    status["total_count"] = total_count_reported
    status["raw_count"] = len(raw_jobs_collected)

    # Application du filtre « stage » élargi
    confirmed_offers = []
    unconfirmed_offers = []

    for j in raw_jobs_collected:
        title = j.get("title", "")
        job_url = j.get("link", "")
        if not job_url:
            continue
        company = j.get("company", "Entreprise confidentielle")
        location = j.get("location", target_loc or "Non spécifié")
        snippet = clean_html(j.get("snippet", ""))[:300]
        job_type = j.get("type", "")

        offer_dict = {
            "title": title,
            "company": company,
            "location": location,
            "url": job_url,
            "snippet": snippet,
            "source": "Jooble",
            "is_confirmed_stage": True,
            "stage_status": "Confirmé"
        }

        if is_internship_match(title, snippet, [job_type]):
            confirmed_offers.append(offer_dict)
        else:
            unconf_copy = dict(offer_dict)
            unconf_copy["is_confirmed_stage"] = False
            unconf_copy["stage_status"] = "Stage non confirmé"
            unconf_copy["title"] = f"{title} (stage non confirmé)"
            unconfirmed_offers.append(unconf_copy)

    status["filtered_count"] = len(confirmed_offers)

    # Exigence B.3 : Si aucune offre ne passe le filtre, afficher les offres brutes avec la mention « stage non confirmé »
    if confirmed_offers:
        final_offers = confirmed_offers[:max_results]
        status["unconfirmed_fallback"] = False
    elif unconfirmed_offers:
        final_offers = unconfirmed_offers[:max_results]
        status["unconfirmed_fallback"] = True
    else:
        final_offers = []
        status["unconfirmed_fallback"] = False

    status["count"] = len(final_offers)
    if last_http_code == 200:
        status["ok"] = True
        if status["count"] == 0 and not status.get("error"):
            status["error"] = "0 offre trouvée pour ces critères"

    return final_offers, status

def fetch_adzuna(
    app_id: str,
    app_key: str,
    queries: List[str],
    country: str = "",
    city: str = "",
    max_results: int = 20
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Interroge l'API Adzuna (clé gratuite sur developer.adzuna.com).
    Couverture RÉELLE : 20 pays (dont France, UK, USA, Allemagne, Canada).
    Aucune valeur par défaut codée en dur.
    """
    norm = normalize_location(country, city)
    status = {
        "name": "Adzuna",
        "ok": False,
        "count": 0,
        "http_status": "N/A",
        "error": None,
        "coverage_desc": f"Adzuna ({norm['canonical_name'] or 'International'})"
    }
    
    code = norm.get("adzuna_code")
    if not code:
        country_label = norm["canonical_name"] if norm["canonical_name"] else "non spécifié"
        status["error"] = f"Le pays '{country_label}' n'est pas couvert par le catalogue Adzuna"
        status["http_status"] = "N/A (Non couvert)"
        return [], status

    if not (app_id and app_key):
        status["error"] = "Identifiants ADZUNA_APP_ID / ADZUNA_APP_KEY non configurés"
        return [], status
        
    base_url = f"https://api.adzuna.com/v1/api/jobs/{code}/search/1"
    matched = []
    
    try:
        search_terms = queries if queries else ["stage"]
        last_code = None
        for q in search_terms[:2]:
            kw = q if any(k in q.lower() for k in INTERNSHIP_KEYWORDS) else f"stage {q}"
            params = {
                "app_id": app_id,
                "app_key": app_key,
                "what": kw,
                "results_per_page": max_results
            }
            if norm["city"]:
                params["where"] = norm["city"]
                
            resp = requests.get(base_url, params=params, timeout=12)
            last_code = resp.status_code
            status["http_status"] = f"HTTP {resp.status_code}"
            
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                for r in results:
                    title = r.get("title", "")
                    job_url = r.get("redirect_url", "")
                    if not job_url:
                        continue
                    company = r.get("company", {}).get("display_name", "Entreprise confidentielle")
                    location = r.get("location", {}).get("display_name", norm["city"] or norm["canonical_name"])
                    snippet = clean_html(r.get("description", ""))[:300]
                    
                    matched.append({
                        "title": title,
                        "company": company,
                        "location": location,
                        "url": job_url,
                        "snippet": snippet,
                        "source": "Adzuna",
                        "is_confirmed_stage": True
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
    Respecte scrupuleusement la localisation demandée (aucune valeur par défaut).
    """
    if secrets is None:
        secrets = {}
        
    all_offers = []
    sources_status = {}
    
    norm = normalize_location(country, city)
    target_country = norm["canonical_name"]
    target_city = norm["city"]
    
    # 1. Arbeitnow (Europe / Remote)
    an_offers, an_status = fetch_arbeitnow(queries, target_country, target_city, max_results=25)
    sources_status["Arbeitnow"] = an_status
    all_offers.extend(an_offers)
    
    # 2. Remotive (100% Télétravail mondial)
    rem_offers, rem_status = fetch_remotive(queries, target_country, target_city, max_results=15)
    sources_status["Remotive"] = rem_status
    all_offers.extend(rem_offers)
    
    # 3. Jooble (70+ pays, actif si clé présente)
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
            "http_status": "N/A (Clé non configurée)",
            "total_count": 0,
            "raw_count": 0,
            "filtered_count": 0,
            "unconfirmed_fallback": False,
            "endpoint_masked": "N/A",
            "keywords_used": "N/A",
            "location_used": norm["jooble_location"],
            "error": "Clé JOOBLE_API_KEY non configurée dans st.secrets",
            "coverage_desc": f"Jooble ({target_country or 'International'})"
        }
        
    # 4. Adzuna (20 pays couverts si clés présentes)
    adzuna_id = secrets.get("ADZUNA_APP_ID", "")
    adzuna_key = secrets.get("ADZUNA_APP_KEY", "")
    if adzuna_id and adzuna_key:
        ad_offers, ad_status = fetch_adzuna(adzuna_id, adzuna_key, queries, target_country, target_city, max_results=20)
        sources_status["Adzuna"] = ad_status
        all_offers.extend(ad_offers)
    else:
        cov_error = "Adzuna ne couvre pas ce pays" if not norm["adzuna_code"] else "Clés ADZUNA non configurées"
        sources_status["Adzuna"] = {
            "name": "Adzuna",
            "ok": False,
            "count": 0,
            "http_status": "N/A (Clés non configurées)",
            "error": cov_error,
            "coverage_desc": f"Adzuna ({target_country or 'International'})"
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
