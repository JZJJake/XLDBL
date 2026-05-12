import sqlite3
import os
import chromadb
from chromadb.config import Settings
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
    # Create Nodes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS nodes (
            id TEXT PRIMARY KEY,
            label TEXT NOT NULL,
            type TEXT
        )
    ''')
    # Create Edges table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS edges (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            target TEXT NOT NULL,
            relation TEXT NOT NULL,
            FOREIGN KEY (source) REFERENCES nodes (id),
            FOREIGN KEY (target) REFERENCES nodes (id)
        )
    ''')
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

# Initialize Embedding Model (High precision multilingual)
def init_embedding_model():
    print("Loading Sentence Transformer model (this may take a while on first run)...")
    # paraphrase-multilingual-MiniLM-L12-v2 is a good balance between speed and precision for multiple languages
    model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    return model

if __name__ == "__main__":
    print("Initializing SQLite...")
    init_sqlite()
    print("Initializing ChromaDB...")
    init_chroma()
    print("Database initialization complete.")
