
import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime, timedelta
from fpdf import FPDF
from io import BytesIO
import plotly.express as px

st.set_page_config(page_title="AgencyGrid Premium", layout="wide")
st.markdown("""
<style>
body {
    font-family: 'Poppins', sans-serif;
}
h1, h2, h3 {
    font-weight: 600;
}
.stButton > button {
    background-color: #0052cc;
    color: white;
    padding: 0.75rem 1.5rem;
    border: none;
    border-radius: 5px;
}
.stButton > button:hover {
    background-color: #003f99;
}
.stMetric {
    background: #f9fafb;
    border-radius: 8px;
    padding: 1rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.1);
}
</style>
""", unsafe_allow_html=True)

DB_FILE = "users.db"

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def generate_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for line in text.split('\n'):
        pdf.cell(200, 10, txt=line, ln=True, align='L')
    output = BytesIO()
    output.write(pdf.output(dest='S').encode('latin1'))
    output.seek(0)
    return output

def create_test_users():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    users = [
        ("starter_user", "starter@example.com", hash_password("starter123"), "Starter"),
        ("growth_user", "growth@example.com", hash_password("growth123"), "Growth"),
        ("scale_user", "scale@example.com", hash_password("scale123"), "Scale"),
        ("agencypro_user", "agencypro@example.com", hash_password("agencypro123"), "Agency Pro")
    ]
    for u in users:
        try:
            c.execute("INSERT INTO users (username, password_hash, email, plan) VALUES (?, ?, ?, ?)", u)
        except:
            pass
    conn.commit()
    conn.close()

#create_test_users()


def landing():
    st.markdown("""
    <h1 style='text-align: center;'>Run Your Business with Confidence</h1>
    <p style='text-align: center;'>AgencyGrid gives founders, operators & agencies the AI insights and tools to scale.</p>
    """, unsafe_allow_html=True)

    if st.button("🚀 Get Started"):
        st.session_state.show_login = True

    st.markdown("""
    ### ⭐️ 10,000+ people use AgencyGrid
    > “AgencyGrid transformed our workflow.” — John S.
    > “AI insights boosted our revenue.” — Lisa M.
    > “The dashboards are a game changer.” — Mark T.

    ### 💼 Pricing Plans
    | Plan | Features | Monthly |
    |------|----------|---------|
    | Starter | Basic KPIs | $29 |
    | Growth | Advanced reports, 3 Integrations | $79 |
    | Scale | Team access, Unlimited Integrations, Contract Generator | $149 |
    | Agency Pro | White-label dashboard, Client Logins, All Features | Contact Us |
    """)



def contract_generator():
    st.header("📄 Contract Generator")
    client_name = st.text_input("Client Name")
    project_title = st.text_input("Project Title")
    project_fee = st.text_input("Project Fee")
    terms = st.text_area("Terms and Conditions")
    signer_name = st.text_input("Signer Full Name")

    if st.button("Generate Contract PDF"):
        contract_text = f"""
        CONTRACT AGREEMENT

        Client: {client_name}
        Project: {project_title}
        Fee: {project_fee}

        Terms:
        {terms}

        Signed by: {signer_name}
        Date: {datetime.now().strftime('%Y-%m-%d')}
        """
        pdf = generate_pdf(contract_text)
        st.download_button("Download Contract PDF", data=pdf, file_name="contract.pdf")

