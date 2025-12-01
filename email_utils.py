# email_utils.py

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Dict
import streamlit as st  # to read st.secrets

def send_email_with_papers(recipient_email: str, papers: List[Dict]) -> None:
    """
    Sends an email listing the given papers (title + link).
    Uses SMTP settings from st.secrets['email'].
    """
    email_conf = st.secrets["email"]
    smtp_server = email_conf["SMTP_SERVER"]
    smtp_port = email_conf["SMTP_PORT"]
    smtp_user = email_conf["SMTP_USER"]
    smtp_password = email_conf["SMTP_PASSWORD"]
    sender_email = email_conf["SENDER_EMAIL"]

    subject = "Top research papers from RAG chatbot"
    # Build a simple HTML list of papers
    lines = []
    for i, p in enumerate(papers, start=1):
        arxiv_id = p.get("arxiv_id", "")
        title = p.get("title", "Untitled")
        url = f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else "#"
        lines.append(f"<p><b>{i}. {title}</b><br><a href='{url}'>{url}</a></p>")

    html_body = (
        "<html><body>"
        "<p>Here are your papers:</p>"
        + "".join(lines) +
        "<p>– RAG Chatbot</p>"
        "</body></html>"
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = recipient_email
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(sender_email, [recipient_email], msg.as_string())
