### Page Admin ###

import sqlite3
import hashlib
from pathlib import Path
import streamlit as st
import pandas as pd
from src.security.security_report import SecurityReport

from views.home import arret_enregistrement

db_path = Path(__file__).parent.parent.parent / "database" / "db_logsv2.db"

query = """
SELECT
    log.id_log,
    log.timestamp,
    prompt.prompt,
    prompt.response,
    status.status,
    origin.origin AS origin
FROM log
LEFT JOIN prompt ON log.id_prompt = prompt.id_prompt
LEFT JOIN status ON log.id_status = status.id_status
LEFT JOIN origin ON log.id_origin = origin.id_origin
ORDER BY log.timestamp DESC
"""


def check_password():
    """
    Fonction de vérification du mot de passe pour accéder à la page Admin.
    Renvoie True si le mot de passe saisi est correct, False sinon.
    """

    def password_entered():
        """
        Fonction pour comparer le hash du mot de passe saisi avec le hash attendu.
        Positionne la variable de session "password_correct" à True si le mot de passe est correct,
        à False sinon.
        """
        if (
            hashlib.sha256(st.session_state["password"].encode()).hexdigest()
            == "676bcf91f4659cccada503f86bfd836889318b87ab691ae812cb572f2e87aa87"
        ):
            st.session_state["password_correct"] = True
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # Premier affichage, pas encore de mot de passe saisi.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Mot de passe incorrect, affichage d'un message d'erreur.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        # Password ok.
        return True


def adm_page():
    """
    La page Admin permet de visualiser les données stockées dans la base de données,
    sous forme compacte grâce à la requête "query" définie ci-dessus.
    """
    # si enregistrement en cours, on l'arrête
    arret_enregistrement()

    # Si mdp correct, afficher les onglets
    if check_password():
        # Tabs
        tab1, tab2, tab3, tab4 = st.tabs(
            [
                "Évènements",
                "Rapport journalier",
                "Accès à l'API SmartRescue",
                "Paramétrer les clés API externes",
            ]
        )

        # Section Évènements SmartRescue
        with tab1:
            st.markdown("## 🚨 Accès aux évènements SmartRescue")

            # Filtrage des données
            st.sidebar.header("Filtres")
            items_per_page = st.sidebar.selectbox(
                "Éléments par page", [10, 20, 50, 100], 0
            )

            start_date = st.sidebar.date_input(
                "Date de début", value=pd.to_datetime("2025-01-01")
            )
            end_date = st.sidebar.date_input(
                "Date de fin", value=pd.to_datetime("today")
            )

            query_filtered = """
            SELECT
                log.id_log,
                log.timestamp,
                prompt.prompt,
                prompt.response,
                status.status,
                origin.origin AS origin
            FROM log
            LEFT JOIN prompt ON log.id_prompt = prompt.id_prompt
            LEFT JOIN status ON log.id_status = status.id_status
            LEFT JOIN origin ON log.id_origin = origin.id_origin
            WHERE DATE(log.timestamp) >= DATE(?) AND DATE(log.timestamp) <= DATE(?)
            ORDER BY log.timestamp DESC
            """

            # Connexion à la base de données
            with sqlite3.connect(db_path) as conn:
                # Récupération des enregistrements filtrés par date
                data = pd.read_sql_query(
                    query_filtered, conn, params=(start_date, end_date)
                )
                cols = [
                    "id_logs",
                    "timestamp",
                    "prompt",
                    "response",
                    "status",
                    "origin",
                ]

            if data.empty:
                data = pd.DataFrame(columns=cols)

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
            st.write(
                f"Affichage des éléments {start_idx + 1} à {end_idx} sur {total_items}"
            )

            # Affichage du tableau
            st.dataframe(
                data.iloc[start_idx:end_idx], use_container_width=True, hide_index=True
            )

        # Section Rapport Journalier
        with tab2:
            st.markdown("## 📊 Rapport Logs")
            st.write(
                "Générez par mail un rapport détaillé des événements, incluant les alertes de sécurité, "
                "les activités suspectes et les tendances globales des interactions avec SmartRescue."
            )

            if st.button("📝 Générer le rapport"):
                report = SecurityReport()
                report.run_report()
                st.success("✅ Rapport généré avec succès !")

        # Section API SmartRescue
        with tab3:
            st.markdown("## 🌐 API SmartRescue")
            st.markdown(
                """
                Les données présentées dans l'onglet *Évènements* peuvent être consultées [via l'API SmartRescue](http://127.0.0.1:8901/docs).

                Voici quelques exemples de requêtes possibles :
                - Requête get sans critères : [http://127.0.0.1:8901/data](http://127.0.0.1:8901/data)
                - Requête get avec une date de début : [http://127.0.0.1:8901/data?start_date=2025-01-29](http://127.0.0.1:8901/data?start_date=2025-01-29)
                - Requête get avec une date de fin : [http://127.0.0.1:8901/data?end_date=2025-01-27](http://127.0.0.1:8901/data?end_date=2025-01-27)
                - Requête get avec une date de début et une date de fin : [http://127.0.0.1:8901/data?start_date=2025-01-28&end_date=2025-01-28](http://127.0.0.1:8901/data?start_date=2025-01-28&end_date=2025-01-28)
                """
            )

        # Section Clés API externes
        with tab4:
            st.markdown("## 🔑 Clés API externes")

            # Texte d'explication
            st.write(
                "Pour utiliser l'API SmartRescue, vous devez fournir les clés API externes suivantes :"
            )

            api_key_hf = st.text_input(
                "HF_API_KEY",
                type="default",
                value=st.session_state.get("HF_API_KEY", ""),
            )
            api_key_m = st.text_input(
                "MISTRAL_API_KEY",
                type="default",
                value=st.session_state.get("MISTRAL_API_KEY", ""),
            )

            if st.button("Submit"):
                st.session_state["HF_API_KEY"] = api_key_hf
                st.session_state["MISTRAL_API_KEY"] = api_key_m
                st.success("Les clés API ont été mises à jour avec succès.")
