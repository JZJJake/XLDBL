import sqlite3
import os

DB_DIR = os.path.join(os.path.dirname(__file__), "backend", "data")
SQLITE_DB_PATH = os.path.join(DB_DIR, "knowledge_graph.db")

conn = sqlite3.connect(SQLITE_DB_PATH)
cursor = conn.cursor()

# Clear existing
cursor.execute("DELETE FROM edges")
cursor.execute("DELETE FROM nodes")

# Insert central node
cursor.execute("INSERT INTO nodes (id, label, type, description) VALUES ('center', 'Central Hub', 'Hub', 'The central hub')")

# Insert 3 connected nodes
cursor.execute("INSERT INTO nodes (id, label, type, description) VALUES ('n1', 'Node 1', 'Sub', 'Sub node 1')")
cursor.execute("INSERT INTO nodes (id, label, type, description) VALUES ('n2', 'Node 2', 'Sub', 'Sub node 2')")
cursor.execute("INSERT INTO nodes (id, label, type, description) VALUES ('n3', 'Node 3', 'Sub', 'Sub node 3')")

# Insert edges
cursor.execute("INSERT INTO edges (id, source, target, relation, description) VALUES ('e1', 'center', 'n1', 'connects', 'connection 1')")
cursor.execute("INSERT INTO edges (id, source, target, relation, description) VALUES ('e2', 'center', 'n2', 'connects', 'connection 2')")
cursor.execute("INSERT INTO edges (id, source, target, relation, description) VALUES ('e3', 'center', 'n3', 'connects', 'connection 3')")

conn.commit()
conn.close()
print("Mock data added.")
