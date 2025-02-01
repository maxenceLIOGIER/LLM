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

    def _get_ip_address(self) -> str:
        """
        Récupère l'adresse IP publique de l'utilisateur via l'API ipify.

        Cette fonction réalise les étapes suivantes :
        1. **Envoi d'une requête HTTP** :
        - Envoie une requête GET à l'API `ipify` pour récupérer l'adresse IP publique au format JSON.
        2. **Traitement de la réponse** :
        - Si la requête réussit, extrait l'adresse IP du JSON retourné.
        3. **Gestion des erreurs** :
        - Si une erreur survient lors de la requête (par exemple, problème de connexion), affiche un message d'erreur et retourne `None`.

        Returns:
            str or None: Retourne l'adresse IP publique sous forme de chaîne de caractères si la requête est réussie,
                        ou `None` en cas d'erreur.
        """

        try:
            # Envoie une requête GET à l'API ipify pour récupérer l'adresse IP publique
            response = requests.get("https://api.ipify.org?format=json")
            response.raise_for_status()  # Vérifie si la requête a échoué

            # Extraction de l'adresse IP depuis le JSON de la réponse
            ip_address = response.json().get("ip")
            return ip_address
        except requests.exceptions.RequestException as e:
            # En cas d'erreur, affiche un message d'erreur et retourne None
            print(f"Erreur lors de la récupération de l'IP : {e}")
            return None

    def filter_and_check_security(
        self, prompt: str, seuil_fuzzy=80, check_char: bool = True
    ) -> str:
        """
        Filtre et normalise les entrées utilisateur.
        Vérifie la présence de caractères interdits et de mots interdits dans le prompt.

        Cette fonction réalise les étapes suivantes :
        1. **Vérification des caractères interdits** :
        - Vérifie si le prompt contient des caractères interdits (par exemple, des symboles spéciaux ou des caractères de contrôle).
        2. **Vérification des mots interdits** :
        - Vérifie si le prompt contient des mots interdits à l'aide d'une comparaison floue (fuzzy matching) basée sur un seuil de similarité défini par `seuil_fuzzy`.
        3. **Gestion des résultats** :
        - Si des caractères ou mots interdits sont trouvés, le prompt est rejeté avec un message approprié.
        - Si aucune règle n'est violée, le prompt est accepté.
        4. **Ajout d'informations supplémentaires** :
        - Enregistre l'adresse IP de l'utilisateur et un timestamp pour chaque vérification.

        Args:
            prompt (str): L'entrée utilisateur à vérifier.
            seuil_fuzzy (int, optional): Seuil de similarité pour la comparaison floue des mots interdits (par défaut 80).
            check_char (bool, optional): Si `True`, vérifie la présence de caractères interdits dans le prompt (par défaut `True`).

        Returns:
            dict: Dictionnaire contenant le statut de l'entrée (`"Rejeté"` ou `"Accepté"`) et les informations associées (adresse IP et timestamp).
        """

        # Liste des caractères interdits
        forbidden_chars = set("{}[]<>|;$&%\n\r\t\\\"'\u200b\u202e")

        # Liste des mots interdits (en incluant des termes liés à la sécurité ou à des comportements malveillants)
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

        # Initialisation du dictionnaire des résultats
        results = dict()

        # Vérification de la présence de caractères interdits
        if check_char:
            if any(char in forbidden_chars for char in prompt):
                results["status"] = "Rejeté : caractères interdits"
                results["origin"] = self._get_ip_address()
                results["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                return results

        # Vérification de la présence de mots interdits avec une comparaison floue (fuzzy matching)
        prompt_words = prompt.split()
        for p_word in prompt_words:
            for f_word in forbidden_words:
                if fuzz.ratio(p_word.lower(), f_word.lower()) >= seuil_fuzzy:
                    results["status"] = "Rejeté : mots interdits"
                    results["origin"] = self._get_ip_address()
                    results["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    return results

        # Si aucun problème n'a été détecté, l'entrée est acceptée
        results["status"] = "Accepté"
        results["origin"] = self._get_ip_address()
        results["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return results

    def prompt_check(
        self, prompt: str, docs_embeddings: list, threshold: float = 0.6
    ) -> bool:
        """
        Vérifie si une requête utilisateur est pertinente.
        Si la requête est hors contexte par rapport aux documents de référence, elle est bloquée.

        Cette fonction calcule la similarité entre le prompt utilisateur et les documents de référence
        en utilisant des embeddings, puis la compare avec un seuil de similarité donné.

        Args:
            - prompt (str): Le texte que l'utilisateur soumet pour interroger le modèle.
            - docs_embeddings (list): Liste des embeddings des documents de référence qui serviront de base de comparaison.
            - threshold (float): Seuil de similarité pour déterminer si le prompt est pertinent (par défaut 0.6).

        Returns:
            - bool: `True` si la similarité entre le prompt et les documents de référence est suffisante (au-dessus du seuil),
                    `False` sinon.
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

            # Trouver les indices des 3 documents les plus similaires
            top_indices = np.argsort(similarities)[-3:][::-1]

            # Vérification par rapport au seuil
            test_sim_cosine = max_similarity >= threshold
            return (test_sim_cosine, top_indices)

        except Exception as e:
            print(f"Erreur lors de la vérification du prompt : {e}")
            return (False, np.array([]))
