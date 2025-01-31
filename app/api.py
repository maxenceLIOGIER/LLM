from datetime import date
from pathlib import Path
from typing import Optional

import sqlite3
import streamlit as st
from fastapi import FastAPI, Query
from fastapi.responses import RedirectResponse

# Chemin de la base de données
dbpath = Path(__file__).parent.parent / "database" / "db_logs.db"

# instanciation de l'API FastAPI
api = FastAPI(
    title="SmartRescue API",
    description="API to access SmartRescue events",
    version="1.0.0",
)


@api.get("/", include_in_schema=False)
async def root():
    """
    Route par défaut, qui redirige vers la page doc
    """
    return RedirectResponse(url="/docs")


# Requête de base, si l'utilisateur de l'API
# ne spécifie pas de date de début ou de fin
base_query = """
    SELECT log.id_log, log.timestamp, prompt.prompt, prompt.response,
    status.status, origin.response AS origin
    FROM log
    LEFT JOIN prompt ON log.id_prompt = prompt.id_prompt
    LEFT JOIN status ON log.id_status = status.id_status
    LEFT JOIN origin ON log.id_origin = origin.id_origin
"""


@api.get("/data")
async def get_data(
    start_date: Optional[date] = Query(None, description="Date de début (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Date de fin (YYYY-MM-DD)"),
):
    """
    Retourne les événements de SmartRescue entre deux dates.

    Args:
        start_date (Optional[datetime.date]): Date de début (YYYY-MM-DD), optionnelle.
        end_date (Optional[datetime.date]): Date de fin (YYYY-MM-DD), optionnelle.

    Returns:
        List[Dict[str, Any]]: Liste des enregistrements, avec chaque champ de la base de données
        comme clé du dictionnaire.
    """

    try:
        # Connexion à la base de données
        conn = sqlite3.connect(dbpath)
        cursor = conn.cursor()

        query = base_query
        params = []

        # Ajout des conditions de date si spécifiées
        if start_date or end_date:
            query += " WHERE "
            conditions = []

            if start_date:
                conditions.append("date(log.timestamp) >= ?")
                params.append(start_date.isoformat())

            if end_date:
                conditions.append("date(log.timestamp) <= ?")
                params.append(end_date.isoformat())

            query += " AND ".join(conditions)

        query += " ORDER BY log.timestamp DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()

        # Récupération des enregistrements
        columns = [description[0] for description in cursor.description]
        result = [dict(zip(columns, row)) for row in rows]

        return result
    except sqlite3.OperationalError as e:
        return {"error": f"Database error: {str(e)}", "path": dbpath}
    finally:
        # pour cloturer proprement la connexion à la base de données
        if "conn" in locals():
            conn.close()
