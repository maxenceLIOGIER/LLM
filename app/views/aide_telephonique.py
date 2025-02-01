import os
import sys
import time
from datetime import datetime
import streamlit as st
import numpy as np
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEndpoint
from langchain.memory import ChatMessageHistory
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import AIMessage, HumanMessage
from langchain_chroma import Chroma

# Ajout du chemin du répertoire parent pour importer les modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.speech_to_text import WhisperLiveTranscription
from src.security.security_check import SecurityCheck


load_dotenv()
HF_API_KEY = os.getenv("HF_API_KEY")

# Instanciation du transcripteur
transcriber = WhisperLiveTranscription(
    model_id="openai/whisper-small", language="french"
)

# Instanciation de la sécurité
security = SecurityCheck()


def get_docs_embeddings():
    """
    Récupère le contexte d'une requête en utilisant les embeddings de la requête.
    """
    persist_directory = "../embed_s1000_o100"
    docs_embeddings = Chroma(
        collection_name="statpearls_articles",
        embedding_function=None,
        persist_directory=persist_directory,
    )
    docs_embeddings = docs_embeddings._collection.get(include=["embeddings"])

    return docs_embeddings


def get_context(prompt, docs_embeddings, top_indices):
    """
    Récupère le contexte d'une requête en utilisant les embeddings de la requête.
    """
    context = ""
    for idx in top_indices:
        context += docs_embeddings[idx] + " "
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
    summary = llm_chain.invoke({"conversation": conversation})
    return summary


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

        template = """
            Tu es une IA conçue pour assister les agents des urgences en analysant leurs appels.  
            
            **Règles à respecter :**  
            - Tu dois être **empathique, calme, direct et professionnel**.  
            - Ton **objectif** est d’extraire uniquement les informations critiques : **diagnostic, localisation, état des personnes, danger...**  
            - **Tu ne dois répondre qu'à la dernière déclaration ou question de l'opérateur.**  
            - **Tu ne dois jamais inventer ou imaginer des éléments de contexte.**  
            - **Tes réponses doivent être très courtes (maximum une ligne), claires et fournir uniquement des instructions ou des questions simples.**  
            - **Tes réponses doivent toujours être en français, sauf si l'opérateur parle en anglais.**  
            - **Formule tes réponses sous forme d’instructions précises pour l’opérateur.**  
            - **Tes réponses doivent toujours être en français, correctes grammaticalement et sans faute de syntaxe.**
            - **Tes réponses ne doivent jamais commencer par "réponse correcte". Réponds directement comme cela t'a été demandé.**

            **Important :** Tu n’as accès **qu'à la voix de l'opérateur**. Tu ne dois pas générer de contenu supplémentaire ni interpréter des éléments que tu ne peux pas entendre.  

            ### **Exemple de réponse attendue :**  
            **Opérateur :** "Il y a eu un accident, des blessés peut-être."  
            **Réponse correcte :** "Demandez à l'appelant combien de blessés il y a."  

            **Opérateur :** "Où est l’accident ?"  
            **Réponse correcte :** "Demandez une adresse exacte ou un point de repère."  

            **Voici la dernière déclaration ou question de l'opérateur :**  
            {text_query}
        """
        #      **Voici le contexte dont tu auras besoin pour répondre au mieux aux questions:**
        #      {context}
        # """

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

                # Check de sécurité, filtre mots interdits
                filtre = security.filter_and_check_security(
                    prompt=new_transcription, check_char=False
                )

                # Check de sécurité, similarité cosine avec les documents de la DB
                docs_embeddings = get_docs_embeddings()
                result = security.prompt_check(new_transcription, docs_embeddings)

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
                    response = llm_chain.invoke(
                        {
                            "text_query": st.session_state.history.messages,
                            "context": get_context(
                                new_transcription, docs_embeddings, top_indices
                            ),
                        }
                    )
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

                # # Réponse du LLM
                # response = llm_chain.invoke(st.session_state.history.messages)
                # st.session_state.history.add_ai_message(response)
                # with st.chat_message("assistant"):
                #     st.markdown(response)

                # # Filtrer les messages pour ne garder que ceux de l'IA
                # ai_messages = [
                #     message.content
                #     for message in st.session_state.history.messages
                #     if isinstance(message, AIMessage)
                # ]
                # st.session_state.ai_history = ai_messages

            else:
                continue

    if col2.button("⏹️ Arrêter l'enregistrement"):
        if st.session_state.recording:
            st.session_state.recording = False
            transcriber.stop_recording()
            st.success("Enregistrement terminé")

            llm = HuggingFaceEndpoint(
                repo_id="mistralai/Mistral-7B-Instruct-v0.2",
                huggingfacehub_api_token=HF_API_KEY,
            )

            # Résumé de la conversation via le LLM
            st.write("Résumé de la conversation :")
            messages = st.session_state.history.messages
            summary = summarize_conversation(messages, llm)
            st.write(summary)
