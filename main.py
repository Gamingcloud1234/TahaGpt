import streamlit as st
import google.generativeai as genai

# --- PAGE CONFIG ---
st.set_page_config(page_title="TahaGpt", page_icon="🤖")

# --- API SETUP ---
# Pulls from Advanced Settings > Secrets
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-pro')
except Exception as e:
    st.error("Missing API Key in Secrets!")
    st.stop()

# --- APP HEADER ---
st.title("🤖 TahaGpt")
st.write("Welcome to Taha's AI!")

# --- CHAT LOGIC ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# Show history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User Input
if prompt := st.chat_input("Ask me anything..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.spinner("Thinking..."):
        response = model.generate_content(prompt)
        st.session_state.messages.append({"role": "assistant", "content": response.text})
        with st.chat_message("assistant"):
            st.markdown(response.text)
