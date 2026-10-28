"""
Application Streamlit : Agent IA de Recherche de Stages (100% Gratuit)
Hébergé sur Streamlit Community Cloud.
"""

import time
import json
import streamlit as st
import pypdf
from typing import List, Dict, Any, Tuple

from sources import fetch_all_internships
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
    La clé de cache utilise les tuples pour garantir l'immutabilité.
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
    
    country_input = st.text_input(
        "🌍 Pays",
        value="France",
        help="Ex: France, Maroc, Allemagne, Suisse, Canada, etc."
    )
    
    city_input = st.text_input(
        "📍 Ville (optionnel)",
        value="",
        placeholder="Ex: Paris, Casablanca, Lyon, Remote..."
    )
    
    domain_input = st.text_input(
        "💼 Domaine (optionnel)",
        value="",
        placeholder="Ex: Data Science, Marketing, Finance..."
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
    st.subheader("ℹ️ Sources actives")
    st.markdown("""
    - **Arbeitnow** : Offres réelles Europe & Télétravail *(Actif)*
    - **Remotive** : Offres réelles Remote mondial *(Actif)*
    - **Jooble** : International & Maroc *(Actif si clé fournie)*
    - **Adzuna** : France, UK, USA *(Actif si clés fournies)*
    """)
    
    st.markdown("---")
    st.caption("🔒 **Respect de la vie privée** : Chaque visiteur teste avec son propre CV. Aucune donnée n'est enregistrée sur le serveur.")

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

search_button = st.button("🚀 Lancer la recherche de stages")

# Traitement lors du clic
if search_button:
    if not uploaded_file:
        st.warning("Veuillez d'abord déposer un fichier CV au format PDF.")
        st.stop()

    # Protection quota gratuit : 1 recherche toutes les 60 secondes par session
    if "last_search_time" not in st.session_state:
        st.session_state.last_search_time = 0

    current_time = time.time()
    elapsed = current_time - st.session_state.last_search_time
    if elapsed < 60:
        remaining = int(60 - elapsed)
        st.warning(f"⏳ **Protection du quota gratuit** : Merci d'attendre encore **{remaining} seconde(s)** avant de relancer une recherche.")
        st.stop()

    # Enregistrement de l'heure de recherche
    st.session_state.last_search_time = current_time

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

    # Étape 2 : Analyse du CV et génération de requêtes avec Gemini
    with st.spinner("🤖 Analyse de ton profil par l'agent IA..."):
        loc_str = f"{city_input.strip()} {country_input.strip()}".strip()
        try:
            profile_analysis = analyze_cv(
                cv_text=extracted_text,
                country_city=loc_str,
                domain=domain_input.strip(),
                duration=duration_input,
                api_key=gemini_key
            )
        except Exception as e:
            st.error(f"❌ Erreur lors de l'analyse du CV : {str(e)}")
            st.stop()

    # Affichage du profil détecté
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

    # Étape 3 : Requêtage des vraies sources d'offres
    queries = profile_analysis.get("search_queries", ["stage"])
    with st.expander("🔍 Requêtes de recherche ciblées générées pour les job-boards", expanded=False):
        for q in queries:
            st.write(f"- `{q}`")

    with st.spinner("🌐 Recherche d'offres de stage réelles en cours sur les sources..."):
        try:
            raw_offers, sources_status = cached_fetch_internships(
                queries_tuple=tuple(queries),
                country=country_input.strip(),
                city=city_input.strip(),
                domain=domain_input.strip(),
                jooble_k=jooble_key,
                adzuna_i=adzuna_id,
                adzuna_k=adzuna_key
            )
        except Exception as e:
            st.error(f"❌ Erreur lors de l'interrogation des sources d'offres : {str(e)}")
            raw_offers = []
            sources_status = {}

    # Rapport d'état des sources dans l'interface
    with st.expander("📊 État des sources d'offres interrogées", expanded=False):
        for s_name, s_info in sources_status.items():
            if s_info.get("ok"):
                st.write(f"✅ **{s_name}** : {s_info.get('count', 0)} offre(s) trouvée(s)")
            else:
                err = s_info.get("error", "Non disponible")
                st.write(f"⚠️ **{s_name}** : {err}")

    # Étape 4 : Vérification des résultats et notation
    if not raw_offers:
        st.warning("⚠️ **Aucune offre de stage correspondante n'a été trouvée pour le moment.**")
        st.info("""
        💡 **Conseils pour trouver des offres :**
        1. Élargis la zone géographique (ex: teste sans ville précise, ou indique un pays limitrophe).
        2. Assure-toi que le domaine n'est pas trop restrictif.
        3. Note qu'aucune offre n'est inventée : l'application n'affiche que des postes réels vérifiés.
        """)
        st.stop()

    # Limitation à 30 offres maximum pour protéger les quotas
    targeted_offers = raw_offers[:30]

    with st.spinner(f"🎯 Évaluation et classement de {len(targeted_offers)} offres réelles par l'IA..."):
        try:
            scored_offers, cv_tips, eval_model = evaluate_offers(
                profile_data=profile_analysis,
                offers=targeted_offers,
                cv_language=profile_analysis.get("language", "fr"),
                api_key=gemini_key
            )
        except Exception as e:
            st.error(f"❌ Erreur lors de la notation des offres : {str(e)}")
            # En cas d'échec de la notation, afficher tout de même les vraies offres brutes
            scored_offers = targeted_offers
            cv_tips = []
            eval_model = "None"

    # Étape 5 : Affichage du tableau classé des offres
    st.markdown("---")
    st.subheader(f"🏆 Offres de stage recommandées ({len(scored_offers)})")

    # Affichage structuré
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

        with st.container():
            col_info, col_score, col_link = st.columns([5, 1.2, 1.8])
            
            with col_info:
                st.markdown(f"**{title}** — *{company}*")
                st.caption(f"📍 {location} | Source : `{source}`")
                st.markdown(f"💡 *{justification}*")
                if snippet:
                    with st.expander("Aperçu de la description", expanded=False):
                        st.write(snippet)
                        
            with col_score:
                st.markdown(f'<span class="{badge_class}">Score : {score} / 100</span>', unsafe_allow_html=True)
                
            with col_link:
                # Lien cliquable direct issu des données de l'API
                st.markdown(f'<a href="{url}" target="_blank" style="text-decoration:none;"><button style="background-color:#059669;color:white;border:none;padding:0.4rem 0.8rem;border-radius:6px;cursor:pointer;width:100%;">Voir l\'offre ↗</button></a>', unsafe_allow_html=True)

            st.markdown("<hr style='margin: 0.8rem 0; border: none; border-top: 1px solid #E2E8F0;'/>", unsafe_allow_html=True)

    # 3 conseils d'amélioration du CV
    if cv_tips:
        st.markdown("---")
        st.subheader("💡 3 Conseils personnalisés pour optimiser ton CV")
        for tip in cv_tips[:3]:
            st.info(f"✨ {tip}")

    st.caption("Données réelles agrégées en direct. Les offres redirigent vers les plateformes d'origine.")
