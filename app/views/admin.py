import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent.parent / "database" / "db_logs.db"

query = """
SELECT
    log.id_log,
    log.timestamp,
    prompt.prompt,
    prompt.response,
    status.status,
    origin.response AS origin
FROM log
LEFT JOIN prompt ON log.id_prompt = prompt.id_prompt
LEFT JOIN status ON log.id_status = status.id_status
LEFT JOIN origin ON log.id_origin = origin.id_origin
ORDER BY log.timestamp DESC
"""


def adm_page():
    """
    La page Admin permet de visualiser les données stockées dans la base de données,
    sous forme compacte grâce à la requête "query" définie ci-dessus.
    """

    # Titre de la page
    st.title("Admin")

    # Connexion à la base de données
    with sqlite3.connect(db_path) as conn:
        # Récupération des enregistrements
        data = pd.read_sql_query(query, conn)
        cols = {"id_logs", "timestamp", "prompt", "response", "status", "origin"}

    if data.empty:
        data = pd.DataFrame(columns=cols)

    # Filtrage des données
    st.sidebar.header("Filtres")
    items_per_page = st.sidebar.selectbox("Éléments par page", [10, 20, 50, 100], 0)

    total_items = len(data)
    total_pages = max(1, (total_items - 1) // items_per_page + 1)

    if "current_page" not in st.session_state:
        st.session_state.current_page = 1

    # Sélection de la page
    current_page = st.sidebar.number_input(
        "Numéro de page",
        1,
        total_pages,
        st.session_state.current_page,
        1,
    )

    st.session_state.current_page = current_page

    # Pagination
    start_idx = (current_page - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, total_items)
    st.write(f"Affichage des éléments {start_idx + 1} à {end_idx} sur {total_items}")

    # Affichage du tableau
    st.dataframe(
        data.iloc[start_idx:end_idx], use_container_width=True, hide_index=True
    )
