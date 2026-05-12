import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
import sqlite3
import chromadb
from sentence_transformers import SentenceTransformer

# Setup Paths
DB_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DB_DIR, exist_ok=True)
SQLITE_DB_PATH = os.path.join(DB_DIR, "knowledge_graph.db")
CHROMA_DB_PATH = os.path.join(DB_DIR, "chroma_db")

# Initialize SQLite for Knowledge Graph Nodes and Edges
def init_sqlite():
    conn = sqlite3.connect(SQLITE_DB_PATH, check_same_thread=False)
    cursor = conn.cursor()
    # Create Nodes table with rich description
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS nodes (
            id TEXT PRIMARY KEY,
            label TEXT NOT NULL,
            type TEXT,
            description TEXT
        )
    ''')

    # Try adding description column to existing nodes table if migrating from old version
    try:
        cursor.execute("ALTER TABLE nodes ADD COLUMN description TEXT")
    except sqlite3.OperationalError:
        pass # Column already exists

    # Create Edges table with rich description
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS edges (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            target TEXT NOT NULL,
            relation TEXT NOT NULL,
            description TEXT,
            FOREIGN KEY (source) REFERENCES nodes (id),
            FOREIGN KEY (target) REFERENCES nodes (id)
        )
    ''')

    # Try adding description column to existing edges table if migrating
    try:
        cursor.execute("ALTER TABLE edges ADD COLUMN description TEXT")
    except sqlite3.OperationalError:
        pass # Column already exists

    conn.commit()
    return conn

# Initialize ChromaDB for Vectors
def init_chroma():
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    collection = client.get_or_create_collection(
        name="document_chunks",
        metadata={"hnsw:space": "cosine"}
    )
    return client, collection

# Initialize Embedding Model
def init_embedding_model():
    print("Loading Sentence Transformer model (this may take a while on first run)...")
    model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    return model

if __name__ == "__main__":
    init_sqlite()
    init_chroma()
    print("Database initialization complete.")
