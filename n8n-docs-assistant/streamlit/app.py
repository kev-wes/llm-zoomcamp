"""Chat UI for the n8n Docs Assistant.

A thin Streamlit front end: every question is sent to the n8n RAG agent
webhook, and the thumbs up/down buttons post to the n8n feedback webhook.
All the actual RAG logic lives in n8n.
"""

import os

import requests
import streamlit as st

N8N_WEBHOOK_BASE = os.getenv("N8N_WEBHOOK_BASE", "http://localhost:5678/webhook")

st.set_page_config(page_title="n8n Docs Assistant", page_icon="🤖")
st.title("🤖 n8n Docs Assistant")
st.caption(
    "Internal platform support bot. Ask anything about building "
    "workflows in n8n - answers come from the official documentation."
)

if "messages" not in st.session_state:
    st.session_state.messages = []


def send_feedback(conversation_id: str, value: int) -> None:
    try:
        requests.post(
            f"{N8N_WEBHOOK_BASE}/feedback",
            json={"conversation_id": conversation_id, "feedback": value},
            timeout=10,
        )
        st.toast("Thanks for your feedback!")
    except requests.RequestException:
        st.toast("Could not send feedback, is n8n running?")


def ask(question: str) -> tuple[str, str | None]:
    try:
        resp = requests.post(
            f"{N8N_WEBHOOK_BASE}/chat",
            json={"question": question},
            timeout=180,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("answer", "(empty answer)"), data.get("conversation_id")
    except requests.RequestException as e:
        return f"Request to the assistant failed: `{e}`", None


# Render the conversation so far
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("conversation_id"):
            up, down, _ = st.columns([1, 1, 10])
            up.button(
                "👍", key=f"up_{i}",
                on_click=send_feedback, args=(msg["conversation_id"], 1),
            )
            down.button(
                "👎", key=f"down_{i}",
                on_click=send_feedback, args=(msg["conversation_id"], -1),
            )

if question := st.chat_input("How do I ... in n8n?"):
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"), st.spinner("Searching the docs..."):
        answer, conv_id = ask(question)

    st.session_state.messages.append(
        {"role": "assistant", "content": answer, "conversation_id": conv_id}
    )
    st.rerun()
