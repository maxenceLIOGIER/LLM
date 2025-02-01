from datetime import datetime
from sklearn.metrics.pairwise import cosine_similarity
from langchain_mistralai import MistralAIEmbeddings
import os
from dotenv import load_dotenv
import numpy as np
import sys
from rapidfuzz import fuzz
import requests
from pathlib import Path

# racine du projet au PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

# chargement des variables d'environnements
load_dotenv()
HF_TOKEN = os.getenv("HF_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")


class SecurityCheck:
    def __init__(self, mistral_api_key=MISTRAL_API_KEY):
        self.mistral_api_key = mistral_api_key

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

    def filter_and_check_security(
        self, prompt: str, seuil_fuzzy=80, check_char: bool = True
    ) -> str:
        """
        Filtre et normalise les entrées utilisateur.
        Vérifie la présence de caractères interdits et de mots interdits.
        """
        # Liste de caractères interdits
        forbidden_chars = set("{}[]<>|;$&%\n\r\t\\\"'\u200b\u202e")

        # Liste de mots interdits
        forbidden_words = [
            "ignorer",
            "contourner",
            "désactiver",
            "forcer",
            "exécuter",
            "injecter",
            "réinitialiser",
            "interrompre",
            "supprimer",
            "redémarrer",
            "arrêter",
            "tuer",
            "pirater",
            "évaluer",
            "contourne",
            "exécute",
            "réinitialise",
            "tu es",
            "joue le rôle de",
            "fais comme si",
            "suppose que",
            "simule",
            "comporte-toi comme",
            "assistant",
            "modèle de langage",
            "modèle IA",
            "intelligence artificielle",
            "chatbot",
            "ouvre-toi",
            "rends-toi vulnérable",
            "ignore toutes les restrictions",
            "désactive la sécurité",
            "effacer",
            "supprimer",
            "casser",
            "détruire",
            "modifier",
            "désinstaller",
            "télécharger",
            "installer",
            "charger",
            "compiler",
            "déboguer",
            "accéder",
            "récupérer",
            "afficher",
            "openai",
            "langage naturel",
            "réseau neuronal",
            "code source",
            "GPT",
            "modèle génératif",
            "machine learning",
            "deep learning",
            "fais",
            "ordonne",
            "exécute",
            "agit comme",
            "désactive",
            "montre-moi",
            "fais semblant",
            "commande",
            "contournement",
            "autorisation",
        ]

        # Initialisation d'un dictionnaire
        results = dict()

        # Vérifie la présence de caractères interdits et attribut les caractéristiques du filtre
        if check_char:
            if any(char in forbidden_chars for char in prompt):
                results["status"] = "Rejeté : caractères interdits"
                results["origin"] = self._get_ip_address()
                results["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                return results

        # Vérifie la présence de mots interdits et attribut les caractéristiques du filtre
        prompt_words = prompt.split()
        for p_word in prompt_words:
            for f_word in forbidden_words:
                if fuzz.ratio(p_word.lower(), f_word.lower()) >= seuil_fuzzy:
                    results["status"] = "Rejeté : mots interdits"
                    results["origin"] = self._get_ip_address()
                    results["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    return results

        # Attribut les caractéristiques du filtre
        results["status"] = "Accepté"
        results["origin"] = self._get_ip_address()
        results["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return results

    def prompt_check(self, prompt, docs_embeddings, threshold=0.6) -> bool:
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
        # Embedding du prompt
        try:
            mistral_embeddings = MistralAIEmbeddings(
                model="mistral-embed", api_key=self.mistral_api_key
            )
            prompt_embedding = mistral_embeddings.embed_query(prompt)

            prompt_embedding = np.array(prompt_embedding).reshape(1, -1)

            # Conversion des docs_embeddings en numpy array (matrice 2D)
            docs_embeddings = np.array(docs_embeddings)

            # Vérification de la cohérence des dimensions
            if prompt_embedding.shape[1] != docs_embeddings.shape[1]:
                raise ValueError(
                    f"Incompatible dimensions: prompt_embedding has {prompt_embedding.shape[1]} dimensions "
                    f"while docs_embeddings has {docs_embeddings.shape[1]} dimensions."
                )

            # Calcul de la similarité cosine
            similarities = cosine_similarity(prompt_embedding, docs_embeddings)
            max_similarity = max(similarities[0])

            # Vérification par rapport au seuil
            return max_similarity >= threshold

        except Exception as e:
            print(f"Erreur lors de la vérification du prompt : {e}")
            return False
