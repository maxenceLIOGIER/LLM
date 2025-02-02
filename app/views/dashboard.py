import streamlit as st
import plotly.express as px

from views.home import arret_enregistrement

# Estimation
COST_PER_TOKEN = 0.0005
CARBON_PER_QUERY = 0.8


def track_metrics(latency, token_count):
    """Met à jour les métriques avec une nouvelle requête"""

    # Initialiser les métriques globales si elles n'existent pas déjà
    if "metrics" not in st.session_state:
        st.session_state.metrics = {
            "total_queries": 0,
            "latency_history": [],
            "cost_history": [],
            "carbon_history": [],
        }

    st.session_state.metrics["total_queries"] += 1
    st.session_state.metrics["latency_history"].append(latency)
    st.session_state.metrics["cost_history"].append(token_count * COST_PER_TOKEN)
    st.session_state.metrics["carbon_history"].append(CARBON_PER_QUERY)


def get_metrics():
    """Retourne les métriques moyennes"""
    queries = max(
        len(st.session_state.metrics["latency_history"]), 1
    )  # éviter division par zéro
    return {
        "latency": round(sum(st.session_state.metrics["latency_history"]) / queries, 2),
        "cost": round(sum(st.session_state.metrics["cost_history"]), 4),
        "carbon_impact": round(sum(st.session_state.metrics["carbon_history"]), 2),
    }


def dashboard_page():
    """Affichage des métriques et graphiques"""
    st.title("Tableau de Bord des Performances")
    st.subheader("Suivi des performances et de l'impact")

    # si enregistrement en cours, on l'arrête
    arret_enregistrement()

    metrics = get_metrics()

    col1, col2, col3 = st.columns(3)
    col1.metric("Latence moyenne (ms)", f"{metrics['latency']} ms")
    col2.metric("Coût estimé (€)", f"{metrics['cost']} €")
    col3.metric("Impact écologique (gCO2)", f"{metrics['carbon_impact']} g")

    if st.session_state.metrics["total_queries"] == 0:
        st.warning(
            "Aucune donnée disponible pour le moment. Posez des questions pour générer des métriques."
        )
        return

    st.subheader("📊 Visualisation des métriques")

    col1, col2 = st.columns(2)

    with col1:
        if st.session_state.metrics["latency_history"]:
            fig1 = px.line(
                x=list(range(1, len(st.session_state.metrics["latency_history"]) + 1)),
                y=st.session_state.metrics["latency_history"],
                labels={"x": "Numéro de la requête", "y": "Latence (ms)"},
                title="Latence par requête",
                color_discrete_sequence=["#1f8b4c"],
            )
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.warning(
                "🚨 Aucune donnée de latence disponible pour générer le graphique."
            )

    with col2:
        if st.session_state.metrics["cost_history"]:
            fig2 = px.line(
                x=list(range(1, len(st.session_state.metrics["cost_history"]) + 1)),
                y=st.session_state.metrics["cost_history"],
                labels={"x": "Numéro de la requête", "y": "Coût (€)"},
                title="Coût cumulé des requêtes",
                color_discrete_sequence=["#1f8b4c"],
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.warning("🚨 Aucune donnée de coût disponible pour générer le graphique.")
