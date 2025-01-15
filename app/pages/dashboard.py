import streamlit as st

def get_metrics():
    # Remplace par des calculs réels
    return {
        "latency": 200,          # en ms
        "cost": 0.05,           # en €
        "carbon_impact": 1.23   # en gCO2
    }

def app():
    st.title("Métriques")
    st.subheader("Suivi des performances et de l'impact")

    # Exemple de métriques
    metrics = get_metrics()
    
    st.metric("Latence moyenne (ms)", metrics['latency'])
    st.metric("Coût estimé (€)", metrics['cost'])
    st.metric("Impact écologique (gCO2)", metrics['carbon_impact'])