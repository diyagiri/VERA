# ============================================================
# INGEST.PY
# ============================================================
# This file is the data preparation script for VERA.
# You run this ONCE before using the chatbot.
#
# What this file does step by step:
# 1. Opens the HR handbook PDF and extracts all the text
# 2. Splits the text into chunks based on section headers
# 3. Converts each chunk into numbers (embeddings) so the
#    computer can understand and search the meaning
# 4. Saves all chunks and their embeddings into a local
#    database called hr_section using ChromaDB
# 5. Prints how many chunks were saved when done
#
# Run this file with:
#   python ingest.py
# ============================================================

# ── Import libraries ─────────────────────────────────────────
# pdfplumber is the library that knows how to open and read PDF files
import pdfplumber

# re is Python's built-in library for detecting text patterns (regex)
import re

# SentenceTransformer converts text into numbers (embeddings)
from sentence_transformers import SentenceTransformer

# chromadb is the local database where we store all chunks
import chromadb


# ============================================================
# STEP 1 — EXTRACT TEXT AND TABLES FROM PDF
# ============================================================

# Open the PDF file called handbook.pdf
# 'with' means: open it, do the work, then close it automatically
with pdfplumber.open("handbook.pdf") as pdf:

    # Create an empty string to collect all the text from every page
    full_text = ""

    # Create an empty list to collect all tables found in the PDF
    all_tables = []

    # Loop through every page in the PDF one by one
    for page in pdf.pages:

        # Extract the plain text from this page
        page_text = page.extract_text()

        # Only add the text if the page actually has text (skip empty/image pages)
        if page_text:
            # Add this page's text to the full text
            # "\n" means new line — keeps pages separated
            full_text += page_text + "\n"

        # Extract any tables on this page
        # Returns a list of tables — each table is a list of rows
        page_tables = page.extract_tables()

        # Only save tables if there are any on this page
        if page_tables:
            # Add all tables from this page to our full tables list
            all_tables.extend(page_tables)

    # Print how many pages were read
    print(f"✅ Read {len(pdf.pages)} pages from handbook.pdf")

# Print how many characters of text were extracted
print(f"✅ Extracted {len(full_text)} characters of text")

# Print how many tables were found
print(f"✅ Found {len(all_tables)} tables in the PDF")


# ============================================================
# STEP 2 — CONVERT TABLES INTO PLAIN ENGLISH SENTENCES
# ============================================================

# This function takes one table (a list of rows) and converts
# each row into a readable English sentence
def convert_table_to_sentences(table):
    """
    Takes a pdfplumber table (list of rows, each row is a list of values)
    and converts each row into a plain English sentence.
    Returns a list of sentences.
    """

    # Empty list to store all the sentences we create
    sentences = []

    # Loop through each row in the table
    for row in table:

        # Clean up the row — remove None values and strip whitespace
        # Some cells might be empty (None) so we replace them with ""
        cleaned_row = [str(cell).strip() if cell is not None else "" for cell in row]

        # Skip rows that are completely empty
        if not any(cleaned_row):
            continue

        # Skip header rows — they usually contain words like "Category" or "Amount"
        # We detect headers by checking if the row looks like column titles
        if cleaned_row[0].lower() in ["category", "categorie", "type", "#", "nr", ""]:
            continue

        # Try to build a meaningful sentence from the row values
        # We check how many columns the row has to decide the format
        # Join all values EXCEPT the first one (category number) into a readable string
        # We skip cleaned_row[0] because we already use it as the category number
        raw = " ".join([c for c in cleaned_row[1:] if c])

        # Build a clean English sentence for this row
        sentence = f"Category {cleaned_row[0]}: {raw}."

        # Add the sentence to our list
        sentences.append(sentence)

    return sentences


# Create an empty list to store all table sentences
table_chunks = []

# Loop through every table we found in the PDF
for table in all_tables:

    # Convert this table's rows into plain English sentences
    sentences = convert_table_to_sentences(table)

    # Add all sentences from this table to our table_chunks list
    table_chunks.extend(sentences)

# Print how many table sentences were created
print(f"✅ Converted tables into {len(table_chunks)} sentences")

# Print the sentences so we can check they look correct
print("\nTable sentences:")
for sentence in table_chunks:
    print(f"  → {sentence}")


# ============================================================
# STEP 3 — SECTION-BASED CHUNKING
# ============================================================

