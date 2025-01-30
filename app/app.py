import base64
import streamlit as st
from streamlit_option_menu import option_menu
import uvicorn
from api import api
from multiprocessing import Process
from views.home import home_page
from views.dashboard import dashboard_page
from views.llm import llm_page
from views.admin import adm_page

APP_TITLE = "SmartRescue"
API_PORT = 8901

st.set_page_config(
    page_title=APP_TITLE,
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="assets/icone.png",
)


def add_logo():
    """
    Fonction d'insertion du logo en arrière-plan du menu latéral de Streamlit.

    Il s'agit de la méthode conseillée par les mainteneurs de Streamlit :
    https://discuss.streamlit.io/t/put-logo-and-title-above-on-top-of-page-navigation-in-sidebar-of-multipage-app/28213/6
    """
    # Lecture du fichier image local
    with open("assets/logo.png", "rb") as f:
        logo_data = base64.b64encode(f.read()).decode()

    st.markdown(
        f"""
        <style>
            [data-testid="stSidebar"] > div {{
                background-image: url("data:image/png;base64,{logo_data}");
                background-repeat: no-repeat;
                margin-top: 25px;
                background-position: 20px 20px;
                background-size: 300px;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def run_fastapi(port: int) -> None:
    """
    Démarre le serveur API FastAPI en arrière-plan.

    Le serveur est configuré pour écouter sur 127.0.0.1,
    et le port spécifié en argument.

    Param :
            - port: Port d'écoute du serveur API
    """
    try:
        uvicorn.run(api, host="127.0.0.1", port=port)
    except Exception as e:
        st.error(f"Échec du démarrage du serveur API : {str(e)}")


def main():
    """
    Fonction main de l'application Streamlit.

    On lance d'abord le serveur FastAPI en arrière-plan,
    puis on affiche l'interface utilisateur Streamlit.
    """
    # Démarrer FastAPI en arrière-plan, dans un autre process
    api_process = Process(target=run_fastapi, args=(API_PORT,), daemon=True)
    api_process.start()

    # Interface utilisateur Streamlit
    with st.sidebar:
        add_logo()
        selected = option_menu(
            menu_title="Navigation",
            options=["Home", "LLM", "Dashboard", "Admin"],
            icons=["house", "robot", "bar-chart", "shield"],
            default_index=0,
        )

    if selected == "Home":
        home_page()
    elif selected == "LLM":
        llm_page()
    elif selected == "Dashboard":
        dashboard_page()
    elif selected == "Admin":
        adm_page()


if __name__ == "__main__":
    main()
