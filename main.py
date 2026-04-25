import streamlit as st
from google import genai
from PIL import Image
import io

# --- 1. THEME & STYLING ---
st.set_page_config(page_title="TahaGpt", page_icon="🤖", layout="wide")

# This CSS makes the chat look modern and clean
st.markdown("""
    <style>
        /* Main background */
        .stApp { background-color: #f7f7f8; }
        
        /* Sidebar styling */
        [data-testid="stSidebar"] {
            background-color: #202123;
            color: white;
        }
        
        /* Chat Input at the bottom */
        .stChatInput {
            border-radius: 15px !important;
            box-shadow: 0 0 15px rgba(0,0,0,0.1);
        }

        /* Message Bubbles */
        .stChatMessage {
            border-radius: 10px;
            padding: 10px;
            margin-bottom: 10px;
        }
    </style>
    """, unsafe_allow_html=True)

# --- 2. API CLIENT ---
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# --- 3. SIDEBAR (The Clean Menu) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/4712/4712035.png", width=80)
    st.title("TahaGpt Pro")
    
    # Simple "+" icon for new chat
    if st.button("➕ New Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    
    # Clean tool selection
    tool_choice = st.selectbox(
        "Choose Assistant:", 
        ["💬 Standard Chat", "🎨 Image Creator", "🖼️ Visual Analysis"]
    )
    
    st.divider()
    st.caption("v2.5 Stable | 2026")

# --- 4. MAIN CHAT INTERFACE ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display welcome if chat is empty
if not st.session_state.messages:
    st.info("👋 Welcome, Taha. What are we building today?")

# Render Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- 5. LOGIC FOR TOOLS ---

if tool_choice == "💬 Standard Chat":
    if prompt := st.chat_input("Message TahaGpt..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        
        with st.chat_message("assistant"):
            st.markdown(response.text)
        st.session_state.messages.append({"role": "assistant", "content": response.text})

elif tool_choice == "🖼️ Visual Analysis":
    st.subheader("Analyze an Image")
    file = st.file_uploader("Upload Image", type=["png", "jpg", "jpeg"])
    if file:
        img = Image.open(file)
        st.image(img, width=400)
        if st.button("Explain this image"):
            res = client.models.generate_content(model="gemini-2.0-flash", contents=["What is in this photo?", img])
            st.write(res.text)

elif tool_choice == "🎨 Image Creator":
    st.subheader("Generate an Image")
    prompt = st.text_input("Describe the image you want to create:")
    if st.button("Generate"):
        # This calls the internal image model
        st.warning("Note: Image generation requires a dedicated Imagen-3 key in this SDK version.")
