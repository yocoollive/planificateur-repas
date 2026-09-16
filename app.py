import streamlit as st
import google.generativeai as genai
import json
import re

# 1. INSÈRE TA CLÉ API ICI
API_KEY = "AQ.Ab8RN6JiARwKiNhKtqEPJF8e2Gri_ieK9j6DWyD5QDNB86iDtQ"
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel(model_name="gemini-3.6-flash")

st.set_page_config(page_title="Générateur de Repas", page_icon="🤖", layout="centered")

st.title("🤖 Menu, Courses & Favoris")
st.caption("✅ Connecté au modèle : models/gemini-3.6-flash")

# Initialisation de la mémoire (Menus et Favoris)
if 'menu_data' not in st.session_state:
    st.session_state.menu_data = {}
if 'favoris' not in st.session_state:
    st.session_state.favoris = {}

jours_semaine = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

# Ajout du 3ème onglet
tab1, tab2, tab3 = st.tabs(["📅 Plan de la semaine", "🛒 Liste de courses", "⭐ Favoris"])

# ONGLET 1 : GÉNÉRATION DU MENU
with tab1:
    st.write("📌 **1. Sélectionne les jours à générer (décoche pour garder un repas)**")
    
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
        if not jours_a_generer:
            st.warning("Aucun jour sélectionné pour la génération !")
        else:
            with st.spinner(f"L'IA prépare les recettes pour : {', '.join(jours_a_generer)}..."):
                
                # Injection des favoris dans le prompt
                liste_favoris = list(st.session_state.favoris.keys())
                consigne_favoris = f"Voici une liste de recettes favorites de l'utilisateur : {liste_favoris}. N'hésite pas à piocher dans cette liste si cela respecte les critères du jour, ou à proposer de nouvelles choses." if liste_favoris else "Propose des recettes inédites."

                prompt = f"""
                Tu es un nutritionniste et chef cuisinier. Génère un menu UNIQUEMENT pour ces jours : {jours_a_generer}.
                {consigne_favoris}
                
                Règles strictes :
                - Souper ciblant entre 450 et 520 kcal par personne.
                - AUCUN POIVRON.
                - Alterner 1 jour Omnivore, 1 jour 100% Végétarien.
                - Portions pour 2 personnes : 400 à 500g de légumes minimum, 80 à 100g de féculents crus (ou 300-350g pommes de terre), 300 à 360g de viande/poisson OU 320-350g d'alternative végétale, maximum 2 c.à.s d'huile.
                - Ajoute les étapes de recette en respectant la méthode Batch Cooking : la cuisson des féculents et légumes se fait le dimanche, les protéines sont saisies à la minute le soir.
                
                Renvoie UNIQUEMENT du JSON valide, sans texte autour. Structure exacte :
                {{
                  "jours": [
                    {{
                      "jour": "Nom du jour (ex: Lundi)",
                      "type": "Omnivore",
                      "nom": "Titre du plat",
                      "temps_prep": "20 min",
                      "kcal": 480,
                      "proteines": 40,
                      "glucides": 45,
                      "lipides": 15,
                      "ingredients": [
                        {{"nom": "Nom ingredient", "quantite": 300, "unite": "g", "rayon": "Viandes"}}
                      ],
                      "recette": [
                        "Dimanche : Préparation des féculents et légumes...",
                        "Jour J : Saisir la protéine...",
                        "Jour J : Dressage..."
                      ]
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
                            st.session_state.menu_data[repas["jour"]] = repas
                        st.rerun() 
                    else:
                        st.error("Format de réponse inattendu. Relance la génération.")
                        
                except Exception as e:
                    st.error(f"Erreur de génération : {e}")

    # Affichage du menu consolidé
    if st.session_state.menu_data:
        st.info("💡 **Rappel Batch Cooking :** L'application adapte les recettes pour que les féculents et légumes soient cuits le dimanche.")
        
        for jour in jours_semaine:
            repas = st.session_state.menu_data.get(jour)
            if repas:
                with st.expander(f"**{jour}** : {repas['nom']} ({repas['type']}) | ⏱️ {repas.get('temps_prep', 'N/A')}"):
                    
                    # Bouton d'ajout aux favoris
                    nom_plat = repas['nom']
                    est_favori = nom_plat in st.session_state.favoris
                    
                    col_fav1, col_fav2 = st.columns([3, 1])
                    if not est_favori:
                        if col_fav2.button("⭐ Ajouter aux favoris", key=f"btn_fav_{jour}_{nom_plat}"):
                            st.session_state.favoris[nom_plat] = repas
                            st.rerun()
                    else:
                        col_fav2.success("⭐ Déjà en favoris")
                    
                    c1, c2, c3, c4 = st.columns(4)
                    
                    kcal = repas.get("kcal", 0)
                    c1.metric("Calories (cible ~500)", f"{kcal} kcal")
                    c1.progress(min(kcal / 520, 1.0)) 
                    
                    prot = repas.get("proteines", 0)
                    c2.metric("Protéines", f"{prot} g")
                    c2.progress(min(prot / 60, 1.0))
                    
                    gluc = repas.get("glucides", 0)
                    c3.metric("Glucides", f"{gluc} g")
                    c3.progress(min(gluc / 60, 1.0))
                    
                    lip = repas.get("lipides", 0)
                    c4.metric("Lipides", f"{lip} g")
                    c4.progress(min(lip / 20, 1.0))
                    
                    st.write("---")
                    
                    col_ing, col_rec = st.columns([1, 2])
                    
                    with col_ing:
                        st.markdown("### 🛒 Ingrédients")
                        for ing in repas["ingredients"]:
                            st.write(f"- {ing['nom']} : {ing['quantite']} {ing['unite']}")
                            
                    with col_rec:
                        st.markdown("### 🍳 Préparation")
                        if "recette" in repas:
                            for etape in repas["recette"]:
                                st.write(f"- {etape}")
                        else:
                            st.write("Aucune étape de recette disponible.")

# ONGLET 2 : LISTE DE COURSES INTELLIGENTE
with tab2:
    if st.session_state.menu_data:
        courses = {}
        for repas in st.session_state.menu_data.values():
            for ing in repas["ingredients"]:
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

        texte_export = "🛒 *LISTE DE COURSES - SEMAINE*\n\n"
        for rayon, ingredients in courses.items():
            texte_export += f"📍 *{rayon}*\n"
            for ing, qte in ingredients.items():
                qte_affichage = int(qte) if isinstance(qte, float) and qte.is_integer() else qte
                texte_export += f"☐ {ing} : {qte_affichage}\n"
            texte_export += "\n"

        st.subheader("📲 Export Rapide")
        st.code(texte_export, language="text")
        st.write("---")
        st.subheader("🛒 Liste Interactive")
        for rayon, ingredients in courses.items():
            st.markdown(f"### {rayon}")
            for ing, qte in ingredients.items():
                qte_affichage = int(qte) if isinstance(qte, float) and qte.is_integer() else qte
                st.checkbox(f"{ing} : {qte_affichage}", key=f"chk_{rayon}_{ing}")
    else:
        st.warning("Générez d'abord un menu pour voir la liste de courses.")

# ONGLET 3 : FAVORIS
with tab3:
    st.subheader("⭐ Vos Recettes Favorites")
    
    if st.session_state.favoris:
        for nom, repas in list(st.session_state.favoris.items()):
            with st.expander(f"⭐ {nom} ({repas.get('type', 'Inconnu')})"):
                
                if st.button("❌ Retirer des favoris", key=f"del_fav_{nom}"):
                    del st.session_state.favoris[nom]
                    st.rerun()
                
                st.write("---")
                
                c1, c2, c3, c4 = st.columns(4)
                kcal = repas.get("kcal", 0)
                c1.metric("Calories", f"{kcal} kcal")
                prot = repas.get("proteines", 0)
                c2.metric("Protéines", f"{prot} g")
                gluc = repas.get("glucides", 0)
                c3.metric("Glucides", f"{gluc} g")
                lip = repas.get("lipides", 0)
                c4.metric("Lipides", f"{lip} g")
                
                col_ing, col_rec = st.columns([1, 2])
                with col_ing:
                    st.markdown("### 🛒 Ingrédients")
                    for ing in repas["ingredients"]:
                        st.write(f"- {ing['nom']} : {ing['quantite']} {ing['unite']}")
                with col_rec:
                    st.markdown("### 🍳 Préparation")
                    if "recette" in repas:
                        for etape in repas["recette"]:
                            st.write(f"- {etape}")
    else:
        st.info("Aucune recette dans vos favoris pour le moment. Cliquez sur le bouton '⭐ Ajouter aux favoris' d'une recette générée pour la conserver ici !")