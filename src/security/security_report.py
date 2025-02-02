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

# Charger les variabels d'environnement
load_dotenv()
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")

# Chemin vers la DB
db_path = "sqlite:///../../database/db_logs.db"


class SecurityReport:
    def __init__(
        self,
        db_path=db_path,
        sendgrid_api_key=SENDGRID_API_KEY,
        from_email=FROM_EMAIL,
        recipient_email=RECIPIENT_EMAIL,
    ):
        self.DB_PATH = db_path
        self.sendgrid_api_key = sendgrid_api_key
        self.from_email = from_email
        self.recipient_email = recipient_email

    def query_logs(self, day:str = None) -> pd.DataFrame:
        """
        Récupère les logs de la journée sous forme de DataFrame.

        Cette fonction effectue les opérations suivantes :
        1. Détermine les horaires de début et de fin de la journée actuelle.
        2. Établit une connexion à la base de données SQLite.
        3. Exécute une requête SQL pour récupérer les logs du jour en effectuant des jointures 
        avec les tables `prompt`, `status` et `origin` afin d'obtenir des informations 
        détaillées sur chaque log.
        4. Retourne les données sous forme d'un DataFrame pandas.

        Returns:
            pd.DataFrame: Un DataFrame contenant les logs de la journée avec les colonnes suivantes :
                - timestamp: Horodatage du log.
                - prompt: Texte de la requête.
                - response: Réponse associée.
                - status: Statut du log.
                - origin: Adresse IP de l'utilisateur.
        """

        # Connection à la BDD et requete
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
        """
        # Initialisation des paramètres
        params = ()

        # Initialisation des horaires si date présente 
        if day:
            start_of_day = datetime.combine(day, datetime.min.time())
            end_of_day = datetime.combine(day, datetime.max.time())
            query += " WHERE log.timestamp BETWEEN ? AND ?"
            params = (start_of_day, end_of_day)

        # Logs récupérés au format DataFrame
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()

        return df

    def _create_pipeline(self):
        """
        Crée un pipeline de prétraitement des données pour le clustering.

        Cette fonction met en place un pipeline de transformation des données, qui comprend :
        1. Un pipeline spécifique pour les données textuelles, appliquant une vectorisation TF-IDF
        avec un nombre de caractéristiques limité à 50.
        2. Un pipeline pour les données catégorielles, appliquant un encodage One-Hot tout en
        ignorant les valeurs inconnues lors de la transformation.
        3. Une combinaison de ces transformations à l'aide d'un `ColumnTransformer` pour appliquer
        les transformations appropriées aux bonnes colonnes du dataset.
        4. Un pipeline principal qui applique ces transformations et normalise les données avec 
        `StandardScaler` (sans soustraction de la moyenne, car TF-IDF produit des matrices creuses).

        Returns:
            sklearn.pipeline.Pipeline: Un pipeline scikit-learn qui prépare les données 
            avant leur utilisation en Machine Learning.
        """

        # Colonnes catégorielles et textuelles
        categorical_features = ["status"]
        text_features = ["timestamp", "prompt", "response", "origin"]

        # Pipeline pour les données textuelles
        text_pipelines = {
            feature: Pipeline([("tfidf", TfidfVectorizer(max_features=50, stop_words=None, analyzer="word"))])
            for feature in text_features
        }

        # Pipeline pour les données catgéorielles
        cat_pipeline = Pipeline(
            [("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False))]
        )

        # Combinaison des méthodes
        preprocessor = ColumnTransformer(
            transformers=[
                ("text_" + feature, text_pipelines[feature], feature) 
                for feature in text_features
            ] + [("cat", cat_pipeline, categorical_features)],
            remainder="drop"
        )

        # Pipeline principale
        pipeline = Pipeline(
            [
                ("preprocessor", preprocessor),
                ("scaler", StandardScaler(with_mean=False)),
            ]
        )

        return pipeline

    def clustering_log(self, max_clusters:int=10) -> int:
        """
        Effectue un clustering sur les logs journaliers et détermine le nombre optimal de clusters.

        Cette fonction réalise les étapes suivantes :
        1. **Initialisation** :
        - Définit les variables pour suivre le meilleur score Silhouette et le nombre optimal de clusters.
        2. **Récupération des logs journaliers** :
        - Charge les logs du jour via `query_daily_logs()`.
        3. **Prétraitement des données** :
        - Applique le pipeline de transformation `_create_pipeline()` pour préparer les logs.
        4. **Clustering avec K-Means** :
        - Teste différentes valeurs de `n_clusters` (de 2 à `max_clusters`).
        - Entraîne un modèle K-Means et calcule le **score de Silhouette** pour mesurer la qualité du clustering.
        - Identifie la valeur de `n_clusters` offrant le meilleur score.
        5. **Affichage des résultats** :
        - Affiche les scores pour chaque nombre de clusters testé.
        - Retourne le nombre optimal de clusters.

        Args:
            max_clusters (int, optional): Nombre maximal de clusters à tester. Par défaut, 10.

        Returns:
            int: Le nombre optimal de clusters basé sur le meilleur score Silhouette.
        """
            
        # Initialisation des paramètres
        best_score = -1  # Score Silhouette le plus élevé trouvé
        best_n_clusters = 2  # Nombre optimal de clusters

        # Récupère les logs journaliers
        logs = self.query_logs()

        # Prétraitement des logs
        preprocessor = self._create_pipeline()
        logs = preprocessor.fit_transform(logs)

        # Teste plusieurs nombres de clusters pour identifier le meilleur
        for n_clusters in range(2, max_clusters + 1):
            self.model = KMeans(n_clusters=n_clusters, random_state=0)
            self.model.fit(logs)
            
            # Calcul du score de Silhouette
            score = silhouette_score(logs, self.model.labels_)
            print(f"Nombre de clusters : {n_clusters}, Silhouette Score : {score:.4f}")

            # Mise à jour du meilleur score et du meilleur nombre de clusters
            if score > best_score:
                best_score = score
                best_n_clusters = n_clusters

        # Affichage du meilleur nombre de clusters
        print(
            f"\nMeilleur nombre de clusters : {best_n_clusters}, Silhouette Score : {best_score:.4f}"
        )

        return best_n_clusters

    def generate_report(self, logs:pd.DataFrame) -> str:
        """
        Génère un rapport HTML sur les logs journaliers, incluant des statistiques et des résultats de clustering.

        Cette fonction effectue les étapes suivantes :
        1. **Calcul des statistiques** :
        - Récupère la date actuelle.
        - Calcule le nombre total de logs.
        - Effectue un comptage des occurrences de chaque statut dans les logs.
        - Exécute un clustering sur les logs pour déterminer le nombre de comportements différents.
        2. **Construction du rapport HTML** :
        - Crée une page HTML contenant les statistiques sous forme de texte et de liste.
        - Ajoute un titre, les informations de répartition des statuts, et le nombre de clusters détectés.
        - Applique un style simple pour rendre le rapport lisible et structuré.
        3. **Retourne le rapport sous forme de chaîne HTML** :
        - Le rapport est sous forme de code HTML prêt à être envoyé ou affiché.

        Args:
            logs (pd.DataFrame): Un DataFrame contenant les logs à analyser, avec au moins une colonne `status`.

        Returns:
            str: Un rapport HTML sous forme de chaîne de caractères.
        """
        
        # Récupération de la date actuelle sous format dd/mm/yyyy
        date_str = datetime.now().strftime("%d/%m/%Y")
        
        # Nombre total de logs
        total_logs = len(logs)
        
        # Comptage des occurrences de chaque statut
        status_counts = logs["status"].value_counts().to_dict()
        
        # Exécution du clustering pour obtenir le nombre de comportements différents détectés
        n_clusters = self.clustering_log()

        # Création d'une liste HTML des statuts et de leurs occurrences
        status_html = "".join(
            f"<li><strong>{status}:</strong> {count}</li>"
            for status, count in status_counts.items()
        )

        # Construction du rapport HTML
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
        """
        Envoie un email en utilisant l'API SendGrid.

        Cette fonction réalise les étapes suivantes :
        1. **Initialisation de l'API SendGrid** :
        - Utilise la clé API de SendGrid (`self.sendgrid_api_key`) pour configurer l'accès à l'API.
        2. **Préparation du contenu de l'email** :
        - Définit l'expéditeur (`from_email`), le destinataire (`to_email`), le sujet (`subject`) 
            et le corps de l'email (`body`), qui est en format HTML.
        3. **Envoi de l'email** :
        - Envoie l'email via l'API SendGrid en utilisant la méthode `send.post`.
        4. **Gestion des erreurs** :
        - Si l'envoi échoue, un message d'erreur est affiché.

        Args:
            subject (str): Le sujet de l'email.
            body (str): Le contenu de l'email en format HTML.

        Returns:
            None: Si l'email est envoyé avec succès, aucun retour n'est généré, 
                sinon un message d'erreur est imprimé.
        """
        
        # Initialisation de l'API SendGrid
        sg = sendgrid.SendGridAPIClient(api_key=self.sendgrid_api_key)
        
        # Création des objets pour l'expéditeur, le destinataire et le contenu
        from_email = Email(self.from_email)
        to_email = To(self.recipient_email)
        content = Content("text/html", body)
        
        # Création de l'objet Mail avec les informations nécessaires
        mail = Mail(from_email, to_email, subject, content)

        try:
            # Envoi de l'email via l'API SendGrid
            response = sg.client.mail.send.post(request_body=mail.get())
            print(f"Email envoyé avec succès: {response.status_code}")
        except Exception as e:
            # Si une erreur survient, affichage du message d'erreur
            print(f"Erreur, email non-envoyé: {e}")

    def run_report(self):
        """
        Exécute le rapport journalier de sécurité et l'envoie par email.

        Cette fonction réalise les étapes suivantes :
        1. **Récupération des logs journaliers** :
        - Utilise la méthode `query_daily_logs()` pour obtenir les logs du jour à analyser.
        2. **Génération du rapport** :
        - Utilise la méthode `generate_report()` pour créer un rapport HTML contenant les statistiques et autres informations pertinentes sur les logs.
        3. **Envoi du rapport par email** :
        - Utilise la méthode `send_email()` pour envoyer l'email avec le rapport généré en pièce jointe dans le corps du message.

        Returns:
            None: Cette fonction n'a pas de valeur de retour. Elle exécute des actions (générer et envoyer un rapport).
        """
        
        # Récupérer les logs de la journée
        logs = self.query_logs()
        
        # Générer un rapport à partir des logs récupérés
        report = self.generate_report(logs)

        # Envoi du rapport par email
        self.send_email(subject="Rapport de sécurité journalier", body=report)
