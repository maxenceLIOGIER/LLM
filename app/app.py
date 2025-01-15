import streamlit as st
from pages import home, llm, dashboard

st.set_page_config(page_title="Interface RAG", layout="wide")

#Menu
PAGES = {
    "Présentation": home,
    "Interrogation du LLM": llm,
    "Métriques": dashboard
}

def main():
    st.sidebar.title("Navigation")
    choice = st.sidebar.radio("Choisissez une page :", list(PAGES.keys()))
    page = PAGES[choice]
    page.app()  #Appelle la fonction principale de la page sélectionnée

if __name__ == "__main__":
    main()