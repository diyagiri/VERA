# ============================================================
# EVALUATE.PY
# ============================================================
# RAG Evaluation and Ablation Study for VERA.
#
# This script runs two separate studies:
#
# PART 1 — Main Evaluation (hr_section only)
#   Generator : Claude (claude-sonnet-4-5)
#   Judge     : GPT (gpt-4o-mini)
#   Output    : evaluation_results.csv
#
# PART 2 — Ablation Study (hr_section vs hr_fixed vs hr_paragraph)
#   Run A: Claude generates answers, Claude judges scores
#          Output: ablation_results_claude.csv
#   Run B: Claude generates answers, GPT judges scores
#          Output: ablation_results_gpt.csv
#   Both results printed side by side for comparison
#
# Using two different judges allows us to check whether the
# evaluation results are consistent across models, which
# strengthens the validity of the ablation study findings.
#
# Run with:
#   python evaluate.py
# ============================================================

# ── Standard library imports ──────────────────────────────────

# time measures wall-clock duration of API calls
import time

# csv writes comma-separated output files
import csv

# re extracts numbers from LLM text responses
import re

# numpy is used for cosine similarity calculations
import numpy as np

# ── Third-party imports ───────────────────────────────────────

# chromadb is the local vector database that stores all chunks
import chromadb

# SentenceTransformer encodes text into embedding vectors
from sentence_transformers import SentenceTransformer

# anthropic is the Python SDK for calling the Claude API
import anthropic

# openai is the Python SDK for calling the GPT API
from openai import OpenAI


# ============================================================
# CONFIGURATION
# ============================================================

# The 20 evaluation questions organised into 6 categories.
# Each tuple is (question_text, category_label).
QUESTIONS = [
    # ── Category 1: Direct Facts ─────────────────────────────
    ("What is the lease budget for category 2?",          "Direct Facts"),
    ("Can I use my lease car privately?",                  "Direct Facts"),
    ("What happens if I lose my fuel card?",               "Direct Facts"),

    # ── Category 2: Table Data ───────────────────────────────
    ("What are all four lease categories and their budgets?",              "Table Data"),
    ("What is the termination cost if I have 26 months remaining?",        "Table Data"),
    ("How much does category 3 cost per month including fuel?",            "Table Data"),

    # ── Category 3: Cross References ─────────────────────────
    ("What happens to my lease car when I leave Xebia?",                   "Cross References"),
    ("What are the conditions mentioned in section C.2?",                  "Cross References"),
    ("What obligations apply if I terminate my employment early?",         "Cross References"),

    # ── Category 4: Dutch Terminology ────────────────────────
    ("What is bijtelling and how does it apply to me?",                    "Dutch Terminology"),
    ("Wat is de leasenorm voor categorie 1?",                              "Dutch Terminology"),
    ("What is APK and when do I need it?",                                 "Dutch Terminology"),

    # ── Category 5: Out of Scope ─────────────────────────────
    # These questions are outside the handbook — VERA should decline
    ("What is Xebia's vacation policy?",                   "Out of Scope"),
    ("How many sick days am I entitled to?",               "Out of Scope"),
    ("What is my salary?",                                 "Out of Scope"),

    # ── Category 6: Partial Information ──────────────────────
    # These questions are only partially covered by the handbook.
    # The document contains some relevant information but not
    # complete answers. This category was designed in advance to
    # test how VERA handles incomplete coverage — the questions
    # were fixed before any evaluation run was executed.
    ("What is the exact process for reporting a stolen lease car?",                    "Partial Information"),
    ("Can I install a roof rack or tow bar on my lease car?",                          "Partial Information"),
    ("What happens if my lease car is written off in an accident?",                    "Partial Information"),
    ("Can I take my lease car outside the Netherlands for more than 30 days?",         "Partial Information"),
    ("What are my responsibilities if my lease car fails the APK inspection?",         "Partial Information"),
]

# The three ChromaDB databases for the ablation study
DATABASES = ["hr_section", "hr_fixed", "hr_paragraph"]

# Number of chunks to retrieve per question
TOP_K = 5

# Claude model — used as generator for all runs, and as judge for Run A
CLAUDE_MODEL = "claude-sonnet-4-5"

# GPT model — used as judge for Part 1 and ablation Run B
GPT_JUDGE_MODEL = "gpt-4o-mini"

# VERA's system prompt — same as in chatbot.py
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

Always close by asking: \"Would you like more explanation, a clarification, or an email template?\" """


# ============================================================
# INITIALISE SHARED RESOURCES
# ============================================================

print("Loading embedding model...")
# Load the same multilingual model used during ingest
# Must be identical — different models produce incompatible embeddings
embedding_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
print("✅ Embedding model loaded")

