import streamlit as st
import json
import os
import hashlib
from google.genai import types
from google import genai
from PIL import Image
import io

# --- 1. PERMANENT STORAGE LOGIC ---
DB_FILE = "users_db.json"

def load_db():
    if not os.path.exists(DB_FILE):
        # Initial Admin Account
        return {"admin": {"pass": hashlib.sha256("taha123".encode()).hexdigest(), "is_pro": True}}
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f)

def hash_pass(password):
    return hashlib.sha256(password.encode()).hexdigest()

# --- 2. CONFIG & THEME ---
st.set_page_config(page_title="TahaGpt Pro V2", page_icon="🚀", layout="wide")

st.markdown("""
    <style>
        .stApp { background-color: #ffffff; color: #000; }
        .auth-box { 
            background: #f9f9f9; padding: 30px; border-radius: 15px; 
            border: 1px solid #eee; box-shadow: 0px 4px 10px rgba(0,0,0,0.05);
        }
        .pro-header {
            background: linear-gradient(90deg, #FFD700, #FFFACD);
            color: #000; padding: 10px; border-radius: 8px;
            text-align: center; font-weight: bold; margin-bottom: 20px;
        }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SESSION STATE ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_data" not in st.session_state:
    st.session_state.user_data = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "page" not in st.session_state:
    st.session_state.page = "Chat"

# --- 4. AUTHENTICATION SCREEN ---
def show_login_page():
    db = load_db()
    st.markdown("<h1 style='text-align: center;'>🚀 TahaGpt V2</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown('<div class="auth-box">', unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["🔑 Login", "📝 Sign Up"])
        
        with tab1:
            u = st.text_input("Username", key="login_u")
            p = st.text_input("Password", type="password", key="login_p")
            if st.button("Access TahaGpt", use_container_width=True):
                hp = hash_pass(p)
                if u in db and db[u]["pass"] == hp:
                    st.session_state.logged_in = True
                    st.session_state.user_data = {"name": u, "is_pro": db[u].get("is_pro", False)}
                    st.rerun()
                else:
                    st.error("Wrong username or password")
        
        with tab2:
            new_u = st.text_input("Choose Username", key="reg_u")
            new_p = st.text_input("Choose Password", type="password", key="reg_p")
            if st.button("Create Permanent Account", use_container_width=True):
                if new_u in db:
                    st.warning("User already exists!")
                elif len(new_u) < 3 or len(new_p) < 4:
                    st.error("Details too short!")
                else:
                    db[new_u] = {"pass": hash_pass(new_p), "is_pro": False}
                    save_db(db)
                    st.success("Account created! Go to Login tab.")
        st.markdown('</div>', unsafe_allow_html=True)

# --- 5. MAIN APP LOGIC ---
if not st.session_state.logged_in:
    show_login_page()
else:
    # Set Identity
    user_name = st.session_state.user_data["name"]
    is_pro = st.session_state.user_data["is_pro"]
    
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    TAHA_IDENTITY = f"Your name is TahaGpt. Created by M. Taha Farooq for {user_name}."

    # --- SIDEBAR ---
    with st.sidebar:
        st.title("TahaGpt V2")
        st.write(f"👤 User: **{user_name}**")
        if is_pro: st.write("🌟 Status: **PRO**")
        
        if st.button("➕ New Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

        st.divider()
        app_mode = st.radio("Menu", ["💬 Chatbot", "🎨 Pic Generate", "🖼️ See & Explain"])
        
        if not is_pro:
            promo = st.text_input("Activate Pro (Code)")
            if st.button("Upgrade"):
                if promo == "TAHA2026":
                    db = load_db()
                    db[user_name]["is_pro"] = True
                    save_db(db)
                    st.session_state.user_data["is_pro"] = True
                    st.rerun()
        
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()

    # --- PAGE ROUTING ---
    if is_pro:
        st.markdown('<div class="pro-header">✨ PRO ACCOUNT ACTIVE ✨</div>', unsafe_allow_html=True)

    if app_mode == "💬 Chatbot":
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])
        
        if prompt := st.chat_input("Ask TahaGpt..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            
            res = client.models.generate_content(
                model="gemini-2.0-flash", # Note: Using stable 2.0 flash
                config=types.GenerateContentConfig(system_instruction=TAHA_IDENTITY),
                contents=prompt
            )
            st.session_state.messages.append({"role": "assistant", "content": res.text})
            with st.chat_message("assistant"): st.markdown(res.text)

    elif app_mode == "🎨 Pic Generate":
        st.header("🎨 AI Image Studio")
        p = st.text_input("What should I draw?")
        if st.button("Generate"):
            with st.spinner("Drawing..."):
                try:
                    res = client.models.generate_content(
                        model='gemini-2.0-flash-exp', 
                        contents=p, 
                        config=types.GenerateContentConfig(response_modalities=["IMAGE"])
                    )
                    for part in res.candidates[0].content.parts:
                        if part.inline_data: 
                            st.image(Image.open(io.BytesIO(part.inline_data.data)))
                except Exception as e: st.error("Image generation is busy or requires a Pro tier API.")

    elif app_mode == "🖼️ See & Explain":
        st.header("🖼️ Vision AI")
        uploaded = st.file_uploader("Upload Image", type=['png', 'jpg', 'jpeg'])
        if uploaded:
            img = Image.open(uploaded)
            st.image(img, width=400)
            if st.button("Explain This"):
                res = client.models.generate_content(model="gemini-2.0-flash", contents=["Explain this image", img])
                st.write(res.text)
