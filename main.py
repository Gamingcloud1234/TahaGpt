import streamlit as st
import google.generativeai as genai
from PIL import Image
import io

# --- PAGE SETUP ---
st.set_page_config(page_title="TahaGpt Super App", page_icon="🚀", layout="wide")

# --- STYLE ---
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 20px; }
    .stTextInput>div>div>input { border-radius: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- API SECRETS ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
except:
    st.error("Add your GEMINI_API_KEY to Streamlit Secrets!")
    st.stop()

# --- SIDEBAR (THE "+" ICON) ---
with st.sidebar:
    st.title("⚙️ TahaGpt Menu")
    if st.button("➕ New Chat"):
        st.session_state.messages = []
        st.rerun()
    
    st.divider()
    app_mode = st.radio("Choose Tool:", ["💬 Chatbot", "🖼️ Image Analysis", "📝 PDF/Text Tools"])
    st.info("Home WiFi Edition - Karachi")

# --- INITIALIZE CHAT ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- MODE 1: CHATBOT ---
if app_mode == "💬 Chatbot":
    st.header("💬 AI Conversation")
    
    # Display History
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask TahaGpt anything..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        model = genai.GenerativeModel('gemini-3.1-flash')
        response = model.generate_content(prompt)
        
        with st.chat_message("assistant"):
            st.markdown(response.text)
        st.session_state.messages.append({"role": "assistant", "content": response.text})

# --- MODE 2: IMAGE ANALYSIS ---
elif app_mode == "🖼️ Image Analysis":
    st.header("🖼️ Image Intelligence")
    uploaded_file = st.file_uploader("Upload a photo to see what's inside", type=['png', 'jpg', 'jpeg'])
    
    if uploaded_file:
        img = Image.open(uploaded_file)
        st.image(img, caption="Uploaded Image", use_container_width=True)
        
        user_ask = st.text_input("What should I do with this image?", "Describe this image in detail")
        
        if st.button("Analyze Image"):
            model = genai.GenerativeModel('gemini-3.1-flash')
            response = model.generate_content([user_ask, img])
            st.write("### Analysis:")
            st.write(response.text)

# --- MODE 3: PDF / TEXT ---
elif app_mode == "📝 PDF/Text Tools":
    st.header("📝 Document Assistant")
    st.write("Coming Soon: PDF Text Extraction for your 9th Grade Board notes!")
    st.warning("Note: Generating actual PDFs requires 'ReportLab' library in requirements.txt")
