import streamlit as st
from streamlit_option_menu import option_menu
from views.home import home_page
from views.dashboard import dashboard_page
from views.llm import llm_page

APP_TITLE = "Agent conversationnel Santé [nom provisoire]"

st.set_page_config(
    page_title=APP_TITLE,
    layout="wide",
    initial_sidebar_state="expanded"
)

with st.sidebar:
    selected = option_menu(
        menu_title='Navigation',
        options=["Home", "Dashboard", "LLM"],
        icons=["house", "bar-chart", "robot"],
        default_index=0
    )

if selected == "Home":
    home_page()
elif selected == "Dashboard":
    dashboard_page()
elif selected == "LLM":
    llm_page()

