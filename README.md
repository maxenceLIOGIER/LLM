---
title: "SmartRescue"
emoji: "🚑"
colorFrom: "red"
colorTo: "blue"
sdk: "streamlit"
sdk_version: "1.41.1"
app_file: app/app.py
pinned: false
---


# SmartRescue

SmartRescue est une application conçue pour assister les opérateurs d'urgence grâce à l'intégration d'un **LLM (Large Language Model)** et d'un **RAG (Retrieval-Augmented Generation)**. Cette technologie permet d'améliorer la prise de décision en temps réel et de fournir une assistance rapide et efficace lors des appels d'urgence.


## Fonctionnalités principales

- **Aide téléphonique** : Enregistrement des conversations et assistance du LLM en temps réel.
- **Dashboard** : Suivi des métriques du système RAG (coût, latence, impact environnemental).
- **Admin** : Suivi des logs d'utilisation, appel d'API, génération de rapports de sécurité et réglage des clés API.


## Installation

1. Clonez le dépôt :
    ```bash
    git clone https://github.com/maxenceLIOGIER/SmartRescue
    ```

2. Creez un environnement virtuel via conda par exemple:
    ```bash
    conda create env myenv python=3.11
    conda activate myenv
    ```

3. Installez les dépendances :
    ```bash
    pip install -r requirements.txt
    ```


## Utilisation

1. Placez vous dans le répertoire du projet :
    ```bash
    cd SmartRescue
    ```

2. Lancez l'application Streamlit :
    ```bash
    streamlit run app/app.py
    ```

3. Accédez à l'interface utilisateur via votre navigateur à l'adresse `http://localhost:8501` si celui-ci ne s'est pas lancé directement.



## Utilisation via Hugging Face

L'application est également disponible sur un space Hugging Face à l'adresse suivante : [https://huggingface.co/spaces/maxenceLIOGIER/SmartRescue](https://huggingface.co/spaces/maxenceLIOGIER/SmartRescue).

Cependant, nous n'avons pas réussi à connecter le micro sur cette plateforme. Pour une utilisation complète, il faudra faire tourner l'application en local comme décrit ci-dessus.