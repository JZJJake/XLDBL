import os
import sqlite3

# Setup Paths
DB_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DB_DIR, exist_ok=True)
os.makedirs(os.path.join(DB_DIR, "raw"), exist_ok=True)
os.makedirs(os.path.join(DB_DIR, "wiki"), exist_ok=True)

SQLITE_DB_PATH = os.path.join(DB_DIR, "knowledge_graph.db")

# Initialize SQLite for Knowledge Graph Nodes and Edges
def init_sqlite():
    conn = sqlite3.connect(SQLITE_DB_PATH, check_same_thread=False)
    cursor = conn.cursor()
    # Create Nodes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS nodes (
            id TEXT PRIMARY KEY,
            label TEXT NOT NULL,
            type TEXT,
            description TEXT,
            source_documents TEXT,
            needs_review BOOLEAN DEFAULT 0
        )
    ''')

    try:
        cursor.execute("ALTER TABLE nodes ADD COLUMN description TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE nodes ADD COLUMN source_documents TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE nodes ADD COLUMN needs_review BOOLEAN DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    # Create Edges table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS edges (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            target TEXT NOT NULL,
            relation TEXT NOT NULL,
            description TEXT,
            source_documents TEXT,
            needs_review BOOLEAN DEFAULT 0,
            FOREIGN KEY (source) REFERENCES nodes (id),
            FOREIGN KEY (target) REFERENCES nodes (id)
        )
    ''')

    try:
        cursor.execute("ALTER TABLE edges ADD COLUMN description TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE edges ADD COLUMN source_documents TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE edges ADD COLUMN needs_review BOOLEAN DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    return conn

if __name__ == "__main__":
    init_sqlite()
    print("Database initialization complete.")
