
# 🚀 AgencyGrid - Clean & Deployable Version
import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import stripe
import openai
from fpdf import FPDF
from io import BytesIO
from datetime import datetime, timedelta
import plotly.express as px
import random
from st_aggrid import AgGrid

st.set_page_config(page_title="AgencyGrid", layout="wide", page_icon="📊")

DB_FILE = "users.db"
STRIPE_API_KEY = st.secrets.get("STRIPE_API_KEY")
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY")

stripe.api_key = STRIPE_API_KEY
openai.api_key = OPENAI_API_KEY

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            plan TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agency_username TEXT,
            client_name TEXT,
            client_email TEXT,
            dashboard_title TEXT,
            notes TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def check_password(password, hashed):
    return hash_password(password) == hashed




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

def landing():
    st.title("📊 Welcome to AgencyGrid")
    st.markdown("""
    ## Run Your Business with Confidence
    AgencyGrid gives founders, operators & agencies the AI insights and tools to scale.

    ### 💼 Plans
    | Plan | Features | Monthly |
    |------|----------|---------|
    | Starter | Basic KPIs | $29 |
    | Growth | Advanced Reports | $79 |
    | Scale | Team Access | $149 |
    | Agency | White-Label, Clients, AI Writer, Contracts | Contact Us |
    """)
    st.image("https://images.unsplash.com/photo-1645023136774-cd91c64e8766", use_column_width=True)

def login():
    st.sidebar.header("🔐 Login")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT password_hash, plan, is_admin FROM users WHERE username=?", (username,))
        result = c.fetchone()
        conn.close()
        if result and check_password(password, result[0]):
            st.session_state.username = username
            st.session_state.plan = result[1]
            st.session_state.is_admin = bool(result[2])
            st.success("Login successful!")
            st.experimental_rerun()
        else:
            st.error("Invalid credentials.")

def register():
    st.sidebar.header("📝 Register")
    username = st.sidebar.text_input("New Username")
    email = st.sidebar.text_input("Email")
    password = st.sidebar.text_input("Password", type="password")
    confirm = st.sidebar.text_input("Confirm Password", type="password")
    plan = st.sidebar.selectbox("Plan", ["Starter", "Growth", "Scale", "Agency"])
    if st.sidebar.button("Register"):
        if password != confirm:
            st.error("Passwords do not match.")
            return
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        try:
            c.execute(
                "INSERT INTO users (username, password_hash, email, plan, is_admin) VALUES (?, ?, ?, ?, ?)",
                (username, hash_password(password), email, plan, 0)
            )
            conn.commit()
            st.success("Registration successful. Please login.")
        except sqlite3.IntegrityError:
            st.error("Username or email already exists.")
        conn.close()

@st.cache_data
def sample_data():
    base = datetime.now() - timedelta(days=30)
    products = ["Alpha Tee", "Beta Hat", "Gamma Shoes"]
    data = []
    for i in range(30):
        for p in products:
            data.append({
                "date": base + timedelta(days=i),
                "product": p,
                "sales": random.randint(5, 30),
                "revenue": random.randint(100, 900),
                "stock": random.randint(20, 100)
            })
    return pd.DataFrame(data)

def ai_overview(df):
    st.subheader("🤖 AI Business Insight")
    if st.button("Generate Insight"):
        summary = df.groupby("product").agg({"sales": "sum", "revenue": "sum", "stock": "mean"}).reset_index()
        prompt = f"Analyze this data and provide 3 insights:\n{summary.to_string(index=False)}"
        with st.spinner("Generating..."):
            res = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}]
            )
        st.success("AI Insight:")
        st.markdown(res.choices[0].message.content)

def inventory_section():
    df = sample_data()
    st.header("📦 Inventory Tracker")
    st.plotly_chart(px.line(df, x="date", y="revenue", color="product"))
    ai_overview(df)
    st.dataframe(df)

def client_dashboard():
    st.header("👤 Clients")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    with st.expander("Add Client"):
        cname = st.text_input("Client Name")
        cemail = st.text_input("Client Email")
        ctitle = st.text_input("Dashboard Title")
        cnotes = st.text_area("Notes")
        if st.button("Save Client"):
            c.execute(
                "INSERT INTO clients (agency_username, client_name, client_email, dashboard_title, notes) VALUES (?, ?, ?, ?, ?)",
                (st.session_state.username, cname, cemail, ctitle, cnotes)
            )
            conn.commit()
            st.success("Client saved.")
    c.execute("SELECT client_name, dashboard_title FROM clients WHERE agency_username=?", (st.session_state.username,))
    for name, title in c.fetchall():
        st.write(f"- **{name}**: {title}")
    conn.close()

if "username" not in st.session_state:
    landing()
    login()
    register()
    st.stop()

st.sidebar.success(f"Logged in as {st.session_state['username']} ({st.session_state['plan']})")
if st.sidebar.button("Log Out"):
    st.session_state.clear()
    st.experimental_rerun()

pages = ["AI Insights", "Inventory"]
if st.session_state.plan == "Agency" or st.session_state.is_admin:
    pages.insert(0, "Client Dashboards")

page = st.sidebar.radio("Navigation", pages)

if page == "Client Dashboards":
    client_dashboard()
elif page == "AI Insights":
    inventory_section()
elif page == "Inventory":
    inventory_section()
