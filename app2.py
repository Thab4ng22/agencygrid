
import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime
from fpdf import FPDF
from io import BytesIO
import plotly.express as px

# ----------------- CONFIG -----------------
st.set_page_config(page_title="AgencyGrid Premium", layout="wide")

# ----------------- CSS -----------------
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

# ----------------- HELPERS -----------------
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

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            plan TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def create_test_users():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    users = [
        ("starter_user", hash_password("starter123"), "starter@example.com", "Starter"),
        ("growth_user", hash_password("growth123"), "growth@example.com", "Growth"),
        ("scale_user", hash_password("scale123"), "scale@example.com", "Scale"),
        ("agencypro_user", hash_password("agencypro123"), "agencypro@example.com", "Agency Pro")
    ]
    for u in users:
        try:
            c.execute("INSERT INTO users (username, password_hash, email, plan) VALUES (?, ?, ?, ?)", u)
        except:
            pass
    conn.commit()
    conn.close()

# Uncomment for first run only:
#create_test_users()

# ----------------- LANDING -----------------
def landing():
    st.title("🚀 Run Your Business with Confidence")
    st.write("AgencyGrid gives founders, operators & agencies the AI insights and tools to scale.")

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

# ----------------- LOGIN -----------------
def login():
    st.sidebar.header("🔐 Login")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT password_hash, plan FROM users WHERE username=?", (username,))
        result = c.fetchone()
        conn.close()
        if result and hash_password(password) == result[0]:
            st.session_state.username = username
            st.session_state.plan = result[1]
            st.success(f"Welcome, {username}!")
            st.experimental_rerun()
        else:
            st.error("Invalid credentials")

def register():
    st.sidebar.header("📝 Register")
    username = st.sidebar.text_input("New Username")
    email = st.sidebar.text_input("Email")
    password = st.sidebar.text_input("New Password", type="password")
    confirm = st.sidebar.text_input("Confirm Password", type="password")
    plan = st.sidebar.selectbox("Choose Plan", ["Starter", "Growth", "Scale", "Agency Pro"])
    if st.sidebar.button("Register"):
        if password != confirm:
            st.error("Passwords do not match")
            return
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password_hash, email, plan) VALUES (?, ?, ?, ?)",
                      (username, hash_password(password), email, plan))
            conn.commit()
            st.success("Registration successful, please log in.")
        except sqlite3.IntegrityError:
            st.error("Username or email already exists")
        conn.close()

# ----------------- DASHBOARD -----------------
def dashboard():
    st.header(f"📊 Welcome, {st.session_state.username}!")
    st.subheader(f"Plan: {st.session_state.plan}")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Sales", "$50,000")
    col2.metric("Average Order", "$500")
    col3.metric("Transactions", "100")

    df = pd.DataFrame({
        "date": pd.date_range(datetime.today(), periods=30),
        "sales": [x*100 for x in range(30)]
    })
    st.plotly_chart(px.line(df, x="date", y="sales", title="Revenue Over Time"))

    if st.session_state.plan in ["Scale", "Agency Pro"]:
        contract_generator()

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

# ----------------- MAIN -----------------
init_db()

if "username" not in st.session_state:
    landing()
    login()
    register()
else:
    if st.sidebar.button("Log Out"):
        st.session_state.clear()
        st.experimental_rerun()
    dashboard()
