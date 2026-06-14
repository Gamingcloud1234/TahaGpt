import os
import io
import re
import sqlite3
import zipfile
from datetime import datetime
import streamlit as st
import bcrypt
from PIL import Image
from gtts import gTTS
from fpdf import FPDF

# --- API SDK IMPORTS & INITIALIZATION UTILS ---
# Using standard google-generativeai and groq packages for reliability
try:
    import google.generativeai as genai
except ImportError:
    genai = None

try:
    from groq import Groq
except ImportError:
    Groq = None

# --- DATABASE MANAGEMENT ---
DB_FILE = "fenix_ai.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Users Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                avatar TEXT,
                created_at TEXT NOT NULL
            )
        """)
        # Conversations Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        # Messages Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            )
        """)
        # Settings Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                user_id INTEGER PRIMARY KEY,
                theme TEXT DEFAULT 'dark',
                default_model TEXT DEFAULT 'gemini-1.5-flash',
                api_key_gemini TEXT,
                api_key_groq TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        conn.commit()

init_db()

# --- AUTHENTICATION SERVICES ---
def register_user(username, password):
    if not username or not password:
        return False, "Username and password cannot be empty."
    if len(password) < 6:
        return False, "Password must be at least 6 characters long."
    
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    now = datetime.now().isoformat()
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (username, password, created_at) VALUES (?, ?, ?)",
                (username, bundle_input(username), now) # bundle_input sanitization wrapper
            )
            user_id = cursor.lastrowid
            # Seed default settings
            cursor.execute(
                "INSERT INTO settings (user_id) VALUES (?)",
                (user_id,)
            )
            conn.commit()
        return True, "Registration successful! Please log in."
    except sqlite3.IntegrityError:
        return False, "Username already exists."

def authenticate_user(username, password):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            return user
    return None

def bundle_input(val):
    return str(val).strip()

# --- USER SETTINGS & DATA SERVICES ---
def get_user_settings(user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM settings WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
    return {"theme": "dark", "default_model": "gemini-1.5-flash", "api_key_gemini": "", "api_key_groq": ""}

def update_user_settings(user_id, theme, default_model, api_key_gemini, api_key_groq):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE settings 
            SET theme = ?, default_model = ?, api_key_gemini = ?, api_key_groq = ?
            WHERE user_id = ?
        """, (theme, default_model, api_key_gemini, api_key_groq, user_id))
        conn.commit()

def update_user_profile(user_id, password=None, avatar=None):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if password:
            hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cursor.execute("UPDATE users SET password = ? WHERE id = ?", (hashed, user_id))
        if avatar:
            cursor.execute("UPDATE users SET avatar = ? WHERE id = ?", (avatar, user_id))
        conn.commit()

# --- CONVERSATION SERVICES ---
def load_conversations(user_id, search_query=None):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if search_query:
            cursor.execute("""
                SELECT * FROM conversations 
                WHERE user_id = ? AND title LIKE ? 
                ORDER BY updated_at DESC
            """, (user_id, f"%{search_query}%"))
        else:
            cursor.execute("""
                SELECT * FROM conversations 
                WHERE user_id = ? 
                ORDER BY updated_at DESC
            """, (user_id,))
        return [dict(row) for row in cursor.fetchall()]

def create_conversation(conversation_id, user_id, title):
    now = datetime.now().isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO conversations (id, user_id, title, updated_at)
            VALUES (?, ?, ?, ?)
        """, (conversation_id, user_id, title, now))
        conn.commit()

def rename_conversation(conversation_id, new_title):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE conversations SET title = ? WHERE id = ?
        """, (new_title, conversation_id))
        conn.commit()

def delete_conversation(conversation_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
        conn.commit()

def load_messages(conversation_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM messages 
            WHERE conversation_id = ? 
            ORDER BY id ASC
        """, (conversation_id,))
        return [dict(row) for row in cursor.fetchall()]

