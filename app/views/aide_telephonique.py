import os
import sqlite3
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
import streamlit as st
import numpy as np
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEndpoint
from langchain.memory import ChatMessageHistory
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import AIMessage, HumanMessage
from langchain_chroma import Chroma
from views.dashboard import track_metrics
from DB_utils import Database

# Base de données
db_path = Path(__file__).parent.parent.parent / "database" / "db_logsv2.db"
# objet DButils pour la base de données
bdd = Database(db_path=str(db_path))
# Objet sqlite3 pour la base de données
db_sqlite = sqlite3.connect(db_path, check_same_thread=False)
cursor_db = db_sqlite.cursor()

# Ajout du chemin du répertoire parent pour importer les modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.speech_to_text import WhisperLiveTranscription
from src.security.security_check import SecurityCheck

# Chargement de la clé API Hugging Face
load_dotenv()
try:
    HF_API_KEY = st.session_state["HF_API_KEY"]
except KeyError:
    HF_API_KEY = os.getenv("HF_API_KEY")

# Instanciation de la sécurité
security = SecurityCheck()


def get_docs_embeddings():
    """
    Récupère le contexte d'une requête en utilisant les embeddings de la requête.
    """
    persist_directory = "../database/embed_s1000_o100"
    docs_embeddings = Chroma(
        collection_name="statpearls_articles",
        embedding_function=None,
        persist_directory=persist_directory,
    )
    docs_data = docs_embeddings._collection.get(include=["embeddings", "documents"])

    return docs_data


def get_context(prompt, docs_data, top_indices):
    """
    Récupère le contexte d'une requête en utilisant les embeddings de la requête.
    """
    context = ""
    top_indices = top_indices[0][:3]  # On garde les 3 premiers indices

    documents = docs_data["documents"]
    for idx in top_indices:
        context += str(documents[idx]) + " "
    context += prompt

    return context


def summarize_conversation(messages, llm):
    """
    Résume la conversation en utilisant le LLM.
    """
    conversation = "\n".join(msg.content for msg in messages)

    prompt = PromptTemplate(
        template="""
        Résume la conversation suivante en **5 phrases maximum** en français. 
        Ne garde que les informations **critiques et essentielles** pour les secours :
        - Nature de l'incident (accident, problème médical, etc.)
        - Localisation de l'incident.
        - Nombre de personnes impliquées et leur état (blessés, inconscients, etc.)
        - Actions ou recommandations immédiates nécessaires pour les secours.
        
        **Ne pas inventer d'informations** et ne pas ajouter de détails qui ne sont pas présents dans la conversation.
        Le résumé doit être clair, direct, et orienté vers les actions urgentes à prendre.
        Si la discussion ne parle pas d'un incident, tu peux le dire et n'invente rien !!

        Conversation :
        {conversation}

        Résumé :""",
        input_variables=["conversation"],
    )
    llm_chain = prompt | llm
    start_time = time.time()
    summary = llm_chain.invoke({"conversation": conversation})
    latency_summary = (time.time() - start_time) * 1000  # Convertir en ms
    tokens_summary = len(summary.split())
    return summary, latency_summary, tokens_summary


