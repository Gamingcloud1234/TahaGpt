```python
import os
import io
import json
import base64
import sqlite3
import zipfile
import uuid
import re
from datetime import datetime
from typing import Optional

import streamlit as st
import bcrypt
from PIL import Image

try:
    from fpdf import FPDF
except ImportError:
    FPDF = None


# ============================================================
# APP CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Fenix AI",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_FILE = os.environ.get("FENIX_DB_FILE", "fenix_ai.db")
DEFAULT_MODEL = os.environ.get(
    "GEMINI_MODEL",
    "gemini-2.5-flash",
)


# ============================================================
# DATABASE
# ============================================================

def get_db_connection():
    conn = sqlite3.connect(
        DB_FILE,
        check_same_thread=False,
    )

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
                FOREIGN KEY(user_id)
                REFERENCES users(id)
                ON DELETE CASCADE
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY(conversation_id)
                REFERENCES conversations(id)
                ON DELETE CASCADE
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
                FOREIGN KEY(user_id)
                REFERENCES users(id)
                ON DELETE CASCADE
            )
        """)

        existing_columns = {
            row["name"]
            for row in cur.execute(
                "PRAGMA table_info(settings)"
            ).fetchall()
        }

        migrations = {
            "language":
                "ALTER TABLE settings ADD COLUMN language TEXT DEFAULT 'English'",

            "voice_enabled":
                "ALTER TABLE settings ADD COLUMN voice_enabled INTEGER DEFAULT 1",

            "auto_send_voice":
                "ALTER TABLE settings ADD COLUMN auto_send_voice INTEGER DEFAULT 0",
        }

        for column, sql in migrations.items():

            if column not in existing_columns:
                cur.execute(sql)

        conn.commit()


init_db()


# ============================================================
# HELPERS
# ============================================================

def clean_text(value) -> str:
    return str(value or "").strip()


# ============================================================
# AUTHENTICATION
# ============================================================

def register_user(username, password):

    username = clean_text(username)

    if not username or not password:
        return False, "Username and password cannot be empty."

    if len(username) < 3:
        return False, "Username must contain at least 3 characters."

    if len(password) < 6:
        return False, "Password must contain at least 6 characters."

    password_hash = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")

    try:

        with get_db_connection() as conn:

            cur = conn.cursor()

            cur.execute(
                """
                INSERT INTO users
                (username, password, created_at)
                VALUES (?, ?, ?)
                """,
                (
                    username,
                    password_hash,
                    datetime.now().isoformat(),
                ),
            )

            user_id = cur.lastrowid

            cur.execute(
                """
                INSERT INTO settings
                (
                    user_id,
                    theme,
                    default_model,
                    language,
                    voice_enabled
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    "dark",
                    DEFAULT_MODEL,
                    "English",
                    1,
                ),
            )

            conn.commit()

        return True, "Account created successfully."

    except sqlite3.IntegrityError:

        return False, "Username already exists."


def authenticate_user(username, password):

    username = clean_text(username)

    with get_db_connection() as conn:

        user = conn.execute(
            """
            SELECT *
            FROM users
            WHERE username = ?
            """,
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

    if not valid:
        return None

    return dict(user)


# ============================================================
# SETTINGS
# ============================================================

def get_user_settings(user_id):

    with get_db_connection() as conn:

        row = conn.execute(
            """
            SELECT *
            FROM settings
            WHERE user_id = ?
            """,
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
    user_id,
    theme,
    model,
    gemini_key,
    groq_key,
    custom_prompt,
    language,
    voice_enabled,
    auto_send_voice,
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


# ============================================================
# CONVERSATIONS
# ============================================================

def load_conversations(
    user_id,
    search_query=None,
):

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
                (
                    user_id,
                    f"%{search_query}%",
                ),
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


def create_conversation(
    user_id,
    title="New Chat",
):

    conversation_id = (
        "chat_" + uuid.uuid4().hex
    )

    now = datetime.now().isoformat()

    with get_db_connection() as conn:

        conn.execute(
            """
            INSERT INTO conversations
            (
                id,
                user_id,
                title,
                updated_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                conversation_id,
                user_id,
                clean_text(title) or "New Chat",
                now,
            ),
        )

        conn.commit()

    return conversation_id


def rename_conversation(
    conversation_id,
    title,
):

    with get_db_connection() as conn:

        conn.execute(
            """
            UPDATE conversations
            SET title = ?
            WHERE id = ?
            """,
            (
                clean_text(title) or "New Chat",
                conversation_id,
            ),
        )

        conn.commit()


def delete_conversation(
    conversation_id,
):

    with get_db_connection() as conn:

        conn.execute(
            """
            DELETE FROM messages
            WHERE conversation_id = ?
            """,
            (conversation_id,),
        )

        conn.execute(
            """
            DELETE FROM conversations
            WHERE id = ?
            """,
            (conversation_id,),
        )

        conn.commit()


def load_messages(
    conversation_id,
):

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


def save_message(
    conversation_id,
    role,
    content,
):

    now = datetime.now().isoformat()

    with get_db_connection() as conn:

        conn.execute(
            """
            INSERT INTO messages
            (
                conversation_id,
                role,
                content,
                timestamp
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                conversation_id,
                role,
                content,
                now,
            ),
        )

        conn.execute(
            """
            UPDATE conversations
            SET updated_at = ?
            WHERE id = ?
            """,
            (
                now,
                conversation_id,
            ),
        )

        conn.commit()


# ============================================================
# FILE PROCESSING
# ============================================================

def extract_text_from_pdf(
    file_bytes,
):

    try:

        from pypdf import PdfReader

        reader = PdfReader(
            io.BytesIO(file_bytes)
        )

        pages = []

        for page in reader.pages:

            pages.append(
                page.extract_text() or ""
            )

        result = "\n\n".join(
            pages
        ).strip()

        return result or "No text found in PDF."

    except ImportError:

        return (
            "PDF support requires pypdf. "
            "Install it using: pip install pypdf"
        )

    except Exception as exc:

        return f"PDF extraction failed: {exc}"


def extract_text_from_zip(
    file_bytes,
):

    output = []

    try:

        with zipfile.ZipFile(
            io.BytesIO(file_bytes)
        ) as archive:

            for filename in archive.namelist():

                lower = filename.lower()

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
                        ".csv",
                    )
                ):

                    try:

                        content = archive.read(
                            filename
                        ).decode(
                            "utf-8",
                            errors="ignore",
                        )

                        output.append(
                            f"\n--- {filename} ---\n"
                            f"{content}"
                        )

                    except Exception:
                        continue

        return "\n".join(output).strip()

    except zipfile.BadZipFile:

        return "Invalid ZIP file."


def extract_uploaded_file(
    uploaded_file,
):

    if uploaded_file is None:
        return "", None

    data = uploaded_file.getvalue()

    filename = uploaded_file.name.lower()

    image = None

    if filename.endswith(
        (
            ".png",
            ".jpg",
            ".jpeg",
            ".webp",
        )
    ):

        try:

            image = Image.open(
                io.BytesIO(data)
            )

        except Exception:

            image = None

    if filename.endswith(".pdf"):

        return (
            extract_text_from_pdf(data),
            image,
        )

    if filename.endswith(".zip"):

        return (
            extract_text_from_zip(data),
            image,
        )

    if filename.endswith(
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

        return (
            data.decode(
                "utf-8",
                errors="ignore",
            ),
            image,
        )

    if image is not None:

        return (
            "Image attached for visual analysis.",
            image,
        )

    return (
        "File uploaded successfully, but "
        "this file type does not have built-in "
        "text extraction.",
        None,
    )


# ============================================================
# GEMINI API
# ============================================================

def get_gemini_api_key(
    settings,
):

    return (
        clean_text(
            settings.get(
                "api_key_gemini"
            )
        )
        or clean_text(
            os.environ.get(
                "GEMINI_API_KEY"
            )
        )
    )


def gemini_request(
    api_key,
    model,
    contents,
    temperature=0.35,
):

    import requests

    url = (
        "https://generativelanguage.googleapis.com/"
        "v1beta/models/"
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
            error_data = response.json()
        except Exception:
            error_data = response.text

        raise RuntimeError(
            f"Gemini API error "
            f"({response.status_code}): "
            f"{error_data}"
        )

    data = response.json()

    candidates = data.get(
        "candidates",
        [],
    )

    if not candidates:

        raise RuntimeError(
            "Gemini returned no response."
        )

    parts = (
        candidates[0]
        .get("content", {})
        .get("parts", [])
    )

    answer = "".join(
        part.get("text", "")
        for part in parts
        if part.get("text")
    ).strip()

    if not answer:

        raise RuntimeError(
            "Gemini returned an empty answer."
        )

    return answer


def build_system_instruction(
    settings,
):

    language = settings.get(
        "language",
        "English",
    )

    if language == "Urdu":

        language_instruction = (
            "Answer in natural Urdu. "
            "Keep important technical terms "
            "in English in parentheses when useful."
        )

    elif language == "English + Urdu":

        language_instruction = (
            "First answer in clear English. "
            "Then provide a detailed Urdu explanation "
            "under the heading 'اردو وضاحت'."
        )

    else:

        language_instruction = (
            "Answer in clear English."
        )

    instruction = f"""
You are Fenix AI, a professional AI assistant.

{language_instruction}

Give accurate, useful and well-structured answers.

Use headings and bullet points when helpful.

Explain difficult concepts step-by-step.

Never pretend to have access to classified information,
real military systems, live radar feeds, private databases,
or restricted intelligence.

For defense-related subjects, provide educational,
historical and high-level technical information.

Do not provide operational targeting instructions,
weapon firing instructions, instructions for constructing
weapons, or instructions intended to harm people.

Do not invent facts or sources.

If you are uncertain, clearly say that you are uncertain.

If the user provides a file, use the file context supplied
by the application.

Current date:
{datetime.now().strftime("%Y-%m-%d")}
"""

    custom_prompt = clean_text(
        settings.get(
            "custom_sys_prompt"
        )
    )

    if custom_prompt:

        instruction += (
            "\n\nAdditional user preference:\n"
            + custom_prompt
        )

    return instruction.strip()


def build_gemini_contents(
    messages,
    settings,
    file_context="",
    image=None,
):

    contents = []

    system_instruction = (
        build_system_instruction(
            settings
        )
    )

    contents.append(
        {
            "role": "user",
            "parts": [
                {
                    "text":
                    "SYSTEM INSTRUCTIONS:\n"
                    + system_instruction
                }
            ],
        }
    )

    if file_context:

        contents.append(
            {
                "role": "user",
                "parts": [
                    {
                        "text":
                        "UPLOADED FILE CONTEXT:\n"
                        + file_context[:50000]
                    }
                ],
            }
        )

    for message in messages:

        role = (
            "model"
            if message["role"] == "assistant"
            else "user"
        )

        contents.append(
            {
                "role": role,
                "parts": [
                    {
                        "text":
                        message["content"]
                    }
                ],
            }
        )

    if image is not None:

        image_buffer = io.BytesIO()

        image.save(
            image_buffer,
            format="PNG",
        )

        encoded = base64.b64encode(
            image_buffer.getvalue()
        ).decode("utf-8")

        if contents:

            contents[-1]["parts"].append(
                {
                    "inline_data": {
                        "mime_type": "image/png",
                        "data": encoded,
                    }
                }
            )

    return contents


def generate_answer(
    settings,
    messages,
    file_context="",
    image=None,
):

    api_key = get_gemini_api_key(
        settings
    )

    if not api_key:

        raise RuntimeError(
            "Gemini API key is not configured. "
            "Open Settings → Gemini AI and add your key."
        )

    model = clean_text(
        settings.get(
            "default_model"
        )
        or DEFAULT_MODEL
    )

    contents = build_gemini_contents(
        messages,
        settings,
        file_context,
        image,
    )

    return gemini_request(
        api_key,
        model,
        contents,
    )


# ============================================================
# VOICE TRANSCRIPTION
# ============================================================

def transcribe_audio(
    audio_bytes,
    mime_type,
    settings,
):

    api_key = get_gemini_api_key(
        settings
    )

    if not api_key:

        raise RuntimeError(
            "Gemini API key is required "
            "for voice transcription."
        )

    language = settings.get(
        "language",
        "English",
    )

    if language == "Urdu":

        instruction = (
            "Transcribe the speech into Urdu script."
        )

    elif language == "English + Urdu":

        instruction = (
            "Transcribe the speech exactly, "
            "preserving English and Urdu words."
        )

    else:

        instruction = (
            "Transcribe the speech into English."
        )

    prompt = f"""
You are a speech-to-text engine.

{instruction}

Return ONLY the transcription.

Do not explain anything.

Do not summarize.

Do not add quotation marks.

Do not invent words.
"""

    encoded = base64.b64encode(
        audio_bytes
    ).decode("utf-8")

    contents = [
        {
            "role": "user",
            "parts": [
                {
                    "text": prompt
                },
                {
                    "inline_data": {
                        "mime_type":
                            mime_type or "audio/wav",
                        "data":
                            encoded,
                    },
                },
            ],
        }
    ]

    return gemini_request(
        api_key,
        clean_text(
            settings.get(
                "default_model"
            )
            or DEFAULT_MODEL
        ),
        contents,
        temperature=0.0,
    )


# ============================================================
# TEXT TO SPEECH
# ============================================================

def text_to_speech(
    text,
    language,
):

    try:

        from gtts import gTTS

        lang = (
            "ur"
            if language == "Urdu"
            else "en"
        )

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


# ============================================================
# PDF EXPORT
# ============================================================

def export_to_pdf(messages):

    """
    Safe PDF exporter.

    This version intentionally does NOT use re.sub().
    It also manually breaks long continuous text so
    FPDF2 cannot fail with:

    FPDFException:
    Not enough horizontal space to render a single character
    """

    if FPDF is None:
        return None

    pdf = FPDF()

    pdf.set_auto_page_break(
        auto=True,
        margin=15,
    )

    pdf.add_page()

    pdf.set_font(
        "Arial",
        size=14,
    )

    pdf.cell(
        0,
        10,
        "Fenix AI - Chat Transcript",
        ln=True,
        align="C",
    )

    pdf.ln(6)

    try:

        from fpdf.enums import WrapMode

        wrap_mode = WrapMode.CHAR

    except Exception:

        wrap_mode = "CHAR"

    for message in messages:

        role = str(
            message.get(
                "role",
                "",
            )
        ).upper()

        timestamp = str(
            message.get(
                "timestamp",
                "",
            )
        )

        header = (
            f"[{timestamp}] {role}"
        )

        # Convert header to an Arial-safe encoding.
        safe_header = header.encode(
            "latin-1",
            errors="replace",
        ).decode(
            "latin-1"
        )

        content = str(
            message.get(
                "content",
                "",
            )
        )

        # Remove control characters WITHOUT regex.
        cleaned = []

        for char in content:

            code = ord(char)

            if (
                code == 9
                or code == 10
                or code == 13
                or code >= 32
            ):

                cleaned.append(char)

            else:

                cleaned.append(" ")

        content = "".join(cleaned)

        # Normalize newlines.
        content = content.replace(
            "\r\n",
            "\n",
        )

        content = content.replace(
            "\r",
            "\n",
        )

        # Hard-wrap every long line.
        #
        # This protects against:
        # - URLs
        # - hashes
        # - code
        # - JSON
        # - long IDs
        # - long unbroken text
        wrapped_lines = []

        for line in content.split("\n"):

            if len(line) <= 70:

                wrapped_lines.append(
                    line
                )

            else:

                for i in range(
                    0,
                    len(line),
                    70,
                ):

                    wrapped_lines.append(
                        line[i:i + 70]
                    )

        content = "\n".join(
            wrapped_lines
        )

        safe_content = content.encode(
            "latin-1",
            errors="replace",
        ).decode(
            "latin-1"
        )

        if not safe_content.strip():

            safe_content = "(empty message)"

        pdf.set_font(
            "Arial",
            size=9,
        )

        pdf.multi_cell(
            0,
            6,
            safe_header,
            wrapmode=wrap_mode,
        )

        pdf.set_font(
            "Arial",
            size=10,
        )

        pdf.multi_cell(
            0,
            6,
            safe_content,
            wrapmode=wrap_mode,
        )

        pdf.ln(3)

    output = pdf.output(
        dest="S"
    )

    if isinstance(
        output,
        str,
    ):

        return output.encode(
            "latin-1"
        )

    return bytes(output)


# ============================================================
# TXT EXPORT
# ============================================================

def export_to_txt(messages):

    lines = [
        "FENIX AI - CHAT EXPORT",
        "======================",
        "",
    ]

    for message in messages:

        lines.append(
            f"[{message['timestamp']}] "
            f"{message['role'].upper()}:"
        )

        lines.append(
            message["content"]
        )

        lines.append("")

    return "\n".join(
        lines
    ).encode(
        "utf-8"
    )


# ============================================================
# ZIP EXPORT
# ============================================================

def export_to_zip(messages):

    buffer = io.BytesIO()

    with zipfile.ZipFile(
        buffer,
        "w",
        zipfile.ZIP_DEFLATED,
    ) as archive:

        archive.writestr(
            "chat_transcript.txt",
            export_to_txt(messages),
        )

        pdf_data = export_to_pdf(
            messages
        )

        if pdf_data:

            archive.writestr(
                "chat_transcript.pdf",
                pdf_data,
            )

    return buffer.getvalue()


# ============================================================
# SESSION STATE
# ============================================================

if "user" not in st.session_state:

    st.session_state.user = None

if "settings" not in st.session_state:

    st.session_state.settings = {}

if "current_conversation_id" not in st.session_state:

    st.session_state.current_conversation_id = None

if "uploaded_file_context" not in st.session_state:

    st.session_state.uploaded_file_context = ""

if "attached_image" not in st.session_state:

    st.session_state.attached_image = None

if "last_transcript" not in st.session_state:

    st.session_state.last_transcript = ""


# ============================================================
# THEME
# ============================================================

def apply_theme():

    theme = st.session_state.settings.get(
        "theme",
        "dark",
    )

    if theme == "light":

        background = "#ffffff"
        surface = "#f5f7fa"
        surface2 = "#ffffff"
        text = "#111111"
        muted = "#667085"
        border = "#d9dee7"
        accent = "#1769ff"

    else:

        background = "#0b0f14"
        surface = "#111820"
        surface2 = "#151e27"
        text = "#f5f7fa"
        muted = "#9aa8b5"
        border = "#263442"
        accent = "#39b7ff"

    st.markdown(
        f"""
        <style>

        html,
        body,
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
            max-width: 1500px;
            padding-top: 2rem;
            padding-bottom: 4rem;
        }}

        .fenix-card {{
            background: {surface2};
            border: 1px solid {border};
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 15px;
        }}

        .status {{
            display: inline-block;
            border: 1px solid {border};
            border-radius: 999px;
            padding: 5px 11px;
            margin-right: 6px;
            color: {muted};
            font-size: 12px;
        }}

        .user-message {{
            background: {surface2};
            border: 1px solid {border};
            border-radius: 15px;
            padding: 16px;
            margin: 10px 0;
        }}

        .assistant-message {{
            background: {surface};
            border-left: 4px solid {accent};
            border-top: 1px solid {border};
            border-right: 1px solid {border};
            border-bottom: 1px solid {border};
            border-radius: 15px;
            padding: 16px;
            margin: 10px 0 20px 0;
        }}

        </style>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# LOGIN
# ============================================================

if st.session_state.user is None:

    st.session_state.settings = {
        "theme": "dark"
    }

    apply_theme()

    st.markdown(
        """
        <div style="
            text-align:center;
            padding:45px 0 25px 0;
        ">
            <div style="font-size:60px;">⚡</div>
            <h1>Fenix AI</h1>
            <p>
                AI command center powered by Gemini
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    login_tab, register_tab = st.tabs(
        [
            "Sign In",
            "Create Account",
        ]
    )

    with login_tab:

        with st.form("login_form"):

            username = st.text_input(
                "Username"
            )

            password = st.text_input(
                "Password",
                type="password",
            )

            submitted = st.form_submit_button(
                "Access Dashboard",
                use_container_width=True,
            )

        if submitted:

            user = authenticate_user(
                username,
                password,
            )

            if user:

                st.session_state.user = user

                st.session_state.settings = (
                    get_user_settings(
                        user["id"]
                    )
                )

                st.session_state.current_conversation_id = None

                st.rerun()

            else:

                st.error(
                    "Invalid username or password."
                )

    with register_tab:

        with st.form("register_form"):

            new_username = st.text_input(
                "Choose Username"
            )

            new_password = st.text_input(
                "Password",
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

                st.error(
                    "Passwords do not match."
                )

            else:

                success, message = register_user(
                    new_username,
                    new_password,
                )

                if success:

                    st.success(
                        message
                    )

                else:

                    st.error(
                        message
                    )

    st.stop()


# ============================================================
# LOAD USER
# ============================================================

user = st.session_state.user

st.session_state.settings = (
    get_user_settings(
        user["id"]
    )
)

settings = st.session_state.settings

apply_theme()


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.title("⚡ Fenix AI")

    st.caption(
        f"User: {user['username']}"
    )

    if get_gemini_api_key(settings):

        st.success(
            "Gemini AI: Connected"
        )

    else:

        st.warning(
            "Gemini AI: Not configured"
        )

    st.divider()

    col1, col2 = st.columns(2)

    with col1:

        if st.button(
            "➕ New Chat",
            use_container_width=True,
        ):

            new_chat = create_conversation(
                user["id"],
                "New Chat",
            )

            st.session_state.current_conversation_id = (
                new_chat
            )

            st.session_state.uploaded_file_context = ""
            st.session_state.attached_image = None
            st.session_state.last_transcript = ""

            st.rerun()

    with col2:

        if st.button(
            "🚪 Logout",
            use_container_width=True,
        ):

            st.session_state.user = None
            st.session_state.current_conversation_id = None

            st.rerun()

    st.divider()

    search = st.text_input(
        "🔍 Search chats",
        placeholder="Search conversations...",
    )

    conversations = load_conversations(
        user["id"],
        search,
    )

    if conversations:

        st.subheader(
            "Conversations"
        )

        for conversation in conversations:

            active = (
                conversation["id"]
                == st.session_state.current_conversation_id
            )

            prefix = (
                "🟢 "
                if active
                else "💬 "
            )

            if st.button(
                prefix
                + conversation["title"][:35],
                key="open_"
                + conversation["id"],
                use_container_width=True,
            ):

                st.session_state.current_conversation_id = (
                    conversation["id"]
                )

                st.rerun()

            d1, d2 = st.columns(2)

            with d1:

                if st.button(
                    "🗑️",
                    key="delete_"
                    + conversation["id"],
                    use_container_width=True,
                ):

                    delete_conversation(
                        conversation["id"]
                    )

                    if (
                        st.session_state.current_conversation_id
                        == conversation["id"]
                    ):

                        st.session_state.current_conversation_id = None

                    st.rerun()

            with d2:

                if st.button(
                    "✏️",
                    key="rename_"
                    + conversation["id"],
                    use_container_width=True,
                ):

                    st.session_state[
                        "rename_"
                        + conversation["id"]
                    ] = True

            if st.session_state.get(
                "rename_"
                + conversation["id"],
                False,
            ):

                new_title = st.text_input(
                    "New title",
                    value=conversation["title"],
                    key="title_"
                    + conversation["id"],
                )

                if st.button(
                    "Save",
                    key="save_"
                    + conversation["id"],
                ):

                    rename_conversation(
                        conversation["id"],
                        new_title,
                    )

                    st.session_state[
                        "rename_"
                        + conversation["id"]
                    ] = False

                    st.rerun()

    else:

        st.info(
            "No conversations yet."
        )

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


# ============================================================
# AUTO SELECT CHAT
# ============================================================

if page in (
    "💬 Chat",
    "🎙️ Voice",
    "📎 Files",
):

    if not st.session_state.current_conversation_id:

        existing = load_conversations(
            user["id"]
        )

        if existing:

            st.session_state.current_conversation_id = (
                existing[0]["id"]
            )

        else:

            st.session_state.current_conversation_id = (
                create_conversation(
                    user["id"],
                    "New Chat",
                )
            )

        st.rerun()


# ============================================================
# CHAT
# ============================================================

if page == "💬 Chat":

    st.title(
        "JARVIS / Fenix AI Command Center"
    )

    st.markdown(
        """
        <span class="status">
        AI ENGINE: GEMINI
        </span>

        <span class="status">
        DATABASE: ONLINE
        </span>

        <span class="status">
        VOICE: READY
        </span>
        """,
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

            <h3>Welcome to Fenix AI</h3>

            <p>
            Ask questions, analyze supported files,
            use English or Urdu, and use the Gemini
            AI engine to generate responses.
            </p>

            </div>
            """,
            unsafe_allow_html=True,
        )

    for message in messages:

        if message["role"] == "user":

            st.markdown(
                f"""
                <div class="user-message">

                <strong>You</strong>

                <br><br>

                {message["content"]}

                </div>
                """,
                unsafe_allow_html=True,
            )

        else:

            st.markdown(
                f"""
                <div class="assistant-message">

                <strong>⚡ JARVIS</strong>

                <br><br>

                {message["content"]}

                </div>
                """,
                unsafe_allow_html=True,
            )

    if st.session_state.uploaded_file_context:

        st.info(
            "File context is attached to this conversation."
        )

    prompt = st.chat_input(
        "Ask JARVIS anything..."
    )

    if prompt:

        prompt = prompt.strip()

        if prompt:

            save_message(
                st.session_state.current_conversation_id,
                "user",
                prompt,
            )

            with st.spinner(
                "JARVIS is thinking..."
            ):

                try:

                    current_messages = load_messages(
                        st.session_state.current_conversation_id
                    )

                    answer = generate_answer(
                        settings,
                        current_messages,
                        st.session_state.uploaded_file_context,
                        st.session_state.attached_image,
                    )

                except Exception as exc:

                    answer = (
                        "⚠️ "
                        + str(exc)
                    )

            save_message(
                st.session_state.current_conversation_id,
                "assistant",
                answer,
            )

            st.rerun()


# ============================================================
# VOICE
# ============================================================

elif page == "🎙️ Voice":

    st.title(
        "🎙️ JARVIS Voice Input"
    )

    st.markdown(
        """
        <div class="fenix-card">

        <h3>Real Voice Input</h3>

        <p>
        Record your voice, send the audio to Gemini
        for transcription, review the recognized text,
        and send it to JARVIS.
        </p>

        </div>
        """,
        unsafe_allow_html=True,
    )

    if not get_gemini_api_key(settings):

        st.warning(
            "Configure your Gemini API key first."
        )

    language = settings.get(
        "language",
        "English",
    )

    st.info(
        f"Voice language: {language}"
    )

    st.subheader(
        "1. Record your voice"
    )

    if hasattr(st, "audio_input"):

        audio = st.audio_input(
            "🎙️ Record",
            key="jarvis_audio",
        )

        if audio:

            st.audio(audio)

            st.subheader(
                "2. Convert speech to text"
            )

            if st.button(
                "📝 Transcribe with Gemini",
                use_container_width=True,
            ):

                try:

                    with st.spinner(
                        "Transcribing..."
                    ):

                        transcript = transcribe_audio(
                            audio.getvalue(),
                            getattr(
                                audio,
                                "type",
                                None,
                            )
                            or "audio/wav",
                            settings,
                        )

                    st.session_state.last_transcript = (
                        transcript
                    )

                    st.success(
                        "Transcription complete."
                    )

                except Exception as exc:

                    st.error(
                        f"Voice input error: {exc}"
                    )

    else:

        st.error(
            "Your Streamlit version does not support "
            "st.audio_input(). Update Streamlit."
        )

    if st.session_state.last_transcript:

        st.subheader(
            "3. Review recognized text"
        )

        edited_transcript = st.text_area(
            "Transcript",
            value=st.session_state.last_transcript,
            height=150,
        )

        if st.button(
            "⚡ Send to JARVIS",
            type="primary",
            use_container_width=True,
        ):

            if edited_transcript.strip():

                save_message(
                    st.session_state.current_conversation_id,
                    "user",
                    edited_transcript.strip(),
                )

                with st.spinner(
                    "JARVIS is thinking..."
                ):

                    try:

                        current_messages = load_messages(
                            st.session_state.current_conversation_id
                        )

                        answer = generate_answer(
                            settings,
                            current_messages,
                            st.session_state.uploaded_file_context,
                            st.session_state.attached_image,
                        )

                    except Exception as exc:

                        answer = (
                            "⚠️ "
                            + str(exc)
                        )

                save_message(
                    st.session_state.current_conversation_id,
                    "assistant",
                    answer,
                )

                st.session_state.last_transcript = ""

                st.rerun()

            else:

                st.warning(
                    "No speech was recognized."
                )


# ============================================================
# FILES
# ============================================================

elif page == "📎 Files":

    st.title(
        "📎 Files & Visual Analysis"
    )

    st.write(
        "Upload supported documents, source files, "
        "ZIP archives, PDFs or images."
    )

    uploaded = st.file_uploader(
        "Upload a file",
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
            "📥 Attach to current chat",
            use_container_width=True,
        ):

            context, image = (
                extract_uploaded_file(
                    uploaded
                )
            )

            st.session_state.uploaded_file_context = (
                context
            )

            st.session_state.attached_image = (
                image
            )

            st.success(
                f"{uploaded.name} attached."
            )

    if st.session_state.attached_image:

        st.subheader(
            "Attached image"
        )

        st.image(
            st.session_state.attached_image,
            use_container_width=True,
        )

    if st.session_state.uploaded_file_context:

        st.subheader(
            "Extracted text"
        )

        preview = (
            st.session_state.uploaded_file_context
        )

        if len(preview) > 12000:

            preview = (
                preview[:12000]
                + "\n\n[Preview truncated]"
            )

        st.text_area(
            "File context",
            value=preview,
            height=400,
            disabled=True,
        )

        if st.button(
            "🧹 Clear attachment"
        ):

            st.session_state.uploaded_file_context = ""
            st.session_state.attached_image = None

            st.rerun()


# ============================================================
# SETTINGS
# ============================================================

elif page == "⚙️ Settings":

    st.title(
        "⚙️ Settings"
    )

    general_tab, voice_tab, gemini_tab = st.tabs(
        [
            "General",
            "Voice",
            "Gemini AI",
        ]
    )

    with general_tab:

        theme = st.selectbox(
            "Theme",
            [
                "dark",
                "light",
            ],
            index=(
                0
                if settings.get(
                    "theme",
                    "dark",
                ) == "dark"
                else 1
            ),
        )

        languages = [
            "English",
            "Urdu",
            "English + Urdu",
        ]

        current_language = settings.get(
            "language",
            "English",
        )

        if current_language not in languages:

            current_language = "English"

        language = st.selectbox(
            "Response language",
            languages,
            index=languages.index(
                current_language
            ),
        )

        custom_prompt = st.text_area(
            "Custom JARVIS instruction",
            value=settings.get(
                "custom_sys_prompt",
                "",
            ),
            height=160,
        )

    with voice_tab:

        voice_enabled = st.checkbox(
            "Enable voice features",
            value=bool(
                settings.get(
                    "voice_enabled",
                    1,
                )
            ),
        )

        auto_send_voice = st.checkbox(
            "Auto-send voice commands",
            value=bool(
                settings.get(
                    "auto_send_voice",
                    0,
                )
            ),
            help=(
                "Leave disabled if you want to "
                "review transcripts before sending."
            ),
        )

        st.info(
            "Voice recording uses Streamlit's microphone "
            "input and Gemini for transcription."
        )

    with gemini_tab:

        st.subheader(
            "Gemini AI Configuration"
        )

        model = st.text_input(
            "Gemini model",
            value=settings.get(
                "default_model",
                DEFAULT_MODEL,
            ),
        )

        gemini_key = st.text_input(
            "Gemini API Key",
            value=settings.get(
                "api_key_gemini",
                "",
            ),
            type="password",
        )

        st.caption(
            "For production deployments, use a server-side "
            "secret/environment variable when possible."
        )

        if st.button(
            "🧪 Test Gemini Connection",
            use_container_width=True,
        ):

            if not gemini_key.strip():

                st.error(
                    "Enter a Gemini API key first."
                )

            else:

                try:

                    result = gemini_request(
                        gemini_key.strip(),
                        model.strip()
                        or DEFAULT_MODEL,
                        [
                            {
                                "role": "user",
                                "parts": [
                                    {
                                        "text":
                                        "Reply exactly with: "
                                        "GEMINI CONNECTION OK"
                                    }
                                ],
                            }
                        ],
                        temperature=0.0,
                    )

                    st.success(
                        result
                    )

                except Exception as exc:

                    st.error(
                        str(exc)
                    )

        st.subheader(
            "Optional Groq API Key"
        )

        groq_key = st.text_input(
            "Groq API Key",
            value=settings.get(
                "api_key_groq",
                "",
            ),
            type="password",
        )

    if st.button(
        "💾 Save Settings",
        type="primary",
        use_container_width=True,
    ):

        update_user_settings(
            user["id"],
            theme,
            model.strip()
            or DEFAULT_MODEL,
            gemini_key.strip(),
            groq_key.strip(),
            custom_prompt,
            language,
            voice_enabled,
            auto_send_voice,
        )

        st.session_state.settings = (
            get_user_settings(
                user["id"]
            )
        )

        st.success(
            "Settings saved successfully."
        )

        st.rerun()


# ============================================================
# DIAGNOSTICS
# ============================================================

elif page == "📊 Diagnostics":

    st.title(
        "📊 System Diagnostics"
    )

    checks = [
        (
            "Application",
            True,
        ),
        (
            "Database",
            os.path.exists(
                DB_FILE
            ),
        ),
        (
            "Authentication",
            st.session_state.user is not None,
        ),
        (
            "Gemini API Key",
            bool(
                get_gemini_api_key(
                    settings
                )
            ),
        ),
        (
            "Voice Recorder",
            hasattr(
                st,
                "audio_input",
            ),
        ),
        (
            "PDF Export",
            FPDF is not None,
        ),
    ]

    for name, status in checks:

        if status:

            st.success(
                f"{name}: READY"
            )

        else:

            st.warning(
                f"{name}: NOT READY"
            )

    st.divider()

    st.subheader(
        "Configuration"
    )

    st.json(
        {
            "user":
                user["username"],

            "theme":
                settings.get(
                    "theme"
                ),

            "language":
                settings.get(
                    "language"
                ),

            "gemini_model":
                settings.get(
                    "default_model"
                ),

            "gemini_configured":
                bool(
                    get_gemini_api_key(
                        settings
                    )
                ),

            "voice_enabled":
                bool(
                    settings.get(
                        "voice_enabled",
                        1,
                    )
                ),

            "auto_send_voice":
                bool(
                    settings.get(
                        "auto_send_voice",
                        0,
                    )
                ),

            "database":
                DB_FILE,

            "conversation":
                st.session_state.current_conversation_id,
        }
    )


# ============================================================
# EXPORT CURRENT CHAT
# ============================================================

if (
    st.session_state.current_conversation_id
    and page in (
        "💬 Chat",
        "🎙️ Voice",
    )
):

    with st.sidebar:

        st.divider()

        st.subheader(
            "Export Chat"
        )

        current_messages = load_messages(
            st.session_state.current_conversation_id
        )

        if current_messages:

            st.download_button(
                "⬇️ TXT",
                data=export_to_txt(
                    current_messages
                ),
                file_name="fenix_chat.txt",
                mime="text/plain",
                use_container_width=True,
            )

            pdf_data = export_to_pdf(
                current_messages
            )

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
                data=export_to_zip(
                    current_messages
                ),
                file_name="fenix_chat.zip",
                mime="application/zip",
                use_container_width=True,
            )
```
