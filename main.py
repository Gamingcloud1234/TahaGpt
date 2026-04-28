import streamlit as st
import json
import os
import hashlib
from google import genai
from google.genai import types
from PIL import Image
import io
import time

# --- 1. STORAGE SYSTEM ---
DB_FILE = "users_db.json"

def load_db():
    if not os.path.exists(DB_FILE):
        initial_db = {"admin": {"pass": hashlib.sha256("taha123".encode()).hexdigest(), "is_pro": True}}
        with open(DB_FILE, "w") as f:
            json.dump(initial_db, f)
        return initial_db
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f)

def hash_pass(password):
    return hashlib.sha256(password.encode()).hexdigest()

# --- 2. PREMIUM UI CONFIG ---
st.set_page_config(page_title="TahaGpt V2.1 Pro", page_icon="💎", layout="wide")

st.markdown("""
    <style>
        /* Global Styles */
        .stApp { background-color: #ffffff; color: #1e1e1e; }
        
        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background-color: #f8f9fa !important;
            border-right: 1px solid #e0e0e0;
        }

        /* Pro Badge */
        .pro-badge {
            background: linear-gradient(45deg, #FFD700, #FFA500);
            color: black; padding: 4px 10px; border-radius: 20px;
            font-size: 12px; font-weight: bold; text-align: center;
        }

        /* Glassmorphism Auth Box */
        .auth-container {
            background: #ffffff; padding: 40px; border-radius: 20px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.05);
            border: 1px solid #f0f0f0;
        }

        /* Pro Header */
        .pro-banner {
            background: linear-gradient(90deg, #1a1a1a, #434343);
            color: #FFD700; padding: 15px; border-radius: 12px;
            text-align: center; font-weight: bold; margin-bottom: 25px;
            border: 1px solid #FFD700; box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }
        
        /* Buttons */
        .stButton>button { border-radius: 8px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SESSION INITIALIZATION ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "user_data" not in st.session_state: st.session_state.user_data = None
if "messages" not in st.session_state: st.session_state.messages = []

# --- 4. AUTH PAGE ---
def show_auth():
    st.markdown("<h1 style='text-align: center; color: #1a1a1a;'>TahaGpt <span style='color:#FFD700'>Pro</span></h1>", unsafe_allow_html=True)
    db = load_db()
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown('<div class="auth-container">', unsafe_allow_html=True)
        t1, t2 = st.tabs(["Login", "Create Account"])
        with t1:
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.button("Sign In", use_container_width=True):
                if u in db and db[u]["pass"] == hash_pass(p):
                    st.session_state.user_data = {"name": u, "is_pro": db[u].get("is_pro", False)}
                    st.session_state.logged_in = True
                    st.rerun()
                else: st.error("Incorrect details.")
        with t2:
            new_u = st.text_input("New User")
            new_p = st.text_input("New Pass", type="password")
            if st.button("Register", use_container_width=True):
                if new_u and new_p:
                    db[new_u] = {"pass": hash_pass(new_p), "is_pro": False}
                    save_db(db)
                    st.success("Success! Please Login.")
        st.markdown('</div>', unsafe_allow_html=True)

# --- 5. MAIN APP ---
if not st.session_state.logged_in:
    show_auth()
else:
    user = st.session_state.user_data["name"]
    is_pro = st.session_state.user_data["is_pro"]
    
    # API Connect
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    
    # --- SIDEBAR UI ---
    with st.sidebar:
        st.markdown(f"## Welcome, {user}")
        if is_pro: st.markdown('<div class="pro-badge">PRO MEMBER</div>', unsafe_allow_html=True)
        else: st.info("Standard Account")
        
        st.divider()
        menu = st.radio("Features", ["💬 Smart Chat", "🎨 Art Studio", "🔍 Vision AI"])
        
        # PRO SPECIAL FEATURE ACCESS
        if is_pro:
            st.divider()
            st.markdown("### 💎 Pro Tools")
            pro_tool = st.selectbox("Switch AI Mode", ["Normal Mode", "Deep Research", "Code Architect"])
            if st.button("🚀 Clear Memory"):
                st.session_state.messages = []
                st.rerun()

        st.divider()
        # MEMBERSHIP SECTION
        if not is_pro:
            with st.expander("⭐ GET PRO"):
                st.write("Unlock Smart AI & Images")
                promo = st.text_input("Promo Code")
                if st.button("Apply Code"):
                    if promo == "TAHA2026":
                        db = load_db(); db[user]["is_pro"] = True; save_db(db)
                        st.session_state.user_data["is_pro"] = True
                        st.balloons(); st.rerun()
                
                st.write("--- OR ---")
                if st.button("💳 Buy for 10 PKR"):
                    st.warning("Redirecting to secure payment... (Simulated)")
                    time.sleep(2)
                    db = load_db(); db[user]["is_pro"] = True; save_db(db)
                    st.session_state.user_data["is_pro"] = True
                    st.rerun()

        if st.button("🚪 Logout"):
            st.session_state.logged_in = False
            st.rerun()

    # --- CONTENT AREA ---
    if is_pro:
        st.markdown('<div class="pro-banner">PREMIUM AI UNLOCKED • NO LIMITS</div>', unsafe_allow_html=True)
    
    # 1. CHAT LOGIC
    if menu == "💬 Smart Chat":
        # Pro users get the smarter Pro model, others get Flash
        active_model = "gemini-1.5-pro" if is_pro else "gemini-1.5-flash"
        
        for m in st.session_state.messages:
            with st.chat_message(m["role"]): st.markdown(m["content"])
            
        if prompt := st.chat_input("Ask TahaGpt..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            
            try:
                with st.spinner("AI is typing..."):
                    res = client.models.generate_content(
                        model=active_model,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=f"You are TahaGpt. User is {user}. Level: {'Pro' if is_pro else 'Free'}"
                        )
                    )
                    st.session_state.messages.append({"role": "assistant", "content": res.text})
                    with st.chat_message("assistant"): st.markdown(res.text)
            except Exception as e:
                st.error("Server overloaded. Please wait 10s.")

    # 2. ART STUDIO
    elif menu == "🎨 Art Studio":
        st.header("🎨 AI Art Studio")
        if not is_pro: st.warning("Standard users have lower image quality. Upgrade to Pro for HD.")
        
        p = st.text_input("Describe the image...")
        if st.button("Create Masterpiece"):
            with st.spinner("Painting..."):
                try:
                    res = client.models.generate_content(
                        model='gemini-1.5-flash', # Or specific image model
                        contents=p,
                        config=types.GenerateContentConfig(response_modalities=["IMAGE"])
                    )
                    for part in res.candidates[0].content.parts:
                        if part.inline_data: st.image(Image.open(io.BytesIO(part.inline_data.data)))
                except: st.error("Image API is busy. Try again in 1 minute.")

    # 3. VISION
    elif menu == "🔍 Vision AI":
        st.header("🔍 Visual Intelligence")
        file = st.file_uploader("Upload Image", type=['png','jpg','jpeg'])
        if file:
            img = Image.open(file)
            st.image(img, width=400)
            if st.button("Analyze"):
                res = client.models.generate_content(model="gemini-1.5-flash", contents=["Analyze this", img])
                st.info(res.text)
