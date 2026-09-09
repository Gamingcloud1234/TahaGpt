import io
import os
import sqlite3
import uuid
import zipfile
import base64
from datetime import datetime

import streamlit as st
import requests
import bcrypt

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

try:
    from fpdf import FPDF
except ImportError:
    FPDF = None


# ============================================================
# CONFIG
# ============================================================

st.set_page_config(
    page_title="JARVIS AI",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_FILE = "jarvis.db"
DEFAULT_MODEL = "gemini-2.5-flash"


# ============================================================
# DATABASE
# ============================================================

def db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                user_id INTEGER PRIMARY KEY,
                gemini_key TEXT DEFAULT '',
                model TEXT DEFAULT 'gemini-2.5-flash',
                language TEXT DEFAULT 'English',
                theme TEXT DEFAULT 'dark',
                system_prompt TEXT DEFAULT '',
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(chat_id) REFERENCES chats(id) ON DELETE CASCADE
            )
        """)
        conn.commit()


init_db()


# ============================================================
# AUTH
# ============================================================

def register(username, password):
    username = username.strip()

    if len(username) < 3:
        return False, "Username must be at least 3 characters."

    if len(password) < 6:
        return False, "Password must be at least 6 characters."

    hashed = bcrypt.hashpw(
        password.encode(),
        bcrypt.gensalt()
    ).decode()

    try:
        with db() as conn:
            cur = conn.execute(
                """
                INSERT INTO users(username, password, created_at)
                VALUES (?, ?, ?)
                """,
                (username, hashed, datetime.now().isoformat())
            )
            user_id = cur.lastrowid

            conn.execute(
                """
                INSERT INTO settings(user_id, model, language, theme)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, DEFAULT_MODEL, "English", "dark")
            )
            conn.commit()

        return True, "Account created."

    except sqlite3.IntegrityError:
        return False, "Username already exists."


def login(username, password):
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username.strip(),)
        ).fetchone()

    if not row:
        return None

    try:
        valid = bcrypt.checkpw(
            password.encode(),
            row["password"].encode()
        )
    except Exception:
        valid = False

    return dict(row) if valid else None


# ============================================================
# SETTINGS
# ============================================================

def get_settings(user_id):
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM settings WHERE user_id = ?",
            (user_id,)
        ).fetchone()

    if row:
        return dict(row)

    return {
        "gemini_key": "",
        "model": DEFAULT_MODEL,
        "language": "English",
        "theme": "dark",
        "system_prompt": "",
    }


def save_settings(user_id, gemini_key, model, language, theme, system_prompt):
    with db() as conn:
        conn.execute(
            """
            UPDATE settings
            SET gemini_key = ?,
                model = ?,
                language = ?,
                theme = ?,
                system_prompt = ?
            WHERE user_id = ?
            """,
            (
                gemini_key.strip(),
                model.strip() or DEFAULT_MODEL,
                language,
                theme,
                system_prompt,
                user_id,
            )
        )
        conn.commit()


# ============================================================
# CHAT DATABASE
# ============================================================

