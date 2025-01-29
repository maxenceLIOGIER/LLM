import streamlit as st
import pandas as pd
import sqlite3

from pathlib import Path

db_path = Path(__file__).parent.parent.parent / "database" / "db_logs.db"


def adm_page():
    st.title("Admin")
    st.write("Tableau des logs")

    # Aller récupérer les logs dans la base de données
    # Se connecter à la base de données
    conn = sqlite3.connect(db_path)

    # Récupérer tous les logs
    logs_df = pd.read_sql_query("SELECT * FROM log", conn)
    conn.close()

    if logs_df.empty:
        logs_df = pd.DataFrame(
            columns=["id_log", "timestamp", "id_prompt", "id_status", "id_origin"]
        )

    # Add filters for each column
    if not logs_df.empty:
        for column in logs_df.columns:
            filter_value = st.selectbox(
                f"Filter {column}", ["All"] + list(logs_df[column].unique())
            )
            if filter_value != "All":
                logs_df = logs_df[logs_df[column] == filter_value]

        # Display filtered dataframe with pagination
        page_size = st.selectbox("Rows per page", [10, 25, 50, 100])
        page_number = st.number_input(
            "Page", min_value=1, max_value=len(logs_df) // page_size + 1, value=1
        )
        start_idx = (page_number - 1) * page_size
        end_idx = start_idx + page_size

        st.dataframe(logs_df.iloc[start_idx:end_idx])

        # Download button
        csv = logs_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download data as CSV",
            data=csv,
            file_name="logs.csv",
            mime="text/csv",
        )
    else:
        st.write("No logs found")
