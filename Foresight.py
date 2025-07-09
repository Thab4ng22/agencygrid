import streamlit as st
import pandas as pd
import sqlite3
import bcrypt
import stripe
import openai
from fpdf import FPDF
from io import BytesIO
import os
from datetime import datetime, timedelta
import plotly.express as px
import random
from st_aggrid import AgGrid

# ----------------- CONFIG -----------------
st.set_page_config(page_title="AgencyGrid", layout="wide", page_icon="📊")

DB_FILE = "users.db"
STRIPE_API_KEY = os.getenv("STRIPE_API_KEY", "sk_test_XXXXXXXXXXXXXXXXXXXXXXXX")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "sk-XXXXXXXXXXXXXXXXXXXXXXXX")

stripe.api_key = STRIPE_API_KEY
openai.api_key = OPENAI_API_KEY

# ----------------- INIT DB -----------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # Users table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            plan TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            stripe_customer_id TEXT
        )
    """)

    # Clients table
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

    # Admin stats log
    c.execute("""
        CREATE TABLE IF NOT EXISTS admin_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            username TEXT,
            action TEXT,
            detail TEXT
        )
    """)

    # Team members for Scale plan
    c.execute("""
        CREATE TABLE IF NOT EXISTS team_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_username TEXT,
            member_email TEXT,
            role TEXT
        )
    """)

    # White-label branding for Agency plan
    c.execute("""
        CREATE TABLE IF NOT EXISTS white_label (
            username TEXT PRIMARY KEY,
            logo BLOB,
            custom_name TEXT
        )
    """)

    conn.commit()
    conn.close()

init_db()

# ----------------- HELPERS -----------------
def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

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

def log_admin_action(username, action, detail):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO admin_stats (username, action, detail) VALUES (?, ?, ?)",
              (username, action, detail))
    conn.commit()
    conn.close()

def get_white_label(username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT logo, custom_name FROM white_label WHERE username=?", (username,))
    result = c.fetchone()
    conn.close()
    return result

# ----------------- LANDING PAGE -----------------
def landing():
    st.title("📊 Welcome to AgencyGrid")
    st.markdown("""
    ## Run Your Business with Confidence
    AgencyGrid gives founders, operators & agencies the AI insights and tools to scale.

    ### ⭐ Trusted by 10,000+ users
    - "AgencyGrid transformed our workflow."
    - "AI insights boosted our revenue."
    - "The dashboards are a game changer."

    ### 💼 Plans & Features

    | Plan | Features | Monthly |
    |------|----------|---------|
    | Starter | Basic KPIs, 1 integration | $29 |
    | Growth | Advanced reports, 3 integrations | $79 |
    | Scale | Team access, unlimited integrations | $149 |
    | Agency | White-label dashboard, client logins, AI writer, contracts | Contact Us |

    ---
    **Register or login to get started!**
    """)
    st.image("https://images.unsplash.com/photo-1645023136774-cd91c64e8766", use_column_width=True)

# ----------------- LOGIN / REGISTER -----------------
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
            st.session_state["username"] = username
            st.session_state["plan"] = result[1]
            st.session_state["is_admin"] = bool(result[2])
            st.success("Login successful")
            st.experimental_rerun()
        else:
            st.error("Invalid credentials")

def register():
    st.sidebar.header("📝 Register")
    username = st.sidebar.text_input("New Username")
    email = st.sidebar.text_input("Email")
    password = st.sidebar.text_input("New Password", type="password")
    confirm = st.sidebar.text_input("Confirm Password", type="password")
    plan = st.sidebar.selectbox("Choose Plan", ["Starter", "Growth", "Scale", "Agency"])
    if st.sidebar.button("Register"):
        if password != confirm:
            st.error("Passwords do not match")
            return
        try:
            customer = stripe.Customer.create(email=email, name=username)
            stripe_customer_id = customer.id
        except Exception as e:
            st.error(f"Stripe error: {e}")
            return

        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password_hash, email, plan, is_admin, stripe_customer_id) VALUES (?, ?, ?, ?, ?, ?)",
                      (username, hash_password(password), email, plan, 0, stripe_customer_id))
            conn.commit()
            st.success("Registration successful, please login")
        except sqlite3.IntegrityError:
            st.error("Username or email already exists")
        conn.close()

# ----------------- AI OVERVIEW & DATA -----------------
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
        prompt = f"Analyze this data and provide 3 strategic insights:\n{summary.to_string(index=False)}"
        with st.spinner("Thinking..."):
            res = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}]
            )
        st.success("Insight ready:")
        st.markdown(res.choices[0].message.content)

def inventory_section():
    df = sample_data()
    st.header("📦 Inventory Tracker")
    st.plotly_chart(px.line(df, x="date", y="revenue", color="product", title="Revenue by Product"))
    ai_overview(df)
    st.dataframe(df)

# ----------------- CLIENT DASHBOARD -----------------
def client_dashboard():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    st.header("👤 Clients")
    with st.expander("Add Client"):
        cname = st.text_input("Client Name")
        cemail = st.text_input("Client Email")
        ctitle = st.text_input("Dashboard Title")
        cnotes = st.text_area("Notes")
        if st.button("Save Client"):
            c.execute("INSERT INTO clients (agency_username, client_name, client_email, dashboard_title, notes) VALUES (?, ?, ?, ?, ?)",
                      (st.session_state.get("username"), cname, cemail, ctitle, cnotes))
            conn.commit()
            st.success("Client saved")
            log_admin_action(st.session_state.get("username"), "Add Client", cname)

        if cnotes:
            pdf = generate_pdf(cnotes)
            st.download_button("📄 Download Notes PDF", pdf, file_name="client_notes.pdf")

    c.execute("SELECT client_name, dashboard_title FROM clients WHERE agency_username=?", (st.session_state.get("username"),))
    for name, title in c.fetchall():
        st.write(f"- **{name}**: {title}")
    conn.close()

# ----------------- CONTRACT GENERATOR -----------------
def contract_generator():
    st.header("📄 Contract Generator")
    contract_type = st.selectbox("Contract Type", ["NDA", "Service Agreement", "Partnership Agreement"])
    key_terms = st.text_area("Key Terms / Details")
    if st.button("Generate Contract"):
        prompt = f"Draft a {contract_type} with the following details:\n{key_terms}"
        with st.spinner("Generating contract..."):
            res = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}]
            )
        contract_text = res.choices[0].message.content
        st.success("Contract ready:")
        st.text_area("Contract", contract_text, height=300)
        pdf = generate_pdf(contract_text)
        st.download_button("📄 Download Contract PDF", pdf, file_name=f"{contract_type}.pdf")

# ----------------- AI WRITER -----------------
def ai_writer():
    st.header("✍️ AI Writer Tool")
    use_case = st.selectbox("Use Case", ["Blog Post", "Social Media Post", "Proposal"])
    topic = st.text_input("Topic")
    details = st.text_area("Additional Details")
    if st.button("Generate Copy"):
        prompt = f"Write a {use_case} about '{topic}' with these details:\n{details}"
        with st.spinner("Writing..."):
            res = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}]
            )
        copy = res.choices[0].message.content
        st.success("Content ready:")
        st.text_area("AI Content", copy, height=300)
        pdf = generate_pdf(copy)
        st.download_button("📄 Download as PDF", pdf, file_name=f"{use_case.replace(' ', '_')}.pdf")
# ----------------- TEAM MANAGEMENT (Scale) -----------------
def team_management():
    st.header("👥 Team Management")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    with st.expander("Add Team Member"):
        member_email = st.text_input("Member Email")
        role = st.text_input("Role (e.g. Manager, Analyst)")
        if st.button("Add Member"):
            c.execute("INSERT INTO team_members (owner_username, member_email, role) VALUES (?, ?, ?)",
                      (st.session_state.get("username"), member_email, role))
            conn.commit()
            st.success("Team member added")

    st.subheader("Your Team Members")
    df = pd.read_sql_query(
        "SELECT id, member_email, role FROM team_members WHERE owner_username=?",
        conn, params=(st.session_state.get("username"),)
    )
    AgGrid(df)

    remove_id = st.number_input("Remove Member by ID", min_value=1, step=1)
    if st.button("Remove Member"):
        c.execute("DELETE FROM team_members WHERE id=? AND owner_username=?", (remove_id, st.session_state.get("username")))
        conn.commit()
        st.success("Team member removed")

    conn.close()

# ----------------- ADMIN USER MANAGER -----------------
def admin_user_manager():
    st.header("🔒 Admin: Manage Users")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    df = pd.read_sql_query("SELECT username, email, plan, is_admin FROM users", conn)
    AgGrid(df)

    username = st.text_input("Username to Delete")
    if st.button("Delete User"):
        c.execute("DELETE FROM users WHERE username=?", (username,))
        conn.commit()
        st.success(f"Deleted user: {username}")

    username = st.text_input("Username to Promote to Admin")
    if st.button("Promote to Admin"):
        c.execute("UPDATE users SET is_admin=1 WHERE username=?", (username,))
        conn.commit()
        st.success(f"Promoted {username} to admin")

    conn.close()

# ----------------- WHITE LABEL BRANDING (Agency) -----------------
def white_label_settings():
    st.header("🏷️ White-Label Branding")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    uploaded_logo = st.file_uploader("Upload Logo", type=["png", "jpg", "jpeg"])
    custom_name = st.text_input("Custom Dashboard Name")

    if st.button("Save Branding"):
        logo_bytes = uploaded_logo.read() if uploaded_logo else None
        c.execute("REPLACE INTO white_label (username, logo, custom_name) VALUES (?, ?, ?)",
                  (st.session_state.get("username"), logo_bytes, custom_name))
        conn.commit()
        st.success("Branding updated!")

    branding = get_white_label(st.session_state.get("username"))
    if branding and branding[0]:
        st.image(branding[0], caption="Your Logo", use_column_width=True)
    if branding and branding[1]:
        st.write(f"Custom Name: **{branding[1]}**")

    conn.close()

# ----------------- MAIN -----------------
if "username" not in st.session_state:
    landing()
    login()
    register()
    st.stop()

# Get white label if exists
branding = get_white_label(st.session_state.get("username")) if st.session_state.get("plan") == "Agency" else None

# Custom branding
custom_title = branding[1] if branding and branding[1] else "AgencyGrid"
st.sidebar.title(f"📊 {custom_title}")
if branding and branding[0]:
    st.sidebar.image(branding[0], use_column_width=True)

st.sidebar.success(f"Logged in as {st.session_state.get('username')} ({st.session_state.get('plan')})")

if st.sidebar.button("Log Out"):
    st.session_state.clear()
    st.experimental_rerun()

# Pages
pages = []
if st.session_state.get("plan") == "Agency":
    pages = ["Client Dashboards", "Contracts", "AI Writer", "White-Label", "AI Insights", "Inventory"]
elif st.session_state.get("plan") == "Scale":
    pages = ["Team Management", "AI Insights", "Inventory"]
else:
    pages = ["AI Insights", "Inventory"]

if st.session_state.get("is_admin"):
    pages.insert(0, "Admin Users")
    pages.insert(1, "Admin Dashboard")

page = st.sidebar.radio("Navigation", pages)

if page == "Client Dashboards":
    client_dashboard()
elif page == "Contracts":
    contract_generator()
elif page == "AI Writer":
    ai_writer()
elif page == "White-Label":
    white_label_settings()
elif page == "Team Management":
    team_management()
elif page == "AI Insights":
    inventory_section()
elif page == "Inventory":
    inventory_section()
elif page == "Admin Dashboard":
    admin_dashboard()
elif page == "Admin Users":
    admin_user_manager()
