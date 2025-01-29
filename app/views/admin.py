import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent.parent / "database" / "db_logs.db"


def adm_page():
    st.title("Admin")
    st.write("Tableau des logs")

    # Lecture des données
    with sqlite3.connect(db_path) as conn:
        total_data = pd.read_sql_query("SELECT * FROM log", conn)

    if total_data.empty:
        total_data = pd.DataFrame(
            columns=["id_log", "timestamp", "id_prompt", "id_status", "id_origin"]
        )

    st.sidebar.header("Filtres")
    items_per_page = st.sidebar.selectbox("Éléments par page", [10, 20, 50, 100], 0)

    total_items = len(total_data)
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
        key="current_page",
    )

    # Pagination
    start_idx = (current_page - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, total_items)
    st.write(f"Affichage des éléments {start_idx + 1} à {end_idx} sur {total_items}")

    st.dataframe(
        total_data.iloc[start_idx:end_idx], use_container_width=True, hide_index=True
    )
