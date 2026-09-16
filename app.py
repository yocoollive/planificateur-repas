import streamlit as st
import google.generativeai as genai
import json
import re
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

# --- 1. INITIALISATION FIREBASE ---
# On vérifie si l'app est déjà initialisée pour éviter les erreurs quand la page s'actualise
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase_key.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

# --- 2. CONFIGURATION DE L'IA ---
API_KEY = "AQ.Ab8RN6JiARwKiNhKtqEPJF8e2Gri_ieK9j6DWyD5QDNB86iDtQ"
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel(model_name="gemini-3.6-flash")

st.set_page_config(page_title="Générateur de Repas", page_icon="🤖", layout="centered")

st.title("🤖 Menu, Courses & Favoris")
st.caption("✅ Connecté au Cloud (Firebase) & IA (Gemini)")

# --- 3. CHARGEMENT DEPUIS LA BASE DE DONNÉES ---
# Récupération du menu de la semaine
doc_semaine = db.collection('planificateur').document('menus_semaine').get()
if doc_semaine.exists:
    st.session_state.menu_data = doc_semaine.to_dict().get("menus", {})
else:
    st.session_state.menu_data = {}

# Récupération des favoris
doc_favoris = db.collection('planificateur').document('recettes_favorites').get()
if doc_favoris.exists:
    st.session_state.favoris = doc_favoris.to_dict().get("liste", {})
else:
    st.session_state.favoris = {}

jours_semaine = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

tab1, tab2, tab3 = st.tabs(["📅 Plan de la semaine", "🛒 Liste de courses", "⭐ Favoris"])

# --- ONGLET 1 : GÉNÉRATION DU MENU ---
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
                liste_favoris = list(st.session_state.favoris.keys())
                consigne_favoris = f"Voici une liste de recettes favorites : {liste_favoris}. N'hésite pas à piocher dedans si ça respecte les critères." if liste_favoris else ""

                prompt = f"""
                Tu es un nutritionniste et chef cuisinier. Génère un menu UNIQUEMENT pour ces jours : {jours_a_generer}.
                {consigne_favoris}
                
                Règles strictes :
                - Souper ciblant entre 450 et 520 kcal par personne.
                - AUCUN POIVRON.
                - Alterner 1 jour Omnivore, 1 jour 100% Végétarien.
                - Portions pour 2 personnes : 400 à 500g de légumes minimum, 80 à 100g de féculents crus (ou 300-350g pommes de terre), 300 à 360g de viande/poisson OU 320-350g d'alternative végétale, maximum 2 c.à.s d'huile.
                - Batch Cooking : cuisson des féculents/légumes le dimanche, protéines à la minute le soir.
                
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
                        
                        # Mise à jour des jours et SAUVEGARDE SUR FIREBASE
                        for repas in nouveaux_jours:
                            st.session_state.menu_data[repas["jour"]] = repas
                        
                        db.collection('planificateur').document('menus_semaine').set({"menus": st.session_state.menu_data})
                        st.rerun() 
                    else:
                        st.error("Format de réponse inattendu. Relance la génération.")
                        
                except Exception as e:
                    st.error(f"Erreur de génération : {e}")

    if st.session_state.menu_data:
        st.info("💡 **Rappel Batch Cooking :** Cuisson des féculents et légumes le dimanche.")
        
        for jour in jours_semaine:
            repas = st.session_state.menu_data.get(jour)
            if repas:
                with st.expander(f"**{jour}** : {repas['nom']} ({repas['type']}) | ⏱️ {repas.get('temps_prep', 'N/A')}"):
                    nom_plat = repas['nom']
                    est_favori = nom_plat in st.session_state.favoris
                    
                    col_fav1, col_fav2 = st.columns([3, 1])
                    if not est_favori:
                        if col_fav2.button("⭐ Ajouter aux favoris", key=f"btn_fav_{jour}_{nom_plat}"):
                            st.session_state.favoris[nom_plat] = repas
                            # SAUVEGARDE SUR FIREBASE
                            db.collection('planificateur').document('recettes_favorites').set({"liste": st.session_state.favoris})
                            st.rerun()
                    else:
                        col_fav2.success("⭐ En favoris")
                    
                    c1, c2, c3, c4 = st.columns(4)
                    kcal = repas.get("kcal", 0)
                    c1.metric("Calories (~500)", f"{kcal} kcal")
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

# --- ONGLET 2 : LISTE DE COURSES ---
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

# --- ONGLET 3 : FAVORIS ---
with tab3:
    st.subheader("⭐ Vos Recettes Favorites")
    if st.session_state.favoris:
        for nom, repas in list(st.session_state.favoris.items()):
            with st.expander(f"⭐ {nom} ({repas.get('type', 'Inconnu')})"):
                if st.button("❌ Retirer des favoris", key=f"del_fav_{nom}"):
                    del st.session_state.favoris[nom]
                    # SAUVEGARDE SUR FIREBASE
                    db.collection('planificateur').document('recettes_favorites').set({"liste": st.session_state.favoris})
                    st.rerun()
                
                st.write("---")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Calories", f"{repas.get('kcal', 0)} kcal")
                c2.metric("Protéines", f"{repas.get('proteines', 0)} g")
                c3.metric("Glucides", f"{repas.get('glucides', 0)} g")
                c4.metric("Lipides", f"{repas.get('lipides', 0)} g")
                
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
        st.info("Aucune recette dans vos favoris. Ajoutez-en depuis le plan de la semaine !")