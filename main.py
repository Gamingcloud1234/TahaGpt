import os
import io
import re
import json
import base64
import sqlite3
import zipfile
import uuid
from datetime import datetime
from typing import Generator, Optional

import streamlit as st
import bcrypt
from PIL import Image

# Optional dependencies are imported only when needed.
try:
    from fpdf import FPDF
except ImportError:
    FPDF = None

# ------------------------------------------------------------
# APP CONFIG
# ------------------------------------------------------------
st.set_page_config(
    page_title="Fenix AI",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_FILE = os.environ.get("FENIX_DB_FILE", "fenix_ai.db")
DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")


# ------------------------------------------------------------
# DATABASE
# ------------------------------------------------------------
def get_db_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_db_connection() as conn:
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                avatar TEXT,
                created_at TEXT NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                user_id INTEGER PRIMARY KEY,
                theme TEXT DEFAULT 'dark',
                default_model TEXT DEFAULT 'gemini-2.5-flash',
                api_key_gemini TEXT DEFAULT '',
                api_key_groq TEXT DEFAULT '',
                custom_sys_prompt TEXT DEFAULT '',
                language TEXT DEFAULT 'English',
                voice_enabled INTEGER DEFAULT 1,
                auto_send_voice INTEGER DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # Migration for databases created by older versions.
        existing = {
            row["name"]
            for row in cur.execute("PRAGMA table_info(settings)").fetchall()
        }

        migrations = {
            "language": "ALTER TABLE settings ADD COLUMN language TEXT DEFAULT 'English'",
            "voice_enabled": "ALTER TABLE settings ADD COLUMN voice_enabled INTEGER DEFAULT 1",
            "auto_send_voice": "ALTER TABLE settings ADD COLUMN auto_send_voice INTEGER DEFAULT 0",
        }

        for column, sql in migrations.items():
            if column not in existing:
                cur.execute(sql)

        conn.commit()


init_db()


# ------------------------------------------------------------
# AUTH
# ------------------------------------------------------------
def clean_text(value) -> str:
    return str(value or "").strip()


def register_user(username: str, password: str):
    username = clean_text(username)

    if not username or not password:
        return False, "Username and password cannot be empty."

    if len(username) < 3:
        return False, "Username must contain at least 3 characters."

    if len(password) < 6:
        return False, "Password must be at least 6 characters long."

    password_hash = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")

    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO users (username, password, created_at)
                VALUES (?, ?, ?)
                """,
                (username, password_hash, datetime.now().isoformat()),
            )
            user_id = cur.lastrowid

            cur.execute(
                """
                INSERT INTO settings
                (user_id, theme, default_model, language, voice_enabled)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, "dark", DEFAULT_MODEL, "English", 1),
            )

            conn.commit()

        return True, "Registration successful. Please sign in."

    except sqlite3.IntegrityError:
        return False, "Username already exists."


def authenticate_user(username: str, password: str):
    username = clean_text(username)

    with get_db_connection() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,),
        ).fetchone()

    if not user:
        return None

    try:
        valid = bcrypt.checkpw(
            password.encode("utf-8"),
            user["password"].encode("utf-8"),
        )
    except Exception:
        valid = False

    return dict(user) if valid else None


# ------------------------------------------------------------
# SETTINGS
# ------------------------------------------------------------
def get_user_settings(user_id: int):
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM settings WHERE user_id = ?",
            (user_id,),
        ).fetchone()

    if row:
        return dict(row)

    return {
        "theme": "dark",
        "default_model": DEFAULT_MODEL,
        "api_key_gemini": "",
        "api_key_groq": "",
        "custom_sys_prompt": "",
        "language": "English",
        "voice_enabled": 1,
        "auto_send_voice": 0,
    }


def update_user_settings(
    user_id: int,
    theme: str,
    model: str,
    gemini_key: str,
    groq_key: str,
    custom_prompt: str,
    language: str,
    voice_enabled: bool,
    auto_send_voice: bool,
):
    with get_db_connection() as conn:
        conn.execute(
            """
            UPDATE settings
            SET theme = ?,
                default_model = ?,
                api_key_gemini = ?,
                api_key_groq = ?,
                custom_sys_prompt = ?,
                language = ?,
                voice_enabled = ?,
                auto_send_voice = ?
            WHERE user_id = ?
            """,
            (
                theme,
                model,
                gemini_key,
                groq_key,
                custom_prompt,
                language,
                int(voice_enabled),
                int(auto_send_voice),
                user_id,
            ),
        )
        conn.commit()


