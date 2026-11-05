# ============================================================
# INGEST_PARAGRAPH.PY
# ============================================================
# Ablation study variant: Paragraph-based chunking strategy.
# This script reads the same handbook.pdf but splits text at
# blank lines and paragraph breaks instead of using section
# headers or fixed character counts. Results are saved to a
# separate ChromaDB database called hr_paragraph.
#
# What this file does step by step:
# 1. Opens handbook.pdf and extracts all text with pdfplumber
# 2. Splits the full text at blank lines / paragraph boundaries
# 3. Filters out chunks that are too short to be useful
# 4. Embeds every chunk with paraphrase-multilingual-MiniLM-L12-v2
# 5. Saves chunks and embeddings to ChromaDB database hr_paragraph
# 6. Prints a summary when done
#
# Run with:
#   python ingest_paragraph.py
# ============================================================

# ── Imports ──────────────────────────────────────────────────

# pdfplumber opens and reads PDF files page by page
import pdfplumber

# re provides regular expressions for detecting blank lines
import re

# SentenceTransformer converts text strings into number vectors
from sentence_transformers import SentenceTransformer

# chromadb is the local vector database for storing chunks
import chromadb


# ============================================================
# STEP 1 — EXTRACT ALL TEXT FROM THE PDF
# ============================================================

# Open handbook.pdf; the 'with' block closes the file automatically
with pdfplumber.open("handbook.pdf") as pdf:

    # Accumulate text from every page into one long string
    full_text = ""

    # Iterate over every page in the document
    for page in pdf.pages:

        # Extract the plain text on this page (returns None if page is blank)
        page_text = page.extract_text()

        # Only append text if the page contained readable content
        if page_text:
            # Separate pages with a newline so words don't merge across pages
            full_text += page_text + "\n"

    # Report how many pages were read
    print(f"✅ Read {len(pdf.pages)} pages from handbook.pdf")

# Report total characters extracted — useful for sanity-checking
print(f"✅ Extracted {len(full_text)} characters of text")


# ============================================================
# STEP 2 — PARAGRAPH-BASED CHUNKING
# ============================================================
# A paragraph boundary is any sequence of two or more newlines,
# which corresponds to a blank line in the extracted text.
# re.split keeps the split clean and handles Windows (\r\n) and
# Unix (\n) line endings through the \r?\n pattern.

# Minimum number of characters a chunk must have to be kept.
# Very short chunks (headers, stray punctuation) add noise without value.
MIN_CHUNK_LENGTH = 40

# Split the full text wherever there are one or more blank lines.
# \r?\n handles both Unix and Windows line endings.
# The {2,} means "two or more newlines in a row" = a blank line separator.
raw_paragraphs = re.split(r'(\r?\n){2,}', full_text)

# List that will hold the accepted paragraph chunks
paragraph_chunks = []

# Review every raw paragraph produced by the split
for raw in raw_paragraphs:

    # Strip leading/trailing whitespace and collapse internal newlines
    # so each chunk reads as a single flowing paragraph
    cleaned = raw.strip().replace("\n", " ")

    # Discard chunks that are shorter than the minimum useful length.
    # These are typically page numbers, lone headings, or artefacts.
    if len(cleaned) < MIN_CHUNK_LENGTH:
        continue

    # Keep this paragraph as a valid chunk
    paragraph_chunks.append(cleaned)

# Report how many usable paragraph chunks were created
print(f"✅ Created {len(paragraph_chunks)} paragraph chunks "
      f"(min_length={MIN_CHUNK_LENGTH})")


# ============================================================
# STEP 3 — LOAD THE EMBEDDING MODEL
# ============================================================

print("\nStep 3: Loading embedding model...")

# Load the multilingual MiniLM model — the same model used in all
# three strategies so that embedding comparisons remain fair
embedding_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

print("✅ Embedding model loaded")


# ============================================================
# STEP 4 — EMBED ALL CHUNKS
# ============================================================

print(f"Embedding {len(paragraph_chunks)} chunks — this may take a moment...")

# Convert every chunk string into a numerical embedding vector.
# show_progress_bar=True displays a live progress bar in the terminal.
embeddings = embedding_model.encode(paragraph_chunks, show_progress_bar=True)

print(f"✅ Embedded {len(embeddings)} chunks")


# ============================================================
# STEP 5 — SAVE TO CHROMADB (hr_paragraph)
# ============================================================

print("\nSaving to ChromaDB (hr_paragraph)...")

# Create a persistent ChromaDB client pointing at the hr_paragraph folder.
# This is a separate database from hr_section and hr_fixed so that
# the three strategies never interfere with each other.
chroma_client = chromadb.PersistentClient(path="hr_paragraph")

# Delete the old collection if it exists so we always start from a clean slate.
# This prevents duplicates when the script is run more than once.
try:
    chroma_client.delete_collection("vera_chunks")
    print("🗑️  Deleted old collection to start fresh")
except Exception:
    # Collection did not exist yet — that is fine, just continue
    pass

# Create a fresh collection called vera_chunks inside the hr_paragraph database
collection = chroma_client.create_collection("vera_chunks")

# Build a unique string ID for each chunk — ChromaDB requires unique IDs
ids = [f"chunk_{i}" for i in range(len(paragraph_chunks))]

# Build minimal metadata for each chunk so we can identify the strategy later
metadatas = [{"strategy": "paragraph", "chunk_index": i} for i in range(len(paragraph_chunks))]

# Insert all chunks, their embeddings, metadata, and IDs in one call
collection.add(
    documents=paragraph_chunks,                    # raw text of each chunk
    embeddings=[e.tolist() for e in embeddings],   # convert numpy arrays to plain lists
    metadatas=metadatas,                           # strategy label and index
    ids=ids                                        # unique identifier per chunk
)

# Confirm how many chunks were stored
print(f"\n🎉 Done! Stored {collection.count()} chunks in ChromaDB (hr_paragraph/vera_chunks)")
print("You can now run evaluate.py to compare this strategy with the others.")
