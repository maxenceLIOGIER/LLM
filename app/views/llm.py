import streamlit as st
import os
import sys
import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.speech_to_text import WhisperLiveTranscription

# Instanciation du transcripteur
transcriber = WhisperLiveTranscription(
    model_id="openai/whisper-small", language="french"
)


def llm_page():
    st.title("Requête du modèle")
    st.subheader("Interrogez le LLM via votre voix ou texte")

    # Initialisation de l'état de session
    if "recording" not in st.session_state:
        st.session_state.recording = False
    if "transcription" not in st.session_state:
        st.session_state.transcription = ""

    # Contrôles d'enregistrement
    col1, col2 = st.columns(2)

    if col1.button("🎤 Démarrer l'enregistrement"):
        st.session_state.recording = True

        # Création du fichier où les transcriptions seront stockées
        # timestamp YYYYMMDD_HHMM :
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        # Créer le fichier texte vide avec son timestamp
        with open(f"transcription_{timestamp}.txt", "a"):
            pass
            # on ira ensuite le remplir via speech_to_text.py

        transcriber.start_recording()
        st.info("Enregistrement en cours...")

    if col2.button("⏹️ Arrêter l'enregistrement"):
        if st.session_state.recording:
            st.session_state.recording = False
            transcriber.stop_recording()
            st.success("Enregistrement terminé")

            # Vérifier si une transcription a été trouvée
            # if st.session_state.final_transcription:
            #     st.session_state.transcription = st.session_state.final_transcription
            #     st.write(f"Transcription : {st.session_state.final_transcription}")
            #     print(
            #         f"DEBUG: Displaying transcription: {st.session_state.final_transcription}"
            #     )
            # else:
            #     st.warning("Aucune transcription trouvée")
            #     print("DEBUG: No transcription found to display")

    # Affichage de la transcription
    # if st.session_state.transcription:
    #     text_query = st.session_state.transcription
    #     st.write(f"Transcription : {text_query}")
    # else:
    #     text_query = st.text_input("Ou entrez votre question ici :")

    # # Upload audio ou entrée texte
    # audio_file = st.file_uploader("Téléversez un fichier audio", type=["wav", "mp3"])
    # if audio_file:
    #     text_query = WhisperLiveTranscription._transcribe_audio(
    #         audio_file
    #     )  # Intercaler ici le modèle speech to text
    #     st.write(f"Transcription : {text_query}")
    # else:
    #     text_query = st.text_input("Ou entrez votre question ici :")

    # Résultat du LLM
    if st.button("Soumettre"):
        # Appeler votre LLM ici
        response = (
            f"Réponse simulée pour : {text_query}"  # Remplacer par un appel au LLM
        )
        st.write("Réponse du LLM :", response)
