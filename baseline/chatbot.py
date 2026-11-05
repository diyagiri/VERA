# ============================================================
# CHATBOT.PY
# ============================================================
# This is the main chatbot file for VERA.
# Run this every time you want to have a conversation.
#
# What this file does step by step:
# 1. Loads the ChromaDB database created by ingest.py
# 2. Loads the embedding model to understand your questions
# 3. Waits for you to type a question
# 4. Converts your question into numbers and searches the database
# 5. Finds the 3 most relevant chunks from the HR handbook
# 6. Sends those chunks + your question to Claude AI
# 7. Claude answers based ONLY on the handbook content
# 8. Keeps the conversation going so follow-up questions work
# 9. Type 'quit' to exit
#
# Run this file with:
#   python chatbot.py
# ============================================================

# ── Import libraries ─────────────────────────────────────────

# os lets us check if files and folders exist on the computer
import os

# sys lets us exit the program cleanly with a message
import sys

# time lets us measure how long the API call takes
import time

# csv lets us write rows to a CSV file (like Excel)
import csv

# datetime lets us record the exact time of each question
from datetime import datetime

# chromadb is the local database where all chunks are stored
import chromadb

# SentenceTransformer converts text into numbers (embeddings)
from sentence_transformers import SentenceTransformer

# anthropic is the library to talk to Claude AI
import anthropic


# ============================================================
# STEP 1 — STARTUP: CHECK DATABASE, LOAD MODELS, GREET USER
# ============================================================

# ── Check if the database exists ─────────────────────────────

# The hr_db folder is created by ingest.py
# If it doesn't exist, the user forgot to run ingest.py first
if not os.path.exists("hr_section"):

    # Print a clear error message explaining what to do
    print("VERA database not found. Please run ingest.py first.")

    # Exit the program — no point continuing without the database
    sys.exit(1)

# ── Load the ChromaDB database ───────────────────────────────

# Connect to the existing ChromaDB database in the hr_section folder
chroma_client = chromadb.PersistentClient(path="hr_section")

# Open the collection called vera_chunks where all chunks are stored
collection = chroma_client.get_collection("vera_chunks")

# ── Load the embedding model ─────────────────────────────────

# Load the same embedding model used in ingest.py
# It MUST be the same model — otherwise the numbers won't match
# and the search will return wrong results
embedding_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

# ── Print the welcome message ────────────────────────────────

# Print the exact welcome message for VERA
print("""
============================================================
[VERA v1.0] Vehicle & Employment Regulations Assistant
============================================================
👋 Hello! How are you? I hope you are doing well.
I am VERA, your Xebia Car Scheme assistant.
How can I help you today?

💡 You can ask me anything about the Xebia Car Scheme policy.
💡 Type 'skeptic on' to activate skeptic mode.
💡 Type 'quit' to exit.
============================================================
""")


# ============================================================
# STEP 2 — RETRIEVAL: FIND RELEVANT CHUNKS FROM CHROMADB
# ============================================================

def retrieve_chunks(question):
    """
    Takes the user's question and finds the 5 most relevant
    chunks from the ChromaDB database.

    Steps:
    1. Convert the question into a number vector (embedding)
    2. Search ChromaDB for the 5 closest matching vectors
    3. Return the chunks with their text and metadata
    4. Print the top result so we can see what was retrieved
    """

    # ── Embed the question ───────────────────────────────────
    # Convert the user's question into a number vector
    # This must use the same model as ingest.py so the numbers match
    question_embedding = embedding_model.encode([question])[0].tolist()

    # ── Search ChromaDB ──────────────────────────────────────
    # Query the collection for the 5 most similar chunks
    # ChromaDB uses cosine similarity by default to compare vectors
    # Cosine similarity measures the angle between two vectors —
    # the smaller the angle, the more similar the meaning
    results = collection.query(
        query_embeddings=[question_embedding],  # the question vector
        n_results=5,                            # return top 5 matches
        include=["documents", "metadatas", "distances"]  # what to return
    )

    # ── Extract results ──────────────────────────────────────
    # results["documents"][0] is a list of the 5 chunk texts
    # results["metadatas"][0] is a list of the 5 chunk metadata dicts
    # results["distances"][0] is a list of the 5 similarity distances
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    # ── Calculate similarity scores ──────────────────────────
    # ChromaDB returns "distances" — lower distance = more similar
    # We convert each distance to an absolute confidence score using:
    # score = max(0, 1 - (distance / 30))
    # 30 is a scaling factor based on the typical distance range we observed
    # distance ~14 → score ~0.53 (moderate match)
    # distance ~16 → score ~0.47 (weak match)
    # distance ~0  → score ~1.0  (perfect match)
    scores = [round(max(0.0, 1 - (d / 30)), 2) for d in distances]

    # ── Print top result ─────────────────────────────────────
    # Show the user which section was most relevant and its score
    top_section = metadatas[0].get("section", "Unknown")
    top_score = scores[0]
    print(f"\n🔍 Top match: [{top_section}] — confidence: {top_score}")

    # ── Return all 5 results ─────────────────────────────────
    # Return a list of dicts with text, metadata and confidence score
    return [
        {
            "text": documents[i],
            "section": metadatas[i].get("section", "Unknown"),
            "rank": i + 1,      # rank 1 = most relevant, 5 = least
            "score": scores[i]  # confidence score between 0 and 1
        }
        for i in range(len(documents))
    ]


