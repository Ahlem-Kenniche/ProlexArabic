# -*- coding: utf-8 -*-
"""
ProlexArabic — Web toolkit for morphological enrichment of Arabic proper names based on ProLexBase.

Run with: streamlit run app/streamlit_app.py
"""

import base64
import io
import json
import math
import os
import re
import time
from datetime import datetime
import requests
import streamlit as st
import pandas as pd
from regles import CATEGORIES, GROUPES, appliquer_regles, appliquer_instances, LABELS_FORMES, STATUT_LABELS, TYPES_AVEC_INSTANCES, normaliser
import db as prolexdb
import notoriete as ntmod

# The original study used Llama 3.3 70B on Groq. That public model was retired
# for Free/Developer accounts in August 2026, so the live demo model is configurable.
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

# English display metadata (internal category keys and rule logic remain unchanged)
_CATEGORY_EN = {
"pays":("Country","Names of sovereign countries"),"region":("Region","Territories within a country"),"supranational":("Supranational entity","Territories spanning several countries — continents"),"territoire":("Territory","General category: country, region, or supranational entity"),"ville":("City","City names"),"geonyme":("Geonym","Natural geographic features"),"hydronyme":("Hydronym","Natural or artificial bodies of water"),"voie":("Thoroughfare","Streets, avenues, squares, and highways"),"edifice":("Building","Buildings, monuments, and places of worship"),"astronyme":("Astronym","Celestial objects — planets, stars, and galaxies"),
"patronyme":("Surname","Family names"),"prenom":("Given name","Given names"),"anthroponyme":("Anthroponym","Names referring to people"),"pseudonyme":("Pseudonym","Assumed names and pen names"),"ethnonyme":("Ethnonym","Names of peoples and ethnic groups"),
"organisation":("Organization","Organizations and institutions"),"entreprise":("Company","Companies and commercial organizations"),"association":("Association","Associations and non-profit organizations"),"parti":("Political party","Political parties"),"equipe":("Team","Sports and other teams"),
"oeuvre":("Work","Titles of creative works"),"evenement":("Event","Named events"),"epoque":("Period","Historical periods"),"fete":("Holiday / Festival","Named holidays and festivals"),"produit":("Product","Named products"),"marque":("Brand","Brand names"),"vehicule":("Vehicle","Named vehicles"),"langue":("Language","Language names"),"religion":("Religion","Names of religions"),"maladie":("Disease","Disease names"),"animal":("Animal","Named animals"),"plante":("Plant","Named plants"),"matiere":("Material","Named materials"),"concept":("Concept","Named concepts"),"titre":("Title","Honorifics and titles"),"document":("Document","Named documents"),"programme":("Program","Named programs"),"autre":("Other","Other proper-name types")
}
for _ck, (_name_en, _desc_en) in _CATEGORY_EN.items():
    if _ck in CATEGORIES:
        CATEGORIES[_ck]["nom_fr"] = _name_en
        CATEGORIES[_ck]["description"] = _desc_en

_GROUP_EN = {"Géographie":"Geography","Personnes":"People","Organisations":"Organizations","Œuvres & événements":"Works & Events","Autres":"Other"}
GROUPES = {_GROUP_EN.get(_g,_g): _v for _g,_v in GROUPES.items()}

# English display labels for generated Nisba forms.
_FORM_EN = {
"singulier_masculin":"Masculine singular","singulier_feminin":"Feminine singular",
"pluriel_masculin_nominatif":"Masculine plural (nominative)","pluriel_masculin_oblique":"Masculine plural (oblique)","pluriel_feminin":"Feminine plural"
}
LABELS_FORMES = {k:(v[0], _FORM_EN.get(k,v[1])) for k,v in LABELS_FORMES.items()}

# =============================================================================
# CONFIGURATION DE LA PAGE
# =============================================================================

st.set_page_config(
    page_title="ProlexArabic — Arabic Proper-Name Enrichment",
    page_icon="🔤",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =============================================================================
# CSS PERSONNALISÉ — DARK MODE MODERNE + RTL
# =============================================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@300;400;500;700;800&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

:root {
    --bg-primary: #f8fafc;
    --bg-secondary: #f1f5f9;
    --bg-card: #ffffff;
    --bg-card-hover: #eef2ff;
    --accent: #6366f1;
    --accent-light: #818cf8;
    --accent-glow: rgba(99, 102, 241, 0.08);
    --text-primary: #1e293b;
    --text-secondary: #64748b;
    --text-muted: #94a3b8;
    --border: #e2e8f0;
    --success: #10b981;
    --warning: #f59e0b;
    --gradient-1: linear-gradient(135deg, #6366f1 0%, #818cf8 100%);
    --gradient-2: linear-gradient(135deg, #6366f1 0%, #7c3aed 100%);
    --shadow-sm: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
    --shadow-md: 0 4px 6px rgba(0,0,0,0.07), 0 2px 4px rgba(0,0,0,0.05);
    --shadow-lg: 0 20px 25px rgba(0,0,0,0.1), 0 10px 10px rgba(0,0,0,0.04);
}

* { box-sizing: border-box; }

.stApp {
    background: var(--bg-primary) !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    color: var(--text-primary);
}

/* Masquer le header Streamlit natif */
header[data-testid="stHeader"] {
    display: none !important;
}
/* Supprimer le padding-top réservé pour le header */
.block-container, [data-testid="stMainBlockContainer"] {
    padding-top: 1rem !important;
}
.stApp header { background-color: transparent !important; }
h1, h2, h3, h4, h5, h6, p, span, div, label {
    color: var(--text-primary) !important;
}

/* RTL pour l'arabe */
.arabic-text {
    direction: rtl;
    text-align: right;
    font-family: 'Tajawal', sans-serif;
    unicode-bidi: bidi-override;
}

/* Hero section */
.hero {
    text-align: center;
    padding: 3rem 1rem 2rem 1rem;
}
.hero-title {
    font-size: 3rem;
    font-weight: 800;
    background: var(--gradient-1);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 0.5rem;
    letter-spacing: -0.5px;
}
.hero-subtitle {
    font-size: 1.15rem;
    color: var(--text-secondary) !important;
    max-width: 700px;
    margin: 0 auto;
    line-height: 1.7;
}
.hero-badge {
    display: inline-block;
    background: var(--accent-glow);
    border: 1px solid var(--accent);
    color: var(--accent-light) !important;
    padding: 0.3rem 1rem;
    border-radius: 20px;
    font-size: 0.8rem;
    margin-bottom: 1rem;
    font-weight: 500;
}

/* Cartes de catégorie */
.cat-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 1rem;
    margin: 1.5rem 0;
}
.cat-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 1.5rem;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    cursor: pointer;
    text-align: center;
    box-shadow: var(--shadow-sm);
}
.cat-card:hover {
    background: var(--bg-card-hover);
    border-color: var(--accent);
    transform: translateY(-4px);
    box-shadow: var(--shadow-lg);
}
.cat-icon { font-size: 2.2rem; margin-bottom: 0.5rem; }
.cat-name {
    font-size: 1.1rem;
    font-weight: 600;
    color: var(--text-primary) !important;
}
.cat-name-ar {
    font-family: 'Tajawal', sans-serif;
    font-size: 1rem;
    color: var(--accent-light) !important;
    direction: rtl;
}
.cat-desc {
    font-size: 0.82rem;
    color: var(--text-secondary) !important;
    margin-top: 0.3rem;
}

/* Section résultat */
.result-container {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 2rem;
    margin: 1rem 0;
    box-shadow: var(--shadow-md);
}
.result-word {
    font-family: 'Tajawal', sans-serif;
    font-size: 2.8rem;
    font-weight: 800;
    text-align: center;
    background: var(--gradient-1);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    direction: rtl;
    margin-bottom: 0.5rem;
}
.result-rule {
    text-align: center;
    color: var(--text-secondary) !important;
    font-size: 0.95rem;
    margin-bottom: 1.5rem;
    padding: 0.5rem 1rem;
    background: var(--accent-glow);
    border-radius: 10px;
    border-left: 3px solid var(--accent);
}

/* Tableau de formes */
.forme-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.9rem 1.2rem;
    border-bottom: 1px solid var(--border);
    transition: background 0.2s;
}
.forme-row:hover { background: rgba(108, 99, 255, 0.05); }
.forme-row:last-child { border-bottom: none; }
.forme-label {
    font-size: 0.85rem;
    color: var(--text-secondary) !important;
    font-weight: 500;
}
.forme-value {
    font-family: 'Tajawal', sans-serif;
    font-size: 1.3rem;
    font-weight: 700;
    color: var(--text-primary) !important;
    direction: rtl;
}
.forme-value-ar {
    font-family: 'Tajawal', sans-serif;
    font-size: 0.8rem;
    color: var(--text-muted) !important;
    direction: rtl;
}

/* Sections panel */
.section-title {
    font-size: 1.15rem;
    font-weight: 700;
    color: var(--text-primary) !important;
    padding-bottom: 0.7rem;
    border-bottom: 2px solid var(--accent);
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

/* Buttons */
.stButton > button {
    background: var(--gradient-1) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 0.6rem 2rem !important;
    font-weight: 600 !important;
    font-size: 1rem !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    box-shadow: 0 2px 8px rgba(99, 102, 241, 0.25) !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px rgba(99, 102, 241, 0.3) !important;
    color: #ffffff !important;
}
/* Boutons retour / navigation — gris discret */
[data-testid="baseButton-secondary"] {
    background: #f1f5f9 !important;
    color: #475569 !important;
    border: 1px solid #e2e8f0 !important;
    box-shadow: none !important;
}
[data-testid="baseButton-secondary"]:hover {
    background: #e2e8f0 !important;
    color: #1e293b !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 2px 6px rgba(0,0,0,0.08) !important;
}
/* Bouton Enregistrer — vert */
[data-testid="baseButton-primary"] {
    background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
    box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3) !important;
}
[data-testid="baseButton-primary"]:hover {
    box-shadow: 0 8px 25px rgba(16, 185, 129, 0.4) !important;
}

/* Input */
.stTextInput > div > div > input {
    background: #ffffff !important;
    border: 2px solid #e2e8f0 !important;
    border-radius: 14px !important;
    color: #1e293b !important;
    -webkit-text-fill-color: #1e293b !important;
    font-family: 'Tajawal', sans-serif !important;
    font-size: 1.4rem !important;
    padding: 0.8rem 1.2rem !important;
    direction: rtl !important;
    text-align: right !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
}
.stTextInput > div > div > input::placeholder {
    color: #94a3b8 !important;
    opacity: 1 !important;
}
.stTextInput > div > div > input:focus {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.12) !important;
}
.stTextInput label {
    color: #64748b !important;
    font-weight: 500 !important;
}

/* Text area */
.stTextArea textarea {
    background: #ffffff !important;
    border: 2px solid #e2e8f0 !important;
    border-radius: 14px !important;
    color: #1e293b !important;
    -webkit-text-fill-color: #1e293b !important;
    font-family: 'Tajawal', sans-serif !important;
    direction: rtl !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
}
.stTextArea textarea::placeholder {
    color: #94a3b8 !important;
    opacity: 1 !important;
}
.stTextArea textarea:focus {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.12) !important;
}

/* Select box */
.stSelectbox > div > div {
    background: #ffffff !important;
    border: 2px solid #e2e8f0 !important;
    border-radius: 12px !important;
    color: #1e293b !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
    cursor: pointer !important;
}
.stSelectbox [data-baseweb="select"] {
    cursor: pointer !important;
}
.stSelectbox [data-baseweb="select"] span {
    color: #1e293b !important;
    cursor: pointer !important;
}
.stSelectbox [data-baseweb="select"] > div {
    cursor: pointer !important;
}
[role="listbox"] {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 12px !important;
    box-shadow: 0 8px 24px rgba(0,0,0,0.1) !important;
    cursor: pointer !important;
}
[role="option"] {
    color: #1e293b !important;
    background: #ffffff !important;
    cursor: pointer !important;
}
[role="option"]:hover {
    background: #eef2ff !important;
    color: #6366f1 !important;
}

/* Divider */
.separator {
    height: 1px;
    background: var(--border);
    margin: 2rem 0;
}

/* Footer */
.footer {
    text-align: center;
    padding: 2rem 0 1rem 0;
    color: var(--text-muted) !important;
    font-size: 0.8rem;
}

/* Tabs override */
.stTabs [data-baseweb="tab-list"] {
    gap: 0.5rem;
    background: var(--bg-secondary);
    border-radius: 12px;
    padding: 0.4rem;
    box-shadow: inset 0 1px 3px rgba(0,0,0,0.04);
}
.stTabs [data-baseweb="tab"] {
    border-radius: 10px !important;
    color: var(--text-secondary) !important;
    transition: all 0.2s ease !important;
    font-weight: 500 !important;
}
.stTabs [aria-selected="true"] {
    background: var(--accent-glow) !important;
    color: var(--accent) !important;
    font-weight: 600 !important;
    box-shadow: var(--shadow-sm) !important;
}

/* Hide streamlit branding */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
.stDeployButton { display: none; }

/* Masquer le message anglais "Press Enter to submit form" */
small[data-testid="InputInstructions"] { display: none !important; }
.stTextInput small { display: none !important; }
[data-testid="InputInstructions"] { display: none !important; }

/* Expander */
.streamlit-expanderHeader {
    background: var(--bg-secondary) !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
}

/* Alerts/info */
.stAlert {
    border-radius: 12px !important;
}

/* Smooth scrolling */
html { scroll-behavior: smooth; }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# GESTION DE L'ÉTAT
# =============================================================================

_DEFAULT_STATE = {
    "page": "landing",         # landing | accueil | prolexbase | prolexbase_detail | categorie | extraction
    "prev_page": "systeme",    # page d'origine avant categorie
    "categorie": None,
    "mot_soumis": "",
    "cat_soumise": "",
    "plx_page": 1,             # pagination prolexbase
    "plx_search": "",
    "plx_type_filter": "",
    "plx_selected": None,      # NUM_PROLEXEME sélectionné
    "extr_texte": "",          # texte saisi en Partie 3
    "plx_mot_query": "",       # mot saisi dans "Identifier un mot"
    "groq_api_key": os.getenv("GROQ_API_KEY", ""),
    "extr_classified": {},      # {nom: type} résultats classification LLM
    "extr_version": 0,          # incrémenté à chaque nouvelle extraction
    # ── Import base ──
    "base_df": None,            # list[dict] — données du fichier importé
    "base_filename": "",        # nom du fichier
    "base_col": "",             # colonne sélectionnée comme prolexèmes
    "base_classified": {},      # {nom: type} résultats classification base
    "base_classify_version": 0, # incrémenté à chaque nouvelle classification
    # ── Feedback ──
    "feedback_sent": False,         # True après soumission dans la session
    "landing_loading": False,        # True pendant la transition landing → accueil
    "modal_shown_1": False,
    "modal_shown_2": False,
    "modal_shown_3": False,
}

