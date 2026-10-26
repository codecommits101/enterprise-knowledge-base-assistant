"""Simple Streamlit chat UI for an AWS Bedrock Knowledge Base."""

import html
import os

import boto3
import streamlit as st
from botocore.config import Config
from dotenv import load_dotenv

load_dotenv()

REGION = os.getenv("AWS_REGION", "us-east-1")
KB_ID = os.getenv("BEDROCK_KNOWLEDGE_BASE_ID", "")
MODEL_ARN = os.getenv("DEFAULT_MODEL_ARN", "google.gemma-3-4b-it")
TOP_K = int(os.getenv("TOP_K_RESULTS", "5"))

st.set_page_config(page_title="Enterprise Knowledge Base Assistant", page_icon="🏢")

STYLE = """
<style>
/* Page background */
.stApp {
    background: linear-gradient(160deg, #eef2ff 0%, #f5f3ff 45%, #e0f2fe 100%);
    background-attachment: fixed;
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stBottom"], [data-testid="stBottom"] > div { background: transparent; }
.block-container { max-width: 860px; padding-top: 1.5rem; padding-bottom: 6rem; }

/* Hero header */
.hero {
    background: linear-gradient(120deg, #4f46e5 0%, #7c3aed 55%, #0ea5e9 100%);
    color: #ffffff;
    border-radius: 20px;
    padding: 28px 32px;
    margin-bottom: 24px;
    box-shadow: 0 10px 30px rgba(79, 70, 229, 0.30);
}
.hero h1 { color: #ffffff; margin: 0; padding: 0; font-size: 1.9rem; font-weight: 700; }
.hero p { color: rgba(255, 255, 255, 0.88); margin: 6px 0 0 0; font-size: 1rem; }

/* Welcome card */
.welcome {
    background: rgba(255, 255, 255, 0.75);
    border: 1px dashed #a5b4fc;
    border-radius: 16px;
    padding: 20px 24px;
    color: #374151;
    text-align: center;
}

/* Chat bubbles */
[data-testid="stChatMessage"] {
    background: #ffffff;
    color: #1f2937;
    border: 1px solid #e5e7eb;
    border-radius: 16px;
    padding: 14px 18px;
    margin-bottom: 12px;
    box-shadow: 0 2px 8px rgba(15, 23, 42, 0.06);
}
[data-testid="stChatMessage"] * { color: #1f2937; }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
    background: #eef2ff;
    border-color: #c7d2fe;
}

/* Source chips */
.sources { margin-top: 10px; display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.sources .label { font-size: 0.78rem; color: #6b7280 !important; margin-right: 2px; }
.chip {
    background: #ede9fe;
    color: #5b21b6 !important;
    border-radius: 999px;
    padding: 2px 10px;
    font-size: 0.78rem;
    font-weight: 500;
}

/* Suggested questions */
.suggest-label { margin: 18px 0 6px 2px; font-size: 0.85rem; font-weight: 600; color: #4338ca; }
.stButton > button {
    background: #ffffff !important;
    color: #3730a3 !important;
    border: 1px solid #c7d2fe !important;
    border-radius: 12px;
    text-align: left;
    justify-content: flex-start;
    box-shadow: 0 2px 6px rgba(79, 70, 229, 0.08);
}
.stButton > button:hover {
    background: #eef2ff !important;
    border-color: #6366f1 !important;
}
.stButton > button p { color: #3730a3 !important; font-size: 0.9rem; }

/* Chat input */
[data-testid="stBottom"] > div { padding-top: 0.75rem; }
[data-testid="stChatInput"],
[data-testid="stChatInput"] > div,
[data-testid="stChatInput"] textarea {
    background: #ffffff !important;
    color: #1f2937 !important;
}
[data-testid="stChatInput"] {
    border: 2px solid #6366f1;
    border-radius: 16px;
    box-shadow: 0 6px 20px rgba(79, 70, 229, 0.25);
}
[data-testid="stChatInput"] textarea { font-size: 1rem; }
[data-testid="stChatInput"] textarea::placeholder {
    color: #6b7280 !important;
    opacity: 1;
}
[data-testid="stChatInput"] button {
    background: #4f46e5 !important;
    color: #ffffff !important;
    border-radius: 10px;
}
[data-testid="stChatInput"] button svg { fill: #ffffff !important; color: #ffffff !important; }
</style>
"""

