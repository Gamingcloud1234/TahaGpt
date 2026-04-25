import streamlit as st
import google.generativeai as genai

# --- PAGE CONFIG ---
st.set_page_config(page_title="TahaGpt", page_icon="🤖", layout="centered")

# --- STYLE ---
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
    }
    stChatMessage {
        border-radius: 15px;
    }
    </style>
    """, unsafe_all_user_tabs=True)

# --- API SETUP ---
# This pulls the key from your Streamlit "Advanced Settings > Secrets"
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-pro')
except Exception as e:
    st.error("Missing API Key! Please add GEMINI_API_KEY to your Streamlit Secrets.")
    st.stop()

# --- APP HEADER ---
st.title("🤖 TahaGpt")
st.caption("Personal AI Assistant | Powered by Gemini")
st.divider()

# --- CHAT LOGIC ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User Input
if prompt := st.chat_input("How can I help you today, Taha?"):
    # Add user message to state
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate Response
    with st.spinner("TahaGpt is thinking..."):
        try:
            response = model.generate_content(prompt)
            full_response = response.text
            
            # Show assistant response
            with st.chat_message("assistant"):
                st.markdown(full_response)
            
            # Add assistant message to state
            st.session_state.messages.append({"role": "assistant", "content": full_response})
        except Exception as e:
            st.error(f"An error occurred: {e}")
