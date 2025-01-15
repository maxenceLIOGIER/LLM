import streamlit as st

def app():
    st.title("Requête du modèle")
    
    # Input utilisateur via speech-to-text ou texte
    st.subheader("Interrogez le LLM via votre voix ou texte")
    
    # Upload audio ou entrée texte
    audio_file = st.file_uploader("Téléversez un fichier audio", type=["wav", "mp3"])
    if audio_file:
        text_query = transcribe_audio(audio_file) #Intercaler ici le modèle speech to text
        st.write(f"Transcription : {text_query}")
    else:
        text_query = st.text_input("Ou entrez votre question ici :")
    
    # Résultat du LLM
    if st.button("Soumettre"):
        # Appeler votre LLM ici
        response = f"Réponse simulée pour : {text_query}"  # Remplacer par un appel au LLM
        st.write("Réponse du LLM :", response)