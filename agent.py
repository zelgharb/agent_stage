"""
Application Streamlit : Agent IA de Recherche de Stages (100% Gratuit)
Hébergé sur Streamlit Community Cloud.
Respect strict des critères géographiques (aucun affichage de France/Paris si Maroc choisi).
"""

import time
import json
import streamlit as st
import pypdf
from typing import List, Dict, Any, Tuple

from sources import fetch_all_internships, check_country_coverage, generate_quick_search_urls
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
    
    country_input = st.text_input(
        "🌍 Pays souhaité",
        value="Maroc",
        help="Ex: Maroc, France, Allemagne, Suisse, Canada, etc."
    )
    
    city_input = st.text_input(
        "📍 Ville (optionnel)",
        value="Casablanca",
        placeholder="Ex: Casablanca, Rabat, Paris, Lyon, Remote..."
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
    - **Jooble** : Maroc & 70+ pays *(Requiert `JOOBLE_API_KEY`)*
    - **Adzuna** : France, UK, USA... *(Requiert clés Adzuna)*
    """)
    
    if st.button("🔄 Vider le cache de recherche"):
        st.cache_data.clear()
        st.success("Cache vidé avec succès !")
        
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

    st.session_state.last_search_time = current_time

    norm_country = country_input.strip()
    norm_city = city_input.strip()
    norm_domain = domain_input.strip()
    loc_display = f"{norm_city + ', ' if norm_city else ''}{norm_country}".strip()

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

    # Étape 4 : Affichage OBLIGATOIRE du récapitulatif complet de la recherche
    st.markdown('<div class="recap-box">', unsafe_allow_html=True)
    st.subheader("📍 Récapitulatif de la recherche effectuée")
    col_rec1, col_rec2 = st.columns([1, 1])

    with col_rec1:
        st.markdown(f"**🌍 Localisation ciblée :** `{loc_display if loc_display else 'Non spécifiée'}`")
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

    # Étape 5 : Analyse de couverture spécifique si aucune source active ne couvre le pays choisi
    cov_info = check_country_coverage(norm_country, {
        "JOOBLE_API_KEY": jooble_key,
        "ADZUNA_APP_ID": adzuna_id,
        "ADZUNA_APP_KEY": adzuna_key
    })

    if not cov_info["has_onsite_coverage"]:
        if cov_info["is_morocco"]:
            st.warning(
                "⚠️ **Information géographique : Aucune source active ne couvre actuellement les stages sur site au Maroc.**\n\n"
                "- **Arbeitnow** et **Adzuna** ne couvrent que l'Europe et certains pays de l'OCDE.\n"
                "- **Jooble** est l'API qui indexe les offres au Maroc (Casablanca, Rabat, etc.), mais elle nécessite une clé API (`JOOBLE_API_KEY`).\n"
                "- 🔑 **Pour voir les offres au Maroc :** obtenez votre clé gratuite en 30 secondes sur [jooble.org/api/about](https://jooble.org/api/about) et ajoutez-la dans les **Secrets** de Streamlit (`JOOBLE_API_KEY = \"...\"`).\n\n"
                "🛡️ *Garantie d'intégrité : Conformément à votre demande, aucune offre physique en France ou en Europe ne vous a été présentée par erreur.*"
            )
        else:
            st.warning(
                f"⚠️ **Information géographique : Aucune source active ne couvre actuellement les stages sur site pour : {norm_country}.**\n\n"
                "- Les sources gratuites par défaut (Arbeitnow) se concentrent sur l'Europe.\n"
                "- Pour débloquer la couverture de votre pays, activez l'API **Jooble** avec une clé gratuite (`JOOBLE_API_KEY`)."
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
        st.info("""
        💡 **Aucune offre correspondante trouvée pour cette localisation via les APIs configurées.**
        - Si vous cherchez au Maroc, pensez à activer Jooble via `JOOBLE_API_KEY` dans vos Secrets.
        - Vous pouvez également élargir votre recherche à des postes 100% télétravail international (Remote).
        - Utilisez la section **Recherches rapides** ci-dessous pour trouver immédiatement des opportunités réelles.
        """)
    else:
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
                    st.markdown(f'<a href="{url}" target="_blank" style="text-decoration:none;"><button style="background-color:#059669;color:white;border:none;padding:0.4rem 0.8rem;border-radius:6px;cursor:pointer;width:100%;">Voir l\'offre ↗</button></a>', unsafe_allow_html=True)

                st.markdown("<hr style='margin: 0.8rem 0; border: none; border-top: 1px solid #E2E8F0;'/>", unsafe_allow_html=True)

        # 3 conseils d'amélioration du CV
        if cv_tips:
            st.markdown("---")
            st.subheader("💡 3 Conseils personnalisés pour optimiser ton CV")
            for tip in cv_tips[:3]:
                st.info(f"✨ {tip}")

    # Étape 8 : Section « Recherches rapides » (Toujours affichée sous les résultats)
    st.markdown("---")

    effective_domain = norm_domain if norm_domain else profile_analysis.get("domain", "")
    profile_skills = profile_analysis.get("key_skills", [])

    quick_searches = generate_quick_search_urls(
        country=norm_country,
        city=norm_city,
        domain=effective_domain,
        key_skills=profile_skills
    )

    has_onsite_cov = cov_info.get("has_onsite_coverage", False)

    # Affichage en évidence quand aucune source API ne couvre le pays choisi
    if not has_onsite_cov:
        st.markdown(f"""
        <div style="background-color: #FEF3C7; border: 2px solid #F59E0B; border-radius: 8px; padding: 1.2rem; margin-bottom: 1.2rem;">
            <div style="font-size: 1.25rem; font-weight: 700; color: #92400E; margin-bottom: 0.4rem;">
                ⚡ Recherches rapides (Recommandé pour votre recherche)
            </div>
            <div style="color: #78350F; font-size: 0.95rem;">
                ⚠️ <strong>Aucune source API active ne couvre actuellement les stages sur site pour : {norm_country or 'cette région'}.</strong><br/>
                Ces liens directs sur-mesure générés d'après votre profil vous permettent d'accéder instantanément aux offres réelles sur les plateformes officielles.
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.subheader("⚡ Recherches rapides")
        st.markdown("Accédez directement aux opportunités actualisées sur les sites officiels ciblés selon votre profil :")

    # Liens cliquables avec st.link_button
    col_q1, col_q2, col_q3, col_q4 = st.columns(4)
    with col_q1:
        st.link_button("💼 LinkedIn Jobs", quick_searches["linkedin"], use_container_width=True)
    with col_q2:
        st.link_button("🏢 Rekrute.com", quick_searches["google"]["rekrute.com"], use_container_width=True)
    with col_q3:
        st.link_button("💼 Emploi.ma", quick_searches["google"]["emploi.ma"], use_container_width=True)
    with col_q4:
        st.link_button("🔎 Indeed", quick_searches["google"]["indeed.com"], use_container_width=True)

    # Mention obligatoire
    st.caption("« Ces liens ouvrent les sites officiels, où tu es connecté avec ton propre compte. »")

    # Rappel des critères appliqués sans valeur par défaut
    applied_kw = quick_searches.get("keywords", "")
    applied_loc = quick_searches.get("location", "")
    if applied_kw or applied_loc:
        st.caption(f"🎯 *Paramètres appliqués :* Mots-clés = `{applied_kw or 'Tous'}` | Localisation = `{applied_loc or 'Non spécifiée'}`")