# ============================================================
# SYSTEM PROMPT — Tells Claude exactly how to behave as VERA
# ============================================================

# This is the personality, rules, and format Claude must follow
# It is sent with every message so Claude never forgets its role
SYSTEM_PROMPT = """You are VERA, Vehicle and Employment Regulations Assistant, an expert HR chatbot for Xebia. You communicate in B1-level English — warm, clear, professional, and strictly based on HR policy.

Every answer must follow this exact structure:
1. Grounded Answer: a direct concise answer based only on the provided document chunks.
2. Citation: mention the specific section where this was found.
3. If the answer is not in the documents say exactly: I cannot find this information in the Car Scheme document. To ensure compliance I only answer questions directly addressed in the policy — and refer to HRBP, Payroll, or Chief People and Payroll.

Knowledge rules:
- Only use information from the provided document chunks.
- Never hallucinate or assume missing information.
- Never quote documents literally — summarize and refer to the section.

Dutch glossary:
- bijtelling = tax addition for private use of company car
- APK = mandatory Dutch vehicle inspection
- wagenpark = company car fleet
- leasenorm = lease budget

Safety and privacy:
- Never repeat personal data (BSN, address, date of birth, phone number, bank details).
- If a question is too sensitive, explain briefly and refer to HR.

Answer format:
- Maximum 5 to 10 bullet points or one short paragraph.
- Point out risks or missing steps without judgement.

Routing:
- Strategy, leadership, reorganisations, culture, or complex HRBP cases → refer to Nova
- Step-by-step plans, checklists, or workflows → refer to Aster
- Labour law, EU rules, tax, or external legislation → refer to External Legislation
- All other HR process questions → answer yourself

Skeptic mode — activate when the user asks to be critical or questions correctness:
- ✅ High – literally in the documents
- ⚠ Medium – derived from the documents
- ❌ Low – interpretation
For Medium or Low, state where it can be verified.

Always close by asking: "Would you like more explanation, a clarification, or an email template?" """


# ============================================================
# CONVERSATION HISTORY
# ============================================================

# This list stores the full conversation so Claude remembers context
# Each item is a dict with "role" (user or assistant) and "content"
# Without this, Claude would forget everything after each message
conversation_history = []

# Create the Anthropic client to send messages to Claude
# It automatically reads the ANTHROPIC_API_KEY from your environment
anthropic_client = anthropic.Anthropic()


# ============================================================
# LOGGING SETUP
# ============================================================

# Counter to track how many questions could not be answered
unanswered_count = 0

# Counter to track total questions asked this session
total_questions = 0

# Skeptic mode flag — False means off, True means on
# When on, every answer gets a confidence label (High/Medium/Low)
skeptic_mode = False