# Anthropic client — used for generating VERA's answers (all runs)
# and for judging in ablation Run A (Claude as judge)
anthropic_client = anthropic.Anthropic()

# OpenAI client — used for judging in Part 1 and ablation Run B (GPT as judge)
gpt_client = OpenAI()


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def load_collection(db_path: str):
    """Connect to a ChromaDB database and return its vera_chunks collection."""
    client = chromadb.PersistentClient(path=db_path)
    return client.get_collection("vera_chunks")


def retrieve_chunks(collection, question: str, top_k: int = TOP_K):
    """Embed the question and return the top_k most similar chunks."""
    question_embedding = embedding_model.encode([question])[0].tolist()
    results = collection.query(
        query_embeddings=[question_embedding],
        n_results=top_k
    )
    return results["documents"][0]


def generate_answer(question: str, chunks: list) -> str:
    """
    Generate VERA's answer using Claude as the generator.
    Claude is always the generator because VERA is built on Claude.
    """
    context_text = "\n\n".join(
        [f"[Chunk {i+1}]\n{chunk}" for i, chunk in enumerate(chunks)]
    )
    user_message = (
        f"Here are the relevant sections from the HR handbook:\n\n"
        f"{context_text}\n\n"
        f"Question: {question}"
    )
    response = anthropic_client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}]
    )
    return response.content[0].text


def parse_score(text: str) -> float:
    """
    Extract the first number from an LLM response and clamp to [0, 1].
    Handles formats like '0.8', 'approximately 0.8', '80%', '80'.
    """
    match = re.search(r'\d+\.?\d*', text)
    try:
        value = float(match.group()) if match else 0.0
        # Convert percentage to decimal if needed
        if value > 1.0:
            value = value / 100.0
        return min(max(value, 0.0), 1.0)
    except (ValueError, AttributeError):
        return 0.0


def score_faithfulness_gpt(chunks: list, answer: str) -> float:
    """
    Score faithfulness using GPT as the judge.
    GPT is independent from Claude so this avoids same-model bias.
    Score 1 = every claim in the answer is supported by the chunks.
    Score 0 = answer is entirely unsupported.
    """
    context_text = "\n\n".join(chunks)
    prompt = (
        f"Given this context:\n{context_text}\n\n"
        f"And this answer:\n{answer}\n\n"
        f"Score the faithfulness from 0 to 1 where 1 means every claim "
        f"is supported by the context. Reply with a single decimal number "
        f"between 0 and 1 only. No words, no explanation, just the number."
    )
    response = gpt_client.chat.completions.create(
        model=GPT_JUDGE_MODEL,
        max_tokens=10,
        messages=[{"role": "user", "content": prompt}]
    )
    return parse_score(response.choices[0].message.content)


def score_faithfulness_claude(chunks: list, answer: str) -> float:
    """
    Score faithfulness using Claude as the judge.
    Used in ablation Run A to compare with GPT judge results.
    """
    context_text = "\n\n".join(chunks)
    prompt = (
        f"Given this context:\n{context_text}\n\n"
        f"And this answer:\n{answer}\n\n"
        f"Score the faithfulness from 0 to 1 where 1 means every claim "
        f"is supported by the context. Reply with a single decimal number "
        f"between 0 and 1 only. No words, no explanation, just the number."
    )
    response = anthropic_client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=10,
        messages=[{"role": "user", "content": prompt}]
    )
    return parse_score(response.content[0].text)


def score_answer_relevance(question: str, answer: str, use_gpt: bool = True) -> float:
    """
    Score answer relevance using synthetic question generation.
    Steps:
    1. Generate 3 synthetic questions the answer could be responding to
    2. Embed original + synthetic questions with MiniLM
    3. Compute cosine similarity between original and each synthetic
    4. Return average similarity score

    use_gpt=True  → GPT generates synthetic questions (Part 1 and Run B)
    use_gpt=False → Claude generates synthetic questions (Run A)
    """
    prompt = (
        f"Given this answer:\n{answer}\n\n"
        f"Generate 3 questions this answer could be responding to. "
        f"Return only 3 questions, one per line."
    )

    # Generate synthetic questions using the selected judge
    if use_gpt:
        response = gpt_client.chat.completions.create(
            model=GPT_JUDGE_MODEL,
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )
        raw_text = response.choices[0].message.content
    else:
        response = anthropic_client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )
        raw_text = response.content[0].text

    # Parse synthetic questions — discard blank lines
    synthetic_questions = [
        line.strip()
        for line in raw_text.strip().split("\n")
        if line.strip()
    ][:3]

    if not synthetic_questions:
        return 0.0

    # Embed original and synthetic questions with MiniLM
    all_questions = [question] + synthetic_questions
    embeddings = embedding_model.encode(all_questions)
    original_embedding = embeddings[0]
    synthetic_embeddings = embeddings[1:]

    # Compute cosine similarity for each synthetic question
    similarities = []
    for syn_emb in synthetic_embeddings:
        cos_sim = np.dot(original_embedding, syn_emb) / (
            np.linalg.norm(original_embedding) * np.linalg.norm(syn_emb)
        )
        similarities.append(cos_sim)

    return float(np.mean(similarities))


