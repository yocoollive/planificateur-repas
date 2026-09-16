import streamlit as st
import google.generativeai as genai
import json
import re
import urllib.parse

# Configuration Gemini via les Secrets
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel(model_name="gemini-1.5-flash")

st.set_page_config(page_title="Menu & Courses - Ulysse & Compagne", page_icon="🥗", layout="centered")
st.title("🥗 Menu & Courses (Partage par Lien)")

jours_semaine = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

# Récupération du menu depuis l'URL si elle contient des données
query_params = st.query_params
menu_actuel = {}

if "data" in query_params:
    try:
        json_str = urllib.parse.unquote(query_params["data"])
        menu_actuel = json.loads(json_str)
    except Exception:
        menu_actuel = {}

tab1, tab2 = st.tabs(["📅 Plan de la semaine", "🛒 Liste de courses"])

# ONGLET 1 : GÉNÉRATION ET AFFICHAGE
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
            with st.spinner("L'IA prépare les recettes..."):
                prompt = f"""
                Tu es un nutritionniste et chef cuisinier. Génère un menu UNIQUEMENT pour ces jours : {jours_a_generer}.
                Règles strictes :
                - Souper ciblant entre 450 et 520 kcal par personne.
                - AUCUN POIVRON.
                - Alterner 1 jour Omnivore, 1 jour 100% Végétarien.
                - Portions pour 2 personnes : 400 à 500g de légumes minimum, 80 à 100g de féculents crus (ou 300-350g pommes de terre), 300 à 360g de viande/poisson OU 320-350g d'alternative végétale, max 2 c.à.s d'huile.
                
                Renvoie UNIQUEMENT du JSON valide :
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
                  ]
                }}
                """
                try:
                    reponse = model.generate_content(prompt)
                    match = re.search(r'\{.*\}', reponse.text, re.DOTALL)
                    if match:
                        nouveaux_jours = json.loads(match.group(0)).get("jours", [])
                        for repas in nouveaux_jours:
                            menu_actuel[repas["jour"]] = repas
                        
                        # Sauvegarde directe dans l'URL de l'application
                        json_data = json.dumps(menu_actuel)
                        st.query_params["data"] = json_data
                        st.success("Menu généré ! Le lien a été mis à jour.")
                        st.rerun()
                except Exception as e:
                    st.error(f"Erreur : {e}")

    # Affichage du menu
    if menu_actuel:
        st.info("💡 **Astuce Partage :** Copie simplement l'URL de cette page et envoie-la à ta compagne pour qu'elle voie exactement le même menu sur son iPhone !")
        for jour in jours_semaine:
            repas = menu_actuel.get(jour)
            if repas:
                with st.expander(f"**{jour}** : {repas['nom']} ({repas['type']}) | ⏱️ {repas.get('temps_prep', '')}"):
                    st.write(f"🔥 **Calories :** {repas.get('kcal', '')} kcal / pers.")
                    st.markdown("### 🛒 Ingrédients (pour 2)")
                    for ing in repas["ingredients"]:
                        st.write(- f"{ing['nom']} : {ing['quantite']} {ing['unite']}")
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
                    courses[rayon] {}
                try:
                    courses[rayon][cle] = courses[rayon].get(cle, 0) + float(qte)
                except ValueError:
                    courses[rayon][cle] = qte

        st.subheader("🛒 Liste de courses consolidée")
        for rayon, ingredients in courses.items():
            st.markdown(f"### 📍 {rayon}")
            for ing, qte in ingredients.items():
                st.checkbox(f"{ing} : {qte}", key=f"shop_{rayon}_{ing}")
    else:
        st.warning("Générez d'abord un menu pour afficher la liste de courses.")