def aide_telephonique_page():
    """
    Page de requête du LLM en passant par un speech-to-text.

    Pour l'instant le LLM est appelé toutes les 5 secondes pendant l'enregistrement.
    TODO il faudra insérer un critère sur la longueur de la transcription pour appeler le LLM.
    Ca ne sert à rien d'appeler le LLM si la transcription est vide ou trop courte.

    TODO lorsque l'enregistrement se termine, la dernière phrase est 3 fois dans la transcription.
    (Mais pas toujours !!)
    Cela peut être gênant en faussant les résultats du LLM.
    """

    st.title("Requête du modèle")
    st.subheader("Interrogez le LLM via votre voix ou texte")

    # Initialisation de l'état de session
    if "recording" not in st.session_state:
        st.session_state.recording = False
    if "transcriber" not in st.session_state:
        st.session_state.transcriber = None
    if "transcription" not in st.session_state:
        st.session_state.transcription = ""
    if "last_transcription" not in st.session_state:
        st.session_state.last_transcription = ""
    if "file" not in st.session_state:
        st.session_state.file = ""
    if "ai_history" not in st.session_state:
        st.session_state.ai_history = ""
    if "message_count" not in st.session_state:
        st.session_state.message_count = 0
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if "latency_summary_list" not in st.session_state:
        st.session_state.latency_summary_list = []
    if "tokens_summary_list" not in st.session_state:
        st.session_state.tokens_summary_list = []
    if "latency_response_list" not in st.session_state:
        st.session_state.latency_response_list = []
    if "tokens_response_list" not in st.session_state:
        st.session_state.tokens_response_list = []

    # Contrôles d'enregistrement
    col1, col2 = st.columns(2)

    if col1.button("🎤 Démarrer l'enregistrement"):
        # Initialisation de l'enregistrement
        st.session_state.recording = True
        st.session_state.history = ChatMessageHistory()

        # Création du fichier où les transcriptions seront stockées
        # timestamp YYYYMMDD_HHMM :
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        # Créer le fichier texte vide avec son timestamp
        st.session_state.file = f"transcription_{timestamp}.txt"
        with open(st.session_state.file, "a"):
            pass
            # on ira ensuite le remplir via speech_to_text.py

        # Instanciation du transcripteur
        transcriber = WhisperLiveTranscription(
            model_id="openai/whisper-small", language="french"
        )
        transcriber.start_recording()
        st.session_state.transcriber = transcriber
        st.info("Enregistrement en cours...")

        template = """
            Tu es une IA conçue pour assister les agents des urgences en analysant leurs appels.

            **Voici le contexte dont tu auras besoin pour répondre au mieux aux questions:**
            {context}
            
            **Règles à respecter :**  
            - Tu dois être **empathique, calme, direct et professionnel**.  
            - Ton **objectif** est d’extraire uniquement les informations critiques : **diagnostic, localisation, état des personnes, danger...**  
            - **Tu ne dois répondre qu'à la dernière déclaration ou question de l'opérateur.**  
            - **Tu ne dois jamais inventer ou imaginer des éléments de contexte.**  
            - **Tes réponses doivent être très courtes (maximum une ligne), claires et fournir uniquement des instructions ou des questions simples.**  
            - **Tes réponses doivent toujours être en français, sauf si l'opérateur parle en anglais.**  
            - **Formule tes réponses sous forme d’instructions précises pour l’opérateur.**  
            - **Tes réponses doivent toujours être en français, correctes grammaticalement et sans faute de syntaxe.**
            - **Tes réponses ne doivent jamais commencer en introduisant la réponse (ex: "réponse :"). Réponds directement comme cela t'a été demandé.**

            **Important :** Tu n’as accès **qu'à la voix de l'opérateur**. Tu ne dois pas générer de contenu supplémentaire ni interpréter des éléments que tu ne peux pas entendre.  

            ### **Exemple de réponse attendue :**  
            **Opérateur :** "Il y a eu un accident, des blessés peut-être."  
            "Demandez à l'appelant combien de blessés il y a."  

            **Opérateur :** "Où est l’accident ?"  
            "Demandez une adresse exacte ou un point de repère."  

            **Voici la dernière déclaration ou question de l'opérateur :**  
            {text_query}

            **Pour rappel** tu dois absolument répondre uniquement en français avec des réponses les plus courtes possibles.
        """

        prompt = PromptTemplate(
            template=template, input_variables=["text_query", "context"]
        )

        llm = HuggingFaceEndpoint(
            repo_id="mistralai/Mistral-7B-Instruct-v0.2",
            huggingfacehub_api_token=HF_API_KEY,
        )
        llm_chain = prompt | llm

        # Appel du LLM toutes les 5 secondes sur la nouvelle transcription
        while st.session_state.recording:
            time.sleep(5)

            with open(st.session_state.file, "r", encoding="utf-8") as f:
                transcription = f.read()

            # On ne garde que la nouvelle transcription pour créer un "dialogue"
            new_transcription = transcription.replace(
                st.session_state.last_transcription, ""
            ).strip()
            st.session_state.last_transcription = transcription

            if new_transcription:
                st.session_state.history.add_user_message(new_transcription)
                # with st.chat_message("user"):
                #     st.markdown(new_transcription)
                # on n'affiche pas les messages de l'utilisateur pour gagner en visibilité

                st.session_state.message_count += 1

                # si plus de 10 messages, on résume les plus anciens
                if st.session_state.message_count > 10:
                    all_messages = st.session_state.history.messages
                    old_messages = all_messages[:-5]
                    recent_messages = all_messages[-5:]  # on garde les 5 derniers

                    # Résumé de la conversation via le LLM
                    summary, latency_summary, tokens_summary = summarize_conversation(
                        old_messages, llm
                    )
                    st.session_state.latency_summary_list.append(latency_summary)
                    st.session_state.tokens_summary_list.append(tokens_summary)
                    # Mettre à jour l'historique avec le résumé et les messages récents
                    st.session_state.history = ChatMessageHistory()
                    for msg in recent_messages:
                        st.session_state.history.add_user_message(summary)
                        if isinstance(msg, HumanMessage):
                            st.session_state.history.add_user_message(msg.content)
                        elif isinstance(msg, AIMessage):
                            st.session_state.history.add_ai_message(msg.content)

                    # Réinitialiser le compteur
                    st.session_state.message_count = len(recent_messages)

                # Check de sécurité, filtre mots interdits
                filtre = security.filter_and_check_security(
                    prompt=new_transcription, check_char=False
                )

                # Update de la base avec les résultats

                # Table origin
                # vérifier que l'origine n'existe pas déjà
                cursor_db.execute(
                    "SELECT id_origin FROM origin WHERE origin = ?", (filtre["origin"],)
                )
                resu = cursor_db.fetchone()
                if resu is None:
                    id_origin = str(uuid.uuid4())
                    cursor_db.execute(
                        """
                        INSERT INTO origin (id_origin, origin)
                        VALUES (?, ?)
                        """,
                        (id_origin, filtre["origin"]),
                    )
                    db_sqlite.commit()
                else:
                    id_origin = resu[0]

                # Table Status
                # vérifier que le status n'existe pas déjà
                cursor_db.execute(
                    "SELECT id_status FROM status WHERE status = ?", (filtre["status"],)
                )
                resu = cursor_db.fetchone()
                if resu is None:
                    id_status = str(uuid.uuid4())
                    cursor_db.execute(
                        """
                        INSERT INTO status (id_status, status)
                        VALUES (?, ?)
                        """,
                        (id_status, filtre["status"]),
                    )
                    db_sqlite.commit()
                else:
                    id_status = resu[0]

                # Table Prompt
                st.session_state.id_prompt = str(uuid.uuid4())
                query = """
                    INSERT INTO prompt (id_prompt, session_id, id_origin, prompt, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """
                cursor_db.execute(
                    query,
                    (
                        st.session_state.id_prompt,
                        st.session_state.session_id,
                        id_origin,
                        new_transcription,
                        filtre["timestamp"],
                    ),
                )
                db_sqlite.commit()
                cursor_db.execute(
                    """
                    UPDATE prompt
                    SET 
                        id_origin = ?,
                        timestamp = ?
                    WHERE id_prompt = ?
                    """,
                    (
                        id_origin,
                        filtre["timestamp"],
                        st.session_state.id_prompt,
                    ),
                )

                db_sqlite.commit()

                # Table Log
                id_log = str(uuid.uuid4())
                cursor_db.execute(
                    """
                    INSERT INTO log
                    (id_log, timestamp, id_prompt, id_status, id_origin)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        id_log,
                        filtre["timestamp"],
                        st.session_state.id_prompt,
                        id_status,
                        id_origin,
                    ),
                )

                db_sqlite.commit()

                # Check de sécurité, similarité cosine avec les documents de la DB
                docs_data = get_docs_embeddings()
                result = security.prompt_check(
                    new_transcription, docs_data["embeddings"], threshold=0.6
                )

                # Safely extract values from result
                top_indices = np.array([])
                if isinstance(result, tuple) and len(result) == 2:
                    test_sim_cos, top_indices = result
                elif isinstance(result, bool):
                    test_sim_cos = result
                else:
                    test_sim_cos = False

                # Appel du LLM si le test de sécurité est accepté
                if filtre["status"] == "Accepté" and test_sim_cos:
                    start_time = time.time()
                    response = llm_chain.invoke(
                        {
                            "text_query": st.session_state.history.messages,
                            "context": get_context(
                                new_transcription, docs_data, top_indices
                            ),
                        }
                    )
                    latency_response = (time.time() - start_time) * 1000  # ms
                    tokens_response = len(response.split())

                    st.session_state.latency_response_list.append(latency_response)
                    st.session_state.tokens_response_list.append(tokens_response)

                    st.session_state.history.add_ai_message(response)
                    with st.chat_message("assistant"):
                        st.markdown(response)

                    # Filtrer les messages pour ne garder que ceux de l'IA
                    ai_messages = [
                        message.content
                        for message in st.session_state.history.messages
                        if isinstance(message, AIMessage)
                    ]
                    st.session_state.ai_history = ai_messages

                elif filtre["status"] == "Refusé":
                    st.error(filtre["message"])
                elif not test_sim_cos:
                    st.error("La requête ne correspond pas à un contexte médical.")

            else:
                # on recommence la boucle et on attend 5 secondes
                continue

    if col2.button("⏹️ Arrêter l'enregistrement"):
        if st.session_state.recording:
            st.session_state.recording = False
            if st.session_state.transcriber:
                st.session_state.transcriber.stop_recording()
            st.success("Enregistrement terminé")

            llm = HuggingFaceEndpoint(
                repo_id="mistralai/Mistral-7B-Instruct-v0.2",
                huggingfacehub_api_token=HF_API_KEY,
            )

            # Résumé de la conversation via le LLM
            st.write("Résumé de la conversation :")
            messages = st.session_state.history.messages
            summary, latency_summary, tokens_summary = summarize_conversation(
                messages, llm
            )
            st.session_state.latency_summary_list.append(latency_summary)
            st.session_state.tokens_summary_list.append(tokens_summary)
            total_latency_response = sum(st.session_state.latency_response_list)
            total_tokens_response = sum(st.session_state.tokens_response_list)
            total_latency_summary = sum(st.session_state.latency_summary_list)
            total_tokens_summary = sum(st.session_state.tokens_summary_list)

            track_metrics(
                total_latency_response + total_latency_summary,
                total_tokens_response + total_tokens_summary,
            )

            st.write(summary)
