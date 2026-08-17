"""
app.py
Streamlit entry point for the AI Healthcare Chatbot.
"""

import json
import streamlit as st

from chatbot import get_response, contains_emergency_language, EMERGENCY_MESSAGE, DEFAULT_MODEL
from pdf_generator import generate_chat_pdf

st.set_page_config(
    page_title="AI Healthcare Chatbot",
    page_icon="🩺",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ---------- Data ----------
@st.cache_data
def load_disease_data():
    with open("disease_data.json", "r", encoding="utf-8") as f:
        return json.load(f)


# ---------- Session state ----------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None

MODEL_OPTIONS = {
    "GPT-4o mini": "openai/gpt-4o-mini",
    "Claude Haiku 4.5": "anthropic/claude-haiku-4.5",
    "Gemini 2.5 Flash": "google/gemini-2.5-flash",
    "Laguna M.1 (free, coding-focused)": "poolside/laguna-m.1:free",
}

# ---------- Sidebar ----------
with st.sidebar:
    st.title("🩺 HealthGuide AI")
    st.caption("General health information, powered by OpenRouter.")

    selected_model_label = st.selectbox("Model", list(MODEL_OPTIONS.keys()), index=0)
    selected_model = MODEL_OPTIONS[selected_model_label]

    st.divider()
    st.subheader("Disease Reference")
    disease_data = load_disease_data()
    for name, info in disease_data.items():
        with st.expander(name):
            st.markdown(f"**Symptoms:** {', '.join(info.get('symptoms', []))}")
            st.markdown(f"**Prevention:** {', '.join(info.get('prevention', []))}")
            st.markdown(f"**Treatment:** {info.get('treatment', 'N/A')}")
            st.markdown(f"**Vaccination:** {info.get('vaccination', 'N/A')}")
            if st.button(f"Ask about {name}", key=f"ask_{name}", use_container_width=True):
                st.session_state.pending_prompt = (
                    f"Can you tell me about {name} — its symptoms, how to prevent it, "
                    f"and general treatment options?"
                )

    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🗑️ Clear chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    with col_b:
        if st.session_state.messages:
            pdf_bytes = generate_chat_pdf(st.session_state.messages)
            st.download_button(
                "⬇️ Export PDF",
                data=pdf_bytes,
                file_name="healthguide_chat_transcript.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

    st.divider()
    st.caption(
        "⚠️ **Disclaimer:** This chatbot provides general health information only. "
        "It does not diagnose, prescribe, or replace professional medical care. "
        "In an emergency, contact your local emergency services immediately."
    )

# ---------- Main chat area ----------
st.title("AI Healthcare Chatbot")
st.caption("Ask general questions about symptoms, conditions, wellness, and more.")

if not st.session_state.messages:
    st.info(
        "👋 Hi, I'm HealthGuide AI. I can help explain symptoms, conditions, medications, "
        "and general wellness topics. I'm not a doctor, so for anything urgent or personal, "
        "please consult a licensed healthcare professional."
    )

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_input = st.chat_input("Ask a health question...")

# A sidebar quick-topic button click also drives a "turn" the same way typed input does.
if st.session_state.pending_prompt and not user_input:
    user_input = st.session_state.pending_prompt
    st.session_state.pending_prompt = None

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        if contains_emergency_language(user_input):
            st.markdown(EMERGENCY_MESSAGE)
            reply = EMERGENCY_MESSAGE
        else:
            with st.spinner("Thinking..."):
                reply = get_response(st.session_state.messages, model=selected_model)
            st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})