for _k, _v in _DEFAULT_STATE.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── Chemin du logo ──
_LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logo.png")
if not os.path.exists(_LOGO_PATH):
    for _c in [
        os.path.join(os.getcwd(), "logo.png"),
        os.path.join(os.getcwd(), "..", "logo.png"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.png"),
    ]:
        if os.path.exists(_c):
            _LOGO_PATH = _c
            break


_REMOVED_T = {
    "fr": {
        # Splash
        "splash_badge":    "Natural Language Processing",
        "splash_subtitle": "Morphological enrichment platform for Arabic proper names",
        "splash_enter":    "Enter the system",
        "splash_about":    "About",
        # Accueil (3 parties)
        "hero_badge":   "Arabic Morphological Enrichment",
        "hero_sub":     "Exploration and enrichment platform for <strong style='color:#6366f1;'>Arabic proper names</strong> — instances, derivatives, morphology, and classification.",
        "p1_title":     "Part 1 — ProLexBase",
        "p1_desc":      "Explore <strong style='color:#6366f1;'>15 000+</strong> Arabic prolexemes — browse instances, derivatives, and pivots.",
        "p1_btn":       "🗄️ Open ProLexBase",
        "p2_title":     "Part 2 — Open System",
        "p2_desc":      "Generate <strong style='color:#6366f1;'>instances</strong> and <strong style='color:#10b981;'>derivatives</strong> (Nisba) of Arabic proper names.",
        "p2_btn":       "⚙️ Open Rule System",
        "p3_title":     "Part 3 — Extraction",
        "p3_desc":      "Extract <strong style='color:#6366f1;'>proper names</strong> from Arabic text and classify them automatically.",
        "p3_btn":       "📝 Open Extraction",
        "footer":       "ProlexArabic — Morphological enrichment of Arabic proper names",
        "suggestion":   "💡 Suggest an improvement",
        # About
        "about_retour": "← Back to home",
    },
    "en": {
        # Splash
        "splash_badge":    "Natural Language Processing",
        "splash_subtitle": "Arabic proper noun morphological enrichment platform",
        "splash_enter":    "Enter the system",
        "splash_about":    "About",
        # Accueil (3 parties)
        "hero_badge":   "Arabic Morphological Enrichment",
        "hero_sub":     "Exploration and enrichment platform for <strong style='color:#6366f1;'>Arabic proper nouns</strong> — instances, derivatives, morphology and classification.",
        "p1_title":     "Part 1 — ProLexBase",
        "p1_desc":      "Explore <strong style='color:#6366f1;'>15,000+</strong> Arabic prolexemes — instances, derivatives and pivots.",
        "p1_btn":       "🗄️ Open ProLexBase",
        "p2_title":     "Part 2 — Open System",
        "p2_desc":      "Generate <strong style='color:#6366f1;'>instances</strong> and <strong style='color:#10b981;'>derivatives</strong> (Nisba) from Arabic proper nouns.",
        "p2_btn":       "⚙️ Open Rule System",
        "p3_title":     "Part 3 — Extraction",
        "p3_desc":      "Extract <strong style='color:#6366f1;'>proper nouns</strong> from Arabic text and classify them automatically.",
        "p3_btn":       "📝 Open Extraction",
        "footer":       "ProlexArabic — Arabic proper noun morphological enrichment",
        "suggestion":   "💡 Suggest an improvement",
        # About
        "about_retour": "← Back to home",
    },
}



@st.cache_data(ttl=600)
def _get_stats():
    s = prolexdb.get_stats()
    return dict(s)

@st.cache_data(ttl=600)
def _get_all_types():
    return [dict(r) for r in prolexdb.get_all_types()]

@st.cache_data(ttl=600)
def _get_type_distribution():
    return [dict(r) for r in prolexdb.get_type_distribution()]

@st.cache_data(ttl=600)
def _get_prolexeme_by_id(num_plx):
    r = prolexdb.get_prolexeme_by_id(num_plx)
    return dict(r) if r else None

@st.cache_data(ttl=600)
def _get_pivot_info(num_pivot):
    r = prolexdb.get_pivot_info(num_pivot)
    return dict(r) if r else None

@st.cache_data(ttl=120)
def _get_frequences_cached(lang_code, num_plx):
    rows = ntmod.get_frequences_prolexeme(lang_code, num_plx)
    return [(r[0], r[1], r[2]) for r in rows]


def aller_categorie(cat_key):
    st.session_state.prev_page = "systeme"
    st.session_state.page = "categorie"
    st.session_state.categorie = cat_key
    st.session_state.mot_soumis = ""
    st.session_state.cat_soumise = cat_key


def aller_accueil():
    st.session_state.page = "accueil"
    st.session_state.categorie = None
    st.session_state.mot_soumis = ""
    st.session_state.cat_soumise = ""


def aller_prolexbase():
    st.session_state.page = "prolexbase"
    st.session_state.plx_selected = None


def aller_prolexbase_detail(num_prolexeme):
    st.session_state.page = "prolexbase_detail"
    st.session_state.plx_selected = num_prolexeme


def aller_systeme():
    st.session_state.page = "accueil"


def aller_extraction():
    st.session_state.page = "extraction"
    st.session_state.extr_texte = ""


def aller_base_import():
    st.session_state.page = "base_import"


def aller_base_classify():
    st.session_state.page = "base_classify"
    st.session_state.base_classified = {}
    st.session_state.base_classify_version += 1


def _aller_retour_extraction():
    st.session_state.page = "extraction"


def _aller_regles_avec_mot(cat_key, mot):
    """Aller en Partie 2 (règles) avec le mot et la catégorie pré-remplis."""
    st.session_state.prev_page = "extraction"
    st.session_state.page = "categorie"
    st.session_state.categorie = cat_key
    st.session_state.mot_soumis = mot
    st.session_state.cat_soumise = cat_key


# =============================================================================
# PAGE D'ACCUEIL
# =============================================================================

def _card_categorie(col, key, cat):
    """Affiche une carte de catégorie dans une colonne donnée."""
    with col:
        st.markdown(
            f"<div style='text-align:center; padding:0.6rem 0 0.2rem 0;'>"
            f"<span style='font-size:2rem;'>{cat['icone']}</span><br>"
            f"<span style='font-weight:700; font-size:0.95rem; color:#1e293b;'>{cat['nom_fr']}</span><br>"
            f"<span style='font-family:Tajawal,sans-serif; font-size:0.88rem; color:#818cf8; direction:rtl;'>{cat['nom']}</span><br>"
            f"<span style='font-size:0.72rem; color:#64748b;'>{cat['description']}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
        st.button(
            f"Ouvrir →",
            key=f"btn_{key}",
            on_click=aller_categorie,
            args=(key,),
            use_container_width=True,
        )


def page_landing():
    import base64 as _b64
    _logo_b64 = ""
    for _lp in [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logo-removebg-preview.png"),
        os.path.join(os.getcwd(), "logo-removebg-preview.png"),
        os.path.join(os.getcwd(), "..", "logo-removebg-preview.png"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo-removebg-preview.png"),
    ]:
        if os.path.exists(_lp):
            with open(_lp, "rb") as _f:
                _logo_b64 = _b64.b64encode(_f.read()).decode()
            break

    # ── Transition loading ────────────────────────────────────────────────────
    if st.session_state.get("landing_loading"):
        _logo_src = ("data:image/png;base64," + _logo_b64) if _logo_b64 else ""
        _tr_html = (
            "<style>"
            "@keyframes tr-fade-up{from{opacity:0;transform:translateY(18px)}to{opacity:1;transform:translateY(0)}}"
            "@keyframes tr-fill{0%{width:0%}12%{width:9%}35%{width:38%}60%{width:59%}80%{width:79%}92%{width:90%}100%{width:100%}}"
            "@keyframes tr-shimmer{0%{background-position:-400% 0}100%{background-position:400% 0}}"
            "@keyframes tr-float{0%,100%{transform:translateY(0) scale(1)}50%{transform:translateY(-22px) scale(1.04)}}"
            "@keyframes tr-blink{0%,80%,100%{opacity:.3;transform:scale(.55)}40%{opacity:1;transform:scale(1)}}"
            ".tr-screen{position:fixed;inset:0;z-index:9999;background:#f9fafb;"
            "display:flex;align-items:center;justify-content:center;"
            "font-family:-apple-system,'Segoe UI',sans-serif;}"
            ".tr-blob{position:absolute;border-radius:50%;pointer-events:none;animation:tr-float 8s ease-in-out infinite;}"
            ".tr-blob-a{width:560px;height:560px;top:-180px;right:-140px;"
            "background:radial-gradient(circle,rgba(139,92,246,.13) 0%,transparent 68%);filter:blur(1px);}"
            ".tr-blob-b{width:480px;height:480px;bottom:-150px;left:-130px;"
            "background:radial-gradient(circle,rgba(99,102,241,.10) 0%,transparent 68%);filter:blur(1px);animation-delay:-4s;}"
            ".tr-card{position:relative;z-index:2;display:flex;flex-direction:column;align-items:center;gap:1.75rem;"
            "background:rgba(255,255,255,.88);border:1px solid rgba(139,92,246,.13);border-radius:30px;"
            "padding:3.2rem 4.5rem;"
            "box-shadow:0 12px 48px rgba(99,102,241,.09),0 2px 10px rgba(0,0,0,.04);"
            "animation:tr-fade-up .5s cubic-bezier(.22,1,.36,1);}"
            ".tr-logo{width:148px;height:auto;display:block;"
            "image-rendering:-webkit-optimize-contrast;"
            "animation:tr-fade-up .6s cubic-bezier(.22,1,.36,1) .08s both;}"
            ".tr-brand{font-size:1.38rem;font-weight:700;letter-spacing:-.03em;"
            "background:linear-gradient(120deg,#5b58eb 0%,#8b5cf6 40%,#a78bfa 60%,#6366f1 100%);"
            "background-size:300% auto;-webkit-background-clip:text;background-clip:text;"
            "-webkit-text-fill-color:transparent;"
            "animation:tr-shimmer 2.6s linear infinite,tr-fade-up .6s cubic-bezier(.22,1,.36,1) .16s both;}"
            ".tr-bar-wrap{width:230px;animation:tr-fade-up .6s cubic-bezier(.22,1,.36,1) .24s both;}"
            ".tr-bar-track{width:100%;height:3px;background:#ede9fe;border-radius:99px;overflow:hidden;}"
            ".tr-bar-fill{height:100%;background:linear-gradient(90deg,#818cf8,#7c3aed,#a78bfa,#818cf8);"
            "background-size:300% 100%;border-radius:99px;"
            "animation:tr-fill 2.85s cubic-bezier(.4,0,.2,1) forwards,tr-shimmer 2s linear infinite;}"
            ".tr-sub{font-size:.71rem;color:#9ca3af;letter-spacing:.14em;text-transform:uppercase;"
            "animation:tr-fade-up .6s cubic-bezier(.22,1,.36,1) .32s both;}"
            ".tr-dots{display:flex;gap:7px;align-items:center;animation:tr-fade-up .6s cubic-bezier(.22,1,.36,1) .4s both;}"
            ".tr-dot{width:6px;height:6px;border-radius:50%;background:#c4b5fd;animation:tr-blink 1.3s ease-in-out infinite;}"
            ".tr-dot:nth-child(2){animation-delay:.22s;}.tr-dot:nth-child(3){animation-delay:.44s;}"
            "</style>"
            "<div class=\"tr-screen\">"
            "  <div class=\"tr-blob tr-blob-a\"></div>"
            "  <div class=\"tr-blob tr-blob-b\"></div>"
            "  <div class=\"tr-card\">"
            "    <img class=\"tr-logo\" src=\"" + _logo_src + "\" alt=\"ProlexArabic\"/>"
            "    <div class=\"tr-brand\">ProlexArabic</div>"
            "    <div class=\"tr-bar-wrap\"><div class=\"tr-bar-track\"><div class=\"tr-bar-fill\"></div></div></div>"
            "    <div class=\"tr-sub\">Opening the platform</div>"
            "    <div class=\"tr-dots\"><div class=\"tr-dot\"></div><div class=\"tr-dot\"></div><div class=\"tr-dot\"></div></div>"
            "  </div>"
            "</div>"
        )
        st.markdown(_tr_html, unsafe_allow_html=True)
        time.sleep(3)
        st.session_state.landing_loading = False
        st.session_state.page = "accueil"
        st.rerun()
        return

    # ── Page landing normale ──────────────────────────────────────────────────
    if _logo_b64:
        _img_tag = (
            '<img src="data:image/png;base64,' + _logo_b64 + '"'
            ' style="width:260px;height:auto;display:block;margin:0 auto 1.6rem auto;'
            'image-rendering:-webkit-optimize-contrast;" alt="ProlexArabic"/>'
        )
    else:
        _img_tag = '<div style="font-size:5rem;text-align:center;margin-bottom:1.5rem;">\U0001f524</div>'

    st.markdown(
        (
            "<style>"
            "footer{display:none!important;}"
            ".stApp>[data-testid='stDecoration']{display:none!important;}"
            "[data-testid='stBottom']{display:none!important;}"
            ".block-container{padding-bottom:0!important;}"
            ".ldp{text-align:center;padding:2.8rem 1rem 2rem 1rem;}"
            # badge
            ".ldp-badge{"
            "display:inline-flex;align-items:center;gap:8px;"
            "font-size:.64rem;font-weight:700;letter-spacing:2px;text-transform:uppercase;"
            "color:#6366f1;background:rgba(99,102,241,0.06);"
            "border:1px solid rgba(99,102,241,0.2);border-radius:100px;"
            "padding:7px 20px;margin-bottom:3rem;}"
            ".ldp-bdot{"
            "width:6px;height:6px;border-radius:50%;"
            "background:#6366f1;box-shadow:0 0 6px #6366f1;"
            "display:inline-block;flex-shrink:0;"
            "animation:ldpBlink 2s ease infinite;}"
            "@keyframes ldpBlink{0%,100%{opacity:1}50%{opacity:.3}}"
            # description
            ".ldp-sub{"
            "font-size:clamp(.88rem,1.6vw,1rem);color:#64748b;line-height:1.9;"
            "margin:0 auto 2.4rem auto;max-width:480px;}"
            # pills
            ".ldp-feats{"
            "display:flex;flex-wrap:wrap;gap:8px;"
            "justify-content:center;margin-bottom:2.8rem;}"
            ".ldp-feat{"
            "display:inline-flex;align-items:center;gap:6px;"
            "font-size:.71rem;font-weight:600;color:#6366f1;"
            "background:rgba(99,102,241,0.07);border:1px solid rgba(99,102,241,0.18);"
            "border-radius:8px;padding:6px 15px;"
            "letter-spacing:.2px;transition:all .2s;cursor:default;}"
            ".ldp-feat:hover{"
            "background:rgba(99,102,241,0.13);border-color:rgba(99,102,241,0.35);"
            "transform:translateY(-2px);}"
            # bouton CTA landing — override global pour padding/shadow
            ".stButton>button{"
            "background:linear-gradient(135deg,#4f46e5 0%,#6366f1 60%,#818cf8 100%)!important;"
            "box-shadow:0 4px 24px rgba(99,102,241,.35),0 1px 4px rgba(0,0,0,.06)!important;"
            "padding:14px 40px!important;border-radius:12px!important;"
            "font-size:.95rem!important;font-weight:600!important;color:#fff!important;}"
            ".stButton>button:hover{"
            "transform:translateY(-3px)!important;"
            "box-shadow:0 8px 36px rgba(99,102,241,.45)!important;}"
            "</style>"
            "<div class='ldp'>"
            "<div class='ldp-badge'><span class='ldp-bdot'></span>"
            "M&eacute;moire de Fin d&apos;&Eacute;tudes"
            " &nbsp;&middot;&nbsp; Natural Language Processing</div>"
            "<br>"
            + _img_tag
            + "<div class='ldp-sub'>"
            "Platform for exploring and enriching "
            "<strong style='color:#6366f1;font-weight:600;'>Arabic proper names</strong>"
            " &mdash; instances, derivatives, morphology, and automatic classification."
            "</div>"
            "<div class='ldp-feats'>"
            "<span class='ldp-feat'>&#128197;&nbsp;ProLexBase</span>"
            "<span class='ldp-feat'>&#9881;&#65039;&nbsp;Rule System</span>"
            "<span class='ldp-feat'>&#10024;&nbsp;Instance &amp; derivative generation</span>"
            "<span class='ldp-feat'>&#128203;&nbsp;Automatic extraction</span>"
            "</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    # ── Bouton CTA — colonnes [3,2,3] + use_container_width ──────────────────
    # La colonne centrale est mathématiquement centrée sur la page.
    # use_container_width=True remplit la colonne → aucun problème d'alignement interne.
    _, _bc, _ = st.columns([3, 2, 3])
    with _bc:
        if st.button(
            "Enter the system →",
            key="btn_landing_go",
            use_container_width=True,
        ):
            st.session_state.landing_loading = True
            st.rerun()

    # ── Footer auteur — dernier élément de la page ──
    st.markdown(
        "<div style='text-align:center;margin-top:2.8rem;padding-bottom:1.2rem;"
        "font-size:.8rem;color:#94a3b8;line-height:2;'>"
        "Travail r&eacute;alis&eacute; par "
        "<span style='color:#6366f1;font-weight:500;font-size:.84rem;'>"
        "KHEDRAOUI Amine"
        "</span>"
        "<span style='margin:0 .5rem;color:#c7d2fe;'>&middot;</span>"
        "M&eacute;moire de fin d&apos;&eacute;tudes en Informatique"
        "<span style='margin:0 .5rem;color:#c7d2fe;'>&middot;</span>"
        "2025&ndash;2026"
        "<span style='margin:0 .5rem;color:#c7d2fe;'>&middot;</span>"
        "<a href='https://www.linkedin.com/in/mohamed-khadraoui-2829a02a9' target='_blank' "
        "style='color:#6366f1;font-weight:500;text-decoration:none;"
        "border-bottom:1px solid rgba(99,102,241,.35);padding-bottom:1px;"
        "transition:opacity .2s;'>Me contacter</a>"
        "</div>",
        unsafe_allow_html=True,
    )


def aller_accueil():
    st.session_state.page = "accueil"


def page_accueil():
    # Bouton About — haut droite
    _, col_about = st.columns([6, 1])
    with col_about:
        st.button("ℹ️ About", key="acc_btn_about", on_click=aller_about)

    # Hero — titre principal
    st.markdown(
        "<div style='text-align:center; padding:3.5rem 1rem 2rem 1rem;'>"
        "<div style='display:inline-block; background:linear-gradient(135deg,rgba(99,102,241,0.12),rgba(129,140,248,0.08));"
        " border:1px solid rgba(99,102,241,0.2); border-radius:50px; padding:0.35rem 1.2rem;"
        " font-size:0.78rem; font-weight:600; color:#6366f1; letter-spacing:1px;"
        " text-transform:uppercase; margin-bottom:1.2rem;'>Arabic Morphological Enrichment</div><br>"
        "<div style='font-size:3rem; font-weight:900; background:linear-gradient(135deg,#6366f1,#818cf8);"
        " -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;"
        " line-height:1.1; letter-spacing:-1px; margin-bottom:0.6rem;'>ProlexArabic</div>"
        "<div style='font-size:1.1rem; font-weight:500; color:#475569;"
        " max-width:560px; margin:0 auto; line-height:1.6;'>Exploration and enrichment platform for "
        "<strong style='color:#6366f1;'>Arabic proper names</strong> \u2014 instances, d\u00e9riv\u00e9s, morphologie et classification.</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown("<hr style='border:none; border-top:1px solid #e2e8f0; margin:0.5rem 0 2rem 0;'>",
                unsafe_allow_html=True)

    # ── Les 3 sections principales côte à côte ──
    col_a, col_b, col_c = st.columns(3)

    # Section 1 : ProLexBase
    with col_a:
        st.markdown(
            "<div style='background:#ffffff; border:1px solid #e2e8f0; border-radius:18px;"
            " padding:2rem 1.3rem; min-height:280px; box-shadow:0 2px 12px rgba(0,0,0,0.04);'>"
            "<div style='font-size:2.5rem; text-align:center; margin-bottom:0.8rem;'>🗄️</div>"
            "<div style='font-size:1.15rem; font-weight:700; color:#1e293b; text-align:center;'>"
            "Part 1 — ProLexBase</div>"
            "<div style='color:#64748b; font-size:0.85rem; text-align:center; margin-top:0.5rem; line-height:1.7;'>"
            "Explore <strong style='color:#6366f1;'>15 000+</strong> Arabic prolexemes — browse instances, derivatives, and pivots.</div>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.button("🗄️ Open ProLexBase", key="btn_prolexbase", on_click=aller_prolexbase, use_container_width=True)

    # Section 2 : Système de Rules
    with col_b:
        st.markdown(
            "<div style='background:#ffffff; border:1px solid #e2e8f0; border-radius:18px;"
            " padding:2rem 1.3rem; min-height:280px; box-shadow:0 2px 12px rgba(0,0,0,0.04);'>"
            "<div style='font-size:2.5rem; text-align:center; margin-bottom:0.8rem;'>⚙️</div>"
            "<div style='font-size:1.15rem; font-weight:700; color:#1e293b; text-align:center;'>"
            "Part 2 — Open System</div>"
            "<div style='color:#64748b; font-size:0.85rem; text-align:center; margin-top:0.5rem; line-height:1.7;'>"
            "Generate <strong style='color:#6366f1;'>instances</strong> et "
            "<strong style='color:#10b981;'>derivatives</strong> (Nisba) of Arabic proper names.</div></div>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.button("⚙️ Open Rule System", key="btn_systeme", on_click=aller_systeme_accueil, use_container_width=True)

    # Section 3 : Extraction
    with col_c:
        st.markdown(
            "<div style='background:#ffffff; border:1px solid #e2e8f0; border-radius:18px;"
            " padding:2rem 1.3rem; min-height:280px; box-shadow:0 2px 12px rgba(0,0,0,0.04);'>"
            "<div style='font-size:2.5rem; text-align:center; margin-bottom:0.8rem;'>📝</div>"
            "<div style='font-size:1.15rem; font-weight:700; color:#1e293b; text-align:center;'>"
            "Part 3 — Extraction</div>"
            "<div style='color:#64748b; font-size:0.85rem; text-align:center; margin-top:0.5rem; line-height:1.7;'>"
            "Extract <strong style='color:#6366f1;'>proper names</strong> from Arabic text and classify them automatically.</div>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.button("📝 Open Extraction", key="btn_extraction", on_click=aller_extraction, use_container_width=True)

    st.markdown(
        "<div style='text-align:center; padding:2.5rem 0 0.3rem 0;'>"
        "<span style='color:#94a3b8; font-size:0.78rem;'>ProlexArabic — Morphological enrichment of Arabic proper names</span><br>"
        "<span style='color:#cbd5e1; font-size:0.75rem;'>Have a suggestion? </span>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown("""
<style>
div[data-testid="stButton"] button[kind="secondary"][id*="btn_feedback"] {
    background: transparent !important;
    border: 1px solid #e2e8f0 !important;
    color: #64748b !important;
    font-size: 0.82rem !important;
    box-shadow: none !important;
}
div[data-testid="stButton"] button[kind="secondary"][id*="btn_feedback"]:hover {
    border-color: #c7d2fe !important;
    color: #6366f1 !important;
    background: rgba(99,102,241,0.04) !important;
}
</style>""", unsafe_allow_html=True)
    col_fb_l, col_fb_c, col_fb_r = st.columns([4, 2, 4])
    with col_fb_c:
        st.button("💡 Suggest an improvement", key="btn_feedback", on_click=aller_feedback, use_container_width=True)




def aller_systeme_accueil():
    st.session_state.page = "systeme"


def aller_feedback():
    st.session_state.page = "feedback"
    st.session_state.feedback_sent = False


def aller_about():
    st.session_state.page = "about"





# =============================================================================
# AFFICHAGE INDICE DE NOTORIÉTÉ
# =============================================================================

_FREQ_COLORS = {1: "#10b981", 2: "#f59e0b", 3: "#ef4444", 4: "#94a3b8"}
_FREQ_ICONS  = {1: "🟢", 2: "🟡", 3: "🔴", 4: "⚫"}
_FREQ_LABELS = {1: "Frequent", 2: "Less frequent", 3: "Rare", 4: "Very rare"}
_LANG_LABELS = {"arb": "🇸🇦 Arabic", "pol": "🇵🇱 Polish", "srp": "🇷🇸 Serbian"}


@st.cache_data(ttl=120)
def _cached_check_mysql(pairs_tuple):
    """Vérifie les paires (lang, num) dans MySQL — mis en cache 2 min pour éviter les reconnexions répétées."""
    return ntmod.check_prolexemes_in_mysql(list(pairs_tuple))


@st.cache_data(ttl=120)
def _trouver_frequence_pivot(lang_code, num_pivot):
    """Cherche la fréquence d'un prolexème via son pivot dans une autre langue."""
    import sqlite3
    conn = sqlite3.connect(ntmod.DB_PATH)
    row = conn.execute(
        f"SELECT p.NUM_PROLEXEME, p.LABEL_PROLEXEME, p.WIKIPEDIA_LINK "
        f"FROM prolexeme_{lang_code} p WHERE p.NUM_PIVOT = ?",
        (num_pivot,),
    ).fetchone()
    if not row:
        conn.close()
        return None, None, [], None
    num_plx_lang = row[0]
    label_lang = row[1]
    wiki_link = row[2]
    freq_rows = conn.execute(
        f"SELECT yf.YEAR_FREQUENCY, f.FRA_FREQUENCY, fl.NUM_FREQUENCY "
        f"FROM frequency_{lang_code} fl "
        f"JOIN year_frequency yf ON fl.NUM_YEAR_FREQUENCY = yf.NUM_YEAR_FREQUENCY "
        f"JOIN frequency f ON fl.NUM_FREQUENCY = f.NUM_FREQUENCY "
        f"WHERE fl.NUM_PROLEXEME = ? ORDER BY yf.YEAR_FREQUENCY",
        (num_plx_lang,),
    ).fetchall()
    conn.close()
    return num_plx_lang, label_lang, freq_rows, wiki_link


def _afficher_notoriete_prolexeme(num_plx, label, num_pivot, wiki_link_arb=None):
    """Affiche l'indice de notoriété pour un prolexème (toutes langues)."""
    st.markdown(
        "<div style='font-size:1rem; font-weight:700; color:#1e293b; margin-bottom:1rem;'>"
        "📊 Temporal Notoriety Index</div>",
        unsafe_allow_html=True,
    )

    found_any = False
    plx_ids = {}

    # ── Phase 1 : collecte données SQLite (local, rapide) ──────────────────
    lang_data = {"arb": {
        "plx_num": num_plx, "plx_label": label,
        "freqs": _get_frequences_cached("arb", num_plx),
        "wiki_link": wiki_link_arb,
    }}
    for _lc in ("pol", "srp"):
        _n, _lbl, _fr, _wl = _trouver_frequence_pivot(_lc, num_pivot)
        lang_data[_lc] = {"plx_num": _n, "plx_label": _lbl, "freqs": _fr, "wiki_link": _wl}

    # ── Phase 2 : UN SEUL appel MySQL, mis en cache 2 min ──────────────────
    _cas3_pairs = tuple(
        (lc, d["plx_num"])
        for lc, d in lang_data.items()
        if d["freqs"] and d["plx_num"] is not None
    )
    _already_in_mysql = _cached_check_mysql(_cas3_pairs)

    # ── Phase 3 : affichage ────────────────────────────────────────────────
    for lang_code, lang_label in _LANG_LABELS.items():
        d = lang_data[lang_code]
        plx_num_lang = d["plx_num"]
        plx_label    = d["plx_label"]
        freqs        = d["freqs"]
        wiki_link    = d["wiki_link"]

        # ── Cas 1 : concept inexistant dans cette langue ────────────────────
        if lang_code != "arb" and plx_label is None:
            found_any = True
            st.markdown(
                f"<div style='display:flex; align-items:center; gap:1rem; padding:0.7rem 1.2rem;"
                f" background:#f8fafc; border-left:4px solid #e2e8f0; border-radius:0 12px 12px 0;"
                f" margin-bottom:0.5rem; opacity:0.6;'>"
                f"<div style='font-size:1.6rem; color:#cbd5e1;'>—</div>"
                f"<div>"
                f"<div style='font-size:0.85rem; font-weight:600; color:#94a3b8;'>{lang_label}</div>"
                f"<div style='font-size:0.75rem; color:#cbd5e1;'>No equivalent in this language</div>"
                f"</div></div>",
                unsafe_allow_html=True,
            )
            continue

        # ── Cas 2 : pas encore calculé ─────────────────────────────────────
        if not freqs:
            found_any = True
            calc_key = f"calc_{lang_code}_{plx_num_lang}"
            st.markdown(
                f"<div style='display:flex; align-items:center; gap:1rem; padding:1rem 1.2rem;"
                f" background:linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);"
                f" border-left:4px solid #818cf8; border-radius:0 14px 14px 0;"
                f" margin-bottom:0.5rem; box-shadow:0 1px 4px rgba(0,0,0,0.04);'>"
                f"<div style='font-size:2rem; font-weight:900; color:#818cf8;'>📊</div>"
                f"<div style='flex:1;'>"
                f"<div style='font-size:0.88rem; font-weight:700; color:#1e293b;'>"
                f"{lang_label}"
                f"{(' — ' + plx_label) if plx_label else ''}"
                f"</div>"
                f"<div style='font-size:0.78rem; color:#64748b; margin-top:2px;'>"
                f"Index not computed · Click to run the calculation in real time</div>"
                f"<div style='font-size:0.68rem; color:#94a3b8; margin-top:2px;'>"
                f"5 Wikipedia criteria · SAW + Shannon · Years 2019–2023</div>"
                f"</div></div>",
                unsafe_allow_html=True,
            )
            if wiki_link and wiki_link.strip():
                if st.button(
                    f"🔄 Calculer maintenant — {lang_label}",
                    key=f"btn_calc_{lang_code}_{plx_num_lang}",
                    use_container_width=True,
                ):
                    with st.spinner(f"⏳ Calcul en cours pour {plx_label} ({lang_label})…"):
                        ntmod.calculer_un_prolexeme(lang_code, plx_num_lang, wiki_link)
                    _get_frequences_cached.clear()
                    _trouver_frequence_pivot.clear()
                    st.rerun()
            else:
                # Expliquer pourquoi le calcul est impossible
                import sqlite3 as _sq2
                _conn2 = _sq2.connect(ntmod.DB_PATH)
                _plx_row = _conn2.execute(
                    f"SELECT LABEL_PROLEXEME, WIKIPEDIA_LINK FROM prolexeme_{lang_code} WHERE NUM_PROLEXEME = ?",
                    (plx_num_lang,),
                ).fetchone()
                _conn2.close()
                if _plx_row is None:
                    _raison = "Prolexeme not found in the database."
                elif not _plx_row[1] or not str(_plx_row[1]).strip():
                    _raison = "No Wikipedia link is stored for this prolexeme in ProLexBase — the calculation requires an associated Wikipedia page."
                else:
                    _raison = f"Wikipedia link available ({_plx_row[1]}) mais calcul non disponible."
                st.markdown(
                    f"<div style='padding:0.5rem 0.8rem; background:#fff7ed; border-left:3px solid #f59e0b;"
                    f" border-radius:0 8px 8px 0; font-size:0.78rem; color:#92400e; margin-top:0.3rem;'>"
                    f"⚠ Calcul impossible — {_raison}</div>",
                    unsafe_allow_html=True,
                )
            continue

        # ── Cas 3 : données disponibles ─────────────────────────────────────
        found_any = True
        # Ajouter au bouton MySQL seulement si pas encore dans MySQL
        if (lang_code, plx_num_lang) not in _already_in_mysql:
            plx_ids[lang_code] = plx_num_lang

        last = freqs[-1]
        num_f = last[2] if isinstance(last, tuple) else last["NUM_FREQUENCY"]
        year  = last[0] if isinstance(last, tuple) else last["YEAR_FREQUENCY"]
        fra   = last[1] if isinstance(last, tuple) else last["FRA_FREQUENCY"]
        color = _FREQ_COLORS.get(num_f, "#94a3b8")
        icon  = _FREQ_ICONS.get(num_f, "⚫")

        st.markdown(
            f"<div style='display:flex; align-items:center; gap:1rem; padding:0.8rem 1.2rem;"
            f" background:#f1f5f9; border-left:4px solid {color}; border-radius:0 12px 12px 0;"
            f" margin-bottom:0.5rem;'>"
            f"<div style='font-size:2rem; font-weight:900; color:{color};'>{num_f}</div>"
            f"<div style='flex:1;'>"
            f"<div style='font-size:0.85rem; font-weight:600; color:#1e293b;'>"
            f"{lang_label}"
            f"{(' — ' + plx_label) if plx_label and plx_label != label else ''}"
            f"</div>"
            f"<div style='font-size:0.9rem; color:{color}; font-weight:700;'>"
            f"{icon} {fra}</div>"
            f"<div style='font-size:0.7rem; color:#94a3b8;'>Latest year : {year}</div>"
            f"</div>"
            f"<div style='text-align:center; padding:0.4rem 0.8rem; background:{color}22;"
            f" border:1px solid {color}55; border-radius:8px;'>"
            f"<div style='font-size:0.65rem; color:#64748b; margin-bottom:2px;'>Index</div>"
            f"<div style='font-size:1.4rem; font-weight:900; color:{color};'>{num_f}</div>"
            f"<div style='font-size:0.65rem; color:{color};'>{fra}</div>"
            f"</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        if len(freqs) > 1:
            with st.expander(f"📅 History {lang_label} ({len(freqs)} years)", expanded=False):
                for fr in freqs:
                    y    = fr[0] if isinstance(fr, tuple) else fr["YEAR_FREQUENCY"]
                    flbl = fr[1] if isinstance(fr, tuple) else fr["FRA_FREQUENCY"]
                    nf   = fr[2] if isinstance(fr, tuple) else fr["NUM_FREQUENCY"]
                    c    = _FREQ_COLORS.get(nf, "#94a3b8")
                    ic   = _FREQ_ICONS.get(nf, "⚫")
                    st.markdown(
                        f"<div style='display:flex; justify-content:space-between; align-items:center;"
                        f" padding:0.3rem 0.5rem; font-size:0.8rem;"
                        f" border-bottom:1px solid #edf2f7;'>"
                        f"<span style='color:#64748b;'>📅 {y}</span>"
                        f"<span style='color:{c}; font-weight:700;'>{ic} {nf} — {flbl}</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

    if not found_any:
        st.markdown(
            "<div style='text-align:center; padding:1.5rem; color:#94a3b8; background:#f1f5f9;"
            " border-radius:12px; border:1px dashed #e2e8f0; font-style:italic;'>"
            "No notoriety data available for this prolexeme.</div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        "<div style='margin-top:1rem; padding:0.6rem 0.8rem; background:#f8fafc; border-radius:8px;"
        " font-size:0.72rem; color:#94a3b8;'>"
        "🟢 1 = Frequent &nbsp;·&nbsp; 🟡 2 = Less frequent &nbsp;·&nbsp; 🔴 3 = Rare<br>"
        "SAW + Shannon entropy · 5 Wikipedia criteria</div>",
        unsafe_allow_html=True,
    )

    # ── Courbe temporelle ────────────────────────────────────────────────────
    # (arb=violet, pol=ambre, srp=vert)
    _lang_info = [
        ("arb", "Arabic",    "🇸🇦", "#6366f1"),
        ("pol", "Polish", "🇵🇱", "#f59e0b"),
        ("srp", "Serbian",    "🇷🇸", "#10b981"),
    ]
    _lang_color_map = {lc: c for lc, _, _, c in _lang_info}

    _data_by_lang = {}
    for _lc, _d in lang_data.items():
        _fqs = _d["freqs"]
        if _fqs:
            _rows = []
            for _fr in _fqs:
                _year = _fr[0] if isinstance(_fr, tuple) else _fr["YEAR_FREQUENCY"]
                _nf   = _fr[2] if isinstance(_fr, tuple) else _fr["NUM_FREQUENCY"]
                _rows.append({"Year": int(_year), "Index": int(_nf)})
            _data_by_lang[_lc] = _rows

    st.markdown(
        "<hr style='border:none; border-top:1px solid #e2e8f0; margin:1.4rem 0 1rem 0;'>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div style='font-size:1rem; font-weight:700; color:#1e293b; margin-bottom:0.6rem;'>"
        "📈 Notoriety index over time</div>",
        unsafe_allow_html=True,
    )

    if _data_by_lang:
        import altair as _alt

        _curve_key = f"curve_lang_{num_plx}"
        if _curve_key not in st.session_state:
            st.session_state[_curve_key] = list(_data_by_lang.keys())[0]
        _sel_lc    = st.session_state[_curve_key]
        _sel_color = _lang_color_map[_sel_lc]

        # ── CSS scoped : cercles dans la colonne de droite ────────────────
        # On utilise :has(#uid) pour cibler uniquement ce bloc-ci
        # et button:nth-of-type(n) pour coloriser chaque cercle selon son état
        _uid = f"nchart_{num_plx}"
        _scope = (
            f"[data-testid='stVerticalBlock']:has(#{_uid})"
            f" > [data-testid='stHorizontalBlock']"
            f" > [data-testid='stColumn']:last-child"
            f" [data-testid='stVerticalBlock']"
        )
        _per_btn_css = ""
        for _ni, (_lc, _name, _flag, _c) in enumerate(_lang_info, 1):
            _active  = _sel_lc == _lc
            _hasdata = _lc in _data_by_lang
            _bg      = _c       if (_active and _hasdata) else ("#f1f5f9" if _hasdata else "#f4f6f9")
            _brd     = _c       if _hasdata               else "#dde3ec"
            _sh      = f"0 6px 20px {_c}55" if (_active and _hasdata) else "0 1px 5px rgba(0,0,0,0.07)"
            _sc      = "1.12"   if (_active and _hasdata) else "1"
            _per_btn_css += (
                f"\n{_scope} button:nth-of-type({_ni}){{"
                f"background:{_bg}!important;"
                f"border-color:{_brd}!important;"
                f"box-shadow:{_sh}!important;"
                f"transform:scale({_sc})!important;}}"
            )

        st.markdown(
            f"<span id='{_uid}'></span>"
            f"<style>"
            f"{_scope} button{{"
            f"  border-radius:50%!important;"
            f"  width:54px!important;height:54px!important;"
            f"  min-width:0!important;padding:0!important;"
            f"  font-size:1.55rem!important;line-height:1!important;"
            f"  border:3px solid transparent!important;"
            f"  transition:all .25s cubic-bezier(.34,1.56,.64,1)!important;"
            f"  display:inline-flex!important;"
            f"  align-items:center!important;justify-content:center!important;"
            f"  -webkit-text-fill-color:unset!important;"
            f"}}"
            f"{_per_btn_css}"
            # Cacher "Show data", "Save as PNG/SVG", "Open in Vega Editor" et fullscreen
            f".vega-embed details,.vega-embed summary,.vega-embed .vega-actions"
            f"{{display:none!important;}}"
            f"[data-testid='StyledFullScreenButton']{{display:none!important;}}"
            f"</style>",
            unsafe_allow_html=True,
        )

        # ── Layout : graphique (gauche large) + cercles (droite étroite) ─
        col_chart, col_btns = st.columns([5, 1])

        # Colonne de droite — 3 cercles empilés
        with col_btns:
            st.markdown("<div style='height:3rem;'></div>", unsafe_allow_html=True)
            for _lc, _name, _flag, _c in _lang_info:
                _hasdata = _lc in _data_by_lang
                _active  = _sel_lc == _lc
                _lbl_col = _c if (_active and _hasdata) else ("#94a3b8" if not _hasdata else "#475569")
                _lbl_fw  = "700" if _active else "500"
                st.markdown(
                    f"<div style='text-align:center;font-size:0.68rem;"
                    f"font-weight:{_lbl_fw};color:{_lbl_col};"
                    f"margin-bottom:2px;letter-spacing:0.03em;'>{_name}</div>",
                    unsafe_allow_html=True,
                )
                # Toujours rendre un bouton (garde nth-of-type stable)
                if st.button(_flag, key=f"circle_{_lc}_{num_plx}"):
                    if _hasdata:
                        st.session_state[_curve_key] = _lc
                        st.rerun()
                st.markdown("<div style='height:0.6rem;'></div>", unsafe_allow_html=True)

        # Colonne de gauche — graphique Altair
        with col_chart:
            _sel_rows = _data_by_lang[_sel_lc]
            _df_sel   = pd.DataFrame(_sel_rows)
            _lang_title = {"arb": "Arabic 🇸🇦", "pol": "Polish 🇵🇱", "srp": "Serbian 🇷🇸"}

            _y_scale = _alt.Scale(domain=[3.4, 0.6], nice=False)
            _y_axis  = _alt.Axis(
                values=[1, 2, 3],
                labelExpr=(
                    "datum.value===1?'① Frequent':"
                    "datum.value===2?'② Less frequent':'③ Rare'"
                ),
                labelFontSize=13, labelFontWeight="bold", labelLimit=200,
                titleFontSize=12, titleFontWeight="normal",
                gridColor="#f1f5f9", gridWidth=1.5, gridDash=[6, 4], tickCount=3,
                labelColor="#64748b", titleColor="#64748b",
            )
            _x_axis = _alt.Axis(
                labelAngle=0, labelFontSize=13, titleFontSize=13,
                labelColor="#64748b", titleColor="#64748b",
                grid=False, tickColor="#e2e8f0",
            )

            # Bandes de fond (zones colorées discrètes)
            _band_df = pd.DataFrame([
                {"y1": 0.6, "y2": 1.5, "Niveau": "Frequent"},
                {"y1": 1.5, "y2": 2.5, "Niveau": "Less frequent"},
                {"y1": 2.5, "y2": 3.4, "Niveau": "Rare"},
            ])
            _band_layer = (
                _alt.Chart(_band_df).mark_rect(opacity=0.055)
                .encode(
                    y=_alt.Y("y1:Q", scale=_y_scale, axis=None),
                    y2=_alt.Y2("y2:Q"),
                    color=_alt.Color(
                        "Niveau:N",
                        scale=_alt.Scale(
                            domain=["Frequent", "Less frequent", "Rare"],
                            range=["#10b981", "#f59e0b", "#ef4444"],
                        ),
                        legend=None,
                    ),
                )
            )
            # Zone sous la courbe
            _area_layer = (
                _alt.Chart(_df_sel)
                .mark_area(interpolate="monotone", opacity=0.13, color=_sel_color)
                .encode(
                    x=_alt.X("Year:O", axis=None),
                    y=_alt.Y("Index:Q", scale=_y_scale, axis=None),
                    y2=_alt.value(3.4),
                )
            )
            # Ligne principale
            _line_layer = (
                _alt.Chart(_df_sel)
                .mark_line(interpolate="monotone", strokeWidth=4, color=_sel_color)
                .encode(
                    x=_alt.X("Year:O", title="Year", axis=_x_axis),
                    y=_alt.Y("Index:Q", title="Notoriety index", scale=_y_scale, axis=_y_axis),
                )
            )
            # Points
            _point_layer = (
                _alt.Chart(_df_sel)
                .mark_circle(size=170, color=_sel_color, opacity=1)
                .encode(
                    x=_alt.X("Year:O", axis=None),
                    y=_alt.Y("Index:Q", scale=_y_scale, axis=None),
                    tooltip=[
                        _alt.Tooltip("Year:O",  title="Year"),
                        _alt.Tooltip("Index:Q", title="Index"),
                    ],
                )
            )
            # Valeurs sur les points
            _text_layer = (
                _alt.Chart(_df_sel)
                .mark_text(dy=-15, fontSize=13, fontWeight="bold", color=_sel_color)
                .encode(
                    x=_alt.X("Year:O", axis=None),
                    y=_alt.Y("Index:Q", scale=_y_scale, axis=None),
                    text=_alt.Text("Index:Q"),
                )
            )

            _final_chart = (
                (_band_layer + _area_layer + _line_layer + _point_layer + _text_layer)
                .resolve_scale(color="independent", y="shared")
                .properties(
                    height=380,
                    title=_alt.TitleParams(
                        text=f"Notoriety index — {_lang_title.get(_sel_lc, _sel_lc)}",
                        fontSize=14, color="#1e293b", anchor="start",
                        font="Inter, sans-serif",
                    ),
                )
                .configure_view(strokeWidth=0, fill="#ffffff", cornerRadius=12)
                .configure_axis(labelFont="Inter, sans-serif", titleFont="Inter, sans-serif")
            )
            st.altair_chart(_final_chart, use_container_width=True)

        # Légende bandes (sous le layout colonnes)
        st.markdown(
            "<div style='display:flex;gap:1.4rem;padding-left:0.4rem;"
            "font-size:0.73rem;color:#64748b;margin-top:-0.3rem;'>"
            "<span>🟢 Zone 1 — Frequent</span>"
            "<span>🟡 Zone 2 — Less frequent</span>"
            "<span>🔴 Zone 3 — Rare</span>"
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div style='padding:1.2rem 1.4rem; background:#f8fafc;"
            " border:1px dashed #e2e8f0; border-radius:12px; color:#94a3b8;"
            " font-size:0.85rem; text-align:center;'>"
            "📉 The curve will appear here once the index has been computed for at least one language.<br>"
            "<span style='font-size:0.78rem;'>Cliquez sur <strong>« Calculer maintenant »</strong>"
            " pour les langues disponibles ci-dessus.</span>"
            "</div>",
            unsafe_allow_html=True,
        )

    # ── Bouton Enregistrer dans MySQL (toujours visible si données disponibles) ─
    if plx_ids:
        st.markdown(
            "<hr style='border:none; border-top:1px solid #e2e8f0; margin:1rem 0 0.8rem 0;'>",
            unsafe_allow_html=True,
        )
        push_result_key = f"push_result_{num_plx}"
        prev = st.session_state.get(push_result_key)

        # Afficher le résultat du dernier push s'il existe
        if prev:
            all_ok = all(ok for ok, _ in prev.values())
            for lc, (ok, msg) in prev.items():
                lbl = _LANG_LABELS.get(lc, lc)
                if ok:
                    st.markdown(
                        f"<div style='padding:0.4rem 0.8rem; background:#f0fdf4; border-left:3px solid #10b981;"
                        f" border-radius:0 8px 8px 0; font-size:0.8rem; color:#10b981; margin-bottom:0.3rem;'>"
                        f"✅ {lbl} — {msg}</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f"<div style='padding:0.4rem 0.8rem; background:#fef2f2; border-left:3px solid #ef4444;"
                        f" border-radius:0 8px 8px 0; font-size:0.8rem; color:#ef4444; margin-bottom:0.3rem;'>"
                        f"❌ {lbl} — {msg}</div>",
                        unsafe_allow_html=True,
                    )

        langs_str = " + ".join(_LANG_LABELS[lc] for lc in plx_ids)
        if st.button(
            f"💾 Save to MySQL ({langs_str})",
            key=f"btn_mysql_{num_plx}",
            use_container_width=True,
            type="primary",
        ):
            results = {}
            for lc, plx_num in plx_ids.items():
                ok, msg = ntmod.push_prolexeme_to_mysql(lc, plx_num)
                results[lc] = (ok, msg)
            st.session_state[push_result_key] = results
            _cached_check_mysql.clear()  # invalider le cache MySQL après enregistrement
            st.rerun()


def _afficher_notoriete_recherche(mot):
    """Affiche l'indice de notoriété d'un mot arabe (recherche dans prolexbase, affichage seul)."""
    st.markdown(
        "<div style='font-size:1rem; font-weight:700; color:#1e293b; margin-bottom:1rem;'>"
        "📊 Notoriety Index</div>",
        unsafe_allow_html=True,
    )

    if not mot:
        st.markdown(
            "<div style='text-align:center; padding:1.5rem; color:#94a3b8; background:#f1f5f9;"
            " border-radius:12px; border:1px dashed #e2e8f0; font-style:italic;'>"
            "Enter a name above to view its notoriety index.</div>",
            unsafe_allow_html=True,
        )
        return

    # Chercher le mot dans prolexeme_arb
    import sqlite3 as _sq
    _conn = _sq.connect(ntmod.DB_PATH)
    _row = _conn.execute(
        "SELECT NUM_PROLEXEME, LABEL_PROLEXEME, NUM_PIVOT FROM prolexeme_arb WHERE LABEL_PROLEXEME = ?",
        (mot,),
    ).fetchone()
    _conn.close()

    if not _row:
        st.markdown(
            f"<div style='text-align:center; padding:1.5rem; color:#ef4444; background:#fef2f2;"
            f" border-radius:12px; border:1px solid #fecaca;'>"
            f"❌ The name <strong style='font-family:Tajawal,sans-serif;'>{mot}</strong> "
            f"n'existe pas dans notre ProLexBase.</div>",
            unsafe_allow_html=True,
        )
        return

    num_plx = _row[0]
    label = _row[1]
    num_pivot = _row[2]

    st.markdown(
        f"<div style='padding:0.6rem 1rem; background:#f0fdf4; border-left:3px solid #10b981;"
        f" border-radius:0 8px 8px 0; font-size:0.85rem; color:#1e293b; margin-bottom:1rem;'>"
        f"✅ Found in ProLexBase — <strong style='font-family:Tajawal,sans-serif;'>{label}</strong>"
        f" (prolexeme #{num_plx})</div>",
        unsafe_allow_html=True,
    )

    found_any = False
    for lang_code, lang_label in _LANG_LABELS.items():
        if lang_code == "arb":
            freqs = ntmod.get_frequences_prolexeme("arb", num_plx)
        else:
            _, plx_label_lang, freqs, _ = _trouver_frequence_pivot(lang_code, num_pivot)
            if plx_label_lang is None:
                st.markdown(
                    f"<div style='display:flex; align-items:center; gap:1rem; padding:0.7rem 1.2rem;"
                    f" background:#f8fafc; border-left:4px solid #e2e8f0; border-radius:0 12px 12px 0;"
                    f" margin-bottom:0.5rem; opacity:0.6;'>"
                    f"<div style='font-size:1.6rem; color:#cbd5e1;'>—</div>"
                    f"<div>"
                    f"<div style='font-size:0.85rem; font-weight:600; color:#94a3b8;'>{lang_label}</div>"
                    f"<div style='font-size:0.75rem; color:#cbd5e1;'>No equivalent in this language</div>"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )
                continue

        if not freqs:
            st.markdown(
                f"<div style='display:flex; align-items:center; gap:1rem; padding:0.7rem 1.2rem;"
                f" background:#f8fafc; border-left:4px solid #f59e0b; border-radius:0 12px 12px 0;"
                f" margin-bottom:0.5rem;'>"
                f"<div style='font-size:1.6rem; color:#f59e0b;'>⏳</div>"
                f"<div>"
                f"<div style='font-size:0.85rem; font-weight:600; color:#1e293b;'>{lang_label}</div>"
                f"<div style='font-size:0.75rem; color:#f59e0b;'>Index not computed yet</div>"
                f"</div></div>",
                unsafe_allow_html=True,
            )
            continue

        found_any = True
        last = freqs[-1]
        num_f = last[2] if isinstance(last, tuple) else last["NUM_FREQUENCY"]
        year  = last[0] if isinstance(last, tuple) else last["YEAR_FREQUENCY"]
        fra   = last[1] if isinstance(last, tuple) else last["FRA_FREQUENCY"]
        color = _FREQ_COLORS.get(num_f, "#94a3b8")
        icon  = _FREQ_ICONS.get(num_f, "⚫")

        st.markdown(
            f"<div style='display:flex; align-items:center; gap:1rem; padding:0.8rem 1.2rem;"
            f" background:#f1f5f9; border-left:4px solid {color}; border-radius:0 12px 12px 0;"
            f" margin-bottom:0.5rem;'>"
            f"<div style='font-size:2rem; font-weight:900; color:{color};'>{num_f}</div>"
            f"<div style='flex:1;'>"
            f"<div style='font-size:0.85rem; font-weight:600; color:#1e293b;'>{lang_label}</div>"
            f"<div style='font-size:0.9rem; color:{color}; font-weight:700;'>{icon} {fra}</div>"
            f"<div style='font-size:0.7rem; color:#94a3b8;'>Latest year : {year}</div>"
            f"</div>"
            f"<div style='text-align:center; padding:0.4rem 0.8rem; background:{color}22;"
            f" border:1px solid {color}55; border-radius:8px;'>"
            f"<div style='font-size:0.65rem; color:#64748b; margin-bottom:2px;'>Index</div>"
            f"<div style='font-size:1.4rem; font-weight:900; color:{color};'>{num_f}</div>"
            f"<div style='font-size:0.65rem; color:{color};'>{fra}</div>"
            f"</div></div>",
            unsafe_allow_html=True,
        )

        if len(freqs) > 1:
            with st.expander(f"📅 History {lang_label} ({len(freqs)} years)", expanded=False):
                for fr in freqs:
                    y    = fr[0] if isinstance(fr, tuple) else fr["YEAR_FREQUENCY"]
                    flbl = fr[1] if isinstance(fr, tuple) else fr["FRA_FREQUENCY"]
                    nf   = fr[2] if isinstance(fr, tuple) else fr["NUM_FREQUENCY"]
                    c    = _FREQ_COLORS.get(nf, "#94a3b8")
                    ic   = _FREQ_ICONS.get(nf, "⚫")
                    st.markdown(
                        f"<div style='display:flex; justify-content:space-between; align-items:center;"
                        f" padding:0.3rem 0.5rem; font-size:0.8rem; border-bottom:1px solid #edf2f7;'>"
                        f"<span style='color:#64748b;'>📅 {y}</span>"
                        f"<span style='color:{c}; font-weight:700;'>{ic} {nf} — {flbl}</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

    if not found_any:
        st.markdown(
            "<div style='text-align:center; padding:1rem; color:#94a3b8; font-size:0.85rem;'>"
            "No notoriety index has been computed for this name in any language.</div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        "<div style='margin-top:1rem; padding:0.6rem 0.8rem; background:#f8fafc; border-radius:8px;"
        " font-size:0.72rem; color:#94a3b8;'>"
        "🟢 1 = Frequent &nbsp;·&nbsp; 🟡 2 = Less frequent &nbsp;·&nbsp; 🔴 3 = Rare<br>"
        "SAW + Shannon entropy · 5 Wikipedia criteria</div>",
        unsafe_allow_html=True,
    )


def _afficher_notoriete_generale():
    """Vue d'ensemble notoriété (onglet Partie 2)."""
    st.markdown(
        "<div style='font-size:1rem; font-weight:700; color:#1e293b; margin-bottom:1rem;'>"
        "📊 Notoriety Index — Overview</div>",
        unsafe_allow_html=True,
    )

    cols = st.columns(3)
    for i, (lang_code, lang_label) in enumerate(_LANG_LABELS.items()):
        stats = ntmod.get_stats_frequence(lang_code)
        with cols[i]:
            st.markdown(
                f"<div style='text-align:center; padding:1rem; background:#f1f5f9;"
                f" border:1px solid #e2e8f0; border-radius:12px; margin-bottom:0.5rem;'>"
                f"<div style='font-size:0.85rem; font-weight:600; color:#818cf8;'>"
                f"{lang_label}</div>"
                f"<div style='font-size:2rem; font-weight:900; color:#1e293b;'>"
                f"{stats['total']}</div>"
                f"<div style='font-size:0.72rem; color:#94a3b8;'>classified prolexemes</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
            if stats["distribution"]:
                for fra, count in stats["distribution"]:
                    # Find NUM_FREQUENCY from FRA label
                    nf = {v: k for k, v in _FREQ_LABELS.items()}.get(fra, 0)
                    color = _FREQ_COLORS.get(nf, "#94a3b8")
                    icon = _FREQ_ICONS.get(nf, "⚫")
                    st.markdown(
                        f"<div style='display:flex; justify-content:space-between; align-items:center;"
                        f" padding:0.25rem 0.5rem; font-size:0.78rem;'>"
                        f"<span style='color:{color};'>{icon} {nf} — {fra}</span>"
                        f"<span style='color:#1e293b; font-weight:600;'>{count}</span></div>",
                        unsafe_allow_html=True,
                    )

    st.markdown(
        "<div style='margin-top:1rem; padding:0.6rem 0.8rem; background:#f8fafc; border-radius:8px;"
        " font-size:0.72rem; color:#94a3b8;'>"
        "🟢 1 = Frequent &nbsp;·&nbsp; 🟡 2 = Less frequent &nbsp;·&nbsp; 🔴 3 = Rare<br>"
        "SAW (Simple Additive Weighting) + Shannon Entropy method<br>"
        "5 Wikipedia criteria: contributors, size, internal links, external links, weighted page views"
        "</div>",
        unsafe_allow_html=True,
    )

    # ── Synchronisation MySQL directe ─────────────────────────────────────────
    st.markdown(
        "<hr style='border:none; border-top:1px solid #e2e8f0; margin:1.5rem 0 1rem 0;'>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div style='font-size:0.9rem; font-weight:700; color:#1e293b; margin-bottom:0.8rem;'>"
        "🗄️ MySQL Connection — Real-time synchronization with phpMyAdmin</div>",
        unsafe_allow_html=True,
    )

    cfg = ntmod.get_mysql_config()
    cfg_status = cfg is not None

    # Résumé statut
    if cfg_status:
        st.markdown(
            f"<div style='padding:0.5rem 0.8rem; background:#f0fdf4; border-left:3px solid #10b981;"
            f" border-radius:0 8px 8px 0; font-size:0.8rem; color:#10b981; margin-bottom:0.6rem;'>"
            f"✅ Configured : <strong>{cfg['user']}@{cfg['host']}:{cfg['port']}</strong>"
            f" / base <strong>{cfg['database']}</strong></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div style='padding:0.5rem 0.8rem; background:#fff7ed; border-left:3px solid #f59e0b;"
            " border-radius:0 8px 8px 0; font-size:0.8rem; color:#92400e; margin-bottom:0.6rem;'>"
            "⚠ Not configured — calculations are stored only in local SQLite</div>",
            unsafe_allow_html=True,
        )

    with st.expander("⚙️ Configure MySQL connection", expanded=not cfg_status):
        col_a, col_b = st.columns([2, 1])
        with col_a:
            mysql_host = st.text_input("Host", value=cfg.get("host", "localhost") if cfg else "localhost", key="mysql_host")
            mysql_db   = st.text_input("Database", value=cfg.get("database", "prolexbase") if cfg else "prolexbase", key="mysql_db")
            mysql_user = st.text_input("User", value=cfg.get("user", "root") if cfg else "root", key="mysql_user")
        with col_b:
            mysql_port = st.text_input("Port", value=cfg.get("port", "3306") if cfg else "3306", key="mysql_port")
            mysql_pass = st.text_input("Password", value=cfg.get("password", "") if cfg else "", type="password", key="mysql_pass")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("💾 Save", key="btn_save_mysql", use_container_width=True):
                ntmod.set_mysql_config(mysql_host, mysql_port, mysql_user, mysql_pass, mysql_db)
                st.success("Configuration saved!")
                st.rerun()
        with c2:
            if st.button("🔌 Test connection", key="btn_test_mysql", use_container_width=True):
                ntmod.set_mysql_config(mysql_host, mysql_port, mysql_user, mysql_pass, mysql_db)
                ok, msg = ntmod.test_mysql_connection()
                if ok:
                    st.success(f"✅ {msg}")
                else:
                    st.error(f"❌ {msg}")

    if cfg_status:
        st.markdown(
            "<div style='font-size:0.78rem; color:#64748b; margin-top:0.4rem; margin-bottom:0.4rem;'>"
            "Each new computation is automatically sent to MySQL. "
            "Vous pouvez aussi tout pousser d'un coup :</div>",
            unsafe_allow_html=True,
        )
        if st.button("🚀 Pousser tout vers MySQL maintenant", key="btn_push_mysql", use_container_width=True):
            with st.spinner("Synchronizing…"):
                n, err = ntmod.push_all_to_mysql()
            if err:
                st.error(f"Error: {err}")
            else:
                st.success(f"✅ {n} rows synchronized to MySQL — check phpMyAdmin!")
        # Bouton export SQL de secours
        if st.button("⬇️ Download SQL (backup)", key="btn_export_sql", use_container_width=False):
            import sqlite3 as _sq2
            _conn2 = _sq2.connect(ntmod.DB_PATH)
            lines = ["-- Frequency update — ProlexArabic\n\n"]
            for lc in ["arb", "pol", "srp"]:
                rows_f = _conn2.execute(
                    f"SELECT NUM_PROLEXEME, NUM_YEAR_FREQUENCY, NUM_FREQUENCY FROM frequency_{lc} ORDER BY NUM_PROLEXEME"
                ).fetchall()
                for row_f in rows_f:
                    lines.append(
                        f"INSERT INTO `frequency_{lc}` (`NUM_PROLEXEME`,`NUM_YEAR_FREQUENCY`,`NUM_FREQUENCY`) "
                        f"VALUES ({row_f[0]},{row_f[1]},{row_f[2]}) "
                        f"ON DUPLICATE KEY UPDATE `NUM_FREQUENCY`=VALUES(`NUM_FREQUENCY`);\n"
                    )
            _conn2.close()
            st.download_button("💾 frequency_update.sql", "".join(lines).encode(), "frequency_update.sql", "text/plain")
    else:
        # Sans MySQL configuré, garder juste l'export SQL
        if st.button("⬇️ Generate SQL for phpMyAdmin (manual)", key="btn_export_sql_only", use_container_width=True):
            import sqlite3 as _sq2
            _conn2 = _sq2.connect(ntmod.DB_PATH)
            lines = ["-- Frequency update — ProlexArabic\n\n"]
            for lc in ["arb", "pol", "srp"]:
                rows_f = _conn2.execute(
                    f"SELECT NUM_PROLEXEME, NUM_YEAR_FREQUENCY, NUM_FREQUENCY FROM frequency_{lc} ORDER BY NUM_PROLEXEME"
                ).fetchall()
                for row_f in rows_f:
                    lines.append(
                        f"INSERT INTO `frequency_{lc}` (`NUM_PROLEXEME`,`NUM_YEAR_FREQUENCY`,`NUM_FREQUENCY`) "
                        f"VALUES ({row_f[0]},{row_f[1]},{row_f[2]}) "
                        f"ON DUPLICATE KEY UPDATE `NUM_FREQUENCY`=VALUES(`NUM_FREQUENCY`);\n"
                    )
            _conn2.close()
            st.download_button("💾 frequency_update.sql", "".join(lines).encode(), "frequency_update.sql", "text/plain")


# =============================================================================
# ONGLETS INSTANCES ET DÉRIVÉS
# =============================================================================

_SITUATION_COLORS = {1: "#10b981", 2: "#f59e0b", 3: "#818cf8"}
_SITUATION_ICONS  = {1: "🔒", 2: "🔄", 3: "📋"}

def _prompt_attente(cat):
    """Message d'invite quand aucun mot n'a encore été soumis."""
    nom = cat.get("nom_fr", "nom propre").lower()
    ar  = cat.get("nom", "")
    st.markdown(
        f"<div style='text-align:center; padding:2.5rem 1rem; background:#f1f5f9;"
        f" border-radius:14px; border:1px dashed #e2e8f0;'>"
        f"<div style='font-size:2rem; margin-bottom:0.6rem;'>{cat.get('icone','🔤')}</div>"
        f"<div style='color:#64748b; font-size:0.95rem;'>Please enter "
        f"<span style='color:#818cf8; font-weight:600;'>{nom}</span>"
        f"<span style='font-family:Tajawal,sans-serif; color:#94a3b8;'> ({ar})</span>"
        f" in the field above to display the results.</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


def _afficher_instances_tab(mot, cat_key, cat):
    """Affiche les instances (إعراب) pour le mot soumis."""
    # Vérifier d'abord si ce type a des règles d'instances
    if cat_key not in TYPES_AVEC_INSTANCES:
        st.markdown(
            f"<div style='text-align:center; padding:2rem; color:#94a3b8; background:#f1f5f9;"
            f" border-radius:12px; border:1px dashed #e2e8f0;'>"
            f"<strong style='color:#64748b;'>Grammatical instances are not applicable in this version</strong><br><br>"
            f"{cat.get('nom_fr', cat_key)}: no instance rule is retained for this type. "
            f"The proper name remains graphically identical in all syntactic contexts.</div>",
            unsafe_allow_html=True,
        )
        return

    if not mot:
        _prompt_attente(cat)
        with st.expander("ℹ️ What is a grammatical instance?"):
            st.markdown(
                "A grammatical **instance** (الإعراب) is the inflection of a proper name according to its syntactic role "
                "in the sentence (subject, object/complement, or after a preposition).  \n\n"
                "**Case 1 — Invariable** : ends in ا or ى → the form remains unchanged across cases.  \n"
                "**Case 2 — Visible change**: sound masculine plural ون/ين → the only visible change in unvocalized text.  \n"
                "**Case 3 — Identical**: all other forms → the spelling remains unchanged across cases."
            )
        return

    info = appliquer_instances(mot, cat_key)
    if info is None:
        st.info("No instance rule is defined for this type in this version.")
        return
    sit  = info["situation"]
    col  = _SITUATION_COLORS.get(sit, "#818cf8")
    ico  = _SITUATION_ICONS.get(sit, "📋")

    st.markdown(
        f"<div style='background:#ffffff; border:1px solid #e2e8f0; border-radius:14px;"
        f" padding:1.2rem 1.4rem; margin-bottom:1rem;'>"
        f"<span style='background:rgba(99,102,241,0.15); border:1px solid {col}; color:{col};"
        f" padding:0.2rem 0.7rem; border-radius:20px; font-size:0.78rem; font-weight:600;'>"
        f"{ico} Case {sit}</span><br><br>"
        f"<div style='color:#1e293b; font-size:0.9rem; line-height:1.7; white-space:pre-line;'>"
        f"{info['description']}</div></div>",
        unsafe_allow_html=True,
    )

    if info.get("formes"):
        st.markdown(
            f"<div style='font-size:0.85rem; color:#64748b; margin-bottom:0.4rem;'>"
            f"Forms of <span style='font-family:Tajawal,sans-serif; color:#818cf8;"
            f" font-size:1.05rem; font-weight:700;'>{mot}</span> :</div>",
            unsafe_allow_html=True,
        )
        toutes_identiques = len(set(info["formes"].values())) == 1
        for cas, forme in info["formes"].items():
            badge = (
                "<span style='background:#e2e8f0; color:#94a3b8; font-size:0.68rem;"
                " padding:0.1rem 0.5rem; border-radius:10px; margin-left:0.4rem;'>unvocalized</span>"
                if toutes_identiques and sit == 3 else ""
            )
            st.markdown(
                f"<div style='display:flex; justify-content:space-between; align-items:center;"
                f" padding:0.65rem 1rem; border-bottom:1px solid #e2e8f0;'>"
                f"<span style='color:#64748b; font-size:0.82rem;'>{cas}</span>"
                f"<span style='display:flex; align-items:center; gap:0.3rem;'>{badge}"
                f"<span style='font-family:Tajawal,sans-serif; font-size:1.35rem;"
                f" font-weight:700; color:#1e293b; direction:rtl;'>{forme}</span></span>"
                f"</div>",
                unsafe_allow_html=True,
            )


def _afficher_derives_tab(mot, cat_key, cat):
    """Affiche les dérivés (Nisba نسبة) pour le mot soumis."""
    if not cat["a_derivation"]:
        nom_fr = cat.get("nom_fr", "This category")
        st.markdown(
            f"<div style='text-align:center; padding:2rem; color:#94a3b8; background:#f1f5f9;"
            f" border-radius:12px; border:1px dashed #e2e8f0;'>"
            f"<strong style='color:#64748b;'>No derivation retained</strong><br><br>"
            f"{nom_fr} : no general productive derivation rule is retained "
            f"in this version.<br>Any attested derivatives will be handled "
            f"later as lexicalized forms.</div>",
            unsafe_allow_html=True,
        )
        return

    if not mot:
        _prompt_attente(cat)
        with st.expander("ℹ️ What is Nisba?"):
            st.markdown(
                "**Nisba (النسبة)** is a relational derivational pattern that transforms a proper name "
                "into a relational adjective or ethnonym by adding the suffix **ي / ية / يون / يين / يات**.  \n\n"
                "Example: فرنسا → فرنسي / فرنسية / فرنسيون / فرنسيين / فرنسيات"
            )
        return

    resultats, explication = appliquer_regles(mot, cat_key)
    if not resultats:
        st.info(f"📐 {explication}")
        return

    st.markdown(
        f"<div style='color:#64748b; font-size:0.85rem; margin-bottom:1rem; padding:0.6rem 1rem;"
        f" background:#f1f5f9; border-radius:10px; border-left:3px solid #6366f1;'>"
        f"📐 {explication}</div>",
        unsafe_allow_html=True,
    )

    cols = st.columns(2)
    for i, (forme_key, (label_ar, label_fr)) in enumerate(LABELS_FORMES.items()):
        valeur = resultats.get(forme_key, "")
        if not valeur:
            continue
        with cols[i % 2]:
            st.markdown(
                f"<div style='background:#ffffff; border:1px solid #e2e8f0; border-radius:14px;"
                f" padding:1rem 1.2rem; margin-bottom:0.9rem;'>"
                f"<div style='font-size:0.75rem; color:#64748b; font-weight:500;'>{label_fr}</div>"
                f"<div style='font-family:Tajawal,sans-serif; font-size:0.7rem; color:#94a3b8;"
                f" direction:rtl; margin:0.2rem 0;'>{label_ar}</div>"
                f"<div style='font-family:Tajawal,sans-serif; font-size:1.8rem; font-weight:800;"
                f" color:#1e293b; direction:rtl; text-align:right;'>{valeur}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )


# =============================================================================
# PAGE CATÉGORIE
# =============================================================================

def page_categorie():
    cat_key = st.session_state.categorie
    cat = CATEGORIES[cat_key]

    # Bouton retour — dynamique selon la page d'origine
    if st.session_state.get("prev_page") == "extraction":
        st.button("← Back to Extraction", on_click=_aller_retour_extraction, type="secondary")
    else:
        st.button("← Back to Types", on_click=aller_systeme_accueil, type="secondary")

    # En-tête de la catégorie — inline styles, pas de classes CSS
    st.markdown(
        f"<div style='text-align:center; margin:1rem 0 1.2rem 0;'>"
        f"<span style='font-size:3rem;'>{cat['icone']}</span><br>"
        f"<span style='font-size:2rem; font-weight:800; color:#1e293b;'>{cat['nom_fr']}</span>"
        f"<span style='font-family:Tajawal,sans-serif; font-size:1.4rem; color:#818cf8;"
        f" margin-right:0.5rem;'> ({cat['nom']})</span><br>"
        f"<span style='color:#64748b; font-size:0.9rem;'>{cat['description']} — {cat['description_ar']}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # Badge dérivation + Statut
    statut = cat.get("statut", "non retenu v1")
    ico_s, label_s, desc_s = STATUT_LABELS.get(statut, ("", statut, ""))
    if cat["a_derivation"]:
        st.success(f"✅ This category has morphological derivation rules (Nisba). — {ico_s} {label_s}")
    else:
        st.info(f"ℹ️ No general productive rule is retained in this version. — {ico_s} {label_s}")
    st.markdown(
        f"<div style='background:#f1f5f9; padding:0.45rem 1rem; border-radius:10px;"
        f" border:1px solid #e2e8f0; margin-bottom:0.6rem; text-align:center;'>"
        f"<span style='font-size:0.82rem; color:#64748b;'>Status: </span>"
        f"<span style='font-size:0.88rem; font-weight:600; color:#818cf8;'>{ico_s} {label_s}</span>"
        f"<span style='font-size:0.75rem; color:#94a3b8; margin-left:0.5rem;'>— {desc_s}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # Exemples
    if cat["exemples"]:
        exemples_str = " ، ".join(cat["exemples"])
        st.markdown(
            f"<div style='background:#f1f5f9; padding:0.7rem 1.2rem; border-radius:12px;"
            f" border:1px solid #e2e8f0; margin-bottom:0.8rem; direction:rtl; text-align:right;"
            f" font-family:Tajawal,sans-serif;'>"
            f"<span style='color:#94a3b8; font-size:0.82rem;'>أمثلة : </span>"
            f"<span style='color:#818cf8; font-weight:600;'>{exemples_str}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<hr style='border:none; border-top:1px solid #e2e8f0; margin:0.5rem 0 1rem 0;'>",
                unsafe_allow_html=True)

    # Formulaire de saisie (Enter ou bouton déclenchent l'analyse)
    placeholder = cat.get("placeholder", "أدخل اسماً عربياً ...")
    with st.form("form_enrichir", clear_on_submit=False):
        mot = st.text_input(
            "✏️ Enter an Arabic proper name:",
            placeholder=placeholder,
            key="input_mot",
            label_visibility="visible",
        )
        submitted = st.form_submit_button("🔎 Enrich", use_container_width=True)

    if submitted and mot and mot.strip():
        st.session_state.mot_soumis  = mot.strip()
        st.session_state.cat_soumise = cat_key
        afficher_resultats(mot.strip(), cat)

    st.markdown("<hr style='border:none; border-top:1px solid #e2e8f0; margin:1rem 0;'>",
                unsafe_allow_html=True)

    # Récupérer le mot soumis valide pour cette catégorie
    mot_actuel = st.session_state.get("mot_soumis", "")
    cat_actuelle = st.session_state.get("cat_soumise", "")
    mot_pour_tabs = mot_actuel if (mot_actuel and cat_actuelle == cat_key) else ""

    # Onglets bas de page — affichent les résultats uniquement après saisie
    tab1, tab2, tab3 = st.tabs(["� Derivatives (النسبة)", "📋 Instances (الإعراب)", "📊 Notoriety Index"])
    with tab1:
        _afficher_derives_tab(mot_pour_tabs, cat_key, cat)
    with tab2:
        _afficher_instances_tab(mot_pour_tabs, cat_key, cat)
    with tab3:
        _afficher_notoriete_recherche(mot_pour_tabs)


# =============================================================================
# AFFICHAGE DES RÉSULTATS
# =============================================================================

def afficher_resultats(mot, cat):
    """Affiche les résultats de l'enrichissement morphologique."""
    cat_key = st.session_state.categorie
    resultats, explication = appliquer_regles(mot, cat_key)

    # --- Mot principal + badge catégorie ---
    st.markdown(
        f"<div style='text-align:center; padding:1.5rem 1rem 1rem 1rem; background:#ffffff;"
        f" border:1px solid #e2e8f0; border-radius:20px; margin:1rem 0 0.8rem 0;"
        f" box-shadow:0 2px 12px rgba(0,0,0,0.04);'>"
        f"<div style='font-family:Tajawal,sans-serif; font-size:3rem; font-weight:800;"
        f" background:linear-gradient(135deg,#6366f1,#818cf8);"
        f" -webkit-background-clip:text; -webkit-text-fill-color:transparent;"
        f" background-clip:text; direction:rtl; margin-bottom:0.6rem;'>{mot}</div>"
        f"<span style='background:rgba(99,102,241,0.2); padding:0.25rem 0.9rem;"
        f" border-radius:20px; font-size:0.85rem; color:#818cf8; font-weight:600;'>"
        f"{cat['icone']} {cat['nom_fr']} &mdash; {cat['nom']}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # --- Applied rule ---
    st.info(f"📐 **Applied rule :** {explication}")


# =============================================================================
# PAGE SYSTÈME DE RÈGLES (ancienne page d'accueil des catégories)
# =============================================================================

def page_systeme():
    """Page avec les catégories et le système de règles (Partie 2)."""
    st.components.v1.html("<script>window.parent.scrollTo(0,0);</script>", height=0)
    if not st.session_state.get("modal_shown_2", False):
        st.session_state.modal_shown_2 = True
        _dialog_part2()
    st.button("← Back to home", on_click=aller_accueil, type="secondary")

    st.markdown(
        "<div style='text-align:center; padding:1.5rem 1rem 1rem 1rem;'>"
        "<div style='font-size:2rem; font-weight:800; background:linear-gradient(135deg,#6366f1,#818cf8);"
        " -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;'>"
        "⚙️ Morphological Rule System</div>"
        "<div style='color:#64748b; font-size:0.9rem; margin-top:0.4rem;'>"
        "Choose an entity category and enter an Arabic proper name to generate its inflected forms and derivatives.</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown("<hr style='border:none; border-top:1px solid #e2e8f0; margin:0.5rem 0 1rem 0;'>",
                unsafe_allow_html=True)

    st.markdown("### 📂 Named-entity categories")
    groupe_labels = list(GROUPES.keys())
    tabs = st.tabs(groupe_labels)

    for tab, label in zip(tabs, groupe_labels):
        keys_in_group = GROUPES[label]
        with tab:
            cols_per_row = 4
            for i in range(0, len(keys_in_group), cols_per_row):
                batch = keys_in_group[i:i + cols_per_row]
                cols = st.columns(cols_per_row)
                for col, key in zip(cols, batch):
                    if key in CATEGORIES:
                        _card_categorie(col, key, CATEGORIES[key])
                st.markdown("")


# =============================================================================
# PAGE PROLEXBASE — Explorateur de la base de données
# =============================================================================

# =============================================================================
# API WIKIDATA — Identifier le type d'un mot arabe (Partie 1)
# =============================================================================

# Mapping QID Wikidata → type français (même vocabulaire que ProLexBase)
_WIKIDATA_QID_TYPES = {
    # Villes
    "Q515": "Ville", "Q1549591": "Ville", "Q532": "Ville",
    "Q7930989": "Ville", "Q3957": "Ville", "Q15284": "Ville",
    "Q486972": "Ville", "Q1637706": "Ville", "Q3910694": "Ville",
    # Pays
    "Q6256": "Pays", "Q3624078": "Pays", "Q7275": "Pays",
    "Q185441": "Pays", "Q112099": "Pays",
    # Personnes
    "Q5": "Anthroponyme",
    # Organisations
    "Q43229": "Organisation", "Q4830453": "Organisation",
    "Q783794": "Organisation", "Q327333": "Organisation",
    # Régions
    "Q82794": "Région", "Q5107": "Région", "Q1620908": "Région",
    "Q10864048": "Région", "Q7631964": "Région",
    # Supranational
    "Q484652": "Supranational", "Q3336843": "Supranational",
}


def _identifier_wikidata(mot):
    """Appelle l'API Wikidata pour identifier le type d'un mot arabe.
    Retourne (type_fr, wikidata_id, label_trouve) ou (None, None, None) si échec.
    """
    try:
        # Étape 1 : chercher l'entité
        r = requests.get(
            "https://www.wikidata.org/w/api.php",
            params={
                "action": "wbsearchentities",
                "search": mot,
                "language": "ar",
                "format": "json",
                "limit": 3,
                "uselang": "fr",
            },
            timeout=6,
        )
        results = r.json().get("search", [])
        if not results:
            return None, None, None

        entity_id = results[0]["id"]
        label = results[0].get("label", mot)

        # Étape 2 : récupérer P31 (instance of)
        r2 = requests.get(
            "https://www.wikidata.org/w/api.php",
            params={
                "action": "wbgetentities",
                "ids": entity_id,
                "props": "claims",
                "format": "json",
            },
            timeout=6,
        )
        claims = r2.json().get("entities", {}).get(entity_id, {}).get("claims", {})
        p31 = claims.get("P31", [])

        for claim in p31:
            qid = (claim.get("mainsnak", {})
                       .get("datavalue", {})
                       .get("value", {})
                       .get("id", ""))
            if qid in _WIKIDATA_QID_TYPES:
                return _WIKIDATA_QID_TYPES[qid], entity_id, label

        # Fallback : description contient souvent le type
        desc = results[0].get("description", "").lower()
        if any(k in desc for k in ["ville", "city", "city", "municipalit"]):
            return "Ville", entity_id, label
        if any(k in desc for k in ["pays", "country", "état", "république"]):
            return "Pays", entity_id, label
        if any(k in desc for k in ["person", "homme", "femme", "acteur", "footballeur", "politique"]):
            return "Anthroponyme", entity_id, label
        if any(k in desc for k in ["organisation", "entreprise", "association", "société"]):
            return "Organisation", entity_id, label
        if any(k in desc for k in ["région", "province", "gouvernorat", "wilaya"]):
            return "Région", entity_id, label

        return None, entity_id, label

    except Exception:
        return None, None, None


# Mapping des types ProLexBase vers les clés de notre système de règles
_TYPE_TO_CAT = {
    "Pays": "pays",
    "Région": "region",
    "Supranational": "supranational",
    "Territoire": "territoire",
    "Ville": "ville",
    "Géonyme": "geonyme",
    "Hydronyme": "hydronyme",
    "Voie": "voie",
    "Edifice": "edifice",
    "Astronyme": "astronyme",
    "Patronyme": "patronyme",
    "First name": "prenom",
    "Pseudo Anthroponyme": "pseudo_anthroponyme",
    "Célébrité": "celebrite",
    "Dynastie": "dynastie",
    "Ethnonyme": "ethnonyme",
    "Individuel": "individuel",
    "Collectif": "collectif",
    "Anthroponyme": "anthroponyme",
    "Groupement": "groupement",
    "Association": "association",
    "Ensemble": "ensemble",
    "Entreprise": "entreprise",
    "Institution": "institution",
    "Organisation": "organisation",
    "Ergonyme": "ergonyme",
    "Pragmonyme": "pragmonyme",
    "Objet": "objet",
    "Produit": "produit",
    "Pensée": "pensee",
    "Vaisseau": "vaisseau",
    "Oeuvre": "oeuvre",
    "Catastrophe": "catastrophe",
    "Manifestation": "manifestation",
    "Fête": "fete",
    "Histoire": "histoire",
    "Météorologie": "meteorologie",
    "Last name propre": None,
    "Toponyme": "toponyme",
}

# 38 types ProLexBase (utilisés pour la classification LLM)
_TYPES_38 = [
    "Pays", "Région", "Supranational", "Territoire", "Ville",
    "Géonyme", "Hydronyme", "Voie", "Edifice", "Astronyme",
    "Patronyme", "First name", "Pseudo Anthroponyme", "Célébrité",
    "Dynastie", "Ethnonyme", "Individuel", "Collectif", "Anthroponyme",
    "Groupement", "Association", "Ensemble", "Entreprise", "Institution",
    "Organisation", "Ergonyme", "Pragmonyme", "Objet", "Produit",
    "Pensée", "Vaisseau", "Oeuvre", "Catastrophe", "Manifestation",
    "Fête", "Histoire", "Météorologie", "Last name propre",
]

# English labels used only for display; internal database/type values stay unchanged.
_TYPE_DISPLAY_EN = {
    "Pays": "Country", "Région": "Region", "Supranational": "Supranational",
    "Territoire": "Territory", "Ville": "City", "Géonyme": "Geonym",
    "Hydronyme": "Hydronym", "Voie": "Route", "Edifice": "Building",
    "Astronyme": "Astronym", "Patronyme": "Surname", "Prénom": "First name",
    "First name": "First name", "Pseudo Anthroponyme": "Pseudonymous anthroponym",
    "Célébrité": "Celebrity", "Dynastie": "Dynasty", "Ethnonyme": "Ethnonym",
    "Individuel": "Individual", "Collectif": "Collective", "Anthroponyme": "Anthroponym",
    "Groupement": "Group", "Association": "Association", "Ensemble": "Ensemble",
    "Entreprise": "Company", "Institution": "Institution", "Organisation": "Organization",
    "Ergonyme": "Ergonym", "Pragmonyme": "Pragmonym", "Objet": "Object",
    "Produit": "Product", "Pensée": "Thought", "Vaisseau": "Vessel",
    "Oeuvre": "Work", "Œuvre": "Work", "Catastrophe": "Disaster",
    "Manifestation": "Event", "Fête": "Celebration", "Histoire": "History",
    "Météorologie": "Meteorology", "Last name propre": "Other proper name",
}

def _display_type_en(value):
    return _TYPE_DISPLAY_EN.get(value, value)


_MODAL_INFO = {
    1: {
        "icon": "🗄️", "color": "#6366f1",
        "title": "Part 1 — ProLexBase",
        "desc": "Lexical database of <strong style='color:#6366f1;'>15,000+ Arabic proper names</strong> with instances, derivatives, and multilingual pivots.",
        "items": [
            ("🔍", "Search for an entry", "Enter an Arabic proper name to find it in the database."),
            ("📋", "Browse and filter", "Filter by type and browse all prolexemes."),
            ("📥", "Import your database", "Import a CSV or Excel file to enrich it."),
        ],
    },
    2: {
        "icon": "⚙️", "color": "#10b981",
        "title": "Part 2 — Rule System",
        "desc": "Morphological generator for <strong style='color:#10b981;'>instances</strong> and <strong style='color:#10b981;'>derivatives (Nisba)</strong>.",
        "items": [
            ("✏️", "Enter a proper name", "Enter an Arabic proper name and its category."),
            ("🔀", "Generate instances", "Generate case forms with vocalization and diacritics."),
            ("🌿", "Generate derivatives", "Produce relational adjectives (Nisba)."),
        ],
    },
    3: {
        "icon": "📝", "color": "#f59e0b",
        "title": "Part 3 — Extraction",
        "desc": "Extraction and <strong style='color:#f59e0b;'>automatic classification</strong> of Arabic proper names.",
        "items": [
            ("📄", "Enter a text", "Paste an Arabic text into the input area."),
            ("🔍", "Automatic extraction", "Proper names are detected automatically."),
            ("🏷️", "NLP classification", "Each proper name is classified into one of 38 types."),
        ],
    },
}


@st.dialog("🗄️ Part 1 — ProLexBase")
def _dialog_part1():
    info = _MODAL_INFO[1]
    st.markdown(
        f"<div style='font-size:0.85rem;color:#64748b;text-align:center;"
        f"margin:-0.4rem 0 1.2rem 0;line-height:1.6;'>{info['desc']}</div>",
        unsafe_allow_html=True,
    )
    for ico, title, desc in info["items"]:
        st.markdown(
            f"<div style='display:flex;align-items:flex-start;gap:0.75rem;"
            f"padding:0.65rem 0.85rem;background:#f8fafc;border-radius:12px;"
            f"border:1px solid #e2e8f0;margin-bottom:0.5rem;'>"
            f"<span style='font-size:1.25rem;flex-shrink:0;'>{ico}</span>"
            f"<div><div style='font-size:0.84rem;font-weight:700;color:#1e293b;'>{title}</div>"
            f"<div style='font-size:0.76rem;color:#64748b;margin-top:2px;'>{desc}</div>"
            f"</div></div>",
            unsafe_allow_html=True,
        )
    st.markdown("<div style='height:0.4rem;'></div>", unsafe_allow_html=True)
    if st.button("Start →", type="primary", use_container_width=True, key="dlg1_ok"):
        st.rerun()


@st.dialog("⚙️ Part 2 — Rule System")
def _dialog_part2():
    info = _MODAL_INFO[2]
    st.markdown(
        f"<div style='font-size:0.85rem;color:#64748b;text-align:center;"
        f"margin:-0.4rem 0 1.2rem 0;line-height:1.6;'>{info['desc']}</div>",
        unsafe_allow_html=True,
    )
    for ico, title, desc in info["items"]:
        st.markdown(
            f"<div style='display:flex;align-items:flex-start;gap:0.75rem;"
            f"padding:0.65rem 0.85rem;background:#f8fafc;border-radius:12px;"
            f"border:1px solid #e2e8f0;margin-bottom:0.5rem;'>"
            f"<span style='font-size:1.25rem;flex-shrink:0;'>{ico}</span>"
            f"<div><div style='font-size:0.84rem;font-weight:700;color:#1e293b;'>{title}</div>"
            f"<div style='font-size:0.76rem;color:#64748b;margin-top:2px;'>{desc}</div>"
            f"</div></div>",
            unsafe_allow_html=True,
        )
    st.markdown("<div style='height:0.4rem;'></div>", unsafe_allow_html=True)
    if st.button("Start →", type="primary", use_container_width=True, key="dlg2_ok"):
        st.rerun()


@st.dialog("📝 Part 3 — Extraction")
def _dialog_part3():
    info = _MODAL_INFO[3]
    st.markdown(
        f"<div style='font-size:0.85rem;color:#64748b;text-align:center;"
        f"margin:-0.4rem 0 1.2rem 0;line-height:1.6;'>{info['desc']}</div>",
        unsafe_allow_html=True,
    )
    for ico, title, desc in info["items"]:
        st.markdown(
            f"<div style='display:flex;align-items:flex-start;gap:0.75rem;"
            f"padding:0.65rem 0.85rem;background:#f8fafc;border-radius:12px;"
            f"border:1px solid #e2e8f0;margin-bottom:0.5rem;'>"
            f"<span style='font-size:1.25rem;flex-shrink:0;'>{ico}</span>"
            f"<div><div style='font-size:0.84rem;font-weight:700;color:#1e293b;'>{title}</div>"
            f"<div style='font-size:0.76rem;color:#64748b;margin-top:2px;'>{desc}</div>"
            f"</div></div>",
            unsafe_allow_html=True,
        )
    st.markdown("<div style='height:0.4rem;'></div>", unsafe_allow_html=True)
    if st.button("Start →", type="primary", use_container_width=True, key="dlg3_ok"):
        st.rerun()


def page_prolexbase():
    """Page d'exploration de la base ProLexBase."""
    st.components.v1.html("<script>window.parent.scrollTo(0,0);</script>", height=0)
    if not st.session_state.get("modal_shown_1", False):
        st.session_state.modal_shown_1 = True
        _dialog_part1()
    col_back, col_spacer, col_import = st.columns([2, 3, 2])
    with col_back:
        st.button("← Back to home", on_click=aller_accueil, type="secondary")
    with col_import:
        st.button("📥 Import Your Database →", on_click=aller_base_import, type="primary")

    st.markdown(
        "<div style='text-align:center; padding:1.5rem 1rem 1rem 1rem;'>"
        "<div style='font-size:2rem; font-weight:800; background:linear-gradient(135deg,#6366f1,#818cf8);"
        " -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;'>"
        "🗄️ ProLexBase — Database</div>"
        "<div style='color:#64748b; font-size:0.9rem; margin-top:0.4rem;'>"
        "Multilingual lexical database of proper names. Browse Arabic prolexemes, "
        "inspect their instances and derivatives, and link each form to its multilingual pivot.</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown("<hr style='border:none; border-top:1px solid #e2e8f0; margin:0.5rem 0 1.5rem 0;'>",
                unsafe_allow_html=True)

    # ── Description ──
    st.markdown(
        "<div style='background:#f8fafc;border:1px solid #e2e8f0;border-radius:14px;"
        "padding:1.1rem 1.4rem;margin-bottom:1.5rem;font-size:0.88rem;color:#374151;line-height:1.8;'>"
        "ProLexBase is a lexical database of <strong style='color:#6366f1;'>Arabic proper names</strong>. "
        "Each entry (prolexeme) groups its <strong>instances</strong> (attested Arabic forms), "
        "its <strong>derivatives</strong> (adjectives, demonyms, etc.) and its multilingual <strong>pivot</strong>.<br>"
        "<span style='color:#6366f1;'>✦</span> You can also import your own database and enrich it automatically."
        "</div>",
        unsafe_allow_html=True,
    )

    # ══════════════════════════════════════════════════════
    # SECTION 1 : Identifier un mot
    # ══════════════════════════════════════════════════════
    st.markdown("<div style='height:2rem;'></div>", unsafe_allow_html=True)
    st.markdown(
        "<div style='font-size:1.15rem; font-weight:700; color:#1e293b; margin-bottom:0.25rem;'>"
        "🔍 Search for an entry</div>"
        "<div style='font-size:0.82rem; color:#64748b; margin-bottom:0.75rem;'>"
        "Enter an Arabic name to identify it in ProLexBase and access its instances and derivatives."
        "</div>",
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        with st.form("form_identifier_mot", clear_on_submit=False):
            col_mot, col_btn = st.columns([4, 1])
            with col_mot:
                mot_saisi = st.text_input(
                    "Arabic name",
                    value=st.session_state.plx_mot_query,
                    placeholder="مثال: باريس ...",
                    label_visibility="collapsed",
                    key="plx_mot_input",
                )
            with col_btn:
                chercher = st.form_submit_button("Search →", use_container_width=True, type="primary")

    if chercher and mot_saisi.strip():
        st.session_state.plx_mot_query = normaliser(mot_saisi.strip())

    if st.session_state.plx_mot_query:
        mot_q = st.session_state.plx_mot_query
        res_mot, _ = prolexdb.search_prolexemes(query=mot_q, type_filter=None, page=1, per_page=10)
        if res_mot:
            if len(res_mot) == 1:
                # Résultat unique — affichage direct
                r = res_mot[0]
                label_r = r["LABEL_PROLEXEME"]
                type_r  = r["FRA_TYPE"]
                num_r   = r["NUM_PROLEXEME"]
                with st.container(border=True):
                    col_word, col_type_badge, col_detail_btn = st.columns([3, 2, 1.5])
                    with col_word:
                        st.markdown(
                            f"<div style='font-family:Tajawal,sans-serif; font-size:1.6rem; font-weight:800;"
                            f" color:#1e293b; direction:rtl; text-align:right; padding:0.3rem 0;'>{label_r}</div>",
                            unsafe_allow_html=True,
                        )
                    with col_type_badge:
                        st.markdown(
                            f"<div style='padding-top:0.4rem;'>"
                            f"<div style='font-size:0.7rem; color:#64748b; margin-bottom:0.25rem;'>IDENTIFIED TYPE</div>"
                            f"<span style='background:rgba(99,102,241,0.15); color:#6366f1; font-weight:700;"
                            f" font-size:0.88rem; padding:0.22rem 0.8rem; border-radius:20px;'>{_display_type_en(type_r)}</span>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                    with col_detail_btn:
                        st.markdown("<div style='height:0.6rem;'></div>", unsafe_allow_html=True)
                        st.button(
                            "View details →",
                            key="btn_voir_detail",
                            on_click=aller_prolexbase_detail,
                            args=(num_r,),
                            type="primary",
                            use_container_width=True,
                        )
            else:
                # Plusieurs résultats — panneau de désambiguïsation
                n_exact = sum(1 for r in res_mot if r["LABEL_PROLEXEME"] == mot_q)
                n_other = len(res_mot) - n_exact
                st.warning(
                    f"⚠️ **{len(res_mot)} entries** found for “{mot_q}”"
                    + (f" — including **{n_exact}** exact match(es)" if n_exact > 0 else "")
                    + ". Choose the desired entry:"
                )
                with st.container(border=True):
                    for i, r in enumerate(res_mot):
                        label_r  = r["LABEL_PROLEXEME"]
                        type_r   = r["FRA_TYPE"]
                        num_r    = r["NUM_PROLEXEME"]
                        is_exact = label_r == mot_q
                        c1, c2, c3 = st.columns([3, 2, 1.3])
                        with c1:
                            exact_tag = (
                                " <span style='background:rgba(16,185,129,0.15); color:#10b981;"
                                " font-size:0.68rem; font-weight:700; padding:0.1rem 0.45rem;"
                                " border-radius:10px; margin-right:0.4rem;'>✓ exact</span>"
                                if is_exact else ""
                            )
                            st.markdown(
                                f"<div style='font-family:Tajawal,sans-serif; font-size:0.9rem;"
                                f" font-weight:700; color:#1e293b; direction:rtl; text-align:right;"
                                f" padding:0.2rem 0;'>{label_r}{exact_tag}</div>",
                                unsafe_allow_html=True,
                            )
                        with c2:
                            st.markdown(
                                f"<div style='padding-top:0.2rem;'><span style='background:rgba(99,102,241,0.12);"
                                f" color:#6366f1; font-size:0.72rem; font-weight:600; padding:0.12rem 0.55rem;"
                                f" border-radius:20px;'>{_display_type_en(type_r)}</span></div>",
                                unsafe_allow_html=True,
                            )
                        with c3:
                            st.button(
                                "Choose →",
                                key=f"choice_{num_r}_{i}",
                                on_click=aller_prolexbase_detail,
                                args=(num_r,),
                                type="secondary",
                                use_container_width=True,
                            )
                        if i < len(res_mot) - 1:
                            st.markdown(
                                "<hr style='border:none; border-top:1px solid #f1f5f9; margin:0;'>",
                                unsafe_allow_html=True,
                            )
        else:
            st.info(f"❌ The name **{mot_q}** is not in ProLexBase.")

    # ══════════════════════════════════════════════════════
    # SECTION 2 : Explorer & Filtrer la base
    # ══════════════════════════════════════════════════════
    st.markdown("<div style='height:2rem;'></div>", unsafe_allow_html=True)
    st.markdown("<hr style='border:none; border-top:2px solid #e2e8f0; margin-bottom:1.5rem;'>",
                unsafe_allow_html=True)
    st.markdown(
        "<div style='font-size:1.15rem; font-weight:700; color:#1e293b; margin-bottom:0.25rem;'>"
        "📂 Browse the database</div>"
        "<div style='font-size:0.82rem; color:#64748b; margin-bottom:0.75rem;'>"
        "Search and filter the 15,000+ prolexemes by type."
        "</div>",
        unsafe_allow_html=True,
    )

    # ── Filtres ──
    with st.container(border=True):
        col_search, col_type = st.columns([2, 1])
        with col_search:
            search_q = st.text_input(
                "🔎 Search for an Arabic prolexeme:",
                value=st.session_state.plx_search,
                placeholder="مثال: فرنسا، باريس، محمد ...",
                key="plx_search_input",
            )
        with col_type:
            all_types = _get_all_types()
            type_dist = _get_type_distribution()
            dist_map = {r['FRA_TYPE']: r['nb'] for r in type_dist}
            type_option_map = {
                f"{_display_type_en(t['FRA_TYPE'])} ({dist_map.get(t['FRA_TYPE'], 0)})": t['FRA_TYPE']
                for t in all_types
            }
            type_options = ["All types"] + list(type_option_map.keys())
            selected_type_idx = 0
            if st.session_state.plx_type_filter:
                for idx, opt in enumerate(type_options):
                    if type_option_map.get(opt) == st.session_state.plx_type_filter:
                        selected_type_idx = idx
                        break
            type_choice = st.selectbox("📁 Type:", type_options, index=selected_type_idx)

    # Parse filter: keep original database value internally.
    type_filter = type_option_map.get(type_choice) if type_choice != "All types" else None

    # Update state
    if search_q != st.session_state.plx_search:
        st.session_state.plx_search = search_q
        st.session_state.plx_page = 1
    if (type_filter or "") != st.session_state.plx_type_filter:
        st.session_state.plx_type_filter = type_filter or ""
        st.session_state.plx_page = 1

    # ── Query ──
    per_page = 15
    rows, total = prolexdb.search_prolexemes(
        query=st.session_state.plx_search,
        type_filter=type_filter,
        page=st.session_state.plx_page,
        per_page=per_page,
    )
    total_pages = max(1, math.ceil(total / per_page))

    st.markdown(
        f"<div style='color:#64748b; font-size:0.83rem; margin:0.8rem 0 0.5rem 0;'>"
        f"📊 <strong style='color:#1e293b;'>{total:,}</strong> prolexemes — "
        f"Page {st.session_state.plx_page} / {total_pages}</div>",
        unsafe_allow_html=True,
    )

    # ── Résultats ──
    if rows:
        # En-tête du tableau
        st.markdown(
            "<div style='display:grid; grid-template-columns:3fr 2fr 0.7fr 1fr;"
            " gap:0; background:#f1f5f9; border:1px solid #e2e8f0;"
            " border-radius:10px 10px 0 0; padding:0.4rem 0.8rem;'>"
            "<div style='font-size:0.72rem; font-weight:700; color:#64748b; text-transform:uppercase; letter-spacing:0.05em; text-align:right;'>Prolexeme</div>"
            "<div style='font-size:0.72rem; font-weight:700; color:#64748b; text-transform:uppercase; letter-spacing:0.05em;'>Type</div>"
            "<div style='font-size:0.72rem; font-weight:700; color:#64748b; text-transform:uppercase; letter-spacing:0.05em;'>Pivot</div>"
            "<div></div>"
            "</div>",
            unsafe_allow_html=True,
        )
        with st.container(border=True):
            for i, row in enumerate(rows):
                label     = row["LABEL_PROLEXEME"]
                fra_type  = row["FRA_TYPE"]
                num_pivot = row["NUM_PIVOT"]
                num_plx   = row["NUM_PROLEXEME"]

                col1, col2, col3, col4 = st.columns([3, 2, 0.7, 1])
                with col1:
                    st.markdown(
                        f"<div style='font-family:Tajawal,sans-serif; font-size:0.85rem; font-weight:600;"
                        f" color:#1e293b; direction:rtl; text-align:right; padding:0.35rem 0;'>{label}</div>",
                        unsafe_allow_html=True,
                    )
                with col2:
                    st.markdown(
                        f"<div style='padding:0.35rem 0;'><span style='background:rgba(99,102,241,0.1);"
                        f" color:#6366f1; font-size:0.7rem; font-weight:600; padding:0.12rem 0.5rem;"
                        f" border-radius:20px;'>{_display_type_en(fra_type)}</span></div>",
                        unsafe_allow_html=True,
                    )
                with col3:
                    st.markdown(
                        f"<div style='color:#94a3b8; font-size:0.7rem; padding:0.35rem 0;"
                        f" text-align:center;'>#{num_pivot}</div>",
                        unsafe_allow_html=True,
                    )
                with col4:
                    st.button(
                        "View →",
                        key=f"plx_{num_plx}",
                        on_click=aller_prolexbase_detail,
                        args=(num_plx,),
                        type="secondary",
                        use_container_width=True,
                    )
                if i < len(rows) - 1:
                    st.markdown(
                        "<hr style='border:none; border-top:1px solid #f1f5f9; margin:0;'>",
                        unsafe_allow_html=True,
                    )
    else:
        st.info("No prolexeme was found for this search.")

    # ── Pagination ──
    if total_pages > 1:
        st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)
        pcol1, pcol2, pcol3 = st.columns([1, 2, 1])
        with pcol1:
            if st.session_state.plx_page > 1:
                if st.button("← Previous", use_container_width=True):
                    st.session_state.plx_page -= 1
                    st.rerun()
        with pcol2:
            st.markdown(
                f"<div style='text-align:center; color:#64748b; font-size:0.85rem; padding-top:0.5rem;'>"
                f"Page {st.session_state.plx_page} / {total_pages}</div>",
                unsafe_allow_html=True,
            )
        with pcol3:
            if st.session_state.plx_page < total_pages:
                if st.button("Next →", use_container_width=True):
                    st.session_state.plx_page += 1
                    st.rerun()


def _stat_card(col, icon, label, value):
    with col:
        st.markdown(
            f"<div style='background:#ffffff; border:1px solid #e2e8f0; border-radius:14px;"
            f" padding:1.4rem 1rem; box-shadow:0 2px 8px rgba(0,0,0,0.04); height:100%;'>"
            f"<div style='display:flex; align-items:center; gap:0.5rem; margin-bottom:0.5rem;'>"
            f"<span style='font-size:1.2rem;'>{icon}</span>"
            f"<span style='font-size:0.72rem; font-weight:700; color:#6366f1; text-transform:uppercase; letter-spacing:0.8px;'>{label}</span>"
            f"</div>"
            f"<div style='font-size:1.9rem; font-weight:800; color:#1e293b; line-height:1;'>{value}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )


# =============================================================================
# RELATIONS SÉMANTIQUES (Synonymy · Meronymy · Accessibility)
# =============================================================================

def _chips_html(items, accent_color="#6366f1"):
    """Construit le HTML des chips arabes — sans pivot, tous les résultats."""
    # Garder uniquement les items avec un vrai label arabe
    valid = [it for it in items if it["label"] and not str(it["label"]).startswith("pivot#")]
    if not valid:
        return (
            "<div style='text-align:center; padding:1rem; color:#94a3b8; font-size:0.85rem;'>"
            "No Arabic name was found in the database.</div>"
        ), 0
    chips = "".join(
        f"<span style='"
        f"font-family:Tajawal,sans-serif;"
        f"font-size:1.05rem;"
        f"font-weight:700;"
        f"color:#1e293b;"
        f"background:#ffffff;"
        f"border:1.5px solid #e2e8f0;"
        f"border-radius:50px;"
        f"padding:0.25rem 0.9rem;"
        f"display:inline-block;"
        f"box-shadow:0 1px 4px rgba(0,0,0,0.06);"
        f"margin:0;"
        f"'>{it['label']}</span>"
        for it in valid
    )
    n = len(valid)
    # Scrollable si > 30 éléments
    if n > 30:
        html = (
            f"<div style='"
            f"max-height:260px;"
            f"overflow-y:auto;"
            f"padding:0.8rem 0.8rem 0.6rem 0.8rem;"
            f"background:#f8fafc;"
            f"border:1px solid #e2e8f0;"
            f"border-radius:14px;"
            f"scrollbar-width:thin;"
            f"scrollbar-color:{accent_color}44 #f1f5f9;"
            f"'>"
            f"<div style='display:flex; flex-wrap:wrap; gap:0.45rem; direction:rtl;'>"
            f"{chips}"
            f"</div></div>"
        )
    else:
        html = (
            f"<div style='display:flex; flex-wrap:wrap; gap:0.45rem; direction:rtl;"
            f" padding:0.5rem 0;'>{chips}</div>"
        )
    return html, n


def _section_relation(icon, title, subtitle, items, accent_color, bg_color):
    """Bloc d'une section de relation (titre coloré + chips)."""
    chips, n = _chips_html(items, accent_color)
    if n == 0:
        return
    st.markdown(
        f"<div style='"
        f"background:{bg_color};"
        f"border:1px solid {accent_color}30;"
        f"border-left:4px solid {accent_color};"
        f"border-radius:0 14px 14px 0;"
        f"padding:1rem 1.2rem 1rem 1.2rem;"
        f"margin-bottom:1rem;"
        f"'>"
        f"<div style='display:flex; align-items:center; justify-content:space-between; margin-bottom:0.6rem;'>"
        f"<div style='display:flex; align-items:center; gap:0.45rem;'>"
        f"<span style='font-size:1.15rem;'>{icon}</span>"
        f"<span style='font-size:0.95rem; font-weight:700; color:#1e293b;'>{title}</span>"
        f"</div>"
        f"<span style='background:{accent_color}; color:#fff; font-size:0.72rem; font-weight:700;"
        f" padding:0.15rem 0.65rem; border-radius:50px;'>{n}</span>"
        f"</div>"
        f"<div style='font-size:0.75rem; color:#64748b; margin-bottom:0.7rem;'>{subtitle}</div>"
        f"{chips}"
        f"</div>",
        unsafe_allow_html=True,
    )


@st.cache_data(ttl=300)
def _cached_synonymes(num_pivot):
    return prolexdb.get_synonymes(num_pivot)

@st.cache_data(ttl=300)
def _cached_meronymie(num_pivot):
    return prolexdb.get_meronymie(num_pivot)

@st.cache_data(ttl=300)
def _cached_accessibilite(num_pivot):
    return prolexdb.get_accessibilite(num_pivot)


def _afficher_relations_tab(num_pivot):
    """Affiche les relations sémantiques d'un prolexème (synonymie, méronymie, accessibilité)."""

    # Check MySQL config availability
    cfg = prolexdb._get_mysql_cfg()
    if not cfg:
        st.markdown(
            "<div style='text-align:center; padding:2rem; background:#fff7ed;"
            " border:1px solid #fed7aa; border-radius:14px;'>"
            "<div style='font-size:2rem; margin-bottom:0.5rem;'>⚙️</div>"
            "<div style='font-weight:700; color:#92400e; margin-bottom:0.4rem;'>"
            "MySQL connection required</div>"
            "<div style='color:#78350f; font-size:0.85rem;'>"
            "Semantic relations are stored in MySQL. "
            "Configure the connection in <strong>Part 1 → Notoriety Index → ⚙️ Configure MySQL</strong>.</div>"
            "</div>",
            unsafe_allow_html=True,
        )
        return

    synonymes  = _cached_synonymes(num_pivot)
    meronymie  = _cached_meronymie(num_pivot)
    accessibilite = _cached_accessibilite(num_pivot)

    parties = meronymie["parties"]
    tout    = meronymie["tout"]
    depuis  = accessibilite["accessible_depuis"]
    vers    = accessibilite["donne_acces_a"]

    n_syn = len([it for it in synonymes  if not str(it["label"]).startswith("pivot#")])
    n_mer = len([it for it in parties    if not str(it["label"]).startswith("pivot#")]) \
          + len([it for it in tout       if not str(it["label"]).startswith("pivot#")])
    n_acc = len([it for it in depuis     if not str(it["label"]).startswith("pivot#")]) \
          + len([it for it in vers       if not str(it["label"]).startswith("pivot#")])

    # ── Bandeau récapitulatif ──────────────────────────────────────────────
    def _summary_pill(icon, label, n, color):
        if n == 0:
            return (
                f"<div style='text-align:center; padding:1rem 0.5rem;"
                f" background:#f8fafc; border:1px solid #e2e8f0; border-radius:16px; opacity:0.55;'>"
                f"<div style='font-size:1.6rem;'>{icon}</div>"
                f"<div style='font-size:0.8rem; font-weight:600; color:#94a3b8; margin-top:0.25rem;'>{label}</div>"
                f"<div style='font-size:0.72rem; color:#cbd5e1;'>—</div>"
                f"</div>"
            )
        return (
            f"<div style='text-align:center; padding:1rem 0.5rem;"
            f" background:linear-gradient(135deg,{color}15,{color}08);"
            f" border:1.5px solid {color}50; border-radius:16px;"
            f" box-shadow:0 2px 8px {color}20;'>"
            f"<div style='font-size:1.6rem;'>{icon}</div>"
            f"<div style='font-size:0.8rem; font-weight:700; color:#1e293b; margin-top:0.25rem;'>{label}</div>"
            f"<div style='font-size:1.4rem; font-weight:900; color:{color};'>{n}</div>"
            f"</div>"
        )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(_summary_pill("🔄", "Synonymy", n_syn, "#6366f1"), unsafe_allow_html=True)
    with col2:
        st.markdown(_summary_pill("🔗", "Meronymy", n_mer, "#10b981"), unsafe_allow_html=True)
    with col3:
        st.markdown(_summary_pill("🌐", "Accessibility", n_acc, "#f59e0b"), unsafe_allow_html=True)

    if n_syn == 0 and n_mer == 0 and n_acc == 0:
        st.markdown(
            "<div style='text-align:center; padding:2.5rem; color:#94a3b8; background:#f1f5f9;"
            " border-radius:14px; border:1px dashed #e2e8f0; margin-top:1.2rem;'>"
            "<div style='font-size:2.5rem; margin-bottom:0.5rem;'>🔍</div>"
            "<div style='font-weight:600; color:#64748b;'>No semantic relation</div>"
            "<div style='font-size:0.82rem; margin-top:0.3rem;'>"
            "This prolexeme has no recorded semantic relations in ProLexBase.</div>"
            "</div>",
            unsafe_allow_html=True,
        )
        return

    st.markdown("<div style='height:1.2rem;'></div>", unsafe_allow_html=True)

    # ── Synonymy ──────────────────────────────────────────────────────────
    # Relation : deux prolexèmes partagent le même référent (même pivot ou pivots liés).
    # Table MySQL : synonymy  (NUM_PIVOT-CANONICAL ↔ NUM_PIVOT-SYNONYMOUS)
    if n_syn > 0:
        _section_relation(
            "🔄", "Synonymy",
            "Two proper names denote the same referent — e.g., فرنسا and الجمهورية الفرنسية. "
            "Source : table synonymy de ProLexBase.",
            synonymes, "#6366f1", "#f5f3ff",
        )

    # ── Meronymy ──────────────────────────────────────────────────────────
    # Relation partie/tout : un lieu contient d'autres lieux, ou fait partie d'un ensemble plus grand.
    # Table MySQL : meronymy  (NUM_PIVOT-HOLONYMOUS → le tout, NUM_PIVOT-MERONYMOUS → la partie)
    # On fusionne les deux directions pour montrer toutes les relations de ce pivot.
    all_mer = parties + tout
    if n_mer > 0:
        _section_relation(
            "🔗", "Meronymy",
            "Relation partie/tout entre lieux — ex. فرنسا contient مارتينيك, ou باريس fait partie de فرنسا. "
            "Source : table meronymy de ProLexBase.",
            all_mer, "#10b981", "#f0fdf4",
        )

    # ── Accessibility ──────────────────────────────────────────────────────
    # Relation spatiale de connexion : on peut accéder d'un lieu à un autre.
    # Table MySQL : accessibility  (NUM_PIVOT-ARGUMENT1 → source, NUM_PIVOT-ARGUMENT2 → destination)
    # On fusionne les deux directions pour montrer tous les lieux liés.
    all_acc = vers + depuis
    if n_acc > 0:
        _section_relation(
            "🌐", "Accessibility",
            "Relation de connexion spatiale — ex. باريس est accessible depuis/vers فرنسا. "
            "Source : table accessibility de ProLexBase.",
            all_acc, "#f59e0b", "#fffbeb",
        )

    st.markdown(
        "<div style='margin-top:0.5rem; padding:0.5rem 0.8rem; background:#f8fafc;"
        " border-radius:8px; font-size:0.72rem; color:#94a3b8;'>"
        "Data retrieved directly from ProLexBase (MySQL) &nbsp;·&nbsp; "
        "🔄 synonymy &nbsp;·&nbsp; 🔗 meronymy &nbsp;·&nbsp; 🌐 accessibility</div>",
        unsafe_allow_html=True,
    )


# =============================================================================
# PAGE PROLEXBASE DÉTAIL — Un prolexème avec ses règles
# =============================================================================

def page_prolexbase_detail():
    """Affiche le détail d'un prolexème + applique les règles automatiquement."""
    num_plx = st.session_state.plx_selected
    if not num_plx:
        aller_prolexbase()
        st.rerun()
        return

    st.button("← Back to Database", on_click=aller_prolexbase, type="secondary")

    # Charger le prolexème
    plx = _get_prolexeme_by_id(num_plx)
    if not plx:
        st.error("Prolexeme introuvable.")
        return

    label = plx["LABEL_PROLEXEME"]
    fra_type = plx["FRA_TYPE"]
    num_pivot = plx["NUM_PIVOT"]
    cat_key = _TYPE_TO_CAT.get(fra_type)

    # ── En-tête ──
    st.markdown(
        f"<div style='text-align:center; padding:1.5rem 1rem; background:#ffffff;"
        f" border:1px solid #e2e8f0; border-radius:20px; margin-bottom:1rem;"
        f" box-shadow:0 2px 12px rgba(0,0,0,0.04);'>"
        f"<div style='font-family:Tajawal,sans-serif; font-size:3rem; font-weight:800;"
        f" background:linear-gradient(135deg,#6366f1,#818cf8);"
        f" -webkit-background-clip:text; -webkit-text-fill-color:transparent;"
        f" background-clip:text; direction:rtl;'>{label}</div>"
        f"<span style='background:rgba(99,102,241,0.2); padding:0.25rem 0.9rem;"
        f" border-radius:20px; font-size:0.85rem; color:#818cf8; font-weight:600;'>"
        f"{_display_type_en(fra_type)}</span>"
        f"<span style='background:rgba(16,185,129,0.15); padding:0.25rem 0.7rem;"
        f" border-radius:20px; font-size:0.78rem; color:#10b981; font-weight:500;"
        f" margin-left:0.5rem;'>Pivot #{num_pivot}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ── Infos Pivot ──
    pivot_info = _get_pivot_info(num_pivot)
    if pivot_info:
        st.markdown(
            f"<div style='background:#f1f5f9; border:1px solid #e2e8f0; border-radius:12px;"
            f" padding:0.8rem 1.2rem; margin-bottom:1rem;'>"
            f"<div style='font-size:0.82rem; color:#64748b;'>🔗 <strong>Pivot #{num_pivot}</strong>"
            f" — Type: <span style='color:#818cf8;'>{pivot_info['FRA_TYPE']}</span>"
            f" ({pivot_info['ENG_TYPE']})</div>"
            f"<div style='font-size:0.78rem; color:#94a3b8; margin-top:0.3rem;'>"
            f"{pivot_info['NOTE'] or ''}</div></div>",
            unsafe_allow_html=True,
        )

    # Wikipedia
    if plx["WIKIPEDIA_LINK"]:
        wiki_link = plx["WIKIPEDIA_LINK"]
        st.markdown(
            f"<div style='font-size:0.82rem; color:#94a3b8; margin-bottom:1rem;'>"
            f"🔗 Wikipedia : <a href='https://ar.wikipedia.org/wiki/{wiki_link}' "
            f"target='_blank' style='color:#818cf8;'>{wiki_link}</a></div>",
            unsafe_allow_html=True,
        )

    # ── Onglets : Dérivés | Instances | Notoriety Index | Relations ──
    tab_derives, tab_instances, tab_notoriete, tab_relations = st.tabs([
        "🔀 Derivatives (rules)", "📋 Instances (rules)", "📊 Notoriety Index", "🔗 Semantic relations"
    ])

    with tab_derives:
        if cat_key and cat_key in CATEGORIES:
            cat = CATEGORIES[cat_key]
            _afficher_derives_tab(label, cat_key, cat)
        else:
            st.info(f"Le type « {fra_type} » has no derivation rules in the current system.")

    with tab_instances:
        if cat_key and cat_key in CATEGORIES:
            cat = CATEGORIES[cat_key]
            _afficher_instances_tab(label, cat_key, cat)
        else:
            st.info(f"Le type « {fra_type} » has no instance rules in the current system.")

    with tab_notoriete:
        _nt_key = f"nt_loaded_{num_plx}"
        if not st.session_state.get(_nt_key):
            st.markdown("<div style='height:1.5rem;'></div>", unsafe_allow_html=True)
            st.button(
                "📊 Load notoriety index",
                key=f"btn_nt_{num_plx}",
                use_container_width=True,
                on_click=lambda k=_nt_key: st.session_state.update({k: True}),
            )
            st.markdown(
                "<div style='text-align:center; color:#94a3b8; font-size:0.8rem; margin-top:0.5rem;'>"
                "Click to view the index (Wikipedia data + local database)</div>",
                unsafe_allow_html=True,
            )
        else:
            _afficher_notoriete_prolexeme(num_plx, label, num_pivot, wiki_link_arb=plx.get("WIKIPEDIA_LINK") if plx else None)

    with tab_relations:
        _rel_key = f"rel_loaded_{num_plx}"
        if not st.session_state.get(_rel_key):
            st.markdown("<div style='height:1.5rem;'></div>", unsafe_allow_html=True)
            st.button(
                "🔗 Load semantic relations",
                key=f"btn_rel_{num_plx}",
                use_container_width=True,
                on_click=lambda k=_rel_key: st.session_state.update({k: True}),
            )
            st.markdown(
                "<div style='text-align:center; color:#94a3b8; font-size:0.8rem; margin-top:0.5rem;'>"
                "Click to load relations from MySQL (synonymy, meronymy, accessibility)</div>",
                unsafe_allow_html=True,
            )
        else:
            _afficher_relations_tab(num_pivot)


# =============================================================================
# PAGE EXTRACTION DE TEXTE (Partie 3) — Groq / Llama 3.3
# =============================================================================

def _extraire_et_classifier_llm(texte, api_key):
    """Extrait les noms propres d'un texte arabe ET les classifie en un seul appel Groq.
    Retourne (dict {nom: type}, erreur_str_ou_None).
    """
    import json, re as _re
    types_str = ", ".join(_TYPES_38)
    prompt = (
        "Tu es un expert en Arabic proper names et en lexicographie. "
        "Extrais TOUS les noms propres du texte arabe suivant, puis classe chacun dans EXACTEMENT "
        "l'un des types ci-dessous.\n"
        f"Types disponibles : {types_str}\n\n"
        "Return ONLY a valid JSON object of the form {\"proper_name\": \"Type\"}. "
        "No explanation or surrounding text; return JSON only.\n\n"
        f"Texte arabe :\n{texte}"
    )
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
                "max_tokens": 1000,
            },
            timeout=30,
        )
        data = r.json()
        if "error" in data:
            return {}, data["error"].get("message", str(data["error"]))
        raw = data["choices"][0]["message"]["content"].strip()
        match = _re.search(r"\{.*\}", raw, _re.DOTALL)
        if not match:
            return {}, f"No JSON object found in the response: {raw[:200]}"
        parsed = json.loads(match.group())
        types_lower = {t.lower(): t for t in _TYPES_38}
        result = {}
        for nom, raw_type in parsed.items():
            normalized = types_lower.get(raw_type.lower(), None)
            result[nom] = normalized if normalized else "Last name propre"
        return result, None
    except json.JSONDecodeError as e:
        return {}, f"JSON parsing error: {e}"
    except Exception as e:
        return {}, str(e)


def _ex_wikidata_raw(mot):  # conservé pour compatibilité interne, non utilisé en Partie 3
    """Stub — remplacé par classification LLM."""
    try:
        r = requests.get(
            "https://www.wikidata.org/w/api.php",
            params={
                "action": "wbsearchentities",
                "search": mot,
                "language": "ar",
                "format": "json",
                "limit": 3,
                "uselang": "fr",
            },
            timeout=8,
        )
        results = r.json().get("search", [])
        if not results:
            return {"found": False}

        hit       = results[0]
        entity_id = hit["id"]
        label     = hit.get("label", mot)
        desc      = hit.get("description", "")

        # Récupérer les claims P31 (instance of)
        r2 = requests.get(
            "https://www.wikidata.org/w/api.php",
            params={"action": "wbgetentities", "ids": entity_id, "props": "claims", "format": "json"},
            timeout=8,
        )
        claims   = r2.json().get("entities", {}).get(entity_id, {}).get("claims", {})
        p31_qids = [
            claim.get("mainsnak", {}).get("datavalue", {}).get("value", {}).get("id", "")
            for claim in claims.get("P31", [])
            if claim.get("mainsnak", {}).get("datavalue", {}).get("value", {}).get("id")
        ][:6]

        p31_labels = []
        if p31_qids:
            r3 = requests.get(
                "https://www.wikidata.org/w/api.php",
                params={
                    "action": "wbgetentities",
                    "ids": "|".join(p31_qids),
                    "props": "labels",
                    "languages": "fr|ar|en",
                    "format": "json",
                },
                timeout=8,
            )
            ents = r3.json().get("entities", {})
            for qid in p31_qids:
                lbl = ents.get(qid, {}).get("labels", {})
                p31_labels.append({
                    "qid":    qid,
                    "fr":     lbl.get("fr", {}).get("value", ""),
                    "en":     lbl.get("en", {}).get("value", ""),
                    "ar":     lbl.get("ar", {}).get("value", ""),
                    "mapped": _WIKIDATA_QID_TYPES.get(qid),
                })

        return {
            "found":       True,
            "entity_id":   entity_id,
            "label":       label,
            "description": desc,
            "p31":         p31_labels,
            "url":         f"https://www.wikidata.org/wiki/{entity_id}",
        }
    except Exception as exc:
        return {"found": False, "error": str(exc)}


def page_extraction():
    """Page Partie 3 — pipeline complet :
    1. Entrer un texte arabe
    2. NER (CAMeL/HuggingFace) extrait les noms propres
    3. Groq/Llama 3.3 classifie chaque nom parmi les 38 types ProLexBase
    4. Tableau avec option de changer le type + bouton vers les règles morphologiques
    """
    st.components.v1.html("<script>window.parent.scrollTo(0,0);</script>", height=0)
    if not st.session_state.get("modal_shown_3", False):
        st.session_state.modal_shown_3 = True
        _dialog_part3()
    st.button("← Back to home", on_click=aller_accueil, type="secondary")

    st.markdown(
        "<div style='text-align:center; padding:1.5rem 1rem 1rem 1rem;'>"
        "<div style='font-size:2rem; font-weight:800; background:linear-gradient(135deg,#6366f1,#818cf8);"
        " -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;'>"
        "📝 Part 3 — Extraction &amp; Classification</div>"
        "<div style='color:#64748b; font-size:0.9rem; margin-top:0.4rem;'>"
        "Enter an Arabic text — proper names are extracted and classified automatically."
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown("<hr style='border:none; border-top:1px solid #e2e8f0; margin:0.5rem 0 1.2rem 0;'>",
                unsafe_allow_html=True)

    # ── Groq API key (compacte, repliable) ──
    with st.expander(
        "🔑 Groq API Key" + (" ✅" if st.session_state.groq_api_key else " — required for classification"),
        expanded=not st.session_state.groq_api_key,
    ):
        st.markdown(
            "<div style='font-size:0.85rem; color:#64748b; margin-bottom:0.5rem;'>"
            "Free key from <a href='https://console.groq.com' target='_blank' style='color:#6366f1;'>"
            f"console.groq.com</a> · Model: <code>{GROQ_MODEL}</code></div>",
            unsafe_allow_html=True,
        )
        new_key = st.text_input(
            "Key:", value=st.session_state.groq_api_key,
            type="password", key="groq_key_field",
            placeholder="gsk_...", label_visibility="collapsed",
        )
        if st.button("💾 Save key", key="btn_save_key", use_container_width=False):
            st.session_state.groq_api_key = new_key.strip()
            st.rerun()

    st.markdown("<hr style='border:none; border-top:1px solid #e2e8f0; margin:0.8rem 0 1rem 0;'>",
                unsafe_allow_html=True)

    # ── Zone de texte + bouton ──
    st.markdown(
        "<style>textarea::placeholder{color:#94a3b8!important;opacity:1!important;}</style>",
        unsafe_allow_html=True,
    )
    texte_saisi = st.text_area(
        "✍️ Enter your Arabic text:",
        value=st.session_state.extr_texte,
        height=160,
        placeholder="مثال: سأذهب إلى فرنسا وأزور مدينة باريس ثم ألتقي بمحمد علي في القاهرة ...",
        key="extr_input",
    )
    col_btn, _ = st.columns([1, 3])
    with col_btn:
        analyser = st.button("🔍 Extract & Classify", use_container_width=True)

    if analyser and texte_saisi.strip():
        st.session_state.extr_texte      = normaliser(texte_saisi.strip())
        st.session_state.extr_classified = {}
        st.session_state.extr_version   += 1

    st.markdown("<hr style='border:none; border-top:1px solid #e2e8f0; margin:1rem 0;'>",
                unsafe_allow_html=True)

    if not st.session_state.extr_texte:
        st.markdown(
            "<div style='text-align:center; padding:2.5rem; background:#f1f5f9;"
            " border-radius:14px; border:1px dashed #e2e8f0; color:#94a3b8;'>"
            "Enter Arabic text and click <strong>Extract &amp; Classify</strong>.</div>",
            unsafe_allow_html=True,
        )
        return

    if not st.session_state.groq_api_key:
        st.warning("⚠️ Add your Groq API key to extract and classify proper names.")
        return

    # ── Extraction + Classification en un seul appel Groq ──
    with st.spinner("🤖 Running extraction & classification with the configured Groq model…"):
        classified, llm_err = _extraire_et_classifier_llm(
            st.session_state.extr_texte, st.session_state.groq_api_key
        )

    if llm_err:
        st.error(f"❌ Groq error: {llm_err}")
        return

    if not classified:
        st.info("No proper name was detected in this text.")
        return

    # Fusionner avec les types déjà modifiés manuellement (si re-run)
    for nom, typ in classified.items():
        if nom not in st.session_state.extr_classified:
            st.session_state.extr_classified[nom] = typ

    noms_propres = list(classified.keys())

    # ── Tableau résultats ──
    st.markdown(
        f"<div style='color:#64748b; font-size:0.85rem; margin-bottom:0.8rem;'>"
        f"<strong style='color:#1e293b;'>{len(noms_propres)}</strong> proper name(s) — "
        f"Extraction & Classification: <code style='color:#818cf8;'>{GROQ_MODEL} (Groq)</code>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # En-têtes
    h1, h2, h3 = st.columns([3, 3, 1.8])
    for col, label in zip([h1, h2, h3],
                          ["Arabic proper name", "ProLexBase type (editable)", "Action"]):
        col.markdown(
            f"<div style='font-size:0.78rem; font-weight:600; color:#818cf8; "
            f"padding-bottom:0.3rem;'>{label}</div>",
            unsafe_allow_html=True,
        )
    st.markdown("<hr style='border:none; border-top:1px solid #e2e8f0; margin:0.2rem 0;'>",
                unsafe_allow_html=True)

    vers = st.session_state.extr_version
    for nom in noms_propres:
        current_type = st.session_state.extr_classified.get(nom, "Last name propre")

        c1, c2, c3 = st.columns([3, 3, 1.8])

        with c1:
            st.markdown(
                f"<div style='font-family:Tajawal,sans-serif; font-size:1.2rem; font-weight:700;"
                f" color:#1e293b; direction:rtl; text-align:right; padding:0.5rem 0;'>{nom}</div>",
                unsafe_allow_html=True,
            )

        with c2:
            idx = _TYPES_38.index(current_type) if current_type in _TYPES_38 else len(_TYPES_38) - 1
            chosen = st.selectbox(
                "Type:", _TYPES_38, index=idx,
                key=f"ts_{vers}_{nom}", label_visibility="collapsed",
            )
            st.session_state.extr_classified[nom] = chosen

        with c3:
            cat_k = _TYPE_TO_CAT.get(chosen)
            if cat_k and cat_k in CATEGORIES:
                st.button(
                    "⚙️ Rules →",
                    key=f"apply_{vers}_{nom}",
                    on_click=_aller_regles_avec_mot,
                    args=(cat_k, nom),
                    type="secondary",
                    use_container_width=True,
                )
            else:
                st.markdown(
                    "<div style='color:#94a3b8; font-size:0.75rem; padding:0.5rem 0; "
                    "font-style:italic;'>—</div>",
                    unsafe_allow_html=True,
                )

        st.markdown("<hr style='border:none; border-top:1px solid #edf2f7; margin:0.05rem 0;'>",
                    unsafe_allow_html=True)


# =============================================================================
# HELPERS IMPORT BASE
# =============================================================================

def _split_sql_values(raw: str):
    """Découpe une ligne VALUES SQL en respectant les chaînes entre apostrophes."""
    cells = []
    current = ""
    in_quote = False
    i = 0
    while i < len(raw):
        ch = raw[i]
        if ch == "'" and not in_quote:
            in_quote = True
        elif ch == "'" and in_quote:
            # escaped '' inside string?
            if i + 1 < len(raw) and raw[i + 1] == "'":
                current += "'"
                i += 2
                continue
            in_quote = False
        elif ch == "," and not in_quote:
            cells.append(current.strip().strip("'"))
            current = ""
            i += 1
            continue
        else:
            current += ch
        i += 1
    cells.append(current.strip().strip("'"))
    return cells


def _parse_sql(content: str):
    """Parse les INSERT INTO d'un fichier SQL. Retourne (DataFrame, message_erreur)."""
    # Extraire les noms de colonnes depuis CREATE TABLE
    col_names = None
    create_m = re.search(
        r'CREATE\s+TABLE\s+[`"]?\w+[`"]?\s*\((.*?)\)\s*(?:ENGINE|;)',
        content, re.IGNORECASE | re.DOTALL,
    )
    if create_m:
        skip = {'PRIMARY', 'UNIQUE', 'KEY', 'INDEX', 'CONSTRAINT', 'FOREIGN', 'CHECK'}
        col_names = [
            m.group(1)
            for m in re.finditer(r'^\s*`?(\w+)`?\s+\w+', create_m.group(1), re.MULTILINE)
            if m.group(1).upper() not in skip
        ]

    # Extraire aussi les noms de colonnes depuis INSERT INTO table (col1, col2, ...)
    insert_cols_m = re.search(
        r'INSERT\s+INTO\s+[`"]?\w+[`"]?\s*\(([^)]+)\)\s*VALUES',
        content, re.IGNORECASE,
    )
    if not col_names and insert_cols_m:
        col_names = [c.strip().strip('`"') for c in insert_cols_m.group(1).split(',')]

    rows = []
    insert_pat = re.compile(
        r'INSERT\s+INTO\s+[`"]?\w+[`"]?\s*(?:\([^)]*\))?\s*VALUES\s*(.*?);',
        re.IGNORECASE | re.DOTALL,
    )
    row_pat = re.compile(r'\(([^)]*)\)')

    for ins_m in insert_pat.finditer(content):
        for row_m in row_pat.finditer(ins_m.group(1)):
            rows.append(_split_sql_values(row_m.group(1)))

    if not rows:
        return None, "No INSERT INTO statement was found in the SQL file."

    max_cols = max(len(r) for r in rows)
    rows = [r + [""] * (max_cols - len(r)) for r in rows]

    if col_names and len(col_names) == max_cols:
        df = pd.DataFrame(rows, columns=col_names)
    else:
        df = pd.DataFrame(rows, columns=[f"col_{i + 1}" for i in range(max_cols)])
    return df, None


def _parse_csv(content: str, sep=None):
    """Parse un fichier CSV/TSV. Retourne (DataFrame, message_erreur)."""
    try:
        if sep is None:
            sample = content[:3000]
            counts = {"\t": sample.count("\t"), ";": sample.count(";"), ",": sample.count(",")}
            sep = max(counts, key=counts.get)
        df = pd.read_csv(io.StringIO(content), sep=sep, dtype=str)
        return df, None
    except Exception as exc:
        return None, str(exc)


# =============================================================================
# PAGE IMPORTER VOTRE BASE
# =============================================================================

def page_base_import():
    """Page d'importation et visualisation d'une base de données externe."""
    st.button("← Back to ProLexBase", on_click=aller_prolexbase, type="secondary")

    st.markdown(
        "<div style='text-align:center; padding:1.5rem 1rem 1rem 1rem;'>"
        "<div style='font-size:2rem; font-weight:800; background:linear-gradient(135deg,#6366f1,#818cf8);"
        " -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;'>"
        "📥 Import Your Database</div>"
        "<div style='color:#64748b; font-size:0.9rem; margin-top:0.4rem;'>"
        "Import your database, preview your data, then apply the morphological rules."
        "</div></div>",
        unsafe_allow_html=True,
    )

    st.markdown("<hr style='border:none; border-top:1px solid #e2e8f0; margin:0.5rem 0 1.5rem 0;'>",
                unsafe_allow_html=True)

    # ── Étapes ──
    with st.container(border=True):
        st.markdown(
            "**How does it work?**\n\n"
            "1. 📂 **Step 1** — Import your file (`.sql`, `.csv`, `.tsv`, `.txt`)\n"
            "2. 👁️ **Step 2** — Preview and verify your data\n"
            "3. 🏷️ **Step 3** — Select the column containing Arabic proper names\n"
            "4. ⚙️ **Step 4** — Automatically classify and apply the morphological rules"
        )

    st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)

    # ── ÉTAPE 1 : Upload ──
    st.markdown(
        "<div style='font-size:1rem; font-weight:700; color:#1e293b; margin-bottom:0.5rem;'>📂 Step 1 — Import Your File</div>",
        unsafe_allow_html=True,
    )
    uploaded = st.file_uploader(
        "Choose your file",
        type=["sql", "csv", "tsv", "txt"],
        help="Accepted formats : .sql (INSERT INTO), .csv, .tsv, .txt",
        label_visibility="collapsed",
    )

    if uploaded is not None:
        content = uploaded.read().decode("utf-8", errors="replace")
        ext = uploaded.name.rsplit(".", 1)[-1].lower()

        df, parse_error = None, None
        if ext == "sql":
            df, parse_error = _parse_sql(content)
        elif ext == "tsv":
            df, parse_error = _parse_csv(content, sep="\t")
        else:
            df, parse_error = _parse_csv(content, sep=None)

        if parse_error:
            st.error(f"❌ Parsing error: {parse_error}")
            return
        if df is None or df.empty:
            st.warning("⚠️ File imported, but no data were found.")
            return

        n_rows, n_cols = df.shape

        # ── ÉTAPE 2 : Visualisation ──
        st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)
        st.markdown(
            "<div style='font-size:1rem; font-weight:700; color:#1e293b; margin-bottom:0.5rem;'>👁️ Step 2 — Database Preview</div>",
            unsafe_allow_html=True,
        )
        m1, m2, m3 = st.columns(3)
        m1.metric("📄 Fichier", uploaded.name)
        m2.metric("📊 Lignes", f"{n_rows:,}")
        m3.metric("📋 Colonnes", n_cols)

        st.markdown("<div style='height:0.4rem;'></div>", unsafe_allow_html=True)

        search_val = st.text_input(
            "🔎 Filtrer :",
            placeholder="Tapez pour filtrer dans toutes les colonnes…",
            key="base_import_search",
        )
        if search_val.strip():
            mask = df.apply(
                lambda col: col.astype(str).str.contains(search_val.strip(), case=False, na=False)
            ).any(axis=1)
            df_display = df[mask].reset_index(drop=True)
            st.caption(f"✅ {len(df_display):,} row(s)")
        else:
            df_display = df

        st.dataframe(df_display, use_container_width=True, hide_index=True)

        # ── ÉTAPE 3 : Sélection de la colonne ──
        st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)
        st.markdown(
            "<div style='font-size:1rem; font-weight:700; color:#1e293b; margin-bottom:0.25rem;'>🏷️ Step 3 — Choose the Arabic proper-name column</div>"
            "<div style='font-size:0.82rem; color:#64748b; margin-bottom:0.75rem;'>"
            "Select the column containing the Arabic proper names (prolexemes) to classify."
            "</div>",
            unsafe_allow_html=True,
        )

        # Auto-détecter les colonnes avec du contenu arabe
        arabic_pat = re.compile(r'[\u0600-\u06FF]')
        arabic_cols = [
            c for c in df.columns
            if df[c].dropna().astype(str).apply(lambda x: bool(arabic_pat.search(x))).mean() > 0.3
        ]

        with st.container(border=True):
            col_sel, col_preview = st.columns([2, 3])
            with col_sel:
                default_idx = 0
                if arabic_cols:
                    try:
                        default_idx = list(df.columns).index(arabic_cols[0])
                    except ValueError:
                        default_idx = 0
                    st.caption(f"🔍 Arabic columns detected : {', '.join(arabic_cols)}")
                else:
                    st.caption("ℹ️ No Arabic column was detected automatically — please select one manually.")

                selected_col = st.selectbox(
                    "Prolexeme column:",
                    options=list(df.columns),
                    index=default_idx,
                    key="base_col_select",
                )

            with col_preview:
                st.markdown(
                    f"<div style='font-size:0.78rem; font-weight:600; color:#64748b; margin-bottom:0.4rem;'>"
                    f"PREVIEW — column <code>{selected_col}</code></div>",
                    unsafe_allow_html=True,
                )
                vals = df[selected_col].dropna().astype(str).tolist()
                preview_items = vals[:8]
                items_html = "".join(
                    f"<span style='display:inline-block; background:#f1f5f9; border:1px solid #e2e8f0;"
                    f" border-radius:8px; padding:0.15rem 0.55rem; margin:0.15rem;"
                    f" font-family:Tajawal,sans-serif; font-size:0.88rem; color:#1e293b;'>{v}</span>"
                    for v in preview_items
                )
                more = f" <span style='color:#94a3b8; font-size:0.75rem;'>+{len(vals)-8} autres</span>" if len(vals) > 8 else ""
                st.markdown(
                    f"<div style='direction:rtl; text-align:right; line-height:2;'>{items_html}{more}</div>",
                    unsafe_allow_html=True,
                )

        # ── Bouton Suivant ──
        st.markdown("<div style='height:0.8rem;'></div>", unsafe_allow_html=True)
        col_btn, _ = st.columns([2, 3])
        with col_btn:
            if st.button(
                f"Step 4 → Classify column « {selected_col} » ⚙️",
                type="primary",
                use_container_width=True,
            ):
                st.session_state.base_df = df.to_dict("records")
                st.session_state.base_filename = uploaded.name
                st.session_state.base_col = selected_col
                aller_base_classify()
                st.rerun()


def _build_export_csv(classified: dict, base_filename: str) -> bytes:
    """Construit un CSV UTF-8 avec BOM avec les colonnes :
    nom_propre | type | derives_... | instances_...
    """
    import csv, io as _io

    # Collecter toutes les clés de dérivés et d'instances possibles
    derives_keys_seen: list[str] = []
    instances_keys_seen: list[str] = []

    rows_data = []
    for nom, typ in classified.items():
        cat_k = _TYPE_TO_CAT.get(typ)
        # Dérivés
        derives_dict = {}
        if cat_k and cat_k in CATEGORIES:
            res, _ = appliquer_regles(nom, cat_k)
            if res:
                for label, forme in res.items():
                    key = f"derive_{label}"
                    derives_dict[key] = forme
                    if key not in derives_keys_seen:
                        derives_keys_seen.append(key)
        # Instances
        instances_dict = {}
        if cat_k and cat_k in CATEGORIES:
            inst = appliquer_instances(nom, cat_k)
            if inst and inst.get("formes"):
                for label, forme in inst["formes"].items():
                    key = f"instance_{label}"
                    instances_dict[key] = forme
                    if key not in instances_keys_seen:
                        instances_keys_seen.append(key)

        rows_data.append((nom, typ, derives_dict, instances_dict))

    # Construire les headers
    headers = ["nom_propre", "type"] + derives_keys_seen + instances_keys_seen

    buf = _io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=headers, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    for nom, typ, derives_dict, instances_dict in rows_data:
        row = {"nom_propre": nom, "type": typ}
        row.update(derives_dict)
        row.update(instances_dict)
        writer.writerow(row)

    # UTF-8 with BOM so Excel opens Arabic correctly
    return ("\ufeff" + buf.getvalue()).encode("utf-8")


# =============================================================================
# PAGE BASE — CLASSIFIER & APPLIQUER LES RÈGLES
# =============================================================================

def page_base_classify():
    """Page Étape 4 : classification Groq + application des règles sur la colonne importée."""
    col_back, _ = st.columns([2, 5])
    with col_back:
        st.button("← Back to Import", on_click=aller_base_import, type="secondary")

    col_title = st.session_state.base_col or "?"
    filename  = st.session_state.base_filename or "?"
    st.markdown(
        "<div style='text-align:center; padding:1.5rem 1rem 1rem 1rem;'>"
        "<div style='font-size:2rem; font-weight:800; background:linear-gradient(135deg,#6366f1,#818cf8);"
        " -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;'>"
        "⚙️ Classification & Rules</div>"
        f"<div style='color:#64748b; font-size:0.9rem; margin-top:0.4rem;'>"
        f"Fichier : <strong>{filename}</strong> · Colonne : "
        f"<code style='background:#f1f5f9; padding:0.1rem 0.4rem; border-radius:6px;'>{col_title}</code>"
        "</div></div>",
        unsafe_allow_html=True,
    )
    st.markdown("<hr style='border:none; border-top:1px solid #e2e8f0; margin:0.5rem 0 1.2rem 0;'>",
                unsafe_allow_html=True)

    # Vérifications
    if not st.session_state.base_df or not st.session_state.base_col:
        st.warning("⚠️ No database has been imported. Please import a file first.")
        return

    import pandas as _pd
    df = _pd.DataFrame(st.session_state.base_df)
    col = st.session_state.base_col
    if col not in df.columns:
        st.error(f"❌ The column “{col}” no longer exists in the database.")
        return

    noms = df[col].dropna().astype(str).str.strip().tolist()
    noms = [n for n in noms if n]

    if not noms:
        st.warning("⚠️ The selected column contains no values.")
        return

    # ── Groq API key ──
    with st.expander(
        "🔑 Groq API Key" + (" ✅" if st.session_state.groq_api_key else " — required"),
        expanded=not st.session_state.groq_api_key,
    ):
        new_key = st.text_input(
            "Key:", value=st.session_state.groq_api_key,
            type="password", key="base_groq_key_field",
            placeholder="gsk_...", label_visibility="collapsed",
        )
        if st.button("💾 Save", key="btn_save_base_key"):
            st.session_state.groq_api_key = new_key.strip()
            st.rerun()

    if not st.session_state.groq_api_key:
        st.warning("⚠️ Add your Groq API key to classify proper names.")
        return

    # ── Bouton classifier ──
    col_btn, _ = st.columns([2, 4])
    with col_btn:
        if st.button(
            f"🤖 Classify the {len(noms)} proper names (Groq)",
            type="primary",
            use_container_width=True,
            key="btn_classify_base",
        ):
            # Send tous les noms comme un faux "texte" en les joignant
            texte_concat = "، ".join(noms)
            with st.spinner("🤖 Running classification with the configured Groq model…"):
                classified, llm_err = _extraire_et_classifier_llm(
                    texte_concat, st.session_state.groq_api_key
                )
            if llm_err:
                st.error(f"❌ Groq error: {llm_err}")
            elif not classified:
                st.warning("No proper name was classified. Check the column content.")
            else:
                # Mapper les résultats sur les noms originaux
                classified_lower = {k.strip(): v for k, v in classified.items()}
                for nom in noms:
                    matched = classified_lower.get(nom) or classified_lower.get(nom.strip())
                    if not matched:
                        # chercher une correspondance approximative
                        for k, v in classified_lower.items():
                            if nom in k or k in nom:
                                matched = v
                                break
                    st.session_state.base_classified[nom] = matched or "Last name propre"
                st.session_state.base_classify_version += 1
                st.rerun()

    # ── Tableau résultats ──
    if st.session_state.base_classified:
        st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)
        n_classified = len(st.session_state.base_classified)
        st.markdown(
            f"<div style='color:#64748b; font-size:0.83rem; margin-bottom:0.8rem;'>"
            f"<strong style='color:#1e293b;'>{n_classified}</strong> classified name(s) — "
            f"<code style='color:#818cf8;'>{GROQ_MODEL} (Groq)</code></div>",
            unsafe_allow_html=True,
        )

        # En-têtes
        h1, h2, h3 = st.columns([3, 3, 1.8])
        for col_h, label in zip([h1, h2, h3], ["Arabic proper name", "Type ProLexBase", "Rules"]):
            col_h.markdown(
                f"<div style='font-size:0.75rem; font-weight:700; color:#818cf8; "
                f"text-transform:uppercase; letter-spacing:0.04em; padding-bottom:0.3rem;'>{label}</div>",
                unsafe_allow_html=True,
            )
        st.markdown("<hr style='border:none; border-top:1px solid #e2e8f0; margin:0.1rem 0 0.3rem 0;'>",
                    unsafe_allow_html=True)

        vers = st.session_state.base_classify_version
        for i, nom in enumerate(noms):
            current_type = st.session_state.base_classified.get(nom, "Last name propre")
            c1, c2, c3 = st.columns([3, 3, 1.8])

            with c1:
                st.markdown(
                    f"<div style='font-family:Tajawal,sans-serif; font-size:0.95rem; font-weight:700;"
                    f" color:#1e293b; direction:rtl; text-align:right; padding:0.4rem 0;'>{nom}</div>",
                    unsafe_allow_html=True,
                )
            with c2:
                idx = _TYPES_38.index(current_type) if current_type in _TYPES_38 else len(_TYPES_38) - 1
                chosen = st.selectbox(
                    "Type:", _TYPES_38, index=idx,
                    key=f"base_ts_{vers}_{i}_{nom}", label_visibility="collapsed",
                )
                st.session_state.base_classified[nom] = chosen
            with c3:
                cat_k = _TYPE_TO_CAT.get(chosen)
                if cat_k and cat_k in CATEGORIES:
                    st.button(
                        "⚙️ Rules →",
                        key=f"base_apply_{vers}_{i}_{nom}",
                        on_click=_aller_regles_avec_mot,
                        args=(cat_k, nom),
                        type="secondary",
                        use_container_width=True,
                    )
                else:
                    st.markdown(
                        "<div style='color:#94a3b8; font-size:0.75rem; padding:0.5rem 0; "
                        "font-style:italic;'>—</div>",
                        unsafe_allow_html=True,
                    )

            st.markdown(
                "<hr style='border:none; border-top:1px solid #f1f5f9; margin:0;'>",
                unsafe_allow_html=True,
            )

        # ── Bouton Export ──
        st.markdown("<div style='height:1.2rem;'></div>", unsafe_allow_html=True)
        st.markdown("<hr style='border:none; border-top:2px solid #e2e8f0; margin-bottom:1rem;'>",
                    unsafe_allow_html=True)
        st.markdown(
            "<div style='font-size:1rem; font-weight:700; color:#1e293b; margin-bottom:0.5rem;'>"
            "📤 Export Results</div>"
            "<div style='font-size:0.82rem; color:#64748b; margin-bottom:0.8rem;'>"
            "Download a CSV file containing each proper name, its type, "
            "its derivatives (Nisba) and its grammatical instances (case forms)."
            "</div>",
            unsafe_allow_html=True,
        )
        csv_bytes = _build_export_csv(
            st.session_state.base_classified,
            st.session_state.base_filename,
        )
        st.download_button(
            label="⬇️ Download Enriched CSV",
            data=csv_bytes,
            file_name=(st.session_state.base_filename.rsplit(".", 1)[0] if st.session_state.base_filename else "base") + "_enrichi.csv",
            mime="text/csv; charset=utf-8",
            type="primary",
            use_container_width=False,
        )
    else:
        st.markdown(
            "<div style='text-align:center; padding:2.5rem; background:#f1f5f9;"
            " border-radius:14px; border:1px dashed #e2e8f0; color:#94a3b8;'>"
            "Click <strong>Classify</strong> to identify the type of each proper name.</div>",
            unsafe_allow_html=True,
        )


# =============================================================================
# PAGE FEEDBACK / SUGGESTIONS
# =============================================================================

_FEEDBACK_FILE = os.path.join(os.path.dirname(__file__), "feedback.json")


def _charger_feedback():
    if os.path.exists(_FEEDBACK_FILE):
        with open(_FEEDBACK_FILE, "r", encoding="utf-8") as fh:
            try:
                return json.load(fh)
            except Exception:
                return []
    return []


def _sauvegarder_feedback(entree):
    data = _charger_feedback()
    data.append(entree)
    with open(_FEEDBACK_FILE, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def page_feedback():
    # Désactiver autocomplete navigateur + corriger direction LTR pour champs latin
    st.markdown("""
<style>
/* Champs feedback en LTR (noms français) */
[data-testid="stTextInput"] input {
    direction: ltr !important;
    text-align: left !important;
    font-size: 0.95rem !important;
}
/* Masquer suggestions autofill navigateur */
[data-testid="stTextInput"] input::-webkit-contacts-auto-fill-button,
[data-testid="stTextInput"] input::-webkit-credentials-auto-fill-button {
    display: none !important;
    visibility: hidden !important;
}
</style>
<script>
setTimeout(function() {
    document.querySelectorAll('input[type="text"]').forEach(function(el) {
        el.setAttribute('autocomplete', 'off');
        el.setAttribute('autocorrect', 'off');
        el.setAttribute('autocapitalize', 'off');
    });
}, 500);
</script>""", unsafe_allow_html=True)

    st.button("← Back", key="btn_feedback_back", on_click=aller_accueil)

    st.markdown("### 💡 Suggest an improvement")
    st.markdown(
        "<div style='background:linear-gradient(135deg,rgba(99,102,241,0.07),rgba(129,140,248,0.04));"
        "border:1px solid rgba(99,102,241,0.18);border-radius:14px;padding:1rem 1.2rem;"
        "margin-bottom:1rem;line-height:1.75;font-size:0.875rem;color:#374151;'>"
        "<strong style='color:#6366f1;'>🌐 Arabic has exceptionally rich morphology.</strong><br>"
        "Its triliteral and quadriliteral root system can generate many derived forms "
        "from a single word. This system covers the most frequent morphological rules "
        "for Arabic proper names (Nisba, grammatical instances, plurals, etc.), but does not claim to be exhaustive.<br><br>"
        "If you identify an uncovered case — a dialectal rule, a rare form, or a specific derivation type — "
        "please report it here. Your contribution helps improve the system's coverage."
        "</div>",
        unsafe_allow_html=True,
    )
    st.divider()

    if st.session_state.feedback_sent:
        st.success("Feedback sent successfully! Thank you for your contribution.")
        return

    col_left, col_right = st.columns([1, 2])

    with col_left:
        st.markdown("**Your profile**")
        nom = st.text_input("Last name", key="fb_nom")
        prenom = st.text_input("First name", key="fb_prenom")
        profil = st.selectbox(
            "You are...",
            options=["— Select —", "NLP expert", "Researcher", "Student", "Teacher / Lecturer", "Other"],
            key="fb_profil",
        )

    with col_right:
        st.markdown("**Your feedback**")
        sujet = st.selectbox(
            "Subject",
            options=[
                "— Select —",
                "About ProLexBase",
                "About the Rule System",
                "New rule to add",
                "Issue / error detected",
                "Other",
            ],
            key="fb_sujet",
        )
        remarque = st.text_area(
            "Feedback",
            key="fb_texte",
            placeholder="Describe your suggestion or observation...",
            height=150,
        )

    envoyer = st.button("Send", key="btn_fb_envoyer", type="primary")

    if envoyer:
        erreurs = []
        if not nom.strip():
            erreurs.append("Last name is required.")
        if not prenom.strip():
            erreurs.append("First name is required.")
        if profil == "— Select —":
            erreurs.append("Please select your profile.")
        if sujet == "— Select —":
            erreurs.append("Please select a subject.")
        if not remarque.strip():
            erreurs.append("Feedback cannot be empty.")
        if erreurs:
            for e in erreurs:
                st.warning(e)
        else:
            entree = {
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "nom": nom.strip(),
                "prenom": prenom.strip(),
                "profil": profil,
                "sujet": sujet,
                "remarque": remarque.strip(),
            }
            _sauvegarder_feedback(entree)
            st.session_state.feedback_sent = True
            st.rerun()


# =============================================================================
# PAGE À PROPOS
# =============================================================================

def page_about():
    # Bouton retour — haut de page
    st.button("← Back to home", key="btn_about_retour", on_click=aller_accueil)
    st.divider()

    st.markdown("## About de ProlexArabic")
    st.markdown(
        "**ProlexArabic** is a Natural Language Processing (NLP) research platform "
        "dedicated to the **morphological enrichment of Arabic proper names**, "
        "developed as part of a research project (2026)."
    )
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📚 What is ProLexBase?")
        st.markdown(
            "ProLexBase is a **multilingual lexical database** of proper names.\n\n"
            "Each entry is represented by a **prolexeme** linked to a multilingual **pivot**, "
            "allowing forms of the same proper name to be linked across languages."
        )
    with col2:
        st.markdown("### 🔧 What the System Does")
        st.markdown(
            "The system applies **morphological rules** to:\n\n"
            "- Generate **inflected forms** (instances) of an Arabic proper name\n"
            "- Produce **relational adjectives** (Nisba / derivatives)\n"
            "- Automatically classify proper names extracted from text\n"
            "- Enrich an imported proper-name database"
        )
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 🗂️ The Three Modules")
        st.markdown(
            "| Module | Description |\n"
            "|---|---|\n"
            "| 🗄️ **Part 1** | ProLexBase exploration |\n"
            "| ⚙️ **Partie 2** | Morphological rule system |\n"
            "| 📝 **Partie 3** | Text extraction and classification |"
        )
    with c2:
        st.markdown("### 🎓 Academic Context")
        st.markdown(
            "Project developed as part of a research project "
            "en informatique, spécialité TAL (Natural Language Processing).\n\n"
            "**Year** : 2025 – 2026"
        )




# =============================================================================
# ROUTEUR
# =============================================================================

if st.session_state.page == "landing":
    page_landing()
elif st.session_state.page == "accueil":
    page_accueil()
elif st.session_state.page == "systeme":
    page_systeme()
elif st.session_state.page == "categorie":
    page_categorie()
elif st.session_state.page == "prolexbase":
    page_prolexbase()
elif st.session_state.page == "prolexbase_detail":
    page_prolexbase_detail()
elif st.session_state.page == "extraction":
    page_extraction()
elif st.session_state.page == "base_import":
    page_base_import()
elif st.session_state.page == "base_classify":
    page_base_classify()
elif st.session_state.page == "feedback":
    page_feedback()
elif st.session_state.page == "about":
    page_about()
else:
    page_accueil()
