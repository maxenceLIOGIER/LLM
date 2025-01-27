import os
import sys
import time
import datetime
import streamlit as st
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEndpoint
from langchain_core.prompts import PromptTemplate
from langchain.memory import ChatMessageHistory
from langchain_core.messages import AIMessage


# Ajout du chemin du répertoire parent pour importer les modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.speech_to_text import WhisperLiveTranscription

load_dotenv()
HF_API_KEY = os.getenv("HF_API_KEY")

# Instanciation du transcripteur
transcriber = WhisperLiveTranscription(
    model_id="openai/whisper-small", language="french"
)
# Ne marche pas très bien pour les transcriptions à la volée


def llm_page():
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
    if "transcription" not in st.session_state:
        st.session_state.transcription = ""
    if "last_transcription" not in st.session_state:
        st.session_state.last_transcription = ""
    if "text_query" not in st.session_state:
        st.session_state.text_query = ""
    if "file" not in st.session_state:
        st.session_state.file = ""
    if "history" not in st.session_state:
        st.session_state.history = ChatMessageHistory()

    # Contrôles d'enregistrement
    col1, col2 = st.columns(2)

    llm_container = st.empty()

    if col1.button("🎤 Démarrer l'enregistrement"):
        st.session_state.recording = True

        # Création du fichier où les transcriptions seront stockées
        # timestamp YYYYMMDD_HHMM :
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        # Créer le fichier texte vide avec son timestamp
        st.session_state.file = f"transcription_{timestamp}.txt"
        with open(st.session_state.file, "a"):
            pass
            # on ira ensuite le remplir via speech_to_text.py

        transcriber.start_recording()
        st.info("Enregistrement en cours...")

        template = "Un LLM conçu pour assister les agents des urgences en analysant leurs appels. \
            Ton : empathique, calme, direct, professionnel. \
            Objectif : extraire les informations critiques (diagnostic, localisation, état des personnes, danger). \
            Le LLM ne doit répondre qu'à la dernière déclaration ou question de l'opérateur, sans inventer de contexte. \
            Les réponses doivent être très courtes (maximum une ligne), claires et fournir uniquement des instructions ou des questions simples. \
            Important : Le LLM n'a accès qu'à la voix de l'opérateur et ne doit pas générer de contenu supplémentaire ni imaginer des éléments de la conversation. \
            Voici la dernière déclaration ou question de l'opérateur : {text_query}"
        prompt = PromptTemplate(template=template, input_variables=["text_query"])

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
                st.session_state.text_query = new_transcription

                st.session_state.history.add_user_message(st.session_state.text_query)
                response = llm_chain.invoke(st.session_state.history.messages)
                st.session_state.history.add_ai_message(response)

                # Filtrer les messages pour ne garder que ceux de l'IA
                ai_messages = [
                    message for message in st.session_state.history.messages
                    if isinstance(message, AIMessage)
                ]
                llm_container.write(ai_messages)

                # llm_container.write(st.session_state.history)
            else:
                # on recommence la boucle et on attend 5 secondes
                continue

    if col2.button("⏹️ Arrêter l'enregistrement"):
        if st.session_state.recording:
            st.session_state.recording = False
            transcriber.stop_recording()
            st.success("Enregistrement terminé")

            # Affichage de l'historique
            llm_container.write(st.session_state.history)
