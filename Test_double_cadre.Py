"""
test_double_cadre.py
=====================
Script de TEST ISOLÉ pour valider le rendu du double encadrement
avant de toucher à page_contacts.py.

Il ne lit aucun fichier JSON, ne modifie aucune donnée, et ne touche à
aucun fichier existant de l'app. On peut le lancer seul avec :

    streamlit run test_double_cadre.py

Objectif : afficher UNE fiche factice avec le cadre épais actuel
(inchangé) + un nouveau cadre extérieur plus clair qui entoure toute
la fiche (y compris les boutons, ce que le cadre HTML seul ne peut
pas faire).

Pourquoi st.container(key=...) : Streamlit ne permet pas de mettre des
boutons/colonnes à l'intérieur d'un bloc HTML classique (st.markdown).
Pour dessiner un cadre autour de VRAIS boutons Streamlit, on utilise
st.container(key=...), qui génère une classe CSS ("st-key-<key>") sur
laquelle on peut ensuite appliquer notre propre style.
Ça nécessite une version assez récente de Streamlit. Pour vérifier la
tienne : `pip show streamlit` (il faut 1.36 ou plus récent). Si ce
script affiche une erreur du type "unexpected keyword argument 'key'"
sur st.container, c'est le signe qu'il faut mettre Streamlit à jour.
"""
import streamlit as st

st.set_page_config(page_title="Test double cadre", layout="centered")


def couleur_eclaircie(hex_couleur: str, taux: float = 0.45) -> str:
    """Mélange une couleur hexadécimale avec du blanc pour l'éclaircir.

    taux=0   -> couleur inchangée
    taux=1   -> blanc pur
    taux=0.45 -> un bon compromis : nettement plus clair que la couleur
                 d'origine, mais encore assez visible pour servir de cadre.
    """
    hex_couleur = hex_couleur.lstrip("#")
    r, g, b = int(hex_couleur[0:2], 16), int(hex_couleur[2:4], 16), int(hex_couleur[4:6], 16)
    r = round(r + (255 - r) * taux)
    g = round(g + (255 - g) * taux)
    b = round(b + (255 - b) * taux)
    return f"#{r:02X}{g:02X}{b:02X}"


st.title("Test : double encadrement")
st.caption(
    "Cadre extérieur clair = nouveau. Cadre intérieur épais = celui qui "
    "existe déjà sur la vraie page Contacts."
)

couleur = "#2980B9"  # couleur d'exemple, dans la vraie page elle vient de _initiales_couleur
couleur_claire = couleur_eclaircie(couleur, taux=0.45)

# Style du cadre EXTÉRIEUR (nouveau), appliqué au container ci-dessous
# via sa clé "carte_test". Chaque fiche aura sa propre clé unique
# (carte_<id_du_contact>) pour avoir sa propre couleur.
st.markdown(
    f"""
    <style>
    .st-key-carte_test {{
        border: 3px solid {couleur_claire} !important;
        border-radius: 16px !important;
        padding: 10px !important;
        margin-bottom: 16px !important;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

with st.container(key="carte_test", border=True):
    # --- Cadre INTÉRIEUR : strictement identique à l'existant, non modifié ---
    st.markdown(
        f"""
        <div style="border:5px solid {couleur}; border-radius:12px; padding:14px; background:#eaf3fb;">
            <b style="font-size:1.05rem; color:#2c3e50;">#1 — Jean Dupont</b>
            <div style="margin-top:4px; font-size:0.9rem; color:#555;">
                📞 06 12 34 56 78 &nbsp;|&nbsp; ✉️ jean@example.com
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --- Le reste de la fiche (boutons, notes...) est maintenant DANS
    # le cadre extérieur, ce qu'un simple <div> HTML ne permettrait pas ---
    c1, c2, c3 = st.columns(3)
    c1.button("📞 Appeler", use_container_width=True)
    c2.button("✉️ Email", use_container_width=True)
    c3.button("💬 WhatsApp", use_container_width=True)

    st.caption("📝 Ceci est une note de test, pour vérifier qu'elle reste bien dans le cadre extérieur.")

st.divider()
st.write("Si tu vois bien DEUX cadres imbriqués (un clair dehors, un foncé dedans) autour de TOUT le bloc "
         "(y compris les 3 boutons), c'est gagné — on peut intégrer ça dans page_contacts.py.")
