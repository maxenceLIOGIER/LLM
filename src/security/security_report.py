import sqlite3
from datetime import datetime, timedelta
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.metrics import silhouette_score
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
db_path = "sqlite:///../../../database/db_logs.db"

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
                log.timestamp AS timestamp,
                prompt.prompt AS prompt,
                prompt.response AS response,
                status.status AS status,
                origin.response AS origin
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

    def _create_pipeline(self):
        '''
        Crée un pipeline pour préparer les données au Machine Learning
        '''
        #Pipeline pour les données textuelles 
        text_pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(max_features=50))
        ])

        #Pipeline pour les données catgéorielles 
        cat_pipeline = Pipeline([
             ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
        ])

        #Combinaison des méthodes 
        preprocessor = ColumnTransformer(
            transformers=[
                ('timestamp', text_pipeline, 'timestamp'),
                ('prompt', text_pipeline, 'prompt'),
                ('response', text_pipeline, 'response'),
                ('status', cat_pipeline, 'status'),
                ('origin', text_pipeline, 'origin')
            ],
            remainder = 'drop'
        )

        #Pipeline principale
        pipeline = Pipeline([
            ('preprocessor', preprocessor),
            ('scaler', StandardScaler(with_mean=False))
        ])

        return pipeline

    def clustering_log(self, max_clusters=10):
        '''
        Réalise un clustering sur les logs journaliers et retourne le meilleur nombre de clusters
        '''
        #Initalisation
        best_score = -1
        best_n_clusters = 2

        #Récupère les logs journaliers 
        logs = self.query_daily_logs()

        #Prétraitement
        preprocessor = self._create_pipeline()
        logs = preprocessor.fit_transform(logs)

        for n_clusters in range(2, max_clusters+1):
            self.model = KMeans(n_clusters = n_clusters, random_state=0)
            self.model.fit(logs)
            score = silhouette_score(logs, self.model.labels_)
            print(f"Nombre de clusters : {n_clusters}, Sillhouette Score : {score:.4f}")

            if score > best_score:
                best_score = score
                best_n_clusters = n_clusters
        
        print(f"\nMeilleur nombre de clusters : {best_n_clusters}, Silhouette Score : {best_score:.4f}")
        return best_n_clusters

    def generate_report(self, logs):
        '''
        Génère un rapport HTML sur les logs journaliers
        '''
        date_str = datetime.now().strftime("%d/%m/%Y")
        total_logs = len(logs)
        status_counts = logs['status'].value_counts().to_dict()
        n_clusters = self.clustering_log()

        #Création d'une liste des statuts sous forme de texte
        status_html = "".join(
            f"<li><strong>{status}:</strong> {count}</li>" for status, count in status_counts.items()
        )

        #Construction du rapport en HTML
        report = f"""
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    color: #333;
                    line-height: 1.6;
                }}
                .container {{
                    max-width: 600px;
                    margin: 20px auto;
                    padding: 20px;
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    background-color: #f9f9f9;
                }}
                h2 {{
                    background-color: #007BFF;
                    color: white;
                    padding: 10px;
                    border-radius: 5px;
                    text-align: center;
                }}
                ul {{
                    list-style-type: none;
                    padding: 0;
                }}
                li {{
                    padding: 5px 0;
                }}
                .footer {{
                    margin-top: 20px;
                    font-size: 12px;
                    text-align: center;
                    color: #777;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>📋 Rapport de Sécurité - {date_str}</h2>
                <p><u><strong>Nombre total de logs :</strong></u> {total_logs}</p>
                <p><u><strong>Répartition des statuts :</strong></u></p>
                <ul>
                    {status_html}
                </ul>
                <p><u><strong>🔍 Nombre de comportements différents détectés :</strong></u> {n_clusters}</p>
                <div class="footer">
                    Rapport généré automatiquement par le système de surveillance. 🛡️
                </div>
            </div>
        </body>
        </html>
        """
        
        return report

    def send_email(self, subject, body):
        '''
        Envoie un email
        '''
        sg = sendgrid.SendGridAPIClient(api_key=self.sendgrid_api_key)
        from_email = Email(self.from_email)
        to_email = To(self.recipient_email)
        content = Content("text/html", body)
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