import os
import base64
import streamlit as st
from streamlit_option_menu import option_menu

# # retour au dossier parent
# os.chdir(os.pardir)

from views.home import home_page
from views.dashboard import dashboard_page
from views.llm import llm_page
from views.admin import adm_page

APP_TITLE = "SmartRescue"


def add_logo():
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


st.set_page_config(
    page_title=APP_TITLE,
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="assets/icone.png",
)


with st.sidebar:
    print(os.getcwd())
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
