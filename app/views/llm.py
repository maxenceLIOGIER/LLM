import os
import sys
import datetime
import streamlit as st
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEndpoint
from langchain_core.prompts import PromptTemplate

from src.speech_to_text import WhisperLiveTranscription

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

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
    Pour l'instant le LLM est appelé à la fin de l'enregistrement.
    A terme, il faudra appeler le LLM pendant l'enregistrement pour une discussion en temps réel.
    (toutes les x secondes ou tous les x caractères)

    ATTENTION !! dans la transcription, la dernière phrase est répétée 3 fois ce qui fausse le modèle.
    """

    st.title("Requête du modèle")
    st.subheader("Interrogez le LLM via votre voix ou texte")

    # Initialisation de l'état de session
    if "recording" not in st.session_state:
        st.session_state.recording = False
    if "transcription" not in st.session_state:
        st.session_state.transcription = ""
    if "text_query" not in st.session_state:
        st.session_state.text_query = ""
    if "file" not in st.session_state:
        st.session_state.file = ""

    # Contrôles d'enregistrement
    col1, col2 = st.columns(2)

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

    if col2.button("⏹️ Arrêter l'enregistrement"):
        if st.session_state.recording:
            st.session_state.recording = False
            transcriber.stop_recording()
            st.success("Enregistrement terminé")

        # Affichage de la transcription
        with open(st.session_state.file, "r", encoding="utf-8") as f:
            transcription = f.read()
        st.session_state.transcription = transcription

        if st.session_state.transcription:
            st.session_state.text_query = st.session_state.transcription
            # st.text_area("Transcription :", st.session_state.text_query, height=200)
        else:
            st.warning("Aucune transcription trouvée")

    # Résultat du LLM
    if st.button("Soumettre"):

        # template = "You are an artificial intelligence assistant, answer the question. {question}"
        template = "Un LLM conçu pour assister les agents des urgences en analysant leurs appels. \
            Ton : empathique, calme, direct, professionnel. \
            Objectif : extraire les informations critiques. (diagnostic, localisation, état des personnes, danger)\
            Toujours rester précis et rapide. \
            Voici la discussion : {text_query}"

        prompt = PromptTemplate(template=template, input_variables=["text_query"])

        llm = HuggingFaceEndpoint(
            repo_id="tiiuae/falcon-7b-instruct", huggingfacehub_api_token=HF_API_KEY
        )
        llm_chain = prompt | llm

        st.write(
            "Réponse du LLM :",
            llm_chain.invoke({"text_query": st.session_state.text_query}),
        )