# ------------------------------------------------------------
# CONVERSATIONS
# ------------------------------------------------------------
def load_conversations(user_id: int, search_query: Optional[str] = None):
    with get_db_connection() as conn:
        if search_query:
            rows = conn.execute(
                """
                SELECT *
                FROM conversations
                WHERE user_id = ?
                  AND title LIKE ?
                ORDER BY updated_at DESC
                """,
                (user_id, f"%{search_query}%"),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT *
                FROM conversations
                WHERE user_id = ?
                ORDER BY updated_at DESC
                """,
                (user_id,),
            ).fetchall()

    return [dict(row) for row in rows]


def create_conversation(user_id: int, title: str = "New Chat"):
    conversation_id = f"chat_{uuid.uuid4().hex}"
    now = datetime.now().isoformat()

    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO conversations (id, user_id, title, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (conversation_id, user_id, clean_text(title) or "New Chat", now),
        )
        conn.commit()

    return conversation_id


def rename_conversation(conversation_id: str, title: str):
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE conversations SET title = ? WHERE id = ?",
            (clean_text(title) or "New Chat", conversation_id),
        )
        conn.commit()


def delete_conversation(conversation_id: str):
    with get_db_connection() as conn:
        conn.execute(
            "DELETE FROM messages WHERE conversation_id = ?",
            (conversation_id,),
        )
        conn.execute(
            "DELETE FROM conversations WHERE id = ?",
            (conversation_id,),
        )
        conn.commit()


def load_messages(conversation_id: str):
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id ASC
            """,
            (conversation_id,),
        ).fetchall()

    return [dict(row) for row in rows]


def save_message(conversation_id: str, role: str, content: str):
    now = datetime.now().isoformat()

    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO messages (conversation_id, role, content, timestamp)
            VALUES (?, ?, ?, ?)
            """,
            (conversation_id, role, content, now),
        )

        conn.execute(
            """
            UPDATE conversations
            SET updated_at = ?
            WHERE id = ?
            """,
            (now, conversation_id),
        )

        conn.commit()


# ------------------------------------------------------------
# FILE / DOCUMENT HELPERS
# ------------------------------------------------------------
def extract_text_from_zip(file_bytes: bytes) -> str:
    output = []

    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as archive:
            for name in archive.namelist():
                lower = name.lower()

                if lower.endswith(
                    (
                        ".txt",
                        ".py",
                        ".js",
                        ".ts",
                        ".tsx",
                        ".jsx",
                        ".html",
                        ".css",
                        ".md",
                        ".json",
                        ".xml",
                        ".yaml",
                        ".yml",
                    )
                ):
                    try:
                        text = archive.read(name).decode(
                            "utf-8",
                            errors="ignore"
                        )
                        output.append(
                            f"\n--- File: {name} ---\n{text}"
                        )
                    except Exception:
                        continue

        return "\n".join(output).strip()

    except zipfile.BadZipFile:
        return "The uploaded ZIP file is invalid."


def extract_text_from_pdf(file_bytes: bytes) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(file_bytes))
        pages = []

        for page in reader.pages:
            pages.append(page.extract_text() or "")

        text = "\n\n".join(pages).strip()
        return text or "No extractable text was found in the PDF."

    except ImportError:
        return (
            "PDF text extraction requires the 'pypdf' package. "
            "Install it with: pip install pypdf"
        )
    except Exception as exc:
        return f"PDF extraction failed: {exc}"


def extract_uploaded_file(uploaded_file):
    if not uploaded_file:
        return "", None

    data = uploaded_file.getvalue()
    name = uploaded_file.name.lower()

    image = None

    if name.endswith((".png", ".jpg", ".jpeg", ".webp")):
        try:
            image = Image.open(io.BytesIO(data))
        except Exception:
            image = None

    if name.endswith(".zip"):
        return extract_text_from_zip(data), image

    if name.endswith(".pdf"):
        return extract_text_from_pdf(data), image

    if name.endswith(
        (
            ".txt",
            ".py",
            ".js",
            ".ts",
            ".tsx",
            ".jsx",
            ".html",
            ".css",
            ".md",
            ".json",
            ".xml",
            ".yaml",
            ".yml",
            ".csv",
        )
    ):
        return data.decode("utf-8", errors="ignore"), image

    if image is not None:
        return "Image attached for visual analysis.", image

    return (
        "The file was uploaded, but this file type does not have built-in "
        "text extraction in this version.",
        None,
    )


# ------------------------------------------------------------
# GEMINI REST API
# ------------------------------------------------------------
def resolve_gemini_key(settings):
    return (
        clean_text(settings.get("api_key_gemini"))
        or clean_text(os.environ.get("GEMINI_API_KEY"))
    )


def gemini_request(
    api_key: str,
    model: str,
    contents,
    temperature: float = 0.4,
):
    """
    Direct REST implementation so the app does not depend on a particular
    google-generativeai SDK version.
    """
    import requests

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent"
    )

    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": temperature,
        },
    }

    response = requests.post(
        url,
        params={"key": api_key},
        json=payload,
        timeout=120,
    )

    if response.status_code >= 400:
        try:
            detail = response.json()
        except Exception:
            detail = response.text

        raise RuntimeError(
            f"Gemini API error ({response.status_code}): {detail}"
        )

    data = response.json()

    candidates = data.get("candidates", [])
    if not candidates:
        raise RuntimeError("Gemini returned no candidates.")

    parts = (
        candidates[0]
        .get("content", {})
        .get("parts", [])
    )

    text_parts = [
        part.get("text", "")
        for part in parts
        if part.get("text")
    ]

    answer = "".join(text_parts).strip()

    if not answer:
        raise RuntimeError("Gemini returned an empty response.")

    return answer


def build_system_instruction(settings):
    language = settings.get("language", "English")

    if language == "Urdu":
        language_rule = (
            "Answer naturally in Urdu script. Keep important technical "
            "terms in English in parentheses when useful."
        )
    elif language == "English + Urdu":
        language_rule = (
            "Give a clear English explanation first, then provide a "
            "detailed Urdu explanation under an 'اردو وضاحت' heading."
        )
    else:
        language_rule = "Answer in clear English."

    base = f"""