def create_chat(user_id, title="New Chat"):
    chat_id = "chat_" + uuid.uuid4().hex
    now = datetime.now().isoformat()

    with db() as conn:
        conn.execute(
            """
            INSERT INTO chats(id, user_id, title, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (chat_id, user_id, title, now)
        )
        conn.commit()

    return chat_id


def list_chats(user_id):
    with db() as conn:
        rows = conn.execute(
            """
            SELECT * FROM chats
            WHERE user_id = ?
            ORDER BY updated_at DESC
            """,
            (user_id,)
        ).fetchall()

    return [dict(r) for r in rows]


def rename_chat(chat_id, title):
    with db() as conn:
        conn.execute(
            "UPDATE chats SET title = ? WHERE id = ?",
            (title.strip() or "New Chat", chat_id)
        )
        conn.commit()


def delete_chat(chat_id):
    with db() as conn:
        conn.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
        conn.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
        conn.commit()


def get_messages(chat_id):
    with db() as conn:
        rows = conn.execute(
            """
            SELECT * FROM messages
            WHERE chat_id = ?
            ORDER BY id ASC
            """,
            (chat_id,)
        ).fetchall()

    return [dict(r) for r in rows]


def save_message(chat_id, role, content):
    now = datetime.now().isoformat()

    with db() as conn:
        conn.execute(
            """
            INSERT INTO messages(chat_id, role, content, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (chat_id, role, content, now)
        )

        conn.execute(
            """
            UPDATE chats SET updated_at = ?
            WHERE id = ?
            """,
            (now, chat_id)
        )
        conn.commit()


# ============================================================
# GEMINI
# ============================================================

def gemini_key(settings):
    return (
        settings.get("gemini_key", "").strip()
        or os.environ.get("GEMINI_API_KEY", "").strip()
    )


def language_instruction(language):
    if language == "Urdu":
        return "Answer in detailed natural Urdu. Keep necessary technical terms in English."
    if language == "English + Urdu":
        return "Answer first in clear English, then provide a detailed Urdu explanation under 'اردو وضاحت'."
    return "Answer in clear English."


def system_instruction(settings):
    text = f"""
You are JARVIS, a fast, intelligent and professional AI assistant.

{language_instruction(settings.get("language", "English"))}

Give accurate, useful and well-structured answers.
Use headings and bullet points when helpful.
Explain difficult subjects step by step.
Never claim access to classified information, private systems, live military systems,
or real-time radar feeds unless such data is explicitly supplied by the user.

For military, air-force, army, navy, weapons, radar and defense topics,
provide educational, historical and high-level technical information.
Do not provide instructions for harming people, weapon targeting, weapon firing,
or construction of dangerous weapons.

Do not invent facts. If uncertain, say so.

You can help with:
- general knowledge
- science and technology
- engineering
- construction materials
- programming
- mathematics
- education
- history
- geography
- defense technology at a safe educational level
- air, land and naval systems at a general informational level

Be concise when the question is simple and detailed when the question requires detail.
"""
    custom = settings.get("system_prompt", "").strip()

    if custom:
        text += "\n\nAdditional user preferences:\n" + custom

    return text.strip()


def gemini_generate(settings, messages, file_context="", image=None):
    key = gemini_key(settings)

    if not key:
        raise RuntimeError(
            "Gemini API key is missing. Open Settings and add your Gemini API key."
        )

    model = settings.get("model", DEFAULT_MODEL).strip() or DEFAULT_MODEL

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        + model
        + ":generateContent"
    )

    parts = [
        {"text": system_instruction(settings)}
    ]

    if file_context:
        parts.append({
            "text": "\nUPLOADED FILE CONTEXT:\n" + file_context[:60000]
        })

    contents = []

    for message in messages:
        role = "model" if message["role"] == "assistant" else "user"

        msg_parts = [{"text": message["content"]}]

        contents.append({
            "role": role,
            "parts": msg_parts
        })

    if contents:
        contents[0]["parts"].insert(
            0,
            {"text": system_instruction(settings)}
        )

    if image is not None and contents:
        image_buffer = io.BytesIO()
        image.save(image_buffer, format="PNG")

        encoded = base64.b64encode(
            image_buffer.getvalue()
        ).decode()

        contents[-1]["parts"].append({
            "inline_data": {
                "mime_type": "image/png",
                "data": encoded
            }
        })

    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": 0.35
        }
    }

    response = requests.post(
        url,
        params={"key": key},
        json=payload,
        timeout=120
    )

    if response.status_code >= 400:
        try:
            error = response.json()
        except Exception:
            error = response.text

        raise RuntimeError(
            f"Gemini API error {response.status_code}: {error}"
        )

    data = response.json()

    candidates = data.get("candidates", [])

    if not candidates:
        raise RuntimeError("Gemini returned no answer.")

    answer_parts = (
        candidates[0]
        .get("content", {})
        .get("parts", [])
    )

    answer = "".join(
        p.get("text", "")
        for p in answer_parts
        if p.get("text")
    ).strip()

    if not answer:
        raise RuntimeError("Gemini returned an empty answer.")

    return answer


# ============================================================
# VOICE
# ============================================================

