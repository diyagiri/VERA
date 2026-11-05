# ============================================================
# APP.PY — Web interface for VERA
# Run with: streamlit run app.py
# This opens VERA as a chat website in your browser
# ============================================================

# ── Imports ──────────────────────────────────────────────────

# streamlit creates the web interface in your browser
import streamlit as st

# os lets us check if the database exists
import os

# time lets us measure response time
import time

# csv and datetime for logging
import csv
from datetime import datetime

# anthropic to talk to Claude AI
import anthropic

# chromadb is our local database
import chromadb

# SentenceTransformer converts text to numbers
from sentence_transformers import SentenceTransformer


# ============================================================
# PAGE CONFIGURATION
# ============================================================

# Set the browser tab title, icon and layout
st.set_page_config(
    page_title="VERA — Xebia HR Assistant",
    page_icon="🚗",
    layout="centered"
)

# ============================================================
# LOAD MODELS — Only load once using Streamlit's cache
# ============================================================

# @st.cache_resource means: load this once and reuse it
# Without this it would reload the model on every message (very slow)
@st.cache_resource
def load_resources():
    """
    Loads ChromaDB, the embedding model, and the Anthropic client.
    Only runs once when the app first starts.
    """

    # Check if the database exists
    if not os.path.exists("hr_section"):
        return None, None, None

    # Load ChromaDB database
    chroma_client = chromadb.PersistentClient(path="hr_section")
    collection = chroma_client.get_collection("vera_chunks")

    # Load the embedding model
    embedding_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

    # Create the Anthropic client
    anthropic_client = anthropic.Anthropic()

    return collection, embedding_model, anthropic_client

# Load all resources
collection, embedding_model, anthropic_client = load_resources()

# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """You are VERA, Vehicle and Employment Regulations Assistant, an expert HR chatbot for Xebia. You communicate in B1-level English — warm, clear, professional, and strictly based on HR policy.

Every answer must follow this exact structure:
1. Grounded Answer: a direct concise answer based only on the provided document chunks.
2. Citation: mention the specific section where this was found.
3. If the answer is not in the documents say exactly: I cannot find this information in the Car Scheme document. To ensure compliance I only answer questions directly addressed in the policy — and refer to HRBP, Payroll, or Chief People and Payroll.

Knowledge rules:
- Only use information from the provided document chunks.
- Never hallucinate or assume missing information.
- Never quote documents literally — summarize and refer to the section.

Safety and privacy:
- Never repeat personal data (BSN, address, date of birth, phone number, bank details).
- If a question is too sensitive, explain briefly and refer to HR.

Answer format:
- Maximum 5 to 10 bullet points or one short paragraph.
- Point out risks or missing steps without judgement.

Routing:
- Strategy, leadership, reorganisations, culture → refer to Nova
- Step-by-step plans, checklists, workflows → refer to Aster
- Labour law, EU rules, tax, external legislation → refer to External Legislation
- All other HR process questions → answer yourself

Skeptic mode — when active, prefix every answer with:
✅ High — literally in the documents
⚠️ Medium — derived from the documents
❌ Low — interpretation
For Medium or Low, state where it can be verified.

