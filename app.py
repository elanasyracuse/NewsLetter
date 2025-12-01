# app.py

import streamlit as st
from typing import List, Dict
from backend import get_top_papers, get_knowledge_graph, get_db_stats
from email_utils import send_email_with_papers
from pyvis.network import Network
import streamlit.components.v1 as components

# ---- Helpers ----

from pyvis.network import Network

def build_graph_html(graph_data: Dict) -> str:
    net = Network(height="600px", width="100%", bgcolor="#ffffff", directed=True)

    for node in graph_data["nodes"]:
        net.add_node(
            node["id"],
            label=node.get("title", node["id"]),
            title=node.get("label", ""),
            color="#1976d2" if node.get("label") == "paper" else "#43a047",
        )

    for edge in graph_data["edges"]:
        net.add_edge(edge["source"], edge["target"], title=edge.get("relation", ""))

    net.toggle_physics(True)

    # IMPORTANT CHANGE: no net.show("graph.html")
    html = net.generate_html()
    return html

@st.dialog("Send Top 5 Papers")
def email_dialog(papers: List[Dict]):
    st.write("Enter your email to receive the top 5 papers.")
    email = st.text_input("Email address")
    if st.button("Send email"):
        if not email:
            st.error("Please enter a valid email.")
        else:
            try:
                send_email_with_papers(email, papers)
                st.success("Email sent successfully!")
            except Exception as e:
                st.error(f"Failed to send email: {e}")


# ---- UI Layout ----

st.title("Medical Research RAG Chatbot – UI Demo")

# Optional DB stats sidebar
with st.sidebar:
    st.header("Database status")
    try:
        stats = get_db_stats()
        st.metric("Total papers", stats["total_papers"])
        st.metric("Processed papers", stats["processed_papers"])
        st.metric("With embeddings", stats["papers_with_embeddings"])
    except Exception:
        st.info("Stats unavailable")

# Main query input
user_query = st.text_input("Ask about medical research:", "")

# Placeholder for chatbot response (your group can wire real RAG here)
if st.button("Ask Chatbot"):
    if not user_query:
        st.warning("Please enter a question.")
    else:
        st.info("Chatbot answer will appear here once backend is wired in.")

st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Knowledge Graph")
    if st.button("Show Knowledge Graph"):
        if not user_query:
            st.warning("Enter a query first.")
        else:
            graph_data = get_knowledge_graph(user_query)
            html = build_graph_html(graph_data)
            components.html(html, height=600, scrolling=True)

with col2:
    st.subheader("Email Top 5 Papers")
    if st.button("Email Top 5 Papers"):
        if not user_query:
            st.warning("Enter a query first.")
        else:
            papers = get_top_papers(user_query, k=5)
            if not papers:
                st.warning("No papers found for this query.")
            else:
                # Preview in UI
                for i, p in enumerate(papers, start=1):
                    st.markdown(f"**{i}. {p.get('title', 'Untitled')}**")
                # Open dialog to collect email and send
                email_dialog(papers)
