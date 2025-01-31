import streamlit as st
import os
from dotenv import load_dotenv
from langchain_mistralai import ChatMistralAI, MistralAIEmbeddings
from langchain_chroma import Chroma
from langchain import hub
from langgraph.graph import StateGraph, START
from langchain_core.documents import Document
from typing_extensions import List, TypedDict
import time
from views.dashboard import track_metrics

load_dotenv()

# Vérifier que la clé API 
api_key = os.getenv("MISTRAL_API_KEY")

if not api_key:
    st.error("⚠️ Erreur API.")
    st.stop()

# Fonction pour initialiser le modèle et les ressources (ne s'exécute qu'une seule fois)
def initialize_resources():
    if "llm" not in st.session_state:
        st.session_state.llm = ChatMistralAI(model="mistral-large-latest")
        
    if "embeddings" not in st.session_state:
        st.session_state.embeddings = MistralAIEmbeddings(model="mistral-embed")
    
    if "docs_embeddings" not in st.session_state:
        persist_directory = "./embed_s1000_o100"
        st.session_state.docs_embeddings = Chroma(
            collection_name="statpearls_articles",
            embedding_function=st.session_state.embeddings,
            persist_directory=persist_directory
        )

    if "graph" not in st.session_state:
        prompt = hub.pull("rlm/rag-prompt")

        class State(TypedDict):
            question: str
            context: List[Document]
            answer: str

        def retrieve(state: State):
            retrieved_docs = st.session_state.docs_embeddings.similarity_search(state["question"], k=5)
            return {"context": retrieved_docs}

        def generate(state: State):
            docs_content = "\n\n".join(doc.page_content for doc in state["context"])
            messages = prompt.invoke({"question": state["question"], "context": docs_content})
            response = st.session_state.llm.invoke(messages)
            return {"answer": response.content}

        # Construire et stocker le graphe
        rag_graph = StateGraph(State)
        rag_graph.add_node("retrieve", retrieve)
        rag_graph.add_node("generate", generate)
        rag_graph.add_edge(START, "retrieve")
        rag_graph.add_edge("retrieve", "generate")
        st.session_state.graph = rag_graph.compile()

# Initialiser une seule fois
initialize_resources()

def get_response(question: str):
    """ Gère la requête et enregistre les métriques """
    start_time = time.time()

    state = {"question": question}
    result = st.session_state.graph.invoke(state)
    response = result["answer"]

    # Estimation
    token_count = len(response.split())  
    latency = (time.time() - start_time) * 1000  # en ms

    # Mettre à jour les métriques
    track_metrics(latency, token_count)

    return response


def rag_page():
    """ Interface RAG sous forme de chat """
    st.title("💬 Chat Medical")
    
    # Initialiser l'historique de conversation
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Affichage des messages précédents
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Zone de saisie pour l'utilisateur
    question = st.chat_input("Posez votre question...")
    
    if question:
        # Ajouter la question à l'historique
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)
        
        # Obtenir la réponse sans réinitialiser le modèle
        response = get_response(question)
        
        # Ajouter la réponse de l'IA à l'historie
        st.session_state.messages.append({"role": "assistant", "content": response})
        with st.chat_message("assistant"):
            st.markdown(response)