def transcribe_audio(settings, audio_bytes, mime_type):
    key = gemini_key(settings)

    if not key:
        raise RuntimeError(
            "Add your Gemini API key in Settings before using voice input."
        )

    model = settings.get("model", DEFAULT_MODEL).strip() or DEFAULT_MODEL

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        + model
        + ":generateContent"
    )

    encoded = base64.b64encode(audio_bytes).decode()

    language = settings.get("language", "English")

    if language == "Urdu":
        prompt = "Transcribe this audio into Urdu script. Return only the transcription."
    elif language == "English + Urdu":
        prompt = "Transcribe this audio exactly, preserving English and Urdu words. Return only the transcription."
    else:
        prompt = "Transcribe this audio into English. Return only the transcription."

    payload = {
        "contents": [{
            "role": "user",
            "parts": [
                {"text": prompt},
                {
                    "inline_data": {
                        "mime_type": mime_type or "audio/wav",
                        "data": encoded
                    }
                }
            ]
        }]
    }

    response = requests.post(
        url,
        params={"key": key},
        json=payload,
        timeout=120
    )

    if response.status_code >= 400:
        try:
            error = response.json()
        except Exception:
            error = response.text
        raise RuntimeError(
            f"Voice transcription error {response.status_code}: {error}"
        )

    data = response.json()
    candidates = data.get("candidates", [])

    if not candidates:
        raise RuntimeError("No transcription returned.")

    parts = candidates[0].get("content", {}).get("parts", [])

    return "".join(
        p.get("text", "")
        for p in parts
        if p.get("text")
    ).strip()


# ============================================================
# FILES
# ============================================================

def read_pdf(data):
    if PdfReader is None:
        return "Install pypdf to read PDF files."

    reader = PdfReader(io.BytesIO(data))
    text = []

    for page in reader.pages:
        text.append(page.extract_text() or "")

    return "\n\n".join(text).strip()


def read_file(uploaded):
    data = uploaded.getvalue()
    name = uploaded.name.lower()

    image = None

    if name.endswith((".png", ".jpg", ".jpeg", ".webp")) and Image:
        image = Image.open(io.BytesIO(data))
        return "Image attached for visual analysis.", image

    if name.endswith(".pdf"):
        return read_pdf(data), None

    if name.endswith(".zip"):
        result = []

        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            for filename in archive.namelist():
                lower = filename.lower()

                if lower.endswith((
                    ".txt", ".py", ".js", ".ts", ".tsx",
                    ".jsx", ".html", ".css", ".md",
                    ".json", ".xml", ".yaml", ".yml", ".csv"
                )):
                    try:
                        content = archive.read(filename).decode(
                            "utf-8",
                            errors="ignore"
                        )
                        result.append(
                            f"\n--- {filename} ---\n{content}"
                        )
                    except Exception:
                        pass

        return "\n".join(result), None

    try:
        return data.decode("utf-8", errors="ignore"), None
    except Exception:
        return "File uploaded, but text extraction is not available for this type.", None


# ============================================================
# PDF EXPORT
# ============================================================

def safe_pdf_text(text):
    """
    Removes control characters without regex and converts unsupported
    Unicode characters to safe text for the built-in PDF font.
    """
    output = []

    for char in str(text):
        code = ord(char)

        if code in (9, 10, 13) or code >= 32:
            output.append(char)
        else:
            output.append(" ")

    cleaned = "".join(output)

    return cleaned.encode(
        "latin-1",
        errors="replace"
    ).decode("latin-1")


def hard_wrap(text, width=65):
    lines = []

    for line in str(text).replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if not line:
            lines.append("")
            continue

        for i in range(0, len(line), width):
            lines.append(line[i:i + width])

    return "\n".join(lines)


def export_pdf(messages):
    if FPDF is None:
        return None

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Arial", size=16)
    pdf.cell(
        0,
        10,
        "JARVIS AI - Chat Transcript",
        ln=True,
        align="C"
    )
    pdf.ln(5)

    try:
        from fpdf.enums import WrapMode
        wrap = WrapMode.CHAR
    except Exception:
        wrap = "CHAR"

    for message in messages:
        timestamp = safe_pdf_text(
            message.get("created_at", "")
        )

        role = safe_pdf_text(
            message.get("role", "").upper()
        )

        content = safe_pdf_text(
            message.get("content", "")
        )

        content = hard_wrap(content, 65)

        pdf.set_font("Arial", size=9)
        pdf.multi_cell(
            0,
            6,
            f"[{timestamp}] {role}",
            wrapmode=wrap
        )

        pdf.set_font("Arial", size=10)
        pdf.multi_cell(
            0,
            6,
            content or "(empty message)",
            wrapmode=wrap
        )

        pdf.ln(3)

    output = pdf.output(dest="S")

    if isinstance(output, str):
        return output.encode("latin-1")

    return bytes(output)