Always close by asking: "Would you like more explanation, a clarification, or an email template?" """


# ============================================================
# SESSION STATE — Remember things between messages
# ============================================================

# Streamlit resets everything on each message unless we use session_state
# Here we initialize all the variables we need to remember

if "messages" not in st.session_state:
    # Add VERA's greeting as the first message when the chat starts
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "👋 Hello! How are you? I hope you are doing well.\n\nI am **VERA**, your Xebia Car Scheme assistant. How can I help you today?\n\n💡 You can ask me anything about the Xebia Car Scheme policy.\n💡 Use the **Skeptic Mode** button on the left to activate confidence labels."
        }
    ]

if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []  # history sent to Claude

if "skeptic_mode" not in st.session_state:
    st.session_state.skeptic_mode = False   # skeptic mode off by default

if "total_questions" not in st.session_state:
    st.session_state.total_questions = 0    # total questions this session

if "unanswered_count" not in st.session_state:
    st.session_state.unanswered_count = 0   # unanswered questions count


# ============================================================
# LOGGING SETUP
# ============================================================

# Create CSV log files if they don't exist yet
if not os.path.exists("query_log.csv"):
    with open("query_log.csv", "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(["timestamp", "question", "top_section", "confidence", "response_time_s", "skeptic_mode", "answer"])

if not os.path.exists("unanswered_log.csv"):
    with open("unanswered_log.csv", "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(["timestamp", "question"])


def log_query(question, top_section, confidence, response_time, answer, skeptic):
    """Saves every question and answer to query_log.csv."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("query_log.csv", "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([timestamp, question, top_section, confidence, response_time, skeptic, answer])

    # Check if guardrail was triggered
    if "I cannot find this information in the Car Scheme document" in answer:
        with open("unanswered_log.csv", "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([timestamp, question])
        return True
    return False


# ============================================================
# RETRIEVAL FUNCTION
# ============================================================

def retrieve_chunks(question):
    """Finds the 5 most relevant chunks from ChromaDB for the question."""

    # Embed the question
    question_embedding = embedding_model.encode([question])[0].tolist()

    # Search ChromaDB for top 5 matches
    results = collection.query(
        query_embeddings=[question_embedding],
        n_results=5,
        include=["documents", "metadatas", "distances"]
    )

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    # Calculate absolute confidence scores
    scores = [round(max(0.0, 1 - (d / 30)), 2) for d in distances]

    return [
        {
            "text": documents[i],
            "section": metadatas[i].get("section", "Unknown"),
            "score": scores[i]
        }
        for i in range(len(documents))
    ]


# ============================================================
# PAGE LAYOUT
# ============================================================

# Main title
st.title("🚗 VERA")
st.caption("Vehicle & Employment Regulations Assistant — Xebia Car Scheme Policy")

# ── Sidebar ──────────────────────────────────────────────────
with st.sidebar:

    st.header("⚙️ Settings")

    # Skeptic mode toggle button
    if st.button("🔍 Skeptic Mode: ON" if st.session_state.skeptic_mode else "🔍 Skeptic Mode: OFF"):
        # Toggle skeptic mode on or off when button is clicked
        st.session_state.skeptic_mode = not st.session_state.skeptic_mode
        mode = "activated" if st.session_state.skeptic_mode else "deactivated"
        st.success(f"Skeptic mode {mode}!")

    # Show current skeptic mode status
    if st.session_state.skeptic_mode:
        st.info("Skeptic mode is ON — answers will be labelled ✅ High / ⚠️ Medium / ❌ Low")

    st.divider()

    # Session stats
    st.header("📊 Session Stats")
    st.metric("Questions asked", st.session_state.total_questions)
    st.metric("Unanswered", st.session_state.unanswered_count)

    st.divider()

    # Clear chat button
    if st.button("🗑️ Clear chat"):
        st.session_state.messages = []
        st.session_state.conversation_history = []
        st.session_state.total_questions = 0
        st.session_state.unanswered_count = 0
        st.rerun()

    st.divider()

    # ── Feedback Form ─────────────────────────────────────────
    st.header("📝 Feedback")

    # Use a form so all 3 answers are submitted together
    with st.form("feedback_form"):

        # Question 1 — Rating slider from 1 to 5
        rating = st.slider(
            "Rate VERA (1 = poor, 5 = excellent)",
            min_value=1,
            max_value=5,
            value=3
        )

        # Question 2 — Free text comment
        comment = st.text_input("What could VERA do better?")

        # Question 3 — Groundedness radio buttons
        groundedness = st.radio(
            "Was the answer based on the document or made up?",
            options=["1 - Made up", "2 - Not sure", "3 - Clearly from document"]
        )

        # Submit button — only saves when clicked
        submitted = st.form_submit_button("Submit Feedback")

        if submitted:

            # Extract just the number from the groundedness answer
            groundedness_score = int(groundedness[0])

            # Save to feedback_log.csv
            if not os.path.exists("feedback_log.csv"):
                with open("feedback_log.csv", "w", newline="", encoding="utf-8") as f:
                    csv.writer(f).writerow(["timestamp", "rating", "comment", "groundedness"])

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open("feedback_log.csv", "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([timestamp, rating, comment, groundedness_score])

            # Calculate average rating across all sessions
            all_ratings = []
            with open("feedback_log.csv", "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        all_ratings.append(int(row["rating"]))
                    except:
                        pass

            avg = round(sum(all_ratings) / len(all_ratings), 2) if all_ratings else 0

            # Show thank you message
            st.success(f"✅ Thank you! Feedback saved.")
            st.info(f"⭐ Average rating across all sessions: {avg} / 5 ({len(all_ratings)} responses)")

    # Check if database is loaded
    if collection is None:
        st.error("❌ Database not found! Please run ingest.py first.")
    else:
        st.success("✅ Database loaded")


# ============================================================
# DISPLAY CHAT HISTORY
# ============================================================

# Show all previous messages in the chat window
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# ============================================================
# CHAT INPUT — The text box at the bottom of the page
# ============================================================

# Show the chat input box only if the database is loaded
if collection is not None:

    if prompt := st.chat_input("Ask a question about the Xebia Car Scheme..."):

        # Show user message in chat
        with st.chat_message("user"):
            st.markdown(prompt)

        # Add to display history
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.total_questions += 1

        # Retrieve relevant chunks
        chunks = retrieve_chunks(prompt)
        top_confidence = chunks[0]["score"]
        top_section = chunks[0]["section"]

        # Build the formatted chunks block
        formatted_chunks = ""
        for i, chunk in enumerate(chunks):
            formatted_chunks += f"--- Chunk {i+1} | Section: {chunk['section']} ---\n"
            formatted_chunks += chunk["text"] + "\n\n"

        # Add skeptic instruction if active
        skeptic_instruction = ""
        if st.session_state.skeptic_mode:
            skeptic_instruction = """
SKEPTIC MODE IS ON. Prefix your answer with:
✅ High — literally in the documents
⚠️ Medium — derived from the documents
❌ Low — interpretation only
"""

        # Build the full message for Claude
        full_message = f"""Here are the relevant sections from the Xebia Car Scheme policy:

{formatted_chunks}
---
Based only on the sections above, please answer this question:
{prompt}{skeptic_instruction}"""

        # Add to conversation history
        st.session_state.conversation_history.append({
            "role": "user",
            "content": full_message
        })

        # Send to Claude and measure response time
        with st.chat_message("assistant"):
            with st.spinner("VERA is thinking..."):

                start_time = time.time()

                response = anthropic_client.messages.create(
                    model="claude-opus-4-5",
                    max_tokens=1000,
                    system=SYSTEM_PROMPT,
                    messages=st.session_state.conversation_history
                )

                response_time = round(time.time() - start_time, 1)
                answer = response.content[0].text

                # Display the answer
                st.markdown(answer)

                # Show confidence and response time below the answer
                col1, col2 = st.columns(2)
                with col1:
                    st.caption(f"📊 Confidence: {top_confidence} | Section: {top_section}")
                with col2:
                    if response_time > 2.5:
                        st.caption(f"⏱️ {response_time}s ⚠️ slow")
                    else:
                        st.caption(f"⏱️ {response_time}s")

        # Add Claude's answer to conversation history
        st.session_state.conversation_history.append({
            "role": "assistant",
            "content": answer
        })

        # Add to display history
        st.session_state.messages.append({"role": "assistant", "content": answer})

        # Log the query
        was_unanswered = log_query(
            question=prompt,
            top_section=top_section,
            confidence=top_confidence,
            response_time=response_time,
            answer=answer,
            skeptic=st.session_state.skeptic_mode
        )

        if was_unanswered:
            st.session_state.unanswered_count += 1

else:
    # Show error if database not loaded
    st.error("❌ VERA database not found. Please run `python ingest.py` first.")