# This function splits the full text into chunks based on section headings.
# It looks for patterns like: A., B., C.1, D.2, E.6 at the start of a line.
# Everything from one heading to the next becomes one chunk.
def split_into_sections(text):
    """
    Scans the text for section headings using regex.
    Returns a list of dicts, each with:
      - 'heading'  : the section title detected
      - 'content'  : the full text of that section
      - 'metadata' : a dict with section name for ChromaDB tagging
    """

    # This regex pattern detects headings like:
    # A.   B.   C.1   D.2   E.6   A.1.1   etc.
    # ^ means "start of line", \s* allows spaces after the letter/number
    header_pattern = re.compile(
        r'^([A-Z]\.\d*\.?\d*\s+.+|[A-Z]\.\s+.+)',
        re.MULTILINE
    )

    # Find all matches and their positions in the text
    matches = list(header_pattern.finditer(text))

    # Empty list to store all our chunks
    sections = []

    # Loop through every detected heading
    for i, match in enumerate(matches):

        # The heading text (e.g. "A. General" or "C.1 Lease Categories")
        heading = match.group().strip()

        # Where this section starts in the full text
        start = match.start()

        # Where this section ends = where the next heading starts
        # If this is the last heading, go to the end of the text
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)

        # Extract the full content of this section
        content = text[start:end].strip()

        # Skip sections that are too short to be useful (less than 30 chars)
        if len(content) < 30:
            continue

        # ── Handle long sections ─────────────────────────────
        # If a section is longer than 1000 characters, split it in half
        # with 50 character overlap so no context is lost at the boundary
        if len(content) > 1000:

            # Calculate the midpoint of the content
            mid = len(content) // 2

            # First half: from start to midpoint
            first_half = content[:mid + 50].strip()

            # Second half: starts 50 chars before midpoint (overlap)
            second_half = content[mid - 50:].strip()

            # Add first half as a chunk with metadata tag
            sections.append({
                "heading": heading,
                "content": first_half,
                "metadata": {"section": heading, "part": "1 of 2"}
            })

            # Add second half as a chunk with the same metadata tag
            sections.append({
                "heading": heading,
                "content": second_half,
                "metadata": {"section": heading, "part": "2 of 2"}
            })

            # Print so we can see this section was split
            print(f"  📄 {heading}  [split into 2 parts]")

        else:
            # Section is short enough — keep it as one chunk
            sections.append({
                "heading": heading,
                "content": content,
                "metadata": {"section": heading, "part": "1 of 1"}
            })

            # Print so we can see this section was detected
            print(f"  📄 {heading}")

    return sections


# Run the section chunking function on the full extracted text
print("\nDetected sections:")
text_chunks = split_into_sections(full_text)

# Print total number of chunks created from text
print(f"\n✅ Created {len(text_chunks)} text chunks from sections")

# Combine text chunks and table chunks into one final list
# text_chunks is a list of dicts, table_chunks is a list of strings
# We convert table_chunks to the same dict format for consistency
all_chunks = text_chunks + [
    {
        "heading": "Table Data",
        "content": sentence,
        "metadata": {"section": "Table Data", "part": "1 of 1"}
    }
    for sentence in table_chunks
]

print(f"✅ Total chunks (text + tables): {len(all_chunks)}")


# ============================================================
# STEP 4 — EMBED ALL CHUNKS AND SAVE TO CHROMADB
# ============================================================

# ── Load the embedding model ─────────────────────────────────
print("\nStep 4: Loading embedding model...")

# Load the multilingual sentence transformer model
# This model understands both Dutch and English
# It converts any text into a list of numbers that capture its meaning
# Example: "lease car" and "company vehicle" get similar numbers
embedding_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

print("✅ Embedding model loaded")

# ── Prepare chunks for embedding ─────────────────────────────

# Extract just the text content from each chunk dict
# The embedding model only needs the text, not the metadata
texts = [chunk["content"] for chunk in all_chunks]

# Extract the metadata from each chunk
# This will be stored alongside the text in ChromaDB
metadatas = [chunk["metadata"] for chunk in all_chunks]

# Create a unique ID for each chunk
# ChromaDB requires every item to have a unique string ID
ids = [f"chunk_{i}" for i in range(len(all_chunks))]

# ── Embed all chunks ─────────────────────────────────────────
print(f"Embedding {len(texts)} chunks — this may take a moment...")

# Convert all text chunks into number vectors (embeddings)
# show_progress_bar=True shows a progress bar in the terminal
embeddings = embedding_model.encode(texts, show_progress_bar=True)

print(f"✅ Embedded {len(embeddings)} chunks")

# ── Save to ChromaDB ─────────────────────────────────────────
print("\nSaving to ChromaDB...")

# Create a ChromaDB client that saves data to a folder called hr_section
# PersistentClient means the data is saved to disk permanently
# The hr_section folder will appear in your XEBIA THESIS directory
chroma_client = chromadb.PersistentClient(path="hr_section")

# Delete the old collection if it exists so we start fresh
# This prevents duplicate chunks if you run ingest.py more than once
try:
    chroma_client.delete_collection("vera_chunks")
    print("🗑️  Deleted old collection to start fresh")
except:
    # If the collection doesn't exist yet, that's fine — just continue
    pass

# Create a new collection called vera_chunks
# A collection is like a table in a database — it holds all our chunks
collection = chroma_client.create_collection("vera_chunks")

# Add everything to ChromaDB in one go:
# - documents: the actual text of each chunk
# - embeddings: the number vectors for each chunk
# - metadatas: the section labels for each chunk
# - ids: the unique ID for each chunk
collection.add(
    documents=texts,
    embeddings=[e.tolist() for e in embeddings],  # convert numpy arrays to lists
    metadatas=metadatas,
    ids=ids
)

# Print confirmation with total chunks stored
print(f"\n🎉 Done! Stored {collection.count()} chunks in ChromaDB (hr_section/vera_chunks)")
print("You can now run chatbot.py to start chatting with VERA!")