You are Fenix AI, a fast, professional general-purpose AI assistant.

{language_rule}

Be accurate, concise when a short answer is enough, and detailed when the
user asks for detail. Explain technical concepts step by step.

Do not invent facts, sources, measurements, or capabilities.

If information is uncertain, say so.

For military and defense topics, provide educational, historical and
high-level technical information. Do not provide operational targeting,
weapon firing instructions, weapon construction instructions, live
military intelligence, or instructions for harming people.

If the user asks about uploaded files, use the supplied file context and
clearly distinguish file-derived information from general knowledge.

Current date: {datetime.now().strftime("%Y-%m-%d")}.
"""

    custom = clean_text(settings.get("custom_sys_prompt"))
    if custom:
        base += f"\nAdditional user instruction:\n{custom}\n"

    return base.strip()


def build_gemini_contents(messages, system_instruction, file_context=""):
    contents = []

    contents.append({
        "role": "user",
        "parts": [
            {
                "text": (
                    "SYSTEM INSTRUCTION:\n"
                    + system_instruction
                    + "\n\n"
                    "Follow these instructions for the conversation."
                )
            }
        ],
    })

    if file_context:
        contents.append({
            "role": "user",
            "parts": [
                {
                    "text": (
                        "UPLOADED FILE CONTEXT:\n"
                        + file_context[:50000]
                    )
                }
            ],
        })

    for message in messages:
        role = "model" if message["role"] == "assistant" else "user"

        contents.append({
            "role": role,
            "parts": [
                {"text": message["content"]}
            ],
        })

    return contents


def generate_gemini_answer(
    settings,
    messages,
    file_context="",
    image=None,
):
    api_key = resolve_gemini_key(settings)

    if not api_key:
        raise RuntimeError(
            "Gemini API key is not configured. "
            "Open Settings → Gemini AI and add your API key."
        )

    model = clean_text(
        settings.get("default_model") or DEFAULT_MODEL
    )

    contents = build_gemini_contents(
        messages,
        build_system_instruction(settings),
        file_context,
    )

    # Add an image to the latest user message when present.
    if image is not None and contents:
        try:
            image_buffer = io.BytesIO()
            image.save(image_buffer, format="PNG")

            encoded = base64.b64encode(
                image_buffer.getvalue()
            ).decode("utf-8")

            contents[-1]["parts"].append({
                "inline_data": {
                    "mime_type": "image/png",
                    "data": encoded,
                }
            })

        except Exception as exc:
            raise RuntimeError(
                f"Could not prepare the image for Gemini: {exc}"
            )

    return gemini_request(
        api_key,
        model,
        contents,
        temperature=0.35,
    )


def transcribe_audio_with_gemini(
    audio_bytes: bytes,
    mime_type: str,
    settings,
):
    """
    Real voice-input path:
    Streamlit records microphone audio -> Gemini receives audio -> Gemini
    returns the transcript -> transcript is placed into the chat input.

    This avoids relying on a browser-specific Web Speech API implementation.
    """
    api_key = resolve_gemini_key(settings)

    if not api_key:
        raise RuntimeError(
            "Gemini API key is required for voice transcription."
        )

    model = clean_text(
        settings.get("default_model") or DEFAULT_MODEL
    )

    language = settings.get("language", "English")

    if language == "Urdu":
        language_instruction = (
            "Transcribe the spoken audio into Urdu script."
        )
    elif language == "English + Urdu":
        language_instruction = (
            "Transcribe the speech faithfully. Preserve English and Urdu "
            "words in the language actually spoken."
        )
    else:
        language_instruction = (
            "Transcribe the spoken audio into English."
        )

    prompt = f"""
You are a speech-to-text engine.

{language_instruction}

Return ONLY the transcription.
Do not add explanations.
Do not summarize.
Do not add quotation marks.
Do not invent words.