st.markdown(STYLE, unsafe_allow_html=True)
st.markdown(
    '<div class="hero"><h1>🏢 Enterprise Knowledge Base Assistant</h1>'
    "<p>Ask questions about your company documents and get answers with sources.</p></div>",
    unsafe_allow_html=True,
)

SUGGESTED_QUESTIONS = [
    "How much is the home office equipment stipend?",
    "What are the remote work eligibility requirements?",
    "How does the 401(k) matching program work?",
    "How much paid time off do employees get?",
    "How do I report a security incident?",
    "What are the rules for storing data in S3?",
]


SYSTEM_PROMPT = (
    "You answer questions using only the provided context passages. "
    "If the context does not contain the answer, say you don't know."
)


@st.cache_resource
def get_clients():
    session = boto3.Session(profile_name=os.getenv("AWS_PROFILE") or None)
    config = Config(retries={"max_attempts": 3, "mode": "standard"}, read_timeout=60)
    return (
        session.client("bedrock-agent-runtime", region_name=REGION, config=config),
        session.client("bedrock-runtime", region_name=REGION, config=config),
    )


def ask(question: str, history: list[dict]) -> tuple[str, list[str]]:
    """Retrieve passages from the managed Knowledge Base, then generate an answer.

    Managed knowledge bases do not support RetrieveAndGenerate, so we call
    Retrieve and then the Converse API ourselves.
    """
    agent_runtime, bedrock_runtime = get_clients()
    results = agent_runtime.retrieve(
        knowledgeBaseId=KB_ID,
        retrievalQuery={"text": question},
        retrievalConfiguration={"managedSearchConfiguration": {"numberOfResults": TOP_K}},
    )["retrievalResults"]

    context = "\n\n".join(
        f"[{i}] {r['content'].get('text', '')}" for i, r in enumerate(results, 1)
    )
    prompt = f"Context:\n{context}\n\nQuestion: {question}"
    messages = [
        {"role": m["role"], "content": [{"text": m["content"]}]} for m in history
    ] + [{"role": "user", "content": [{"text": prompt}]}]

    response = bedrock_runtime.converse(
        modelId=MODEL_ARN,
        system=[{"text": SYSTEM_PROMPT}],
        messages=messages,
    )
    answer = response["output"]["message"]["content"][0]["text"]
    return answer, sources(results)


def sources(results: list[dict]) -> list[str]:
    """Unique source locations of retrieved passages."""
    found = []
    for r in results:
        loc = r.get("location", {})
        uri = loc.get("s3Location", {}).get("uri") or next(
            (v.get("uri") for v in loc.values() if isinstance(v, dict) and v.get("uri")),
            None,
        )
        if uri and uri not in found:
            found.append(uri)
    return found


def render_sources(uris: list[str]) -> None:
    """Show cited documents as small chips."""
    chips = "".join(
        f'<span class="chip" title="{html.escape(u)}">{html.escape(u.rsplit("/", 1)[-1])}</span>'
        for u in uris
    )
    st.markdown(
        f'<div class="sources"><span class="label">Sources</span>{chips}</div>',
        unsafe_allow_html=True,
    )


if not KB_ID or not MODEL_ARN:
    st.error("Set BEDROCK_KNOWLEDGE_BASE_ID and DEFAULT_MODEL_ARN in your .env file.")
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []

welcome = st.empty()
if not st.session_state.messages:
    welcome.markdown(
        '<div class="welcome">Welcome! Try asking about the remote work policy, '
        "employee benefits or IT security guidelines.</div>",
        unsafe_allow_html=True,
    )

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            render_sources(msg["sources"])

def queue_question(q: str) -> None:
    st.session_state.pending = q


question = st.chat_input("Ask a question about your documents") or st.session_state.pop(
    "pending", None
)
if question:
    welcome.empty()
    history = list(st.session_state.messages)
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Thinking..."):
                answer, cited = ask(question, history)
            st.markdown(answer)
            if cited:
                render_sources(cited)
            st.session_state.messages.append(
                {"role": "assistant", "content": answer, "sources": cited}
            )
        except Exception as e:
            st.error(f"Bedrock error: {e}")

st.markdown('<div class="suggest-label">Suggested questions</div>', unsafe_allow_html=True)
cols = st.columns(2)
for i, q in enumerate(SUGGESTED_QUESTIONS):
    cols[i % 2].button(q, key=f"suggest_{i}", on_click=queue_question, args=(q,), use_container_width=True)
