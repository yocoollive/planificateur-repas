import streamlit as st
import google.generativeai as genai
import json
import re
import urllib.parse

# Configuration Gemini mise à jour
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel(model_name="gemini-2.5-flash")

st.set_page_config(page_title="Menu & Courses - Ulysse & Compagne", page_icon="🥗", layout="centered")
st.title("🥗 Menu, Courses, Batch & Favoris")

jours_semaine = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

# Récupération des données depuis l'URL
query_params = st.query_params
app_data = {"menu": {}, "batch": [], "favoris": {}}

if "data" in query_params:
    try:
        json_str = urllib.parse.unquote(query_params["data"])
        app_data = json.loads(json_str)
        if not isinstance(app_data, dict):
            app_data = {"menu": {}, "batch": [], "favoris": {}}
    except Exception:
        app_data = {"menu": {}, "batch": [], "favoris": {}}

menu_actuel = app_data.get("menu", {})
batch_actuel = app_data.get("batch", [])
favoris_actuels = app_data.get("favoris", {})

tab1, tab2, tab3, tab4 = st.tabs(["📅 Plan", "🛒 Courses", "🧊 Batch Cooking", "⭐ Favoris"])

# Fonction de sauvegarde globale dans l'URL
def sauvegarder_url():
    app_data["menu"] = menu_actuel
    app_data["batch"] = batch_actuel
    app_data["favoris"] = favoris_actuels
    st.query_params["data"] = json.dumps(app_data)

# ONGLET 1 : PLAN DE LA SEMAINE
with tab1:
    st.write("📌 **Sélectionne les jours à générer :**")
    jours_a_generer = []
    cols = st.columns(7)
    for i, jour in enumerate(jours_semaine):
        with cols[i]:
            if st.checkbox(jour[:3], value=True, key=f"chk_{jour}"):
                jours_a_generer.append(jour)

    if st.button("✨ Générer les repas sélectionnés (IA)", type="primary"):
        if not jours_a_generer:
            st.warning("Sélectionne au moins un jour !")
        else:
            with st.spinner("L'IA prépare les recettes, le batch cooking et les calories..."):
                prompt = f"""
                Tu es un nutritionniste et chef cuisinier. Génère un menu UNIQUEMENT pour ces jours : {jours_a_generer}.
                Règles strictes :
                - Souper ciblant entre 450 et 520 kcal par personne.
                - AUCUN POIVRON.
                - Alterner 1 jour Omnivore, 1 jour 100% Végétarien.
                - Portions pour 2 personnes : 400 à 500g de légumes minimum, 80 à 100g de féculents crus (ou 300-350g pommes de terre), 300 à 360g de viande/poisson OU 320-350g d'alternative végétale, max 2 c.à.s d'huile.
                - Inclus une liste "batch_cooking" indiquant quoi préparer le dimanche (féculents, légumes racines).
                
                Renvoie UNIQUEMENT du JSON valide avec cette structure exacte :
                {{
                  "jours": [
                    {{
                      "jour": "Nom du jour",
                      "type": "Omnivore",
                      "nom": "Titre du plat",
                      "temps_prep": "20 min",
                      "kcal": 480,
                      "ingredients": [
                        {{"nom": "Ingredient", "quantite": 300, "unite": "g", "rayon": "Viandes"}}
                      ],
                      "recette": ["Étape 1...", "Étape 2..."]
                    }}
                  ],
                  "batch_cooking": [
                    {{
                      "element": "Riz complet",
                      "quantite": "180g cru",
                      "instruction": "Cuire dans l'eau bouillante et stocker en boîte hermétique."
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
                            menu_actuel[repas["jour"]] = repas
                        batch_actuel = data_brute.get("batch_cooking", [])
                        
                        sauvegarder_url()
                        st.success("Menu et Batch Cooking générés ! Le lien a été mis à jour.")
                        st.rerun()
                except Exception as e:
                    st.error(f"Erreur : {e}")

    if menu_actuel:
        st.info("💡 **Astuce Partage :** Copie l'URL de cette page pour la partager avec ta compagne sur son iPhone !")
        for jour in jours_semaine:
            repas = menu_actuel.get(jour)
            if repas:
                with st.expander(f"**{jour}** : {repas['nom']} ({repas['type']}) | ⏱️ {repas.get('temps_prep', '')}"):
                    c1, c2 = st.columns([3, 1])
                    c1.write(f"🔥 **Calories :** {repas.get('kcal', '')} kcal / pers.")
                    
                    nom_plat = repas['nom']
                    est_favori = nom_plat in favoris_actuels
                    if not est_favori:
                        if c2.button("⭐ Favori", key=f"fav_{jour}"):
                            favoris_actuels[nom_plat] = repas
                            sauvegarder_url()
                            st.rerun()
                    else:
                        c2.success("⭐ Favori")

                    st.markdown("### 🛒 Ingrédients (pour 2)")
                    for ing in repas["ingredients"]:
                        st.write(f"- {ing['nom']} : {ing['quantite']} {ing['unite']}")
                    st.markdown("### 🍳 Préparation")
                    for etape in repas.get("recette", []):
                        st.write(f"- {etape}")

# ONGLET 2 : LISTE DE COURSES
with tab2:
    if menu_actuel:
        courses = {}
        for repas in menu_actuel.values():
            for ing in repas.get("ingredients", []):
                rayon = str(ing.get("rayon", "Autre")).capitalize()
                nom = str(ing["nom"]).capitalize()
                qte = ing["quantite"]
                unite = ing["unite"]
                cle = f"{nom} ({unite})"
                if rayon not in courses:
                    courses[rayon] = {}
                try:
                    courses[rayon][cle] = courses[rayon].get(cle, 0) + float(qte)
                except ValueError:
                    courses[rayon][cle] = qte

        st.subheader("🛒 Liste de courses consolidée")
        for rayon, ingredients in courses.items():
            st.markdown(f"### 📍 {rayon}")
            for ing, qte in ingredients.items():
                qte_aff = int(qte) if isinstance(qte, float) and qte.is_integer() else qte
                st.checkbox(f"{ing} : {qte_aff}", key=f"shop_{rayon}_{ing}")
    else:
        st.warning("Générez d'abord un menu dans le premier onglet pour afficher la liste de courses.")

# ONGLET 3 : BATCH COOKING
with tab3:
    st.subheader("🧊 Préparation Batch Cooking (Dimanche)")
    if batch_actuel:
        for item in batch_actuel:
            st.markdown(f"- **{item.get('element')}** ({item.get('quantite')}) : {item.get('instruction')}")
    else:
        st.info("Aucun batch cooking généré. Génère un menu dans le premier onglet pour voir les instructions du dimanche.")

# ONGLET 4 : FAVORIS
with tab4:
    st.subheader("⭐ Vos Recettes Favorites")
    if favoris_actuels:
        for nom, repas in list(favoris_actuels.items()):
            with st.expander(f"⭐ {nom} ({repas.get('type', '')})"):
                if st.button("❌ Supprimer", key=f"del_fav_{nom}"):
                    del favoris_actuels[nom]
                    sauvegarder_url()
                    st.rerun()
                st.markdown("### Ingrédients")
                for ing in repas.get("ingredients", []):
                    st.write(f"- {ing['nom']} : {ing['quantite']} {ing['unite']}")
    else:
        st.info("Aucun favori enregistré. Clique sur le bouton 'Favori' dans l'onglet Plan pour sauvegarder un plat.")