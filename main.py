import streamlit as st
import json
import os
import hashlib
import io
import time
import base64
from google import genai
from google.genai import types
from PIL import Image
from gtts import gTTS
from fpdf import FPDF

# --- 1. DATA STORAGE ---
DB_FILE = "users_db.json"

def load_db():
    if not os.path.exists(DB_FILE):
        # Default Admin is the only Pro by default
        db = {"admin": {"pass": hashlib.sha256("taha123".encode()).hexdigest(), "is_pro": True}}
        with open(DB_FILE, "w") as f: json.dump(db, f)
        return db
    with open(DB_FILE, "r") as f: return json.load(f)

def save_db(db):
    with open(DB_FILE, "w") as f: json.dump(db, f)

def get_audio_html(text):
    tts = gTTS(text=text, lang='en')
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    audio_b64 = base64.b64encode(fp.read()).decode()
    return f'<audio autoplay src="data:audio/mp3;base64,{audio_b64}">'

# --- 2. PREMIUM WHITE UI DESIGN ---
st.set_page_config(page_title="TahaGpt V3.1", page_icon="🚀", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #ffffff; color: #000000; }
    [data-testid="stSidebar"] { background-color: #f8f9fa !important; border-right: 1px solid #eeeeee; }
    .auth-card {
        background: #ffffff; padding: 40px; border-radius: 20px;
        border: 1px solid #eeeeee; box-shadow: 0 10px 30px rgba(0,0,0,0.05);
        text-align: center; color: #000;
    }
    .pro-tag {
        background: linear-gradient(90deg, #FFD700, #FFA500);
        color: black; padding: 5px 15px; border-radius: 50px;
        font-weight: bold; font-size: 14px; display: inline-block;
    }
    .stButton>button { border-radius: 10px !important; }
    .stChatMessage { background-color: #f7f7f8; border-radius: 15px; border: 1px solid #eee; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SESSION STATE ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "user_data" not in st.session_state: st.session_state.user_data = None
if "messages" not in st.session_state: st.session_state.messages = []
if "voice_enabled" not in st.session_state: st.session_state.voice_enabled = False

# --- 4. LOGIN / REGISTER UI ---
if not st.session_state.logged_in:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown('<div class="auth-card">', unsafe_allow_html=True)
        st.markdown("<h1 style='color:#000;'>TahaGpt V3.1</h1><p style='color:#666;'>Elite Intelligence</p>", unsafe_allow_html=True)
        
        tab_l, tab_r = st.tabs(["🔒 Login", "📝 Register"])
        db = load_db()
        
        with tab_l:
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.button("Sign In", use_container_width=True):
                hp = hashlib.sha256(p.encode()).hexdigest()
                if u in db and db[u]["pass"] == hp:
                    st.session_state.user_data = {"name": u, "is_pro": db[u].get("is_pro", False)}
                    st.session_state.logged_in = True
                    st.rerun()
                else: st.error("Invalid Credentials")

        with tab_r:
            new_u = st.text_input("Choose Username")
            new_p = st.text_input("Choose Password", type="password")
            if st.button("Create Account", use_container_width=True):
                if new_u and new_p:
                    # New accounts are NOT pro by default
                    db[new_u] = {"pass": hashlib.sha256(new_p.encode()).hexdigest(), "is_pro": False}
                    save_db(db); st.success("Account created successfully!")
        st.markdown('</div>', unsafe_allow_html=True)

# --- 5. MAIN APPLICATION ---
else:
    user = st.session_state.user_data["name"]
    is_pro = st.session_state.user_data["is_pro"]

    try:
        active_key = st.secrets["PRO_API_KEY"] if is_pro else st.secrets["FREE_API_KEY"]
        client = genai.Client(api_key=active_key)
    except:
        st.error("API Keys missing in Secrets.")
        st.stop()

    # --- SIDEBAR ---
    with st.sidebar:
        st.markdown(f"### 👤 {user}")
        if is_pro: 
            st.markdown('<span class="pro-tag">⭐ PRO</span>', unsafe_allow_html=True)
        
        st.divider()
        mode = st.radio("Menu", ["💬 Chat", "🎨 Art Studio", "📄 PDF Creator"])
        
        if mode == "💬 Chat":
            if is_pro:
                st.session_state.voice_enabled = st.toggle("🔊 Voice Response", value=st.session_state.voice_enabled)
            else:
                st.info("🔊 Voice is a Pro Feature")

        st.divider()
        if not is_pro:
            with st.expander("💎 Upgrade Account"):
                code = st.text_input("Promo Code")
                if st.button("Activate"):
                    if code == "TAHA2026":
                        db = load_db(); db[user]["is_pro"] = True; save_db(db)
                        st.session_state.user_data["is_pro"] = True
                        st.toast("🎉 PRO ACTIVATED!"); st.balloons()
                        time.sleep(1); st.rerun()
                if st.button("💳 Buy for 10 PKR"):
                    db = load_db(); db[user]["is_pro"] = True; save_db(db)
                    st.session_state.user_data["is_pro"] = True
                    st.toast("💳 Payment Successful!"); st.balloons()
                    time.sleep(1); st.rerun()

        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False; st.rerun()

    # --- CHAT & VOICE ---
    if mode == "💬 Chat":
        st.markdown(f"## Welcome to TahaGpt")
        for m in st.session_state.messages:
            with st.chat_message(m["role"]): st.markdown(m["content"])

        if prompt := st.chat_input("Message TahaGpt..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)

            try:
                # Use Flash for stability against 429 errors
                res = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
                ans = res.text
                st.session_state.messages.append({"role": "assistant", "content": ans})
                with st.chat_message("assistant"): 
                    st.markdown(ans)
                    if is_pro and st.session_state.voice_enabled:
                        st.markdown(get_audio_html(ans[:300]), unsafe_allow_html=True)
            except Exception as e:
                if "429" in str(e):
                    st.error("⚠️ Server Busy. Please retry in 10 seconds.")
                else:
                    st.error("An error occurred. Please try again.")

    # --- ART STUDIO ---
    elif mode == "🎨 Art Studio":
        st.header("🎨 AI Image Studio")
        desc = st.text_input("Describe the image:")
        if st.button("Generate"):
            with st.spinner("AI is drawing..."):
                try:
                    res = client.models.generate_content(
                        model='gemini-1.5-flash', 
                        contents=desc, 
                        config=types.GenerateContentConfig(response_modalities=["IMAGE"])
                    )
                    for part in res.candidates[0].content.parts:
                        if part.inline_data:
                            st.image(Image.open(io.BytesIO(part.inline_data.data)), use_container_width=True)
                except: st.error("Image limit reached. Retry in 1 minute.")

    # --- PDF CREATOR ---
    elif mode == "📄 PDF Creator":
        st.header("📄 PDF Document Export")
        if not is_pro: 
            st.warning("PDF Creator is for PRO members only.")
        else:
            pdf_title = st.text_input("Title")
            pdf_content = st.text_area("Content", height=300)
            if st.button("Download PDF"):
                pdf = FPDF()
                pdf.add_page(); pdf.set_font("Arial", 'B', 16)
                pdf.cell(40, 10, pdf_title); pdf.ln(20)
                pdf.set_font("Arial", size=12); pdf.multi_cell(0, 10, pdf_content)
                pdf_output = pdf.output(dest='S').encode('latin-1')
                st.download_button("📥 Save PDF", data=pdf_output, file_name=f"{pdf_title}.pdf", mime="application/pdf")