def save_message(conversation_id, role, content):
    now = datetime.now().isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO messages (conversation_id, role, content, timestamp)
            VALUES (?, ?, ?, ?)
        """, (conversation_id, role, content, now))
        cursor.execute("""
            UPDATE conversations SET updated_at = ? WHERE id = ?
        """, (now, conversation_id))
        conn.commit()

# --- PARSING & FILE UTILS ---
def extract_text_from_zip(file_bytes):
    extracted_text = ""
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            for filename in z.namelist():
                if filename.endswith(('.txt', '.py', '.js', '.html', '.css', '.sk')):
                    with z.open(filename) as f:
                        extracted_text += f"\n--- File: {filename} ---\n"
                        extracted_text += f.read().decode('utf-8', errors='ignore')
    except Exception as e:
        extracted_text = f"Error extracting ZIP content: {str(e)}"
    return extracted_text

def extract_text_from_pdf(file_bytes):
    # Fallback/Lightweight text extraction from PDF binary streams safely without extra hefty deps
    text = ""
    try:
        pdf_str = file_bytes.decode('utf-8', errors='ignore')
        strings = re.findall(r'\(.*?\)', pdf_str)
        for s in strings:
            cleaned = s.strip('()')
            if len(cleaned) > 2:
                text += cleaned + " "
    except Exception:
        text = "Could not parse system PDF natively."
    return text if text.strip() else "PDF structural stream processed but no clear ASCII sequences discovered."

# --- AI ENGINES & STREAMING ---
def generate_ai_stream(model_name, messages, system_instruction, api_keys, attached_image=None):
    # Route model requests
    if "gemini" in model_name:
        if not genai:
            yield "Google GenAI package not available."
            return
        key = api_keys.get("gemini") or os.environ.get("GEMINI_API_KEY")
        if not key:
            yield "Missing Gemini API Key. Configure it in Settings."
            return
        
        genai.configure(api_key=key)
        
        try:
            # Construct model input format
            formatted_contents = []
            if attached_image:
                formatted_contents.append(attached_image)
            
            # Combine historical messages for execution
            history_text = f"System Instruction: {system_instruction}\n\n"
            for m in messages:
                history_text += f"{m['role'].capitalize()}: {m['content']}\n"
            
            formatted_contents.append(history_text)
            
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(formatted_contents, stream=True)
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            yield f"Gemini Engine Error: {str(e)}"

    elif "groq" in model_name or "llama" in model_name or "mixtral" in model_name:
        if not Groq:
            yield "Groq package not available."
            return
        key = api_keys.get("groq") or os.environ.get("GROQ_API_KEY")
        if not key:
            yield "Missing Groq API Key. Configure it in Settings."
            return
        
        try:
            client = Groq(api_key=key)
            groq_messages = [{"role": "system", "content": system_instruction}]
            for m in messages:
                # Basic translation mapping
                role = "assistant" if m['role'] == "assistant" else "user"
                groq_messages.append({"role": role, "content": m['content']})
                
            # Handle vision requests cleanly if fallback allowed
            if attached_image and "vision" in model_name:
                groq_messages.append({"role": "user", "content": "Analyze the previously uploaded context asset image."})

            completion = client.chat.completions.create(
                model=model_name,
                messages=groq_messages,
                stream=True
            )
            for chunk in completion:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as e:
            yield f"Groq Engine Error: {str(e)}"
    else:
        yield "Unsupported or unrecognized pipeline orchestration model layout selected."

# --- DOCUMENT & EXPORT MANAGEMENT ---
def export_to_txt(messages):
    output = "FENIX AI - CHAT EXPORT\n=======================\n\n"
    for m in messages:
        output += f"[{m['timestamp']}] {m['role'].upper()}:\n{m['content']}\n\n"
    return output.encode('utf-8')

def export_to_pdf(messages):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Fenix AI - Chat Transcript Summary", ln=1, align="C")
    pdf.ln(10)
    
    for m in messages:
        role_stamp = f"[{m['timestamp']}] {m['role'].upper()}: "
        pdf.set_bold() if m['role'] == 'assistant' else pdf.set_text_color(50, 50, 50)
        pdf.multi_cell(0, 10, txt=role_stamp.encode('latin-1', 'ignore').decode('latin-1'))
        pdf.set_font("Arial", size=10)
        pdf.multi_cell(0, 8, txt=m['content'].encode('latin-1', 'ignore').decode('latin-1'))
        pdf.ln(4)
    return pdf.output(dest='S').encode('latin-1')

def export_to_zip(messages):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        txt_data = export_to_txt(messages)
        zip_file.writestr("chat_transcript.txt", txt_data)
    return zip_buffer.getvalue()

# --- APPLICATION STATE STORAGE ---
if 'user' not in st.session_state:
    st.session_state.user = None
if 'settings' not in st.session_state:
    st.session_state.settings = {}
if 'current_conversation_id' not in st.session_state:
    st.session_state.current_conversation_id = None
if 'uploaded_file_context' not in st.session_state:
    st.session_state.uploaded_file_context = ""
if 'attached_image' not in st.session_state:
    st.session_state.attached_image = None
if 'tts_audio_data' not in st.session_state:
    st.session_state.tts_audio_data = {}

# --- PAGE STYLING & CORE CONFIGS ---
st.set_page_config(page_title="Fenix AI", layout="wide", initial_sidebar_state="expanded")

# Inject ChatGPT-styled Dark/Light Themes dynamically via Custom CSS Injector Layout
def apply_theme_styles():
    theme = st.session_state.settings.get('theme', 'dark')
    if theme == 'dark':
        st.markdown("""
            <style>
                html, body, [data-testid="stAppViewContainer"] { background-color: #212121; color: #ececf1; }
                [data-testid="stSidebar"] { background-color: #171717 !important; }
                div.stButton > button { background-color: #343541; color: white; border: 1px solid #4d4d4f; border-radius: 6px; }
                div.stButton > button:hover { background-color: #40414f; }
                .chat-msg-user { background-color: #212121; padding: 15px; border-radius: 8px; margin-bottom: 10px; }
                .chat-msg-assistant { background-color: #2f2f2f; padding: 15px; border-radius: 8px; margin-bottom: 10px; border-left: 3px solid #10a37f; }
                code { background-color: #0d0d0d !important; color: #f8f8f2 !important; }
            </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <style>
                html, body, [data-testid="stAppViewContainer"] { background-color: #ffffff; color: #191919; }
                [data-testid="stSidebar"] { background-color: #f9f9f9 !important; }
                div.stButton > button { background-color: #ffffff; color: #191919; border: 1px solid #e5e5e5; border-radius: 6px; }
                div.stButton > button:hover { background-color: #f2f2f2; }
                .chat-msg-user { background-color: #ffffff; padding: 15px; border-radius: 8px; margin-bottom: 10px; border: 1px solid #e5e5e5; }
                .chat-msg-assistant { background-color: #f7f7f8; padding: 15px; border-radius: 8px; margin-bottom: 10px; border-left: 3px solid #10a37f; }
                code { background-color: #f1f1f1 !important; color: #c41d7f !important; }
            </style>
        """, unsafe_allow_html=True)

apply_theme_styles()

# --- AUTHENTICATION INTERFACE SHIELD ---
if st.session_state.user is None:
    st.title("⚡ Fenix AI Workspace")
    tabs = st.tabs(["Sign In", "Create Account"])
    
    with tabs[0]:
        st.subheader("Login Credentials")
        login_user = st.text_input("Username", key="login_user_input")
        login_pass = st.text_input("Password", type="password", key="login_pass_input")
        if st.button("Access Dashboard", use_container_width=True):
            user = authenticate_user(bundle_input(login_user), login_pass)
            if user:
                st.session_state.user = dict(user)
                st.session_state.settings = get_user_settings(user['id'])
                st.rerun()
            else:
                st.error("Invalid username or matching password profile layout verification failed.")
                
    with tabs[1]:
        st.subheader("Registration Portal")
        reg_user = st.text_input("Choose Username", key="reg_user_input")
        reg_pass = st.text_input("Choose Password", type="password", key="reg_pass_input")
        if st.button("Register Account", use_container_width=True):
            success, msg = register_user(bundle_input(reg_user), reg_pass)
            if success:
                st.success(msg)
            else:
                st.error(msg)
    st.stop()

# --- INITIALIZE USER DATA CONTEXTS ---
current_user = st.session_state.user
user_settings = st.session_state.settings

# --- SIDEBAR ORCHESTRATION ---
with st.sidebar:
    st.title("⚡ Fenix AI")
    st.caption(f"Authenticated as: **{current_user['username']}**")
    
    # Navigation Action Hub
    col_nav_1, col_nav_2 = st.columns(2)
    with col_nav_1:
        if st.button("➕ New Chat", use_container_width=True):
            new_id = f"chat_{int(datetime.now().timestamp())}"
            create_conversation(new_id, current_user['id'], "New Dialogue Chain")
            st.session_state.current_conversation_id = new_id
            st.session_state.uploaded_file_context = ""
            st.session_state.attached_image = None
            st.rerun()
    with col_nav_2:
        if st.button("🚪 Sign Out", use_container_width=True):
            st.session_state.user = None
            st.session_state.current_conversation_id = None
            st.rerun()

    st.write("---")
    
    # Conversation Search Bar
    search_q = st.text_input("🔍 Search Logs", placeholder="Keywords...")
    
    # Active Conversation Tree Builder
    conversations = load_conversations(current_user['id'], search_query=search_q)
    
    if conversations:
        st.write("### Conversations Logs")
        for conv in conversations:
            # Simple list layouts
            is_active = (conv['id'] == st.session_state.current_conversation_id)
            lbl = f"💬 {conv['title'][:22]}" + ("" if len(conv['title']) <= 22 else "...")
            
            col_c1, col_c2 = st.columns([4, 1])
            with col_c1:
                if st.button(lbl, key=f"select_{conv['id']}", use_container_width=True, type="secondary" if not is_active else "primary"):
                    st.session_state.current_conversation_id = conv['id']
                    st.rerun()
            with col_c2:
                if st.button("🗑️", key=f"del_{conv['id']}", help="Delete log"):
                    delete_conversation(conv['id'])
                    if st.session_state.current_conversation_id == conv['id']:
                        st.session_state.current_conversation_id = None
                    st.rerun()
    else:
        st.caption("No chat records found.")

    st.write("---")
    st.write("### Quick Management Controls")
    if st.session_state.current_conversation_id:
        new_title = st.text_input("Rename Current Session", value="")
        if st.button("Confirm Title Update") and new_title.strip():
            rename_conversation(st.session_state.current_conversation_id, new_title.strip())
            st.rerun()

# --- MAIN CONTROLLER ROUTING PANELS ---
if not st.session_state.current_conversation_id:
    # Auto select or prompt creation setup
    conversations_pre = load_conversations(current_user['id'])
    if conversations_pre:
        st.session_state.current_conversation_id = conversations_pre[0]['id']
        st.rerun()
    else:
        st.info("💡 Create your first chat pipeline log by clicking on 'New Chat' inside the left navigation pane.")
        st.stop()

# Load current operational parameters
active_conv_id = st.se