If the audio is unclear, return the words you can confidently recognize.
"""

    encoded = base64.b64encode(audio_bytes).decode("utf-8")

    contents = [{
        "role": "user",
        "parts": [
            {"text": prompt},
            {
                "inline_data": {
                    "mime_type": mime_type or "audio/wav",
                    "data": encoded,
                }
            },
        ],
    }]

    return gemini_request(
        api_key,
        model,
        contents,
        temperature=0.0,
    ).strip()


# ------------------------------------------------------------
# TEXT-TO-SPEECH
# ------------------------------------------------------------
def text_to_speech(text: str, language: str):
    try:
        from gtts import gTTS

        if language == "Urdu":
            lang = "ur"
        else:
            lang = "en"

        buffer = io.BytesIO()

        gTTS(
            text=text[:5000],
            lang=lang,
            slow=False,
        ).write_to_fp(buffer)

        buffer.seek(0)
        return buffer.getvalue()

    except Exception:
        return None


# ------------------------------------------------------------
# EXPORTS
# ------------------------------------------------------------
def export_to_txt(messages):
    output = [
        "FENIX AI - CHAT EXPORT",
        "======================",
        "",
    ]

    for message in messages:
        output.extend([
            f"[{message['timestamp']}] {message['role'].upper()}:",
            message["content"],
            "",
        ])

    return "\n".join(output).encode("utf-8")


def export_to_pdf(messages):
    if FPDF is None:
        return None

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", size=14)
    pdf.cell(
        0,
        10,
        "Fenix AI - Chat Transcript",
        ln=True,
        align="C",
    )
    pdf.ln(6)

    pdf.set_font("Helvetica", size=9)

    for message in messages:
        role = message["role"].upper()
        timestamp = message["timestamp"]

        header = f"[{timestamp}] {role}"
        safe_header = header.encode(
            "latin-1",
            errors="replace"
        ).decode("latin-1")

        safe_content = message["content"].encode(
            "latin-1",
            errors="replace"
        ).decode("latin-1")

        pdf.multi_cell(0, 6, safe_header)
        pdf.set_font("Helvetica", size=10)
        pdf.multi_cell(0, 6, safe_content)
        pdf.ln(3)
        pdf.set_font("Helvetica", size=9)

    output = pdf.output(dest="S")

    if isinstance(output, str):
        return output.encode("latin-1")

    return bytes(output)


def export_to_zip(messages):
    buffer = io.BytesIO()

    with zipfile.ZipFile(
        buffer,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        archive.writestr(
            "chat_transcript.txt",
            export_to_txt(messages),
        )

        pdf_data = export_to_pdf(messages)
        if pdf_data:
            archive.writestr(
                "chat_transcript.pdf",
                pdf_data,
            )

    return buffer.getvalue()


# ------------------------------------------------------------
# SESSION STATE
# ------------------------------------------------------------
DEFAULT_SETTINGS = {
    "theme": "dark",
    "default_model": DEFAULT_MODEL,
    "api_key_gemini": "",
    "api_key_groq": "",
    "custom_sys_prompt": "",
    "language": "English",
    "voice_enabled": 1,
    "auto_send_voice": 0,
}

if "user" not in st.session_state:
    st.session_state.user = None

if "settings" not in st.session_state:
    st.session_state.settings = DEFAULT_SETTINGS.copy()

if "current_conversation_id" not in st.session_state:
    st.session_state.current_conversation_id = None

if "uploaded_file_context" not in st.session_state:
    st.session_state.uploaded_file_context = ""

if "attached_image" not in st.session_state:
    st.session_state.attached_image = None

if "last_transcript" not in st.session_state:
    st.session_state.last_transcript = ""

if "voice_error" not in st.session_state:
    st.session_state.voice_error = ""

if "tts_audio" not in st.session_state:
    st.session_state.tts_audio = None


# ------------------------------------------------------------
# THEME
# ------------------------------------------------------------
def apply_theme_styles():
    theme = st.session_state.settings.get("theme", "dark")

    if theme == "light":
        background = "#ffffff"
        surface = "#f6f7f9"
        surface2 = "#ffffff"
        text = "#111111"
        muted = "#606770"
        border = "#dfe3e8"
        accent = "#1769ff"
    else:
        background = "#0b0f14"
        surface = "#111820"
        surface2 = "#151e27"
        text = "#f2f5f8"
        muted = "#9aa8b5"
        border = "#263442"
        accent = "#39b7ff"

    st.markdown(
        f"""
        <style>
        html, body,
        [data-testid="stAppViewContainer"] {{
            background: {background};
            color: {text};
        }}

        [data-testid="stHeader"] {{
            background: transparent;
        }}

        [data-testid="stSidebar"] {{
            background: {surface};
            border-right: 1px solid {border};
        }}

        .block-container {{
            padding-top: 2rem;
            padding-bottom: 4rem;
            max-width: 1500px;
        }}

        h1, h2, h3, h4, h5, p, label, span {{
            color: {text};
        }}

        .fenix-card {{
            background: {surface2};
            border: 1px solid {border};
            border-radius: 14px;
            padding: 18px;
            margin-bottom: 14px;
        }}

        .status-pill {{
            display: inline-block;
            border: 1px solid {border};
            border-radius: 999px;
            padding: 5px 10px;
            font-size: 12px;
            color: {muted};
            margin-right: 6px;
        }}

        .chat-user {{
            background: {surface2};
            border: 1px solid {border};
            border-radius: 14px;
            padding: 16px;
            margin: 8px 0;
        }}

        .chat-assistant {{
            background: {surface};
            border: 1px solid {border};
            border-left: 4px solid {accent};
            border-radius: 14px;
            padding: 16px;
            margin: 8px 0 18px 0;
        }}

        .small-muted {{
            color: {muted} !important;
            font-size: 0.88rem;
        }}

        div.stButton > button {{
            border-radius: 10px;
            border: 1px solid {border};
            min-height: 42px;
        }}

        div[data-testid="stChatInput"] {{
            border-radius: 14px;
        }}

        .voice-ready {{
            border: 1px solid {accent};
            border-radius: 12px;
            padding: 10px 12px;
            margin: 8px 0;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ------------------------------------------------------------
# LOGIN SCREEN
# ------------------------------------------------------------
if st.session_state.user is None:
    apply_theme_styles()

    st.markdown(
        """
        <div style="text-align:center;padding:35px 0 20px 0;">
            <div style="font-size:54px;">⚡</div>
            <h1 style="margin-bottom:4px;">Fenix AI</h1>
            <p>Personal AI workspace with Gemini, files, voice and chat history.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tabs = st.tabs(["Sign In", "Create Account"])

    with tabs[0]:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input(
                "Password",
                type="password",
            )
            submitted = st.form_submit_button(
                "Access Dashboard",
                use_container_width=True,
            )

        if submitted:
            user = authenticate_user(username, password)

            if user:
                st.session_state.user = user
                st.session_state.settings = get_user_settings(user["id"])
                st.session_state.current_conversation_id = None
                st.rerun()
            else:
                st.error("Invalid username or password.")

    with tabs[1]:
        with st.form("register_form"):
            new_username = st.text_input("Choose Username")
            new_password = st.text_input(
                "Choose Password",
                type="password",
            )
            confirm_password = st.text_input(
                "Confirm Password",
                type="password",
            )
            submitted = st.form_submit_button(
                "Create Account",
                use_container_width=True,
            )

        if submitted:
            if new_password != confirm_password:
                st.error("Passwords do not match.")
            else:
                success, message = register_user(
                    new_username,
                    new_password,
                )

                if success:
                    st.success(message)
                else:
                    st.error(message)

    st.stop()


# ------------------------------------------------------------
# CURRENT USER
# ------------------------------------------------------------
current_user = st.session_state.user
st.session_state.settings = get_user_settings(current_user["id"])
settings = st.session_state.settings

apply_theme_styles()


# ------------------------------------------------------------
# SIDEBAR
# ------------------------------------------------------------
with st.sidebar:
    st.title("⚡ Fenix AI")
    st.caption(f"User: **{current_user['username']}**")

    gemini_ready = bool(resolve_gemini_key(settings))

    if gemini_ready:
        st.success("Gemini AI: Connected")
    else:
        st.warning("Gemini AI: Not configured")

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        if st.button(
            "➕ New Chat",
            use_container_width=True,
        ):
            new_id = create_conversation(
                current_user["id"],
                f"Session {datetime.now().strftime('%b %d, %H:%M')}",
            )
            st.session_state.current_conversation_id = new_id
            st.session_state.uploaded_file_context = ""
            st.session_state.attached_image = None
            st.session_state.last_transcript = ""
            st.rerun()

    with col2:
        if st.button(
            "🚪 Sign Out",
            use_container_width=True,
        ):
            st.session_state.user = None
            st.session_state.current_conversation_id = None
            st.rerun()

    st.divider()

    search_q = st.text_input(
        "🔍 Search conversations",
        placeholder="Search...",
    )

    conversations = load_conversations(
        current_user["id"],
        search_q,
    )

    if conversations:
        st.subheader("Conversations")

        for conversation in conversations:
            active = (
                conversation["id"]
                == st.session_state.current_conversation_id
            )

            button_label = (
                ("🟢 " if active else "💬 ")
                + conversation["title"][:32]
            )

            if st.button(
                button_label,
                key=f"open_{conversation['id']}",
                use_container_width=True,
            ):
                st.session_state.current_conversation_id = conversation["id"]
                st.session_state.last_transcript = ""
                st.rerun()

            delete_col, rename_col = st.columns(2)

            with delete_col:
                if st.button(
                    "🗑️",
                    key=f"delete_{conversation['id']}",
                    use_container_width=True,
                ):
                    delete_conversation(conversation["id"])

                    if (
                        st.session_state.current_conversation_id
                        == conversation["id"]
                    ):
                        st.session_state.current_conversation_id = None

                    st.rerun()

            with rename_col:
                if st.button(
                    "✏️",
                    key=f"rename_{conversation['id']}",
                    use_container_width=True,
                ):
                    st.session_state[f"rename_mode_{conversation['id']}"] = True

            if st.session_state.get(
                f"rename_mode_{conversation['id']}",
                False,
            ):
                new_title = st.text_input(
                    "New title",
                    value=conversation["title"],
                    key=f"title_input_{conversation['id']}",
                )

                if st.button(
                    "Save title",
                    key=f"save_title_{conversation['id']}",
                ):
                    rename_conversation(
                        conversation["id"],
                        new_title,
                    )
                    st.session_state[
                        f"rename_mode_{conversation['id']}"
                    ] = False
                    st.rerun()

    else:
        st.info("No conversations yet. Create your first chat.")

    st.divider()

    page = st.radio(
        "Workspace",
        [
            "💬 Chat",
            "🎙️ Voice",
            "📎 Files",
            "⚙️ Settings",
            "📊 Diagnostics",
        ],
    )


# ------------------------------------------------------------
# AUTO-CREATE / SELECT CHAT
# ------------------------------------------------------------
if page in ("💬 Chat", "🎙️ Voice", "📎 Files"):
    if not st.session_state.current_conversation_id:
        existing = load_conversations(current_user["id"])

        if existing:
            st.session_state.current_conversation_id = existing[0]["id"]
        else:
            st.session_state.current_conversation_id = create_conversation(
                current_user["id"],
                f"Session {datetime.now().strftime('%b %d, %H:%M')}",
            )

        st.rerun()


# ------------------------------------------------------------
# CHAT PAGE
# ------------------------------------------------------------
if page == "💬 Chat":
    st.title("FENIX / Fenix AI Command Center")

    st.markdown(
        '<span class="status-pill">AI ENGINE: GEMINI</span>'
        '<span class="status-pill">DATABASE: ONLINE</span>'
        '<span class="status-pill">VOICE: AVAILABLE</span>',
        unsafe_allow_html=True,
    )

    st.write("")

    messages = load_messages(
        st.session_state.current_conversation_id
    )

    if not messages:
        st.markdown(
            """
            <div class="fenix-card">
                <h3>Welcome</h3>
                <p>
                Ask anything you need help with. Fenix AI can answer,
                explain, summarize, compare, analyze supported files,
                and respond in English or Urdu.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    for message in messages:
        if message["role"] == "user":
            st.markdown(
                f"""
                <div class="chat-user">
                    <strong>You</strong><br><br>
                    {message["content"]}
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div class="chat-assistant">
                    <strong>⚡ FENIX</strong><br><br>
                    {message["content"]}
                </div>
                """,
                unsafe_allow_html=True,
            )

    if st.session_state.uploaded_file_context:
        st.info(
            "A file is attached to the current chat. "
            "FENIX will use its extracted context."
        )

    prompt = st.chat_input(
        "Ask FENIX anything..."
    )

    if prompt:
        prompt = prompt.strip()

        if prompt:
            save_message(
                st.session_state.current_conversation_id,
                "user",
                prompt,
            )

            with st.spinner("FENIX is thinking..."):
                try:
                    current_messages = load_messages(
                        st.session_state.current_conversation_id
                    )

                    answer = generate_gemini_answer(
                        settings,
                        current_messages,
                        st.session_state.uploaded_file_context,
                        st.session_state.attached_image,
                    )

                except Exception as exc:
                    answer = f"⚠️ {exc}"

            save_message(
                st.session_state.current_conversation_id,
                "assistant",
                answer,
            )

            st.rerun()


# ------------------------------------------------------------
# VOICE PAGE
# ------------------------------------------------------------
elif page == "🎙️ Voice":
    st.title("🎙️ FENIX Voice Input")

    st.markdown(
        """
        <div class="fenix-card">
            <h3>Real microphone input</h3>
            <p>
            Click the microphone control below, speak your question,
            and FENIX will use Gemini to transcribe the recording.
            The transcript is then placed into the chat workflow.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not resolve_gemini_key(settings):
        st.warning(
            "Add your Gemini API key in Settings before using voice input."
        )

    language = settings.get("language", "English")

    if language == "Urdu":
        st.info("Voice mode: Urdu")
    elif language == "English + Urdu":
        st.info("Voice mode: English + Urdu")
    else:
        st.info("Voice mode: English")

    st.markdown("### Step 1 — Record")

    audio = st.audio_input(
        "🎙️ Start recording",
        key="fenix_voice_input",
    )

    if audio:
        st.audio(audio)

        st.markdown("### Step 2 — Transcribe")

        if st.button(
            "📝 Transcribe with Gemini",
            use_container_width=True,
        ):
            if not resolve_gemini_key(settings):
                st.error(
                    "Gemini API key is missing. "
                    "Open Settings → Gemini AI."
                )
            else:
                try:
                    with st.spinner(
                        "FENIX is converting your speech to text..."
                    ):
                        transcript = transcribe_audio_with_gemini(
                            audio.getvalue(),
                            getattr(audio, "type", None) or "audio/wav",
                            settings,
                        )

                    st.session_state.last_transcript = transcript
                    st.session_state.voice_error = ""
                    st.success("Voice transcription complete.")

                except Exception as exc:
                    st.session_state.voice_error = str(exc)
                    st.error(f"Voice input error: {exc}")

    if st.session_state.voice_error:
        st.error(st.session_state.voice_error)

    if st.session_state.last_transcript:
        st.markdown("### Recognized text")

        transcript = st.text_area(
            "Review and edit before sending",
            value=st.session_state.last_transcript,
            height=140,
            key="voice_transcript_editor",
        )

        send_voice = st.button(
            "⚡ Send to FENIX",
            use_container_width=True,
        )

        if send_voice:
            if not transcript.strip():
                st.warning("There is no recognized text to send.")
            else:
                save_message(
                    st.session_state.current_conversation_id,
                    "user",
                    transcript.strip(),
                )

                with st.spinner("FENIX is thinking..."):
                    try:
                        current_messages = load_messages(
                            st.session_state.current_conversation_id
                        )

                        answer = generate_gemini_answer(
                            settings,
                            current_messages,
                            st.session_state.uploaded_file_context,
                            st.session_state.attached_image,
                        )

                    except Exception as exc:
                        answer = f"⚠️ {exc}"

                save_message(
                    st.session_state.current_conversation_id,
                    "assistant",
                    answer,
                )

                st.session_state.last_transcript = ""
                st.rerun()

    st.divider()

    st.markdown("### Voice workflow")

    st.write(
        "🎙️ Record → 📝 Gemini transcription → ✏️ Review → "
        "⚡ Send → 🤖 Gemini answer"
    )

    st.caption(
        "If microphone recording is unavailable in your browser, "
        "use the browser's microphone permission settings or update "
        "to a current Chromium/Edge/Chrome browser."
    )


# ------------------------------------------------------------
# FILES PAGE
# ------------------------------------------------------------
elif page == "📎 Files":
    st.title("📎 Files & Visual Analysis")

    st.write(
        "Upload a supported text, PDF, ZIP, or image file to provide "
        "additional context to FENIX."
    )

    uploaded = st.file_uploader(
        "Upload file",
        type=[
            "txt",
            "pdf",
            "zip",
            "py",
            "js",
            "ts",
            "tsx",
            "jsx",
            "html",
            "css",
            "md",
            "json",
            "xml",
            "yaml",
            "yml",
            "csv",
            "png",
            "jpg",
            "jpeg",
            "webp",
        ],
    )

    if uploaded:
        if st.button(
            "📥 Load into current chat",
            use_container_width=True,
        ):
            context, image = extract_uploaded_file(uploaded)

            st.session_state.uploaded_file_context = context
            st.session_state.attached_image = image

            st.success(
                f"{uploaded.name} is now attached to the current chat."
            )

    if st.session_state.attached_image is not None:
        st.subheader("Attached image")
        st.image(
            st.session_state.attached_image,
            use_container_width=True,
        )

    if st.session_state.uploaded_file_context:
        st.subheader("Extracted context")

        preview = st.session_state.uploaded_file_context

        if len(preview) > 12000:
            preview = preview[:12000] + "\n\n[Preview truncated]"

        st.text_area(
            "Text available to FENIX",
            value=preview,
            height=400,
            disabled=True,
        )

        if st.button("🧹 Clear attachment"):
            st.session_state.uploaded_file_context = ""
            st.session_state.attached_image = None
            st.rerun()


# ------------------------------------------------------------
# SETTINGS PAGE
# ------------------------------------------------------------
elif page == "⚙️ Settings":
    st.title("⚙️ Settings")

    settings_tab, voice_tab, ai_tab = st.tabs(
        ["General", "Voice", "Gemini AI"]
    )

    with settings_tab:
        theme = st.selectbox(
            "Theme",
            ["dark", "light"],
            index=(
                0
                if settings.get("theme", "dark") == "dark"
                else 1
            ),
        )

        language = st.selectbox(
            "Response language",
            ["English", "Urdu", "English + Urdu"],
            index=[
                "English",
                "Urdu",
                "English + Urdu",
            ].index(settings.get("language", "English")),
        )

        custom_prompt = st.text_area(
            "Custom FENIX instruction",
            value=settings.get("custom_sys_prompt", ""),
            height=160,
            placeholder=(
                "Example: Explain technical subjects step-by-step."
            ),
        )

    with voice_tab:
        voice_enabled = st.checkbox(
            "Enable voice features",
            value=bool(settings.get("voice_enabled", 1)),
        )

        auto_send_voice = st.checkbox(
            "Auto-send transcribed voice commands",
            value=bool(settings.get("auto_send_voice", 0)),
            help=(
                "The current safe default is OFF so you can review "
                "the transcript before it is sent."
            ),
        )

        st.info(
            "Voice input uses your browser microphone through "
            "Streamlit's audio recorder and Gemini for transcription."
        )

    with ai_tab:
        st.subheader("Gemini AI")

        model = st.text_input(
            "Gemini model",
            value=settings.get(
                "default_model",
                DEFAULT_MODEL,
            ),
            help=(
                "Use a Gemini model currently available to your API key."
            ),
        )

        gemini_key = st.text_input(
            "Gemini API key",
            value=settings.get("api_key_gemini", ""),
            type="password",
            help="Your key is stored in the local SQLite settings database.",
        )

        st.caption(
            "For production deployment, prefer a server-side secret/"
            "environment variable instead of storing a user key."
        )

        if st.button(
            "🧪 Test Gemini connection",
            use_container_width=True,
        ):
            if not gemini_key.strip():
                st.error("Enter a Gemini API key first.")
            else:
                test_settings = dict(settings)
                test_settings["api_key_gemini"] = gemini_key
                test_settings["default_model"] = model

                try:
                    result = gemini_request(
                        gemini_key.strip(),
                        model.strip(),
                        [{
                            "role": "user",
                            "parts": [{
                                "text": (
                                    "Reply with exactly: "
                                    "GEMINI CONNECTION OK"
                                )
                            }],
                        }],
                        temperature=0.0,
                    )

                    st.success(result)

                except Exception as exc:
                    st.error(str(exc))

        st.subheader("Optional Groq fallback")

        groq_key = st.text_input(
            "Groq API key",
            value=settings.get("api_key_groq", ""),
            type="password",
        )

    if st.button(
        "💾 Save Settings",
        type="primary",
        use_container_width=True,
    ):
        update_user_settings(
            current_user["id"],
            theme,
            model.strip() or DEFAULT_MODEL,
            gemini_key.strip(),
            groq_key.strip(),
            custom_prompt,
            language,
            voice_enabled,
            auto_send_voice,
        )

        st.session_state.settings = get_user_settings(
            current_user["id"]
        )

        st.success("Settings saved successfully.")
        st.rerun()


# ------------------------------------------------------------
# DIAGNOSTICS PAGE
# ------------------------------------------------------------
elif page == "📊 Diagnostics":
    st.title("📊 System Diagnostics")

    gemini_key_present = bool(resolve_gemini_key(settings))

    checks = [
        ("Application", True),
        ("Database", os.path.exists(DB_FILE)),
        ("Authentication", st.session_state.user is not None),
        ("Gemini API Key", gemini_key_present),
        ("Voice Recorder", hasattr(st, "audio_input")),
        ("PDF Export", FPDF is not None),
    ]

    for name, status in checks:
        if status:
            st.success(f"{name}: READY")
        else:
            st.warning(f"{name}: NOT READY")

    st.divider()

    st.subheader("Current configuration")

    st.json({
        "user": current_user["username"],
        "theme": settings.get("theme"),
        "language": settings.get("language"),
        "gemini_model": settings.get(
            "default_model",
            DEFAULT_MODEL,
        ),
        "gemini_key_configured": gemini_key_present,
        "voice_enabled": bool(settings.get("voice_enabled", 1)),
        "auto_send_voice": bool(
            settings.get("auto_send_voice", 0)
        ),
        "database": DB_FILE,
        "current_conversation": (
            st.session_state.current_conversation_id
        ),
    })


# ------------------------------------------------------------
# GLOBAL CHAT EXPORT
# ------------------------------------------------------------
if (
    st.session_state.current_conversation_id
    and page in ("💬 Chat", "🎙️ Voice")
):
    with st.sidebar:
        st.divider()
        st.subheader("Export current chat")

        current_messages = load_messages(
            st.session_state.current_conversation_id
        )

        if current_messages:
            st.download_button(
                "⬇️ TXT",
                data=export_to_txt(current_messages),
                file_name="fenix_chat.txt",
                mime="text/plain",
                use_container_width=True,
            )

            pdf_data = export_to_pdf(current_messages)
            if pdf_data:
                st.download_button(
                    "⬇️ PDF",
                    data=pdf_data,
                    file_name="fenix_chat.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )

            st.download_button(
                "⬇️ ZIP",
                data=export_to_zip(current_messages),
                file_name="fenix_chat.zip",
                mime="application/zip",
                use_container_width=True,
            )
