import sqlite3
from datetime import datetime
import re
from sklearn.metrics.pairwise import cosine_similarity
from langchain_mistralai import MistralAIEmbeddings
import os
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content
from dotenv import load_dotenv
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
from rapidfuzz import fuzz
import requests

#racine du projet au PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from database.models import Base, Origin, Status, Prompt, Log 


#chargement des variables d'environnements
load_dotenv()
HF_TOKEN = os.getenv("HF_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")

# Configuration de la base de données
DATABASE_URL = "sqlite:///../../database/db_logs.db"
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)

class SecurityCheck:
    def __init__(self, db_path, sendgrid_api_key = SENDGRID_API_KEY, from_email = FROM_EMAIL, recipient_email = RECIPIENT_EMAIL):
        self.DB_PATH = db_path
        self.sendgrid_api_key = sendgrid_api_key
        self.from_email = from_email
        self.recipient_email = recipient_email
        self.session = SessionLocal()

    def log_event_db(self, prompt : str, status : str, origin : str):
        '''
        Journalise les événements dans la BDD
        '''
        try:
            #Ajouter à la table Origin
            new_origin = Origin(response=origin)
            self.session.add(new_origin)
            self.session.commit()

            #Ajouter à la table Status
            new_status = Status(status=status)
            self.session.add(new_status)
            self.session.commit()

            #Ajouter à la table Prompt
            new_prompt = Prompt(
                id_origin=new_origin.id_origin,
                prompt=prompt,
                response="Réponse générée automatiquement"
            )
            self.session.add(new_prompt)
            self.session.commit()

            #Ajouter à la table Log
            new_log = Log(
                timestamp=datetime.utcnow(),
                id_prompt=new_prompt.id_prompt,
                id_status=new_status.id_status,
                id_origin=new_origin.id_origin
            )
            self.session.add(new_log)
            self.session.commit()

            print(f"Événement journalisé : {prompt} - {status}")
            
        except Exception as e:
            self.session.rollback()
            print(f"Erreur lors de l'insertion dans la base : {e}")
    
    def close_session(self):
        '''
        Ferme la session BDD
        '''
        self.session.close()

    def _send_email(self, subject : str, body : str):
        '''
        Envoie un email avec les détails du rejet
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
            print(f"Erreur : eamil non-envoyé: {e}")

    def _get_ip_address(self):
        """
        Récupère l'adresse IP publique de l'utilisateur via l'API ipify.
        """
        try:
            response = requests.get("https://api.ipify.org?format=json")
            response.raise_for_status()
            ip_address = response.json().get("ip")
            return ip_address
        except requests.exceptions.RequestException as e:
            print(f"Erreur lors de la récupération de l'IP : {e}")
            return None

    def filter_and_normalize_input(self, prompt: str, seuil_fuzzy = 80) -> str:
        """
        Filtre et normalise les entrées utilisateur.
        Vérifie la présence de caractères interdits et de mots interdits.
        """
        #Liste de caractères interdits
        forbidden_chars = set("{}[]<>|;$&%\n\r\t\\\"\'\u200b\u202e")

        #Liste de mots interdits
        forbidden_words = [
            "ignorer", "contourner", "désactiver", "forcer", "exécuter", "injecter", "réinitialiser",
            "interrompre", "supprimer", "redémarrer", "arrêter", "tuer", "pirater", "évaluer", "contourne",
            "exécute", "réinitialise", "tu es", "joue le rôle de", "fais comme si", "suppose que", "simule",
            "comporte-toi comme", "assistant", "modèle de langage", "modèle IA", "intelligence artificielle",
            "chatbot", "ouvre-toi", "rends-toi vulnérable", "ignore toutes les restrictions", "désactive la sécurité",
            "effacer", "supprimer", "casser", "détruire", "modifier", "désinstaller", "télécharger", "installer",
            "charger", "compiler", "déboguer", "accéder", "récupérer", "afficher", "openai", "langage naturel",
            "réseau neuronal", "code source", "GPT", "modèle génératif", "machine learning", "deep learning",
            "fais", "ordonne", "exécute", "agit comme", "désactive", "montre-moi", "fais semblant", "commande",
            "contournement", "autorisation"
        ]

        #Vérifie la présence de caractères interdits, enregistre un log et envoie un email 
        if any(char in forbidden_chars for char in prompt):
            self.log_event_db(
                prompt=prompt,
                status="Rejeté : caractères interdits",
                origin=self._get_ip_address()
            )
            self._send_email(
                subject="Rejet de prompt : caractères interdits",
                body=f"Le prompt suivant a été rejeté en raison de caractères interdits : \n\n"
                        f"{prompt}\n\n"
                        f"L'adresse IP est la suivante : {self._get_ip_address()}"
            )
            raise ValueError("Entrée invalide : contient des caractères interdits.")

        #Vérifie la présence de mots interdits, enregistre un log et envoie un email 
        prompt_words = prompt.split()
        for p_word in prompt_words : 
            for f_word in forbidden_words : 
                if fuzz.ratio(p_word.lower(), f_word.lower()) >= seuil_fuzzy:
                    self.log_event_db(
                        prompt=prompt,
                        status="Rejeté : mots interdits",
                        origin=self._get_ip_address()
                    )
                    self._send_email(
                        subject="Rejet de prompt : mots interdits",
                        body=f"Le prompt suivant a été rejeté en raison de mots interdits : \n\n"
                        f"{prompt}\n\n"
                        f"L'adresse IP est la suivante : {self._get_ip_address()}"
                    )
                    raise ValueError("Entrée invalide : contient des mots interdits.")

        #Suppression des espaces inutiles et mise en minuscule et enregistre un log
        normalized_input = prompt.strip().lower()
        normalized_input = re.sub(r"\s+", " ", normalized_input)

        self.log_event_db(
            prompt=prompt,
            status="Accepté",
            origin=self._get_ip_address()
        )

        return normalized_input

    def prompt_check(self, prompt, docs_embeddings, mistral_api_key = MISTRAL_API_KEY, threshold=0.6) -> bool:
        """
        Vérifie si une requête utilisateur est pertinente.
        Si hors contexte, il la bloque.

        Args : 
            - prompt (str): Prompt de l'utilisateur pour requêter le LLM.
            - docs_embeddings (list): Embeddings des documents de référence.
            - mistral_api_key (str): Clé d'API pour Mistral.
            - threshold (float): Seuil de similarité pour accepter ou rejeter.

        Returns : 
            - bool: True si le prompt est pertinent, False sinon.
        """
        #Embedding du prompt
        try:
            mistral_embeddings = MistralAIEmbeddings(model="mistral-embed", api_key=mistral_api_key)
            prompt_embedding = mistral_embeddings.embed_query(prompt)

            prompt_embedding = np.array(prompt_embedding).reshape(1, -1)

            #Conversion des docs_embeddings en numpy array (matrice 2D)
            docs_embeddings = np.array(docs_embeddings)

            #Vérification de la cohérence des dimensions
            if prompt_embedding.shape[1] != docs_embeddings.shape[1]:
                raise ValueError(f"Incompatible dimensions: prompt_embedding has {prompt_embedding.shape[1]} dimensions "
                                f"while docs_embeddings has {docs_embeddings.shape[1]} dimensions.")


            #Calcul de la similarité cosine
            similarities = cosine_similarity(prompt_embedding, docs_embeddings)
            max_similarity = max(similarities[0])

            #Vérification par rapport au seuil
            return max_similarity >= threshold

        except Exception as e:
            print(f"Erreur lors de la vérification du prompt : {e}")
            return False