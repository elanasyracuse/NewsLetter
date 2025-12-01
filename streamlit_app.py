import streamlit as st

st.set_page_config(page_title="🧪 Multipage Labs", page_icon="🧪", layout="centered")

old = st.Page("standalone.py", icon="📘", title="News Letters")

new = st.Page("app.py", title="Medical RAG Chatbot", icon="🧬", default=True)

nav = st.navigation({"Labs": [old,new]})
nav.run()