# query_log.csv — logs every question and answer
# If the file doesn't exist yet, write the header row first
if not os.path.exists("query_log.csv"):
    with open("query_log.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        # Write the column headers — skeptic_mode column added
        writer.writerow(["timestamp", "question", "top_section", "confidence", "response_time_s", "skeptic_mode", "answer"])

# unanswered_log.csv — logs questions VERA couldn't answer from the document
# If the file doesn't exist yet, write the header row first
if not os.path.exists("unanswered_log.csv"):
    with open("unanswered_log.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        # Write the column headers
        writer.writerow(["timestamp", "question"])

# feedback_log.csv — logs user ratings and comments at end of each session
if not os.path.exists("feedback_log.csv"):
    with open("feedback_log.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        # Write the column headers
        writer.writerow(["timestamp", "rating", "comment", "groundedness"])


def log_query(question, top_section, confidence, response_time, answer, skeptic):
    """
    Saves every question and answer to query_log.csv.
    Also checks if VERA's guardrail was triggered (couldn't find the answer)
    and if so saves the question to unanswered_log.csv too.
    """

    # Get the current date and time as a readable string
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ── Write to query_log.csv ───────────────────────────────
    # Open the file in append mode ("a") so we add rows without overwriting
    with open("query_log.csv", "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        # Write one row with all the data for this question
        # skeptic column records whether skeptic mode was on or off
        writer.writerow([timestamp, question, top_section, confidence, response_time, skeptic, answer])

    # ── Check if guardrail was triggered ────────────────────
    # VERA uses this exact phrase when it can't find the answer
    guardrail_phrase = "I cannot find this information in the Car Scheme document"

    # If this phrase appears in the answer, it means VERA couldn't answer
    if guardrail_phrase in answer:

        # Write to unanswered_log.csv
        with open("unanswered_log.csv", "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, question])

        # Return True so the main loop knows to increment the unanswered counter
        return True

    # Return False — the question was answered normally
    return False


def collect_feedback():
    """
    Asks the user 3 feedback questions after the session ends.
    Saves the answers to feedback_log.csv.
    Also calculates and prints the average rating across all sessions.
    """

    print("\n" + "="*50)
    print("📝 Before you go — quick feedback on VERA")
    print("="*50)

    # ── Question 1: Rating ───────────────────────────────────
    # Keep asking until the user gives a valid number between 1 and 5
    while True:
        rating_input = input("\nPlease rate VERA from 1 to 5: ").strip()
        if rating_input in ["1", "2", "3", "4", "5"]:
            rating = int(rating_input)
            break
        print("Please enter a number between 1 and 5.")

    # ── Question 2: Comment ──────────────────────────────────
    # Free text — the user can type anything
    comment = input("\nWhat could VERA do better? ").strip()

    # ── Question 3: Groundedness ─────────────────────────────
    # How grounded did the answer feel — made up or from the document?
    print("\nWas the answer based on the document or did it feel made up?")
    print("  1 = Made up")
    print("  2 = Not sure")
    print("  3 = Clearly from the document")

    while True:
        groundedness_input = input("Your choice (1/2/3): ").strip()
        if groundedness_input in ["1", "2", "3"]:
            groundedness = int(groundedness_input)
            break
        print("Please enter 1, 2, or 3.")

    # ── Save to feedback_log.csv ─────────────────────────────
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("feedback_log.csv", "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, rating, comment, groundedness])

    print("\n✅ Thank you! Feedback saved.")

    # ── Calculate average rating across all sessions ─────────
    # Read all ratings from the feedback_log.csv file
    all_ratings = []
    with open("feedback_log.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                all_ratings.append(int(row["rating"]))
            except:
                pass  # skip any rows that can't be read

    # Calculate and print the average
    if all_ratings:
        avg_rating = round(sum(all_ratings) / len(all_ratings), 2)
        print(f"⭐ Average VERA rating across all sessions: {avg_rating} / 5 ({len(all_ratings)} total responses)")


# ============================================================
# STEP 3 — PROMPT CONSTRUCTION: BUILD THE MESSAGE FOR CLAUDE
# ============================================================

def build_prompt(question, chunks):
    """
    Builds the full message to send to Claude.
    It contains:
    1. The 5 retrieved chunks labelled with their section
    2. The user's current question
    Claude will use only these chunks to answer.
    """

    # ── Format the retrieved chunks ──────────────────────────
    # Label each chunk with its section name so Claude knows where it came from
    formatted_chunks = ""
    for i, chunk in enumerate(chunks):
        formatted_chunks += f"--- Chunk {i+1} | Section: {chunk['section']} ---\n"
        formatted_chunks += chunk["text"] + "\n\n"

    # ── Build the full user message ──────────────────────────
    # This combines the chunks + the question into one message
    # Claude reads the chunks first, then answers the question
    full_message = f"""Here are the relevant sections from the Xebia Car Scheme policy document:

{formatted_chunks}
---

Based only on the sections above, please answer this question:
{question}"""

    return full_message


# ── Main chat loop ────────────────────────────────────────────
# This keeps the conversation going until the user types quit
while True:

    # Ask the user to type a question
    user_input = input("\nYou: ").strip()

    # Exit if the user types quit
    if user_input.lower() == "quit":

        # Print the session summary
        print(f"\n📋 Session summary: {unanswered_count} out of {total_questions} questions could not be answered from the document.")

        # Collect feedback before exiting
        collect_feedback()

        print("Goodbye! / Tot ziens!")
        break

    # Skip empty input
    if not user_input:
        continue

    # ── Skeptic mode toggle ──────────────────────────────────
    # Check if the user wants to turn skeptic mode on or off
    if user_input.lower() == "skeptic on":
        skeptic_mode = True
        print("🔍 Skeptic mode activated — every answer will be labelled High / Medium / Low.")
        continue  # go back to the top of the loop, don't send to Claude

    if user_input.lower() == "skeptic off":
        skeptic_mode = False
        print("✅ Skeptic mode deactivated.")
        continue  # go back to the top of the loop, don't send to Claude

    # Count this as a question
    total_questions += 1

    # ── Step 2: Retrieve relevant chunks ────────────────────
    # Find the 5 most relevant sections from ChromaDB
    chunks = retrieve_chunks(user_input)

    # ── Confidence check ────────────────────────────────────
    # Get the similarity score of the top chunk
    # Use .get() with a default of 0 in case score is missing
    top_confidence = chunks[0].get("score", 0)

    # Print the confidence score right after retrieval
    print(f"📊 Retrieval confidence: {top_confidence}")

    # If the best match score is below 0.5 the question may not
    # be well covered by the document — warn the user
    if top_confidence < 0.5:
        print("⚠️  Warning — Low confidence. This answer may not be well supported by the document.")

    # ── Step 3: Build the prompt ─────────────────────────────
    # Combine chunks + question into one message for Claude
    # If skeptic mode is on, add an extra instruction to label the answer
    skeptic_instruction = ""
    if skeptic_mode:
        skeptic_instruction = """
SKEPTIC MODE IS ON. You must prefix your answer with one of these labels:
✅ High — the answer is literally stated in the retrieved chunks
⚠️ Medium — the answer is derived or implied from the chunks
❌ Low — the answer requires interpretation beyond what is in the chunks
For Medium or Low, state exactly where the user can verify the information.
"""
    user_message = build_prompt(user_input, chunks) + skeptic_instruction

    # Add the constructed message to conversation history
    # We use the full message (with chunks) so Claude has context
    conversation_history.append({
        "role": "user",
        "content": user_message
    })

    # ── Step 4: Send to Claude and measure response time ────────
    # Record the time BEFORE sending the request to Claude
    # We use time.time() which gives us the current time in seconds
    start_time = time.time()

    # Send the system prompt + full conversation history to Claude
    # Using claude-opus-4-5 — Anthropic's powerful model
    response = anthropic_client.messages.create(
        model="claude-opus-4-5",           # the Claude model to use
        max_tokens=1000,                    # maximum length of the answer
        system=SYSTEM_PROMPT,               # VERA's personality and rules
        messages=conversation_history       # full conversation so far
    )

    # Record the time AFTER Claude has responded
    end_time = time.time()

    # Calculate how many seconds the API call took
    # Round to 1 decimal place for clean display
    response_time = round(end_time - start_time, 1)

    # Extract the text from Claude's response
    answer = response.content[0].text

    # Add Claude's answer to conversation history
    # This allows follow-up questions to work correctly
    conversation_history.append({
        "role": "assistant",
        "content": answer
    })

    # Print Claude's answer
    print(f"\nVERA: {answer}")

    # ── Print response time ──────────────────────────────────
    print(f"\n⏱️  Response time: {response_time}s")

    # Warn if response exceeded 2.5 seconds
    if response_time > 2.5:
        print("⚠️  Response time exceeded 2.5 second requirement.")

    # ── Log the question and answer ──────────────────────────
    # Save everything to query_log.csv
    # If VERA couldn't answer, also save to unanswered_log.csv
    was_unanswered = log_query(
        question=user_input,
        top_section=chunks[0]["section"],
        confidence=top_confidence,
        response_time=response_time,
        answer=answer,
        skeptic=skeptic_mode
    )

    # If guardrail was triggered, increment the unanswered counter
    if was_unanswered:
        unanswered_count += 1
        print("📝 Logged to unanswered_log.csv")
