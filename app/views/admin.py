import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent.parent / "database" / "db_logs.db"


def adm_page():

    # Titre de la page
    st.title("Admin")

    # Connexion à la base de données
    with sqlite3.connect(db_path) as conn:
        # Récupération des tables et des colonnes
        tables = pd.read_sql_query(
            "SELECT name FROM sqlite_master WHERE type='table'", conn
        )
        table_cols = {}
        for t in tables["name"]:
            cols = pd.read_sql_query(f"PRAGMA table_info({t})", conn)["name"].tolist()
            table_cols[t] = cols

    # Sélection de la table
    options = list(table_cols.keys())
    # Par défaut, on affiche la table "log"
    default_table = "log"
    default_index = options.index(default_table) if default_table in options else 0
    selected_table = st.selectbox(
        "Sélectionnez une table", options, index=default_index
    )

    # Récupération des données de la table sélectionnée
    with sqlite3.connect(db_path) as conn:
        total_data = pd.read_sql_query(f"SELECT * FROM {selected_table}", conn)

    if total_data.empty:
        total_data = pd.DataFrame(columns=table_cols[selected_table])

    # Filtrage des données
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

    # Affichage du tableau
    st.dataframe(
        total_data.iloc[start_idx:end_idx], use_container_width=True, hide_index=True
    )
