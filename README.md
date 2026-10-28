# 🎯 Agent IA de Recherche de Stages (100% Gratuit)

Application web propulsée par Streamlit et l'API Google Gemini, permettant aux étudiants et chercheurs de stage d'importer leur CV (PDF), d'indiquer leurs critères géographiques et d'obtenir une sélection classée d'offres de **stages réelles** avec score de pertinence /100, justification personnalisée et conseils d'optimisation.

---

## 🌟 Fonctionnalités Clés
- **100 % Gratuit** : Fonctionne entièrement sur des paliers gratuits, sans carte bancaire requise.
- **Offres 100% Réelles** : Aucune offre ni aucun lien URL n'est inventé par l'IA. Les données proviennent directement d'APIs tierces réelles (**Arbeitnow**, **Remotive**, et optionnellement **Jooble** / **Adzuna**).
- **Analyse IA sur-mesure** : Extraction du profil, compétences clés, génération de requêtes ciblées et notation de chaque offre (/100) par Gemini.
- **Résilience & Cascade de modèles** : Bascule automatique en cas de quota (429) ou de surcharge (503 avec 3 tentatives) :
  1. `gemini-3.6-flash`
  2. `gemini-3.5-flash-lite`
  3. `gemini-3.8-flash`
  4. `gemini-3.7-flash`
- **Protection du quota gratuit** :
  - Limite de 1 recherche toutes les 60 secondes par session.
  - Mise en cache intelligente des résultats pendant 1 heure (`st.cache_data`).
  - Plafond de 30 offres transmises à l'IA.
- **Confidentialité garantie** : Aucun CV n'est stocké sur le serveur. Chaque testeur utilise son propre fichier en mémoire éphémère.

---

## 📋 Prérequis et Clés nécessaires

### 1. Clé Google Gemini (Obligatoire)
- **Coût** : 100 % Gratuit (sans carte bancaire).
- **Obtention** : Rendez-vous sur [Google AI Studio](https://aistudio.google.com/app/apikey) et cliquez sur **Create API Key**.

### 2. Clé Jooble (Optionnelle - Recommandée pour le Maroc & Monde)
- **Coût** : Gratuite.
- **Obtention** : Rendez-vous sur [Jooble API](https://jooble.org/api/about), entrez votre adresse e-mail. La clé est envoyée directement par e-mail.

### 3. Clés Adzuna (Optionnelles - France / Europe / USA)
- **Coût** : Gratuite.
- **Obtention** : Rendez-vous sur [Adzuna Developer](https://developer.adzuna.com).

*(Note : Même sans clé Jooble ou Adzuna, l'application fonctionne immédiatement avec Arbeitnow et Remotive).*

---

## 💻 Installation et Test Local

### 1. Cloner et préparer l'environnement
```bash
cd ~/agent_stage
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configurer les secrets en local
Créez le fichier `.streamlit/secrets.toml` (exclu par `.gitignore`) :
```toml
GEMINI_API_KEY = "votre_cle_gemini_ici"

# Optionnel :
JOOBLE_API_KEY = "votre_cle_jooble"
ADZUNA_APP_ID = "votre_app_id_adzuna"
ADZUNA_APP_KEY = "votre_app_key_adzuna"
```

### 3. Valider les sources et scénarios d'offres sans Gemini
```bash
python test_scenarios.py
python test_sources.py
python test_app.py
```

### 4. Lancer l'application web
```bash
streamlit run agent.py
```
Accédez à l'interface sur `http://localhost:8501`.

---

## 🚀 Déploiement sur Streamlit Community Cloud

1. **Créer le dépôt GitHub public** :
   Le code est synchronisé sur votre dépôt public GitHub (ex: `https://github.com/zelgharb/agent_stage`).
2. **Se connecter à Streamlit Community Cloud** :
   Rendez-vous sur [share.streamlit.io](https://share.streamlit.io) et connectez votre compte GitHub.
3. **Créer une nouvelle application** :
   - **Repository** : `zelgharb/agent_stage`
   - **Branch** : `main`
   - **Main file path** : `agent.py`
4. **Configurer les Secrets** :
   Dans l'écran de configuration (ou dans `Settings` > `Secrets`), collez :
   ```toml
   GEMINI_API_KEY = "votre_cle_gemini"
   # Optionnel :
   JOOBLE_API_KEY = "votre_cle_jooble"
   ```
5. **Cliquer sur Deploy** :
   Votre application sera accessible via son lien public `https://<nom-choisi>.streamlit.app`.

---

## 🔒 Confidentialité
> *« Ton CV est envoyé à l'API Gemini de Google pour l'analyse et n'est pas enregistré par cette application. Sur le palier gratuit, Google peut utiliser ces données pour améliorer ses produits. »*
