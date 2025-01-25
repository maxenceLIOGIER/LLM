import streamlit as st
import os
import sys
import datetime
import glob

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.speech_to_text import WhisperLiveTranscription

# Instanciation du transcripteur
transcriber = WhisperLiveTranscription(
    model_id="openai/whisper-small", language="french"
)
# Ne marche pas très bien pour les transcriptions à la volée


def llm_page():
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
            st.text_area("Transcription :", st.session_state.text_query, height=200)
        else:
            st.warning("Aucune transcription trouvée")
            st.session_state.text_query = st.text_input(
                "Ou entrez votre question ici :"
            )

    # Résultat du LLM
    if st.button("Soumettre"):
        # Appeler votre LLM ici (à remplacer par un réel appel)
        response = f"Réponse simulée pour : {st.session_state.text_query}"
        st.write("Réponse du LLM :", response)
