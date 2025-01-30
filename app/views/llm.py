import os
import sys
import time
from datetime import datetime
import streamlit as st
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEndpoint
from langchain.memory import ChatMessageHistory
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import AIMessage, HumanMessage

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


def summarize_conversation(history, llm):
    """
    Résume l'historique de la conversation en utilisant le LLM.
    """
    conversation = "\n".join([msg.content for msg in history.messages])
    prompt = PromptTemplate(
        template="Résumez la conversation suivante : {conversation}",
        input_variables=["conversation"],
    )
    llm_chain = prompt | llm
    summary = llm_chain.invoke({"conversation": conversation})
    return summary


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
    if "file" not in st.session_state:
        st.session_state.file = ""
    if "ai_history" not in st.session_state:
        st.session_state.ai_history = ""
    if "message_count" not in st.session_state:
        st.session_state.message_count = 0

    # Contrôles d'enregistrement
    col1, col2 = st.columns(2)

    llm_container = st.empty()

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

        transcriber.start_recording()
        st.info("Enregistrement en cours...")

        template = "Un LLM conçu pour assister les agents des urgences en analysant leurs appels. \
            Il doit être empathique, calme, direct, professionnel. \
            Objectif : extraire les informations critiques (diagnostic, localisation, état des personnes, danger). \
            Le LLM ne doit répondre qu'à la dernière déclaration ou question de l'opérateur, sans inventer de contexte. \
            Les réponses doivent être très courtes (maximum une ligne), claires et fournir uniquement des instructions ou des questions simples. \
            Les réponses doivent être en français. \
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
                st.session_state.history.add_user_message(new_transcription)
                st.session_state.message_count += 1

                # si plus de 10 messages, on résume les plus anciens
                if st.session_state.message_count > 10:
                    all_messages = st.session_state.history.messages
                    old_messages = all_messages[:-5]
                    recent_messages = all_messages[-5:]  # on garde les 5 derniers

                    # Résumé de la conversation via le LLM
                    summary = summarize_conversation(old_messages, llm)

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

                # Appel du LLM
                response = llm_chain.invoke(st.session_state.history.messages)
                st.session_state.history.add_ai_message(response)

                # Filtrer les messages pour ne garder que ceux de l'IA
                ai_messages = [
                    message.content
                    for message in st.session_state.history.messages
                    if isinstance(message, AIMessage)
                ]
                llm_container.write(ai_messages)
                st.session_state.ai_history = ai_messages

            else:
                # on recommence la boucle et on attend 5 secondes
                continue

    if col2.button("⏹️ Arrêter l'enregistrement"):
        if st.session_state.recording:
            st.session_state.recording = False
            transcriber.stop_recording()
            st.success("Enregistrement terminé")

            # Affichage de l'historique
            llm_container.write(st.session_state.ai_history)

            llm = HuggingFaceEndpoint(
                repo_id="mistralai/Mistral-7B-Instruct-v0.2",
                huggingfacehub_api_token=HF_API_KEY,
            )

            # Résumé de la conversation via le LLM
            st.write("Résumé de la conversation :")
            summary = summarize_conversation(st.session_state.history, llm)
            st.write(summary)