def export_txt(messages):
    lines = ["JARVIS AI - CHAT TRANSCRIPT", ""]

    for message in messages:
        lines.append(
            f"[{message['created_at']}] {message['role'].upper()}"
        )
        lines.append(message["content"])
        lines.append("")

    return "\n".join(lines).encode("utf-8")


def export_zip(messages):
    buffer = io.BytesIO()

    with zipfile.ZipFile(
        buffer,
        "w",
        zipfile.ZIP_DEFLATED
    ) as archive:

        archive.writestr(
            "chat.txt",
            export_txt(messages)
        )

        pdf = export_pdf(messages)

        if pdf:
            archive.writestr(
                "chat.pdf",
                pdf
            )

    return buffer.getvalue()


# ============================================================
# SESSION
# ============================================================

if "user" not in st.session_state:
    st.session_state.user = None

if "chat_id" not in st.session_state:
    st.session_state.chat_id = None

if "file_context" not in st.session_state:
    st.session_state.file_context = ""

if "image" not in st.session_state:
    st.session_state.image = None

if "transcript" not in st.session_state:
    st.session_state.transcript = ""


# ============================================================
# LOGIN PAGE
# ============================================================

if st.session_state.user is None:

    st.markdown(
        """
        <div style="text-align:center;padding:50px 0 25px;">
            <div style="font-size:70px;">⚡</div>
            <h1>JARVIS AI</h1>
            <p>Intelligent AI Command Center</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    login_tab, register_tab = st.tabs(
        ["Sign In", "Create Account"]
    )

    with login_tab:
        with st.form("login"):
            username = st.text_input("Username")
            password = st.text_input(
                "Password",
                type="password"
            )

            submit = st.form_submit_button(
                "Access JARVIS",
                use_container_width=True
            )

        if submit:
            user = login(username, password)

            if user:
                st.session_state.user = user
                st.rerun()
            else:
                st.error("Invalid username or password.")

    with register_tab:
        with st.form("register"):
            username = st.text_input("New username")
            password = st.text_input(
                "Password",
                type="password"
            )
            confirm = st.text_input(
                "Confirm password",
                type="password"
            )

            submit = st.form_submit_button(
                "Create Account",
                use_container_width=True
            )

        if submit:
            if password != confirm:
                st.error("Passwords do not match.")
            else:
                ok, message = register(username, password)

                if ok:
                    st.success(message)
                else:
                    st.error(message)

    st.stop()


# ============================================================
# USER
# ============================================================

user = st.session_state.user
settings = get_settings(user["id"])


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.title("⚡ JARVIS AI")
    st.caption("User: " + user["username"])

    if gemini_key(settings):
        st.success("Gemini: CONNECTED")
    else:
        st.warning("Gemini: API KEY REQUIRED")

    st.divider()

    if st.button(
        "➕ New Chat",
        use_container_width=True
    ):
        st.session_state.chat_id = create_chat(
            user["id"],
            "New Chat"
        )
        st.session_state.file_context = ""
        st.session_state.image = None
        st.session_state.transcript = ""
        st.rerun()

    if st.button(
        "🚪 Logout",
        use_container_width=True
    ):
        st.session_state.user = None
        st.session_state.chat_id = None
        st.rerun()

    st.divider()

    chats = list_chats(user["id"])

    st.subheader("Chats")

    for chat in chats:
        if st.button(
            "💬 " + chat["title"][:32],
            key="open_" + chat["id"],
            use_container_width=True
        ):
            st.session_state.chat_id = chat["id"]
            st.rerun()

        c1, c2 = st.columns(2)

        with c1:
            if st.button(
                "✏️",
                key="rename_" + chat["id"]
            ):
                st.session_state[
                    "rename_" + chat["id"]
                ] = True

        with c2:
            if st.button(
                "🗑️",
                key="delete_" + chat["id"]
            ):
                delete_chat(chat["id"])

                if st.session_state.chat_id == chat["id"]:
                    st.session_state.chat_id = None

                st.rerun()

        if st.session_state.get(
            "rename_" + chat["id"],
            False
        ):
            title = st.text_input(
                "New title",
                value=chat["title"],
                key="title_" + chat["id"]
            )

            if st.button(
                "Save",
                key="save_" + chat["id"]
            ):
                rename_chat(chat["id"], title)
                st.session_state[
                    "rename_" + chat["id"]
                ] = False
                st.rerun()

    st.divider()

    section = st.radio(
        "Section",
        [
            "💬 Chat",
            "🎙️ Voice",
            "📎 Files",
            "⚙️ Settings",
            "📊 Diagnostics"
        ]
    )


# ============================================================
# CREATE CHAT WHEN NEEDED
# ============================================================

if not st.session_state.chat_id:
    chats = list_chats(user["id"])

    if chats:
        st.session_state.chat_id = chats[0]["id"]
    else:
        st.session_state.chat_id = create_chat(
            user["id"],
            "New Chat"
        )


# ============================================================
# CHAT
# ============================================================

if section == "💬 Chat":

    st.title("JARVIS AI")

    st.caption(
        "Ask questions in English or Urdu. "
        "Gemini powers the AI responses."
    )

    messages = get_messages(
        st.session_state.chat_id
    )

    for message in messages:

        with st.chat_message(
            "user" if message["role"] == "user" else "assistant"
        ):
            st.markdown(
                message["content"]
            )

    if st.session_state.file_context:
        st.info("A file is attached to this conversation.")

    prompt = st.chat_input(
        "Ask JARVIS anything..."
    )

    if prompt:

        save_message(
            st.session_state.chat_id,
            "user",
            prompt
        )

        current = get_messages(
            st.session_state.chat_id
        )

        with st.spinner("JARVIS is thinking..."):
            try:
                answer = gemini_generate(
                    settings,
                    current,
                    st.session_state.file_context,
                    st.session_state.image
                )
            except Exception as exc:
                answer = "⚠️ " + str(exc)

        save_message(
            st.session_state.chat_id,
            "assistant",
            answer
        )

        st.rerun()


# ============================================================
# VOICE
# ============================================================

elif section == "🎙️ Voice":

    st.title("🎙️ JARVIS Voice Input")

    st.write(
        "Record your voice, transcribe it with Gemini, "
        "review the text, and send it to JARVIS."
    )

    if not gemini_key(settings):
        st.warning(
            "Add your Gemini API key in Settings first."
        )

    if hasattr(st, "audio_input"):

        audio = st.audio_input(
            "🎙️ Record your voice",
            key="jarvis_voice"
        )

        if audio:

            st.audio(audio)

            if st.button(
                "📝 Transcribe with Gemini",
                use_container_width=True
            ):
                try:
                    with st.spinner("Transcribing..."):
                        st.session_state.transcript = transcribe_audio(
                            settings,
                            audio.getvalue(),
                            getattr(
                                audio,
                                "type",
                                None
                            ) or "audio/wav"
                        )

                    st.success("Transcription complete.")

                except Exception as exc:
                    st.error(str(exc))

    else:
        st.error(
            "Your Streamlit version does not provide st.audio_input(). "
            "Update Streamlit to the latest version."
        )

    if st.session_state.transcript:

        st.subheader("Review transcript")

        transcript = st.text_area(
            "Recognized speech",
            value=st.session_state.transcript,
            height=160
        )

        if st.button(
            "⚡ Send to JARVIS",
            type="primary",
            use_container_width=True
        ):

            if transcript.strip():

                save_message(
                    st.session_state.chat_id,
                    "user",
                    transcript.strip()
                )

                current = get_messages(
                    st.session_state.chat_id
                )

                with st.spinner("JARVIS is thinking..."):
                    try:
                        answer = gemini_generate(
                            settings,
                            current,
                            st.session_state.file_context,
                            st.session_state.image
                        )
                    except Exception as exc:
                        answer = "⚠️ " + str(exc)

                save_message(
                    st.session_state.chat_id,
                    "assistant",
                    answer
                )

                st.session_state.transcript = ""
                st.rerun()


# ============================================================
# FILES
# ============================================================

elif section == "📎 Files":

    st.title("📎 Files")

    uploaded = st.file_uploader(
        "Upload PDF, text, code, ZIP or image",
        type=[
            "pdf",
            "txt",
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
            "zip",
            "png",
            "jpg",
            "jpeg",
            "webp"
        ]
    )

    if uploaded:

        if st.button(
            "📥 Attach file",
            use_container_width=True
        ):
            try:
                context, image = read_file(uploaded)

                st.session_state.file_context = context
                st.session_state.image = image

                st.success(
                    uploaded.name + " attached successfully."
                )

            except Exception as exc:
                st.error(
                    "File processing failed: " + str(exc)
                )

    if st.session_state.image:
        st.image(
            st.session_state.image,
            caption="Attached image",
            use_container_width=True
        )

    if st.session_state.file_context:

        st.subheader("File text")

        preview = st.session_state.file_context

        if len(preview) > 12000:
            preview = (
                preview[:12000]
                + "\n\n[Preview truncated]"
            )

        st.text_area(
            "Extracted content",
            preview,
            height=400,
            disabled=True
        )

        if st.button("🧹 Clear attachment"):
            st.session_state.file_context = ""
            st.session_state.image = None
            st.rerun()


# ============================================================
# SETTINGS
# ============================================================

elif section == "⚙️ Settings":

    st.title("⚙️ Settings")

    theme = st.selectbox(
        "Theme",
        ["dark", "light"],
        index=0 if settings.get("theme") == "dark" else 1
    )

    language_options = [
        "English",
        "Urdu",
        "English + Urdu"
    ]

    current_language = settings.get(
        "language",
        "English"
    )

    if current_language not in language_options:
        current_language = "English"

    language = st.selectbox(
        "Response language",
        language_options,
        index=language_options.index(
            current_language
        )
    )

    model = st.text_input(
        "Gemini model",
        value=settings.get(
            "model",
            DEFAULT_MODEL
        )
    )

    gemini = st.text_input(
        "Gemini API Key",
        value=settings.get(
            "gemini_key",
            ""
        ),
        type="password"
    )

    st.caption(
        "You can also set GEMINI_API_KEY as an environment variable."
    )

    system_prompt = st.text_area(
        "Custom JARVIS instructions",
        value=settings.get(
            "system_prompt",
            ""
        ),
        height=180
    )

    if st.button(
        "🧪 Test Gemini",
        use_container_width=True
    ):

        if not gemini.strip():
            st.error("Enter a Gemini API key.")
        else:
            test_settings = dict(settings)
            test_settings["gemini_key"] = gemini
            test_settings["model"] = model

            try:
                answer = gemini_generate(
                    test_settings,
                    [{
                        "role": "user",
                        "content": "Reply exactly: GEMINI CONNECTION OK"
                    }]
                )

                st.success(answer)

            except Exception as exc:
                st.error(str(exc))

    if st.button(
        "💾 Save Settings",
        type="primary",
        use_container_width=True
    ):

        save_settings(
            user["id"],
            gemini,
            model,
            language,
            theme,
            system_prompt
        )

        st.success(
            "Settings saved successfully."
        )

        st.rerun()


# ============================================================
# DIAGNOSTICS
# ============================================================

elif section == "📊 Diagnostics":

    st.title("📊 Diagnostics")

    checks = [
        ("Database", os.path.exists(DB_FILE)),
        ("Gemini API Key", bool(gemini_key(settings))),
        ("Voice Input", hasattr(st, "audio_input")),
        ("PDF Export", FPDF is not None),
        ("PDF Reader", PdfReader is not None),
        ("Image Support", Image is not None),
    ]

    for name, status in checks:
        if status:
            st.success(name + ": READY")
        else:
            st.warning(name + ": NOT READY")

    st.divider()

    st.json({
        "user": user["username"],
        "model": settings.get("model"),
        "language": settings.get("language"),
        "theme": settings.get("theme"),
        "gemini_configured": bool(gemini_key(settings)),
        "current_chat": st.session_state.chat_id,
    })


# ============================================================
# EXPORT
# ============================================================

with st.sidebar:

    st.divider()
    st.subheader("Export current chat")

    current_messages = get_messages(
        st.session_state.chat_id
    )

    if current_messages:

        st.download_button(
            "⬇️ TXT",
            data=export_txt(current_messages),
            file_name="jarvis_chat.txt",
            mime="text/plain",
            use_container_width=True
        )

        pdf_data = export_pdf(current_messages)

        if pdf_data:

            st.download_button(
                "⬇️ PDF",
                data=pdf_data,
                file_name="jarvis_chat.pdf",
                mime="application/pdf",
                use_container_width=True
            )

        st.download_button(
            "⬇️ ZIP",
            data=export_zip(current_messages),
            file_name="jarvis_chat.zip",
            mime="application/zip",
            use_container_width=True
        )