def score_context_relevance_gpt(question: str, chunks: list) -> float:
    """
    Score context relevance using GPT as the judge.
    Measures what proportion of retrieved chunks was needed to answer the question.
    Score 1 = all chunks were necessary.
    Score 0 = none of the chunks were relevant.
    """
    context_text = "\n\n".join(chunks)
    prompt = (
        f"Given this question: {question}\n\n"
        f"And these chunks:\n{context_text}\n\n"
        f"What proportion of the retrieved content is necessary to answer "
        f"the question? Reply with a single decimal number between 0 and 1 "
        f"only. No words, no explanation, just the number."
    )
    response = gpt_client.chat.completions.create(
        model=GPT_JUDGE_MODEL,
        max_tokens=10,
        messages=[{"role": "user", "content": prompt}]
    )
    return parse_score(response.choices[0].message.content)


def score_context_relevance_claude(question: str, chunks: list) -> float:
    """
    Score context relevance using Claude as the judge.
    Used in ablation Run A to compare with GPT judge results.
    """
    context_text = "\n\n".join(chunks)
    prompt = (
        f"Given this question: {question}\n\n"
        f"And these chunks:\n{context_text}\n\n"
        f"What proportion of the retrieved content is necessary to answer "
        f"the question? Reply with a single decimal number between 0 and 1 "
        f"only. No words, no explanation, just the number."
    )
    response = anthropic_client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=10,
        messages=[{"role": "user", "content": prompt}]
    )
    return parse_score(response.content[0].text)


def run_evaluation(databases, questions, use_gpt_judge: bool, label: str):
    """
    Run the full evaluation loop for all questions and databases.

    databases    : list of ChromaDB database paths to evaluate
    questions    : list of (question, category) tuples
    use_gpt_judge: True = GPT judges, False = Claude judges
    label        : string label for printing (e.g. 'GPT judge')

    Returns a dict: { db_path: [ result_row, ... ] }
    """
    # Load all collections
    print(f"\nLoading ChromaDB collections for {label}...")
    collections = {}
    for db in databases:
        try:
            collections[db] = load_collection(db)
            print(f"  ✅ Loaded {db}")
        except Exception as e:
            print(f"  ⚠️  Could not load {db}: {e}")

    judge_name = "GPT (gpt-4o-mini)" if use_gpt_judge else "Claude (claude-sonnet-4-5)"
    print(f"\nGenerator: Claude (claude-sonnet-4-5)")
    print(f"Judge    : {judge_name}")
    print(f"Questions: {len(questions)} | Databases: {len(collections)}\n")

    all_results = {db: [] for db in databases}

    for q_idx, (question, category) in enumerate(questions):
        print(f"[{q_idx+1}/{len(questions)}] {category}: {question[:60]}...")

        for db in databases:
            if db not in collections:
                continue

            # Step 1 — retrieve top-K chunks
            chunks = retrieve_chunks(collections[db], question, TOP_K)

            # Step 2 — generate VERA's answer with Claude
            t_start = time.time()
            answer = generate_answer(question, chunks)
            t_end = time.time()
            response_time = round(t_end - t_start, 3)

            # Step 3 — score faithfulness with selected judge
            if use_gpt_judge:
                faithfulness = score_faithfulness_gpt(chunks, answer)
            else:
                faithfulness = score_faithfulness_claude(chunks, answer)

            # Step 4 — score answer relevance with selected judge
            answer_relevance = score_answer_relevance(
                question, answer, use_gpt=use_gpt_judge
            )

            # Step 5 — score context relevance with selected judge
            if use_gpt_judge:
                context_relevance = score_context_relevance_gpt(question, chunks)
            else:
                context_relevance = score_context_relevance_claude(question, chunks)

            # Step 6 — store all results
            all_results[db].append({
                "question":          question,
                "category":          category,
                "answer":            answer,
                "faithfulness":      round(faithfulness, 4),
                "answer_relevance":  round(answer_relevance, 4),
                "context_relevance": round(context_relevance, 4),
                "response_time":     response_time,
            })

            print(f"    {db:15s}  F={faithfulness:.2f}  "
                  f"AR={answer_relevance:.2f}  "
                  f"CR={context_relevance:.2f}  t={response_time:.1f}s")

    return all_results


