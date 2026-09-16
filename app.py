import streamlit as st
import google.generativeai as genai
import json
import re

# Configuration de la page
st.set_page_config(page_title="Menu & Courses", page_icon="🥗", layout="centered")

# --- DESIGN CSS : FOND SOMBRE & STYLE APP NATIVE ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    
    .streamlit-expanderHeader {
        background-color: #1E2530 !important;
        color: #FAFAFA !important;
        border-radius: 12px !important;
        border: 1px solid #2D3748 !important;
        margin-bottom: 8px;
    }
    
    .stTabs [data-baseweb="tab-list"] button div div {
        color: #FAFAFA !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🥗 Menu & Courses")

# --- CONNEXION IA SÉCURISÉE AUTOMATIQUE ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # Recherche automatique du premier modèle disponible qui génère du contenu
    modelsDisponibles = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    nom_modele = modelsDisponibles[0] if modelsDisponibles else 'gemini-1.5-flash'
    model = genai.GenerativeModel(nom_modele)
except Exception as e:
    st.error(f"Erreur de configuration IA : {e}")
    model = None

# Initialisation de la mémoire
if 'menu_data' not in st.session_state:
    st.session_state.menu_data = {}
if 'batch_data' not in st.session_state:
    st.session_state.batch_data = {}
if 'favoris' not in st.session_state:
    st.session_state.favoris = {}

jours_semaine = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

# --- ONGLETS ---
tab1, tab2, tab3, tab4 = st.tabs(["📅 Plan", "🛒 Courses", "🧊 Batch", "⭐ Favoris"])

# ONGLET 1 : PLAN DE LA SEMAINE
with tab1:
    st.write("📌 **Sélectionne les jours à générer**")
    
    jours_a_generer = []
    cols = st.columns(7)
    
    for i, jour in enumerate(jours_semaine):
        is_locked = st.session_state.menu_data.get(jour) is not None
        with cols[i]:
            a_generer = st.checkbox(jour[:3], value=not is_locked, key=f"chk_{jour}")
            if a_generer:
                jours_a_generer.append(jour)

    st.write("---")
    
    if st.button("✨ Générer les repas sélectionnés", type="primary"):
        if not model:
            st.error("L'IA n'est pas disponible.")
        elif not jours_a_generer:
            st.warning("Aucun jour sélectionné !")
        else:
            with st.spinner("L'IA prépare vos menus..."):
                liste_favoris = list(st.session_state.favoris.keys())
                consigne_favoris = f"Favoris à considérer si possible : {liste_favoris}." if liste_favoris else ""
                
                prompt = f"""
                Tu es un nutritionniste et chef cuisinier. Génère un menu UNIQUEMENT pour ces jours : {jours_a_generer}.
                {consigne_favoris}
                Règles strictes :
                - Souper ciblant entre 450 et 520 kcal par personne.
                - AUCUN POIVRON.
                - Alterner 1 jour Omnivore, 1 jour 100% Végétarien.
                - Portions pour 2 personnes : 400 à 500g de légumes min, 80-100g de féculents crus (ou 300-350g pommes de terre), 300-360g de viande/poisson OU 320-350g végé, max 2 c.à.s d'huile.
                - Inclus les macros précises (protéines, glucides, lipides), le temps de préparation, et le type ("Omnivore" ou "Végétarien").
                - Inclus également une section "batch_cooking" qui liste précisément les féculents et légumes de base à cuire en avance le dimanche.

                Renvoie UNIQUEMENT du JSON valide, sans texte autour :
                {{
                  "jours": [
                    {{
                      "jour": "Lundi",
                      "type": "Omnivore",
                      "nom": "Titre du plat",
                      "temps_prep": "20 min",
                      "kcal": 480,
                      "proteines": 40,
                      "glucides": 45,
                      "lipides": 15,
                      "ingredients": [
                        {{"nom": "Poulet", "quantite": 340, "unite": "g", "rayon": "Viandes"}}
                      ],
                      "recette": [
                        "Cuisson des féculents et légumes.",
                        "Saisir la viande à la minute."
                      ]
                    }}
                  ],
                  "batch_cooking": [
                    {{
                      "boite": "Boîte Féculent (ex: Riz complet)",
                      "quantite_par_boite": "90g cru (ou 220g cuit pour 2)",
                      "frequence": "Préparer 3 boîtes pour la semaine"
                    }}
                  ]
                }}
                """
                try:
                    reponse = model.generate_content(prompt)
                    match = re.search(r'\{.*\}', reponse.text, re.DOTALL)
                    if match:
                        data_brute = json.loads(match.group(0))
                        nouveaux_jours = data_brute.get("jours", [])
                        for repas in nouveaux_jours:
                            st.session_state.menu_data[repas["jour"]] = repas
                        
                        st.session_state.batch_data = data_brute.get("batch_cooking", [])
                        
                        st.success("Menu généré avec succès !")
                        st.rerun()
                    else:
                        st.error("Erreur de format de l'IA. Relance.")
                except Exception as e:
                    st.error(f"Erreur de génération : {e}")

    st.write("---")
    if st.session_state.menu_data:
        for jour in jours_semaine:
            repas = st.session_state.menu_data.get(jour)
            if repas:
                type_repas = repas.get('type', 'Omnivore')
                badge = "🥬 Végé" if type_repas == "Végétarien" else "🥩 Omnivore"
                titre_label = f"{jour} : {badge} | {repas['nom']} | ⏱️ {repas.get('temps_prep', 'N/A')} | 🔥 {repas.get('kcal', 0)} kcal"
                
                with st.expander(titre_label):
                    col_swap, col_fav = st.columns([1, 1])
                    with col_swap:
                        if st.button(f"🔄 Remplacer ce plat", key=f"swap_{jour}"):
                            with st.spinner(f"Remplacement du menu de {jour}..."):
                                prompt_swap = f"""
                                Génère un unique repas du soir (souper) pour le jour de {jour}, destiné à 2 personnes.
                                Type imposé : {type_repas}.
                                Règles strictes : Entre 450 et 520 kcal, AUCUN POIVRON.
                                Renvoie UNIQUEMENT du JSON valide au format :
                                {{
                                  "jour": "{jour}",
                                  "type": "{type_repas}",
                                  "nom": "Titre du plat",
                                  "temps_prep": "20 min",
                                  "kcal": 480,
                                  "proteines": 40,
                                  "glucides": 45,
                                  "lipides": 15,
                                  "ingredients": [{{"nom": "Ingrédient", "quantite": 100, "unite": "g", "rayon": "Légumes"}}],
                                  "recette": ["Etape 1"]
                                }}
                                """
                                try:
                                    rep_swap = model.generate_content(prompt_swap)
                                    match_s = re.search(r'\{.*\}', rep_swap.text, re.DOTALL)
                                    if match_s:
                                        nouveau_repas = json.loads(match_s.group(0))
                                        st.session_state.menu_data[jour] = nouveau_repas
                                        st.success(f"Plat de {jour} remplacé !")
                                        st.rerun()
                                except Exception as e:
                                    st.error(f"Erreur lors du swap : {e}")
                    
                    with col_fav:
                        nom_plat = repas['nom']
                        if nom_plat not in st.session_state.favoris:
                            if st.button("⭐ Mettre en favori", key=f"fav_{jour}_{nom_plat}"):
                                st.session_state.favoris[nom_plat] = repas
                                st.rerun()
                        else:
                            st.info("⭐ Déjà en favoris")
                    
                    st.write("---")
                    st.markdown(f"**Résumé macro** — {repas.get('kcal', 0)} kcal")
                    prot = repas.get('proteines', 0)
                    gluc = repas.get('glucides', 0)
                    lip = repas.get('lipides', 0)
                    
                    st.text(f"Protéines : {prot}g / 45g")
                    st.progress(min(float(prot) / 45.0, 1.0))
                    st.text(f"Glucides : {gluc}g / 55g")
                    st.progress(min(float(gluc) / 55.0, 1.0))
                    st.text(f"Lipides : {lip}g / 20g")
                    st.progress(min(float(lip) / 20.0, 1.0))
                    
                    st.write("---")
                    col_ing, col_rec = st.columns([1, 2])
                    with col_ing:
                        st.markdown("### 🛒 Ingrédients (2 pers.)")
                        for ing in repas.get("ingredients", []):
                            st.write(f"- {ing['nom']} : {ing['quantite']} {ing['unite']}")
                    with col_rec:
                        st.markdown("### 🍳 Préparation")
                        for etape in repas.get("recette", []):
                            st.write(f"- {etape}")

# ONGLET 2 : LISTE DE COURSES
with tab2:
    if st.session_state.menu_data:
        courses = {}
        for repas in st.session_state.menu_data.values():
            for ing in repas.get("ingredients", []):
                rayon = str(ing.get("rayon", "Autre")).capitalize()
                nom = str(ing["nom"]).capitalize()
                qte = ing["quantite"]
                unite = ing["unite"]
                cle_ing = f"{nom} ({unite})"
                
                if rayon not in courses:
                    courses[rayon] = {}
                try:
                    courses[rayon][cle_ing] = courses[rayon].get(cle_ing, 0) + float(qte)
                except ValueError:
                    courses[rayon][cle_ing] = qte

        st.subheader("🛒 Liste de courses consolidée")
        for rayon, ingredients in courses.items():
            st.markdown(f"### 📍 {rayon}")
            for ing, qte in ingredients.items():
                qte_affichage = int(qte) if isinstance(qte, float) and qte.is_integer() else qte
                st.checkbox(f"{ing} : {qte_affichage}", key=f"chk_{rayon}_{ing}")
    else:
        st.warning("Générez d'abord un menu dans le premier onglet.")

# ONGLET 3 : BATCH COOKING
with tab3:
    st.subheader("🧊 Préparation Batch Cooking du Dimanche")
    if st.session_state.batch_data:
        st.info("Voici le détail exact des quantités à cuisiner en avance et à répartir dans vos boîtes hermétiques :")
        for item in st.session_state.batch_data:
            st.write(f"- {item.get('boite')} : {item.get('quantite_par_boite')} *({item.get('frequence')})*")
    else:
        st.warning("Générez d'abord un menu pour voir le planning de batch cooking.")

# ONGLET 4 : FAVORIS
with tab4:
    st.subheader("⭐ Vos Recettes Favorites")
    if st.session_state.favoris:
        for nom, repas in list(st.session_state.favoris.items()):
            with st.expander(f"⭐ {nom} ({repas.get('type', 'Inconnu')})"):
                if st.button("❌ Retirer", key=f"del_{nom}"):
                    del st.session_state.favoris[nom]
                    st.rerun()
                
                st.markdown("### 🛒 Ingrédients")
                for ing in repas.get("ingredients", []):
                    st.write(f"- {ing['nom']} : {ing['quantite']} {ing['unite']}")
    else:
        st.info("Aucun favori pour le moment.")