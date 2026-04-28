import streamlit as st
import json
import os
import hashlib
from google import genai
from google.genai import types
from PIL import Image
import io

# --- 1. PERMANENT STORAGE SYSTEM ---
DB_FILE = "users_db.json"

def load_db():
    """Loads the user database from a JSON file."""
    if not os.path.exists(DB_FILE):
        # Default Admin Account: Username 'admin', Password 'taha123'
        initial_db = {"admin": {"pass": hashlib.sha256("taha123".encode()).hexdigest(), "is_pro": True}}
        with open(DB_FILE, "w") as f:
            json.dump(initial_db, f)
        return initial_db
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(db):
    """Saves the user database to the JSON file."""
    with open(DB_FILE, "w") as f:
        json.dump(db, f)

def hash_pass(password):
    """Encrypts passwords for security."""
    return hashlib.sha256(password.encode()).hexdigest()

# --- 2. PAGE CONFIG & STYLING ---
st.set_page_config(page_title="TahaGpt Pro V2", page_icon="🚀", layout="wide")

st.markdown("""
    <style>
        .stApp { background-color: #ffffff; color: #000; }
        [data-testid="stSidebar"] { background-color: #f8f9fa !important; border-right: 1px solid #eee; }
        .auth-box { 
            background: #f9f9f9; padding: 30px; border-radius: 15px; 
            border: 1px solid #eee; box-shadow: 0px 4px 10px rgba(0,0,0,0.05);
        }
        .pro-header {
            background: linear-gradient(90deg, #FFD700, #FFFACD);
            color: #000; padding: 10px; border-radius: 8px;
            text-align: center; font-weight: bold; margin-bottom: 20px; border: 1px solid #E6B800;
        }
        .main-title { text-align: center; font-size: 40px; font-weight: bold; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SESSION STATE INITIALIZATION ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_data" not in st.session_state:
    st.session_state.user_data = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "page_selection" not in st.session_state:
    st.session_state.page_selection = "💬 Chatbot"

# --- 4. AUTHENTICATION LOGIC ---
def show_auth_page():
    st.markdown("<div class='main-title'>TahaGpt Access</div>", unsafe_allow_html=True)
    db = load_db()
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown('<div class="auth-box">', unsafe_allow_html=True)
        auth_tab1, auth_tab2 = st.tabs(["🔑 Login", "📝 Sign Up"])
        
        with auth_tab1:
            u = st.text_input("Username", key="l_user")
            p = st.text_input("Password", type="password", key="l_pass")
            if st.button("Login", use_container_width=True):
                hp = hash_pass(p)
                if u in db and db[u]["pass"] == hp:
                    st.session_state.user_data = {"name": u, "is_pro": db[u].get("is_pro", False)}
                    st.session_state.logged_in = True
                    st.success(f"Welcome, {u}!")
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
                    
        with auth_tab2:
            new_u = st.text_input("New Username", key="r_user")
            new_p = st.text_input("New Password", type="password", key="r_pass")
            if st.button("Create Account", use_container_width=True):
                if new_u and new_p:
                    if new_u in db:
                        st.warning("Username already exists!")
                    else:
                        db[new_u] = {"pass": hash_pass(new_p), "is_pro": False}
                        save_db(db)
                        st.success("Account created! Please log in.")
                else:
                    st.error("Please fill in all fields.")
        st.markdown('</div>', unsafe_allow_html=True)

# --- 5. MAIN APP LOGIC ---
if not st.session_state.logged_in:
    show_auth_page()
else:
    # Safe access to user data
    user_name = st.session_state.user_data["name"]
    is_pro = st.session_state.user_data["is_pro"]

    # API Setup
    if "GEMINI_API_KEY" not in st.secrets:
        st.error("Missing GEMINI_API_KEY in Secrets!")
        st.stop()
    
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    TAHA_IDENTITY = f"Your name is TahaGpt. Created by M. Taha Farooq for {user_name}."

    # --- SIDEBAR ---
    with st.sidebar:
        st.markdown(f"### 👤 {user_name}")
        if is_pro: st.markdown("⭐ **PRO MEMBER**")
        
        if st.button("➕ New Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

        st.divider()
        st.session_state.page_selection = st.radio("Navigation", ["💬 Chatbot", "🎨 Pic Generate", "🖼️ See & Explain"])
        
        st.divider()
        if not is_pro:
            with st.expander("💎 Upgrade to Pro"):
                promo = st.text_input("Promo Code")
                if st.button("Activate"):
                    if promo == "TAHA2026":
                        db = load_db()
                        db[user_name]["is_pro"] = True
                        save_db(db)
                        st.session_state.user_data["is_pro"] = True
                        st.success("Pro Activated!")
                        st.rerun()
                    else:
                        st.error("Invalid Code")
        
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user_data = None
            st.rerun()

    # --- HEADER ---
    if is_pro:
        st.markdown('<div class="pro-header">✨ TAHA GPT PRO ACTIVE ✨</div>', unsafe_allow_html=True)
    else:
        st.markdown("<h2 style='text-align: center;'>TahaGpt</h2>", unsafe_allow_html=True)

    # --- PAGE ROUTING ---
    
    # 1. CHATBOT MODE
    if st.session_state.page_selection == "💬 Chatbot":
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])
        
        if prompt := st.chat_input("Message TahaGpt..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            
            try:
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    config=types.GenerateContentConfig(system_instruction=TAHA_IDENTITY),
                    contents=prompt
                )
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                with st.chat_message("assistant"): st.markdown(response.text)
            except Exception as e:
                st.error(f"AI Error: {e}")

    # 2. IMAGE GENERATION
    elif st.session_state.page_selection == "🎨 Pic Generate":
        st.header("🎨 AI Image Studio")
        p = st.text_input("Describe the image you want to create:")
        if st.button("Generate Image"):
            with st.spinner("AI is painting..."):
                try:
                    res = client.models.generate_content(
                        model='gemini-2.0-flash', 
                        contents=p, 
                        config=types.GenerateContentConfig(response_modalities=["IMAGE"])
                    )
                    for part in res.candidates[0].content.parts:
                        if part.inline_data: 
                            st.image(Image.open(io.BytesIO(part.inline_data.data)), use_container_width=True)
                except Exception as e:
                    st.info("Image generation might require specific model permissions or a different model name depending on your API tier.")

    # 3. VISION MODE
    elif st.session_state.page_selection == "🖼️ See & Explain":
        st.header("🖼️ Vision Intelligence")
        uploaded_file = st.file_uploader("Upload an image", type=["jpg", "jpeg", "png"])
        if uploaded_file:
            img = Image.open(uploaded_file)
            st.image(img, caption="Uploaded Image", width=500)
            if st.button("Analyze Image"):
                with st.spinner("Analyzing..."):
                    res = client.models.generate_content(
                        model="gemini-2.0-flash", 
                        contents=["Explain this image in detail and tell me what you see.", img]
                    )
                    st.write(res.text)
