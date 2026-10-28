"""
Application Streamlit : Agent IA de Recherche de Stages (100% Gratuit)
Hébergé sur Streamlit Community Cloud.
Respect strict des critères géographiques choisis par l'utilisateur.
"""

import time
import json
import streamlit as st
import pypdf
from typing import List, Dict, Any, Tuple

from sources import fetch_all_internships, check_country_coverage, normalize_location
from gemini_client import analyze_cv, evaluate_offers

# Configuration de la page
st.set_page_config(
    page_title="StageFinder AI | Recherche Intelligente de Stages",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS pour une interface soignée et moderne
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .privacy-box {
        background-color: #F8FAFC;
        border-left: 4px solid #3B82F6;
        padding: 0.85rem 1rem;
        border-radius: 4px;
        font-size: 0.85rem;
        color: #334155;
        margin-bottom: 1.5rem;
    }
    .recap-box {
        background-color: #F1F5F9;
        border: 1px solid #CBD5E1;
        border-radius: 8px;
        padding: 1rem;
        margin-top: 1rem;
        margin-bottom: 1.5rem;
    }
    .score-badge-high {
        background-color: #DCFCE7;
        color: #166534;
        font-weight: 700;
        padding: 0.25rem 0.6rem;
        border-radius: 9999px;
        font-size: 0.85rem;
    }
    .score-badge-mid {
        background-color: #FEF3C7;
        color: #92400E;
        font-weight: 700;
        padding: 0.25rem 0.6rem;
        border-radius: 9999px;
        font-size: 0.85rem;
    }
    .score-badge-low {
        background-color: #F1F5F9;
        color: #475569;
        font-weight: 600;
        padding: 0.25rem 0.6rem;
        border-radius: 9999px;
        font-size: 0.85rem;
    }
    .unconfirmed-badge {
        background-color: #FEF08A;
        color: #854D0E;
        font-weight: 700;
        padding: 0.2rem 0.55rem;
        border-radius: 4px;
        font-size: 0.78rem;
        display: inline-block;
        margin-top: 0.2rem;
    }
    .stButton>button {
        background-color: #2563EB;
        color: white;
        font-weight: 600;
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        border: none;
        width: 100%;
    }
    .stButton>button:hover {
        background-color: #1D4ED8;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# Récupération sécurisée des clés depuis st.secrets
def get_secret(key: str, default: str = "") -> str:
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default

gemini_key = get_secret("GEMINI_API_KEY")
jooble_key = get_secret("JOOBLE_API_KEY")
adzuna_id = get_secret("ADZUNA_APP_ID")
adzuna_key = get_secret("ADZUNA_APP_KEY")

# Mise en cache des résultats des sources pendant 1 heure (3600 secondes)
# Note : 'country' et 'city' font explicitement partie de la signature et de la clé de hash du cache
@st.cache_data(ttl=3600, show_spinner=False)
def cached_fetch_internships(
    queries_tuple: Tuple[str, ...],
    country: str,
    city: str,
    domain: str,
    jooble_k: str,
    adzuna_i: str,
    adzuna_k: str
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Interroge et met en cache les résultats des sources d'offres réelles.
    La clé de cache utilise le tuple de requêtes, le pays et la ville.
    """
    secrets_dict = {
        "JOOBLE_API_KEY": jooble_k,
        "ADZUNA_APP_ID": adzuna_i,
        "ADZUNA_APP_KEY": adzuna_k
    }
    return fetch_all_internships(
        queries=list(queries_tuple),
        country=country,
        city=city,
        domain=domain,
        secrets=secrets_dict,
        max_total_offers=30
    )

# Barre latérale (Paramètres & Confidentialité)
with st.sidebar:
    st.header("⚙️ Paramètres de recherche")

    COUNTRY_OPTIONS = [
        "Maroc",
        "France",
        "Belgique",
        "Suisse",
        "Canada",
        "Allemagne",
        "Espagne",
        "Royaume-Uni",
        "États-Unis",
        "Tunisie",
        "Algérie",
        "Sénégal",
        "Côte d'Ivoire",
        "Télétravail / Remote",
        "Autre pays"
    ]
    
    country_selected = st.selectbox(
        "🌍 Pays souhaité",
        options=COUNTRY_OPTIONS,
        index=None,
        placeholder="Choisis un pays...",
        help="Sélectionne ton pays ou 'Télétravail / Remote'. Aucune valeur par défaut."
    )
    
    other_country_input = st.text_input(
        "✍️ Autre pays (saisie libre)",
        value="",
        placeholder="Indique le pays si absent de la liste...",
        help="Utilisé seulement si le pays voulu n'est pas dans la liste déroulante ci-dessus."
    )
    
    city_input = st.text_input(
        "📍 Ville (optionnel)",
        value="",
        placeholder="Laisser vide pour chercher dans tout le pays...",
        help="Si la ville est vide, la recherche porte sur l'ensemble du pays."
    )
    
    domain_input = st.text_input(
        "💼 Domaine (optionnel)",
        value="",
        placeholder="Ex: Data Science, Marketing, Informatique..."
    )
    
    duration_input = st.selectbox(
        "⏱️ Durée du stage souhaitée",
        options=[
            "Indifférente / Toutes durées",
            "Stage court (1 à 2 mois)",
            "Stage intermédiaire (3 à 4 mois)",
            "Stage long / PFE (5 à 6 mois)",
            "Alternance / Contrat pro"
        ],
        index=0
    )
    
    st.markdown("---")
    st.subheader("ℹ️ Couverture réelle des sources")
    st.markdown("""
    - **Arbeitnow** : Offres réelles Europe & Télétravail *(Actif sans clé)*
    - **Remotive** : Télétravail 100% mondial *(Actif sans clé)*
    - **Jooble** : 70+ pays dont Maroc, France... *(Requiert `JOOBLE_API_KEY`)*
    - **Adzuna** : France, UK, USA, Canada... *(Requiert clés Adzuna)*
    """)
    
    if st.button("🔄 Vider le cache de recherche"):
        st.cache_data.clear()
        st.success("Cache vidé avec succès !")
        
    st.markdown("---")
    st.caption("🔒 **Respect de la vie privée** : Chaque visiteur teste avec son propre CV. Aucune donnée n'est enregistrée sur le serveur.")

# Résolution et normalisation du pays et de la ville
if country_selected == "Autre pays":
    raw_chosen_country = other_country_input.strip()
elif country_selected:
    raw_chosen_country = country_selected.strip()
elif other_country_input.strip():
    raw_chosen_country = other_country_input.strip()
else:
    raw_chosen_country = ""

norm_geo = normalize_location(raw_chosen_country, city_input)
norm_country = norm_geo["canonical_name"]
norm_city = norm_geo["city"]
loc_display = norm_geo["display_location"]
is_remote_search = norm_geo["is_remote"]
is_country_chosen = bool(norm_country)

# Corps principal
st.markdown('<div class="main-title">🎯 Agent IA de Recherche de Stages</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Dépose ton CV en PDF, précise tes préférences géographiques et découvre des opportunités réelles avec un score de matching sur-mesure.</div>', unsafe_allow_html=True)

# Message de confidentialité obligatoire
st.markdown("""
<div class="privacy-box">
  🔒 <strong>Confidentialité</strong> : Ton CV est envoyé à l'API Gemini de Google pour l'analyse et n'est pas enregistré par cette application.
  Sur le palier gratuit, Google peut utiliser ces données pour améliorer ses produits.
</div>
""", unsafe_allow_html=True)

# Vérification présence clé Gemini
if not gemini_key:
    st.error("⚠️ **Clé API Gemini non configurée !**")
    st.info("""
    Pour activer l'application, configure ta clé gratuite dans les paramètres de Streamlit Cloud :
    1. Va dans ton tableau de bord Streamlit Community Cloud.
    2. Clique sur les paramètres de l'application -> **Secrets**.
    3. Ajoute la ligne :
    ```toml
    GEMINI_API_KEY = "ta_cle_gemini_ici"
    ```
    """)
    st.stop()

# Zone d'import du CV
uploaded_file = st.file_uploader("📄 Dépose ton CV au format PDF :", type=["pdf"])

# Exigence A.3 : Le bouton est désactivé et affiche un message clair tant qu'aucun pays n'est sélectionné
if not is_country_chosen:
    st.warning("⚠️ **Choisis d'abord un pays** dans la barre latérale pour activer la recherche.")
    search_button = st.button("🚀 Lancer la recherche de stages", disabled=True)
else:
    search_button = st.button("🚀 Lancer la recherche de stages", disabled=False)

# Traitement lors du clic
if search_button:
    if not is_country_chosen:
        st.error("Choisis d'abord un pays.")
        st.stop()

    if not uploaded_file:
        st.warning("Veuillez d'abord déposer un fichier CV au format PDF.")
        st.stop()

    # Protection quota gratuit : 1 recherche par minute par localisation
    # Changer le pays ou la ville relance immédiatement une vraie recherche sans être bloqué
    if "last_searches" not in st.session_state:
        st.session_state.last_searches = {}

    loc_rate_key = f"{norm_country.lower()}||{norm_city.lower()}"
    current_time = time.time()
    last_time_for_loc = st.session_state.last_searches.get(loc_rate_key, 0)
    elapsed = current_time - last_time_for_loc

    if elapsed < 60:
        remaining = int(60 - elapsed)
        st.warning(f"⏳ **Protection du quota gratuit** : Une recherche pour `{loc_display}` a déjà été lancée. Merci d'attendre encore **{remaining} seconde(s)** avant de relancer pour cette localisation.")
        st.stop()

    st.session_state.last_searches[loc_rate_key] = current_time

    norm_domain = domain_input.strip()

    # Étape 1 : Lecture du PDF avec pypdf
    with st.spinner("📖 Lecture et extraction du texte du CV..."):
        extracted_text = ""
        try:
            reader = pypdf.PdfReader(uploaded_file)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    extracted_text += page_text + "\n"
        except Exception as e:
            st.error(f"Erreur technique lors de la lecture du fichier PDF : {str(e)}")
            st.stop()

        extracted_text = extracted_text.strip()
        
        # Validation : moins de 100 caractères -> PDF scanné ou illisible
        if len(extracted_text) < 100:
            st.error("⚠️ **PDF scanné ou illisible, utilise un PDF avec du texte.**")
            st.stop()

    # Étape 2 : Analyse du CV et génération de requêtes adaptées STRICTEMENT à la localisation
    with st.spinner(f"🤖 Analyse de ton profil et ciblage géographique sur '{loc_display}'..."):
        try:
            profile_analysis = analyze_cv(
                cv_text=extracted_text,
                country_city=loc_display,
                domain=norm_domain,
                duration=duration_input,
                api_key=gemini_key
            )
        except Exception as e:
            st.error(f"❌ Erreur lors de l'analyse du CV : {str(e)}")
            st.stop()

    queries = profile_analysis.get("search_queries", ["stage"])

    # Étape 3 : Requêtage des sources réelles avec mise en cache
    with st.spinner(f"🌐 Recherche d'offres réelles pour '{loc_display}'..."):
        try:
            raw_offers, sources_status = cached_fetch_internships(
                queries_tuple=tuple(queries),
                country=norm_country,
                city=norm_city,
                domain=norm_domain,
                jooble_k=jooble_key,
                adzuna_i=adzuna_id,
                adzuna_k=adzuna_key
            )
        except Exception as e:
            st.error(f"❌ Erreur lors de l'interrogation des sources d'offres : {str(e)}")
            raw_offers = []
            sources_status = {}

    # Étape 4 : Affichage OBLIGATOIRE du récapitulatif complet de la recherche (Exigence A.7)
    st.markdown('<div class="recap-box">', unsafe_allow_html=True)
    st.subheader("📍 Récapitulatif de la recherche effectuée")
    col_rec1, col_rec2 = st.columns([1, 1])

    with col_rec1:
        st.markdown(f"**🌍 Pays exact utilisé :** `{norm_country}`")
        st.markdown(f"**📍 Ville exacte utilisée :** `{norm_city if norm_city else 'Toutes les villes (recherche nationale)'}`")
        st.markdown(f"**💼 Domaine :** `{norm_domain if norm_domain else profile_analysis.get('domain', 'Non spécifié')}`")
        st.markdown(f"**⏱️ Durée :** `{duration_input}`")
        st.markdown("**🔍 Requêtes envoyées aux APIs :**")
        for q in queries:
            st.markdown(f"- `{q}`")

    with col_rec2:
        st.markdown("**📊 Offres trouvées par source :**")
        for s_name, s_info in sources_status.items():
            count = s_info.get("count", 0)
            cov = s_info.get("coverage_desc", "")
            if s_info.get("ok") and count > 0:
                st.markdown(f"- ✅ **{s_name}** : **{count} offre(s)** *({cov})*")
            elif s_info.get("ok") and count == 0:
                err = s_info.get("error")
                note = f" — *{err}*" if err else ""
                st.markdown(f"- ⚪ **{s_name}** : 0 offre *({cov})*{note}")
            else:
                err = s_info.get("error", "Non disponible")
                st.markdown(f"- ⚠️ **{s_name}** : {err} *({cov})*")

    st.markdown('</div>', unsafe_allow_html=True)

    # Exigence B.2 : Zone dépliable « Détails techniques » (Statut Jooble, totalCount, avant/après filtre)
    with st.expander("🛠️ Détails techniques (Jooble & Sources)", expanded=False):
        j_info = sources_status.get("Jooble", {})
        st.markdown("#### 🔍 Source : Jooble")
        c_j1, c_j2 = st.columns(2)
        with c_j1:
            st.markdown(f"- **Statut HTTP :** `{j_info.get('http_status', 'N/A')}`")
            st.markdown(f"- **totalCount (Jooble) :** `{j_info.get('total_count', 0)}`")
            st.markdown(f"- **Offres reçues (avant filtre « stage ») :** `{j_info.get('raw_count', 0)}`")
            st.markdown(f"- **Offres retenues (après filtre « stage ») :** `{j_info.get('filtered_count', 0)}`")
        with c_j2:
            st.markdown(f"- **Endpoint contacté :** `{j_info.get('endpoint_masked', 'N/A')}`")
            st.markdown(f"- **Paramètre location envoyé :** `{j_info.get('location_used', 'N/A')}`")
            st.markdown(f"- **Mots-clés envoyés :** `{j_info.get('keywords_used', 'N/A')}`")
            if j_info.get("unconfirmed_fallback"):
                st.info("ℹ️ *Filtre assoupli : Aucune offre n'a passé le filtre strict de stage. Les offres brutes sont affichées avec la mention « stage non confirmé ».*")
            if j_info.get("error"):
                st.caption(f"⚠️ Information : {j_info.get('error')}")

        st.markdown("---")
        st.markdown("#### 🌐 Autres sources")
        for s_name in ["Arbeitnow", "Remotive", "Adzuna"]:
            s_data = sources_status.get(s_name, {})
            s_cnt = s_data.get("count", 0)
            s_http = s_data.get("http_status", "200 OK" if s_data.get("ok") else "N/A")
            s_err = s_data.get("error") or "Aucune erreur"
            st.markdown(f"- **{s_name}** : `{s_cnt} offre(s)` | Statut : `{s_http}` | Info : *{s_err}*")

    # Étape 5 : Analyse de couverture spécifique si aucune source active ne couvre le pays choisi
    cov_info = check_country_coverage(norm_country, {
        "JOOBLE_API_KEY": jooble_key,
        "ADZUNA_APP_ID": adzuna_id,
        "ADZUNA_APP_KEY": adzuna_key
    })

    if not cov_info["has_onsite_coverage"] and not is_remote_search:
        st.warning(
            f"⚠️ **Information géographique : Aucune source active ne couvre actuellement les stages sur site pour : {norm_country}.**\n\n"
            f"- **Arbeitnow** ne couvre que l'Europe et le télétravail.\n"
            f"- **Adzuna** ne couvre pas ce pays ou nécessite des identifiants valides.\n"
            f"- **Jooble** est l'API capable d'indexer les offres pour ce pays, mais elle nécessite une clé (`JOOBLE_API_KEY`).\n"
            f"- 🔑 **Pour débloquer la couverture de {norm_country} :** activez votre clé gratuite sur [jooble.org/api/about](https://jooble.org/api/about) et ajoutez-la dans les Secrets de Streamlit (`JOOBLE_API_KEY = \"...\"`).\n\n"
            f"🛡️ *Garantie d'intégrité : Aucune offre physique d'un autre pays ne vous est présentée.*"
        )

    # Étape 6 : Profil du candidat détecté
    st.success(f"✅ Profil analysé avec succès (Modèle utilisé : `{profile_analysis.get('model_used', 'Gemini')}`) !")
    col_p1, col_p2 = st.columns([2, 1])
    with col_p1:
        st.subheader("📋 Résumé du profil (3 lignes)")
        summary_lines = profile_analysis.get("summary", "").split("\n")
        for line in summary_lines:
            if line.strip():
                st.write(f"• {line.strip()}")
                
    with col_p2:
        st.subheader("🛠️ Compétences clés")
        skills = profile_analysis.get("key_skills", [])
        st.write(", ".join([f"`{s}`" for s in skills[:8]]))

    # Étape 7 : Vérification et affichage des offres
    if not raw_offers:
        st.info(f"""
        💡 **Aucune offre correspondante trouvée pour {loc_display}.**
        - Pour étendre la couverture de ton pays, assure-toi d'avoir configuré `JOOBLE_API_KEY` dans les Secrets.
        - Tu peux également sélectionner l'option **« Télétravail / Remote »** pour découvrir des opportunités internationales en distanciel.
        """)
        st.stop()

    targeted_offers = raw_offers[:30]

    with st.spinner(f"🎯 Évaluation et notation de {len(targeted_offers)} offres par l'IA..."):
        try:
            scored_offers, cv_tips, eval_model = evaluate_offers(
                profile_data=profile_analysis,
                offers=targeted_offers,
                cv_language=profile_analysis.get("language", "fr"),
                api_key=gemini_key
            )
        except Exception as e:
            st.error(f"❌ Erreur lors de la notation des offres : {str(e)}")
            scored_offers = targeted_offers
            cv_tips = []
            eval_model = "None"

    st.markdown("---")
    st.subheader(f"🏆 Offres de stage recommandées ({len(scored_offers)})")

    for offer in scored_offers:
        score = offer.get("score", 50)
        if score >= 75:
            badge_class = "score-badge-high"
        elif score >= 50:
            badge_class = "score-badge-mid"
        else:
            badge_class = "score-badge-low"

        title = offer.get("title", "Poste sans titre")
        company = offer.get("company", "Entreprise")
        location = offer.get("location", "Lieu non précisé")
        url = offer.get("url", "#")
        source = offer.get("source", "Web")
        justification = offer.get("justification", "Offre correspondant à votre domaine.")
        snippet = offer.get("snippet", "")
        is_confirmed = offer.get("is_confirmed_stage", True)

        with st.container():
            col_info, col_score, col_link = st.columns([5, 1.2, 1.8])
            
            with col_info:
                st.markdown(f"**{title}** — *{company}*")
                st.caption(f"📍 {location} | Source : `{source}`")
                if not is_confirmed:
                    st.markdown('<span class="unconfirmed-badge">⚠️ Stage non confirmé</span>', unsafe_allow_html=True)
                st.markdown(f"💡 *{justification}*")
                if snippet:
                    with st.expander("Aperçu de la description", expanded=False):
                        st.write(snippet)
                        
            with col_score:
                st.markdown(f'<span class="{badge_class}">Score : {score} / 100</span>', unsafe_allow_html=True)
                
            with col_link:
                st.markdown(f'<a href="{url}" target="_blank" style="text-decoration:none;"><button style="background-color:#059669;color:white;border:none;padding:0.4rem 0.8rem;border-radius:6px;cursor:pointer;width:100%;">Voir l\'offre ↗</button></a>', unsafe_allow_html=True)

            st.markdown("<hr style='margin: 0.8rem 0; border: none; border-top: 1px solid #E2E8F0;'/>", unsafe_allow_html=True)

    # 3 conseils d'amélioration du CV
    if cv_tips:
        st.markdown("---")
        st.subheader("💡 3 Conseils personnalisés pour optimiser ton CV")
        for tip in cv_tips[:3]:
            st.info(f"✨ {tip}")
