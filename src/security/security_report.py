import sqlite3
from datetime import datetime, timedelta
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content
import os
from dotenv import load_dotenv

#Charger les variabels d'environnement 
load_dotenv()
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")

#Chemin vers la DB
db_path = "../../database/db_logs.db"

class SecurityReport:
    def __init__(self, db_path = db_path, sendgrid_api_key = SENDGRID_API_KEY, from_email = FROM_EMAIL, recipient_email = RECIPIENT_EMAIL):
        self.DB_PATH = db_path
        self.sendgrid_api_key = sendgrid_api_key
        self.from_email = from_email
        self.recipient_email = recipient_email

    def query_daily_logs(self):
        '''
        Récupère les logs de la journée
        '''
        #Initialisation des horaires
        today = datetime.now().date()
        start_of_day = datetime.combine(today, datetime.min.time())
        end_of_day = datetime.combine(today, datetime.max.time())

        #Connection à la BDD et requete
        conn = sqlite3.connect(self.DB_PATH)
        query = """
            SELECT 
                log.id_log,
                log.timestamp,
                prompt.prompt AS prompt_text,
                prompt.response AS prompt_response,
                status.status AS status_text,
                origin.response AS origin_response
            FROM log
            LEFT JOIN prompt ON log.id_prompt = prompt.id_prompt
            LEFT JOIN status ON log.id_status = status.id_status
            LEFT JOIN origin ON log.id_origin = origin.id_origin
            WHERE log.timestamp BETWEEN ? AND ?
        """

        #Logs récupérés au format DataFrame 
        df = pd.read_sql_query(query, conn, params = (start_of_day, end_of_day))
        conn.close()
        return df

    def generate_report(self, logs):
        '''
        Génère un rapport sur les logs journaliers
        '''
        report = f"Rapport de sécurité journalier pour la date du {datetime.now().date()}\n"
        report += f"Nombre total de logs : {len(logs)}\n"
        report += f"Répartition des status : \n{logs['status'].values_counts()}\n"

        return report 

    def send_email(self, subject, body):
        '''
        Envoie un email
        '''
        sg = sendgrid.SendGridAPIClient(api_key=self.sendgrid_api_key)
        from_email = Email(self.from_email)
        to_email = To(self.recipient_email)
        content = Content("text/plain", body)
        mail = Mail(from_email, to_email, subject, content)

        try:
            response = sg.client.mail.send.post(request_body=mail.get())
            print(f"Email envoyé avec succès: {response.status_code}")
        except Exception as e:
            print(f"Erreur, email non-envoyé: {e}")

    def run_daily_report(self):
        '''
        Exécute le rapport journalier
        '''
        #Génère le rapport
        logs = self.query_daily_logs()
        report = self.generate_report(logs)

        #Envoie de l'email 
        self.send_email(
            subject="Rapport de sécurité journalier",
            body = report
        )