import streamlit as st


def home_page():
    st.image("../assets/logo.png", width=550)
    st.title("Présentation du Projet")
    st.markdown(
        """
    Bienvenue dans l'interface RAG (Retrieval-Augmented Generation).  
    Ce projet a pour but de démontrer comment intégrer un LLM avec des fonctionnalités supplémentaires :
    - **Interrogation vocale** (speech-to-text)
    - **Suivi des métriques** (latence, coût, impact écologique)
    """
    )
