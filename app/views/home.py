import streamlit as st
from pathlib import Path

logopath = Path(__file__).parent.parent.parent / "assets" / "logo.png"


def home_page():
    # Affichage du logo
    st.image(logopath, width=550)
    
    # Titre principal
    st.title("Smart Rescue - Assistance d'Urgence Augmentée")
    
    # Présentation du projet
    st.markdown(
        """
        Bienvenue sur **Smart Rescue**, une application conçue pour assister les opérateurs d'urgence
        grâce à l'intégration d'un **LLM (Large Language Model) et d'un RAG (Retrieval-Augmented Generation)**.  
        Cette technologie permet d'améliorer la prise de décision en temps réel et de fournir une assistance
        rapide et efficace lors des appels d'urgence.
        """
    )
    
    # Affichage des fonctionnalités principales
    st.subheader("🔹 Fonctionnalités principales")
    st.markdown(
        """
        - 🎙️ **Aide téléphonique** : Enregistrement des conversations et assistance du LLM en temps réel.
        - 📊 **Dashboard** : Suivi des métriques du système RAG (coût, latence, impact environnemental).
        - 🔐 **Admin** : Suivi des logs d'utilisation, appel d'API, et génération de rapports de sécurité.
        """
    )
    
    # Affichage d'un encadré informatif
    st.info(
        "🔎 *Smart Rescue vise à optimiser la gestion des urgences en fournissant un support basé sur l'IA*"
    )
    
    # Message de bienvenue final
    st.success("🚀 Explorez les différentes fonctionnalités à travers les onglets de l'application !")

