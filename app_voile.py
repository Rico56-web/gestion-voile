# --- STYLE CSS MIS À JOUR ---
st.markdown("""
    <style>
    .cal-table { 
        width: 100%; 
        border-collapse: collapse; 
        table-layout: fixed; 
        background: white;
    }
    .cal-table td { 
        border: 1px solid #eee; 
        height: 40px; 
        padding: 0;
    }
    /* LA MAGIE EST ICI : Force l'alignement horizontal */
    .day-container {
        display: flex;
        flex-direction: row;
        justify-content: center;
        align-items: center;
        width: 100%;
        height: 100%;
        white-space: nowrap;
    }
    .day-num { 
        font-weight: bold; 
        font-size: 0.85rem; /* Taille réduite pour iPhone SE/Mini */
        font-family: sans-serif;
        display: inline-block;
    }
    </style>
    """, unsafe_allow_html=True)

# --- ET DANS LA BOUCLE DU CALENDRIER, REMPLACEZ LA LIGNE TD PAR CELLE-CI ---
html_cal += f'''
    <td style="background:{bg}; color:{col};">
        <div class="day-container">
            <span class="day-num">{day_str}</span>
        </div>
    </td>
'''

























































