def save_evaluation_csv(results, db_name, path):
    """Save per-question detailed results for one database to a CSV file."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "question", "category", "answer",
            "faithfulness", "answer_relevance",
            "context_relevance", "response_time",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in results.get(db_name, []):
            writer.writerow(row)
    print(f"✅ Saved detailed results to {path}")


def save_ablation_csv(all_results, databases, path):
    """Save average scores per strategy to a CSV file."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "strategy", "avg_faithfulness",
            "avg_answer_relevance", "avg_context_relevance", "avg_overall",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for db in databases:
            rows = all_results[db]
            if not rows:
                continue
            avg_f  = np.mean([r["faithfulness"]      for r in rows])
            avg_ar = np.mean([r["answer_relevance"]   for r in rows])
            avg_cr = np.mean([r["context_relevance"]  for r in rows])
            avg_overall = np.mean([avg_f, avg_ar, avg_cr])
            writer.writerow({
                "strategy":              db,
                "avg_faithfulness":      round(avg_f,  4),
                "avg_answer_relevance":  round(avg_ar, 4),
                "avg_context_relevance": round(avg_cr, 4),
                "avg_overall":           round(avg_overall, 4),
            })
    print(f"✅ Saved ablation results to {path}")


def print_ablation_table(all_results, databases, judge_label):
    """Print a formatted summary table for one judge's ablation results."""
    print(f"\n{'='*70}")
    print(f"ABLATION STUDY — {judge_label.upper()}")
    print(f"{'='*70}")
    print(f"{'Strategy':<16} {'Faithfulness':>14} {'Ans.Relevance':>14} "
          f"{'Ctx.Relevance':>14} {'Overall':>10}")
    print(f"{'-'*70}")
    for db in databases:
        rows = all_results[db]
        if not rows:
            print(f"{db:<16} {'N/A':>14} {'N/A':>14} {'N/A':>14} {'N/A':>10}")
            continue
        avg_f  = np.mean([r["faithfulness"]      for r in rows])
        avg_ar = np.mean([r["answer_relevance"]   for r in rows])
        avg_cr = np.mean([r["context_relevance"]  for r in rows])
        avg_overall = np.mean([avg_f, avg_ar, avg_cr])
        print(f"{db:<16} {avg_f:>14.4f} {avg_ar:>14.4f} "
              f"{avg_cr:>14.4f} {avg_overall:>10.4f}")
    print(f"{'='*70}")


# ============================================================
# PART 1 — SKIPPED (evaluation_results.csv already saved)
# ============================================================
# Part 1 has already been completed in a previous run.
# evaluation_results.csv is already saved and does not need
# to be regenerated. Only the ablation study runs below.

print("\n" + "="*70)
print("SKIPPING PART 1 — evaluation_results.csv already saved")
print("="*70)


# ============================================================
# PART 2A — ABLATION STUDY WITH CLAUDE AS JUDGE
# ============================================================
# Compare all three chunking strategies with Claude as judge.
# This is Run A — results saved to ablation_results_claude.csv

print("\n" + "="*70)
print("PART 2A — ABLATION STUDY (Claude judge)")
print("="*70)

ablation_claude = run_evaluation(
    databases=DATABASES,
    questions=QUESTIONS,
    use_gpt_judge=False,
    label="Ablation — Claude judge"
)

save_ablation_csv(ablation_claude, DATABASES, "ablation_results_claude.csv")


# ============================================================
# PART 2B — ABLATION STUDY WITH GPT AS JUDGE
# ============================================================
# Compare all three chunking strategies with GPT as judge.
# This is Run B — results saved to ablation_results_gpt.csv

print("\n" + "="*70)
print("PART 2B — ABLATION STUDY (GPT judge)")
print("="*70)

ablation_gpt = run_evaluation(
    databases=DATABASES,
    questions=QUESTIONS,
    use_gpt_judge=True,
    label="Ablation — GPT judge"
)

save_ablation_csv(ablation_gpt, DATABASES, "ablation_results_gpt.csv")


# ============================================================
# FINAL SUMMARY — SIDE BY SIDE COMPARISON
# ============================================================

print_ablation_table(ablation_claude, DATABASES, "Claude as Judge")
print_ablation_table(ablation_gpt,    DATABASES, "GPT as Judge")

print("\n" + "="*70)
print("EVALUATION COMPLETE")
print("="*70)
print("  Detailed results (hr_section) : evaluation_results.csv")
print("  Ablation — Claude judge        : ablation_results_claude.csv")
print("  Ablation — GPT judge           : ablation_results_gpt.csv")
print("="*70)
