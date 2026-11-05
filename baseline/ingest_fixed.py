# ============================================================
# INGEST_FIXED.PY
# ============================================================
# Ablation study variant: Fixed-size chunking strategy.
# This script uses the same PDF and embedding model as the
# main ingest.py but splits text into fixed 500-character
# chunks with 50-character overlap instead of section-based
# chunking. Results are saved to a separate ChromaDB database
# called hr_fixed so all three strategies can be compared.
#
# What this file does step by step:
# 1. Opens handbook.pdf and extracts all text with pdfplumber
# 2. Splits the full text into overlapping fixed-size chunks
# 3. Embeds every chunk with paraphrase-multilingual-MiniLM-L12-v2
# 4. Saves chunks and embeddings to ChromaDB database hr_fixed
# 5. Prints a summary when done
#
# Run with:
#   python ingest_fixed.py
# ============================================================

# ── Imports ──────────────────────────────────────────────────

# pdfplumber opens and reads PDF files page by page
import pdfplumber

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
# STEP 2 — FIXED-SIZE CHUNKING WITH OVERLAP
# ============================================================
# We slide a window of CHUNK_SIZE characters across the full text.
# Each step moves forward by (CHUNK_SIZE - OVERLAP) characters so
# that the last OVERLAP characters of one chunk appear at the start
# of the next. This prevents context from being cut off at boundaries.

# Size of each chunk in characters
CHUNK_SIZE = 500

# Number of characters shared between consecutive chunks
OVERLAP = 50

# List that will hold all fixed-size chunk strings
fixed_chunks = []

# Starting position of the current chunk window
start = 0

# Slide the window until we have covered the entire text
while start < len(full_text):

    # The window ends at start + CHUNK_SIZE, capped at the text length
    end = min(start + CHUNK_SIZE, len(full_text))

    # Extract the substring for this chunk and strip leading/trailing whitespace
    chunk_text = full_text[start:end].strip()

    # Only store the chunk if it contains actual content (skip blank windows)
    if chunk_text:
        fixed_chunks.append(chunk_text)

    # Move the window forward by (CHUNK_SIZE - OVERLAP) so the next chunk
    # starts OVERLAP characters before where this chunk ended
    start += CHUNK_SIZE - OVERLAP

# Report total number of chunks created
print(f"✅ Created {len(fixed_chunks)} fixed-size chunks "
      f"(size={CHUNK_SIZE}, overlap={OVERLAP})")


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

print(f"Embedding {len(fixed_chunks)} chunks — this may take a moment...")

# Convert every chunk string into a numerical embedding vector.
# show_progress_bar=True displays a live progress bar in the terminal.
embeddings = embedding_model.encode(fixed_chunks, show_progress_bar=True)

print(f"✅ Embedded {len(embeddings)} chunks")


# ============================================================
# STEP 5 — SAVE TO CHROMADB (hr_fixed)
# ============================================================

print("\nSaving to ChromaDB (hr_fixed)...")

# Create a persistent ChromaDB client pointing at the hr_fixed folder.
# This is a separate database from hr_section and hr_paragraph so that
# the three strategies never interfere with each other.
chroma_client = chromadb.PersistentClient(path="hr_fixed")

# Delete the old collection if it exists so we always start from a clean slate.
# This prevents duplicates when the script is run more than once.
try:
    chroma_client.delete_collection("vera_chunks")
    print("🗑️  Deleted old collection to start fresh")
except Exception:
    # Collection did not exist yet — that is fine, just continue
    pass

# Create a fresh collection called vera_chunks inside the hr_fixed database
collection = chroma_client.create_collection("vera_chunks")

# Build a unique string ID for each chunk — ChromaDB requires unique IDs
ids = [f"chunk_{i}" for i in range(len(fixed_chunks))]

# Build minimal metadata for each chunk so we can identify the strategy later
metadatas = [{"strategy": "fixed", "chunk_index": i} for i in range(len(fixed_chunks))]

# Insert all chunks, their embeddings, metadata, and IDs in one call
collection.add(
    documents=fixed_chunks,                        # raw text of each chunk
    embeddings=[e.tolist() for e in embeddings],   # convert numpy arrays to plain lists
    metadatas=metadatas,                           # strategy label and index
    ids=ids                                        # unique identifier per chunk
)

# Confirm how many chunks were stored
print(f"\n🎉 Done! Stored {collection.count()} chunks in ChromaDB (hr_fixed/vera_chunks)")
print("You can now run evaluate.py to compare this strategy with the others.")
