import streamlit as st
import google.generativeai as genai
import json
import re

# Configuration de la page
st.set_page_config(page_title="Menu & Courses", page_icon="🥗", layout="centered")
st.title("🤖 Menu, Courses & Batch Cooking")

# --- CONNEXION IA SÉCURISÉE ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel(model_name="gemini-3.6-flash")
    st.success("✅ Connecté à l'IA avec succès")
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

# --- ONGLETS (4 onglets désormais) ---
tab1, tab2, tab3, tab4 = st.tabs(["📅 Plan de la semaine", "🛒 Liste de courses", "🧊 Batch Cooking", "⭐ Favoris"])

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
            with st.spinner("L'IA prépare vos menus et calcule votre Batch Cooking..."):
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
                - Inclus également une section "batch_cooking" qui liste précisément les féculents et légumes de base à cuire en avance le dimanche pour la semaine, avec le nombre de boîtes/tupperwares et le grammage exact par boîte pour 2 personnes.

                Renvoie UNIQUEMENT du JSON valide, sans texte autour, selon cette structure exacte :
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
                        
                        st.success("Menu et Batch Cooking générés avec succès !")
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
                with st.expander(f"**{jour}** : {repas['nom']} ({repas['type']}) | ⏱️ {repas.get('temps_prep', 'N/A')}"):
                    nom_plat = repas['nom']
                    est_favori = nom_plat in st.session_state.favoris
                    
                    if not est_favori:
                        if st.button("⭐ Ajouter aux favoris", key=f"fav_{jour}_{nom_plat}"):
                            st.session_state.favoris[nom_plat] = repas
                            st.rerun()
                    else:
                        st.success("⭐ Déjà en favoris")
                    
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Calories", f"{repas.get('kcal', 0)} kcal")
                    c2.metric("Protéines", f"{repas.get('proteines', 0)} g")
                    c3.metric("Glucides", f"{repas.get('glucides', 0)} g")
                    c4.metric("Lipides", f"{repas.get('lipides', 0)} g")
                    
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

# ONGLET 3 : BATCH COOKING DU DIMANCHE
with tab3:
    st.subheader("🧊 Préparation Batch Cooking du Dimanche")
    if st.session_state.batch_data:
        st.info("Voici le détail exact des quantités à cuisiner en avance et à répartir dans vos boîtes hermétiques pour la semaine :")
        for item in st.session_state.batch_data:
            st.write(f"- **{item.get('boite')}** : {item.get('quantite_par_boite')} *({item.get('frequence')})*")
    else:
        st.warning("Générez d'abord un menu dans le premier onglet pour voir le planning de batch cooking.")

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