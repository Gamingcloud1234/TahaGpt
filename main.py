import streamlit as st
from google import genai
from google.genai import types
from openai import OpenAI
from PIL import Image
import io
import zipfile
import os

# --- 1. PREMIUM WHITE & COMPACT UI THEME ---
st.set_page_config(page_title="Fenix Pro", page_icon="🔥", layout="wide")

st.markdown("""
    <style>
        /* Global App Reset */
        .stApp { background-color: #ffffff !important; color: #000000 !important; }
        [data-testid="stSidebar"] { background-color: #f8f9fa !important; border-right: 1px solid #eeeeee; }
        
        /* Input & Elements styling */
        .stChatInput { border-radius: 24px !important; border: 1px solid #e0e0e0 !important; }
        .stChatMessage { background-color: #f7f7f8; border-radius: 16px; margin-bottom: 12px; padding: 15px; }
        
        /* Premium Badges & Headers */
        .pro-header {
            background: linear-gradient(135deg, #FFD700, #FFA500);
            color: #000; padding: 10px; border-radius: 12px;
            text-align: center; font-weight: 800; font-size: 16px;
            margin-bottom: 20px; box-shadow: 0px 4px 10px rgba(255, 215, 0, 0.2);
        }
        .normal-header { text-align: center; font-size: 32px; font-weight: 800; margin-bottom: 20px; color: #ff4b4b; letter-spacing: -1px; }
        .pro-item-text { color: #B8860B; font-weight: bold; font-size: 14px; margin-top: 10px; }
        
        /* Utility styles */
        .stFileUploader { border: 1px dashed #cccccc !important; border-radius: 12px; background-color: #fafafa; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SESSION STATE MANAGEMENT ---
if "users" not in st.session_state: st.session_state.users = {"admin": "taha123"}  
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "current_user" not in st.session_state: st.session_state.current_user = ""
if "is_pro" not in st.session_state: st.session_state.is_pro = False
if "messages" not in st.session_state: st.session_state.messages = []
if "page" not in st.session_state: st.session_state.page = "Chat"
if "last_qa_text" not in st.session_state: st.session_state.last_qa_text = ""

# --- 3. AUTHENTICATION PAGES ---
def show_auth_page():
    st.markdown("<div class='normal-header'>Fenix Access</div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        auth_tab1, auth_tab2 = st.tabs(["🔑 Login", "📝 Register"])
        with auth_tab1:
            u = st.text_input("Username", key="l_user")
            p = st.text_input("Password", type="password", key="l_pass")
            if st.button("Login", use_container_width=True):
                if u in st.session_state.users and st.session_state.users[u] == p:
                    st.session_state.logged_in = True
                    st.session_state.current_user = u
                    st.success(f"Welcome back, {u}!")
                    st.rerun()
                else: st.error("Invalid Username or Password")
        with auth_tab2:
            new_u = st.text_input("Choose Username", key="r_user")
            new_p = st.text_input("Choose Password", type="password", key="r_pass")
            if st.button("Create Account", use_container_width=True):
                if new_u and new_p:
                    if new_u in st.session_state.users: st.warning("Username already exists!")
                    else:
                        st.session_state.users[new_u] = new_p
                        st.success("Account created! Please login.")
                else: st.error("Please fill all fields.")

# --- 4. MAIN PROGRAM CONTROLLER ---
if not st.session_state.logged_in:
    show_auth_page()
else:
    # --- CROSS-COMPATIBLE CLIENT FACTORY ---
    gemini_available = "GEMINI_API_KEY" in st.secrets
    openai_available = "OPENAI_API_KEY" in st.secrets

    if not gemini_available and not openai_available:
        st.error("⚠️ CRITICAL ERROR: No API credentials found. Please configure GEMINI_API_KEY or OPENAI_API_KEY inside your Streamlit secrets.")
        st.stop()

    gemini_client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"]) if gemini_available else None
    openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"]) if openai_available else None
    
    FENIX_IDENTITY = f"Your name is Fenix. You are a brilliant, elite AI system. Created by M. Taha Farooq for your user, {st.session_state.current_user}."

    # --- SIDEBAR DESIGNS ---
    with st.sidebar:
        try: st.image("https://raw.githubusercontent.com/Gamingcloud1234/TahaGpt/main/Taha.jpeg", width=90)
        except: st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=80)
        
        st.markdown(f"👤 Active: **{st.session_state.current_user}**")
        if st.button("➕ Clean New Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.last_qa_text = ""
            st.session_state.page = "Chat"
            st.rerun()
        
        st.divider()
        app_mode = st.radio("Main Navigation", ["💬 Chatbot Ecosystem", "🎨 Digital Painter", "🖼️ Sight Intelligence"])
        if "Chatbot" in app_mode: st.session_state.page = "Chat"
        elif "Painter" in app_mode: st.session_state.page = "Draw"
        elif "Sight" in app_mode: st.session_state.page = "See"

        st.divider()
        
        # --- MODEL SELECTOR (DUAL ECOSYSTEM) ---
        st.markdown("### 🤖 Brain Engine Ecosystem")
        models_list = []
        if gemini_available: models_list += ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"]
        if openai_available: models_list += ["gpt-4o-mini", "gpt-4o"]
        
        selected_model = st.selectbox("Active Brain Core", models_list, index=0)
        is_openai_selected = selected_model.startswith("gpt-")

        # --- DYNAMIC DOWNLOAD ZIP GENERATOR IN SIDEBAR ---
        if st.session_state.last_qa_text:
            st.divider()
            st.markdown("### 🗂️ Export Package Available")
            
            # Setup dynamic zip compilation in binary stream
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                zip_file.writestr("fenix_qa_output.txt", st.session_state.last_qa_text)
            zip_buffer.seek(0)
            
            st.download_button(
                label="📥 Download last QA (.zip)",
                data=zip_buffer,
                file_name="fenix_packaged_output.zip",
                mime="application/zip",
                use_container_width=True
            )

        st.divider()
        st.caption("🔥 Fenix Ecosystem | Karachi 2026")

        # --- PRO MEMBERSHIP UTILITIES ---
        if not st.session_state.is_pro:
            with st.expander("💎 Upgrade to Fenix Pro"):
                promo = st.text_input("Promo Code", key="promo_input")
                if st.button("Validate Access", use_container_width=True):
                    if promo == "TAHA2026":
                        st.session_state.is_pro = True
                        st.rerun()
                    else: st.error("Code unauthorized")
                st.write("--- OR ---")
                st.button("💳 Purchase Access (100 PKR)", use_container_width=True)
        else:
            st.markdown("<p class='pro-item-text'>💎 Unlocked Modules</p>", unsafe_allow_html=True)
            if st.button("📄 Pro Document Engine", use_container_width=True):
                st.session_state.page = "PDF_Mode"; st.rerun()
            if st.button("💻 Automated Coding Lab", use_container_width=True):
                st.session_state.page = "Code_Mode"; st.rerun()
            if st.button("❌ Core Downgrade", use_container_width=True):
                st.session_state.is_pro = False; st.rerun()

        st.divider()
        if st.button("🚪 Leave Session", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.current_user = ""
            st.rerun()

    # --- TOP INTERFACE HEADER ---
    if st.session_state.is_pro:
        st.markdown('<div class="pro-header">✨ FENIX ELITE ARCHITECTURE PRO ✨</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="normal-header">Fenix Architecture</div>', unsafe_allow_html=True)

    # --- ROUTING ENGINE ---
    if st.session_state.page == "PDF_Mode":
        st.header("📄 Pro: Structured Document Factory")
        content = st.text_area("Write plaintext to compile into document structure:", height=200)
        if st.button("Compile Document"): st.success("Document framework processed.")

    elif st.session_state.page == "Code_Mode":
        st.header("💻 Pro: Advanced Coding Lab")
        lang = st.selectbox("Target Stack", ["Python", "JavaScript", "HTML/CSS", "Minecraft Skript"])
        query = st.text_input("Technical prompt specifications:")
        if st.button("Execute Code Synthesis"):
            with st.spinner("Synthesizing logic layers..."):
                try:
                    if is_openai_selected:
                        res = openai_client.chat.completions.create(
                            model=selected_model,
                            messages=[{"role": "system", "content": FENIX_IDENTITY}, {"role": "user", "content": f"Write {lang} code for: {query}"}]
                        )
                        output_text = res.choices[0].message.content
                    else:
                        res = gemini_client.models.generate_content(model=selected_model, contents=f"Write {lang} code for: {query}")
                        output_text = res.text
                    st.code(output_text, language=lang.lower())
                except Exception as e: st.error(f"Synthesis failed: {e}")

    elif st.session_state.page == "Chat":
        # Render Past Messages
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])
        
        # --- UNIVERSAL ACCESSIBILITY FILE HUB BUTTON (+) ---
        with st.expander("➕ Attach Media, Scripts, Documentations or ZIP archives to context"):
            uploaded_files = st.file_uploader("Drop elements into memory pipeline:", accept_multiple_files=True, type=["jpg", "jpeg", "png", "txt", "py", "pdf", "zip"])
            context_payload = ""
            
            if uploaded_files:
                for file in uploaded_files:
                    if file.name.endswith(".zip"):
                        try:
                            with zipfile.ZipFile(file) as z:
                                context_payload += f"\n[Contents extracted from attached Archive: {file.name}]\n"
                                for name in z.namelist():
                                    if not name.endswith('/'): # Ignore root folders
                                        with z.open(name) as f:
                                            context_payload += f"--- File: {name} ---\n{f.read().decode('utf-8', errors='ignore')}\n"
                            st.success(f"Successfully processed archive: {file.name}")
                        except Exception as zip_err:
                            st.error(f"Could not fully extract contents from {file.name}: {zip_err}")
                    elif file.name.endswith((".txt", ".py")):
                        context_payload += f"\n[Attached Code/Script Content from {file.name}]:\n{file.read().decode('utf-8', errors='ignore')}\n"
                        st.success(f"Loaded textual file data: {file.name}")
                    else:
                        st.info(f"Loaded asset item: {file.name} (Ready for structural pipeline inspection)")

        # Main Chat Field Interaction
        if prompt := st.chat_input("Dispatch query instructions..."):
            if context_payload:
                prompt = f"{context_payload}\n\n[User Command Instructions]: {prompt}"
                
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            
            with st.spinner("Retrieving model answers..."):
                try:
                    if is_openai_selected:
                        response = openai_client.chat.completions.create(
                            model=selected_model,
                            messages=[{"role": "system", "content": FENIX_IDENTITY}, {"role": "user", "content": prompt}]
                        )
                        bot_response = response.choices[0].message.content
                    else:
                        response = gemini_client.models.generate_content(
                            model=selected_model,
                            config=types.GenerateContentConfig(system_instruction=FENIX_IDENTITY),
                            contents=prompt
                        )
                        bot_response = response.text
                        
                    with st.chat_message("assistant"): st.markdown(bot_response)
                    st.session_state.messages.append({"role": "assistant", "content": bot_response})
                    
                    # Core check: Pack tracking log matrix if user requests automation output packaging
                    trigger_words = ["zip", "save as zip", "convert to zip", "compress this"]
                    if any(word in prompt.lower() for word in trigger_words):
                        st.session_state.last_qa_text = f"--- CHAT LOG ARCHIVE ---\nUser:\n{prompt}\n\nFenix Brain Output:\n{bot_response}"
                        st.sidebar.info("✨ Package compiled! Download icon deployed in left menu panel.")
                        st.rerun()
                        
                except Exception as e: st.error(f"Ecosystem Execution Failure: {e}")

    elif st.session_state.page == "Draw":
        st.header("🎨 AI Generative Spatial Painter")
        p = st.text_input("Provide aesthetic specifications:")
        if st.button("Render Spatial Grid"):
            with st.spinner("Constructing image arrays..."):
                try:
                    if not gemini_available:
                        st.error("Image generation mode requires a valid Gemini connection fallback core configured.")
                    else:
                        res = gemini_client.models.generate_content(
                            model='gemini-2.5-flash-image', 
                            contents=p, 
                            config=types.GenerateContentConfig(response_modalities=["IMAGE"])
                        )
                        for part in res.candidates[0].content.parts:
                            if part.inline_data: st.image(io.BytesIO(part.inline_data.data), use_container_width=True)
                except Exception as e: st.error(f"Renderer Fault: {e}")

    elif st.session_state.page == "See":
        st.header("🖼️ Multimodal Intelligence Interface")
        uploaded_file = st.file_uploader("Upload asset for visual tracking analysis:", type=["jpg", "jpeg", "png"])
        if uploaded_file:
            img = Image.open(uploaded_file)
            st.image(img, caption='Active Workspace Element', use_container_width=True)
            if st.button("Initialize Deep Visual Processing"):
                with st.spinner("Processing optical metadata matrices..."):
                    try:
                        if is_openai_selected:
                            st.warning("Switch to an industrial Gemini processing core variant for inline native vision extraction chains.")
                        else:
                            res = gemini_client.models.generate_content(model=selected_model, contents=["Analyze and break down this workspace image asset data meticulously:", img])
                            st.write(res.text)
                    except Exception as e: st.error(f"Optical engine trace fault: {e}")
