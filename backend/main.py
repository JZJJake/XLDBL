from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
import uuid
import json
import os
import shutil
from typing import List, Optional
import sqlite3

# Import our database and model setup
from database import init_sqlite, init_chroma, init_embedding_model

app = FastAPI()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize systems
sqlite_conn = init_sqlite()
chroma_client, chroma_collection = init_chroma()
# Loading the model here ensures it's kept in memory while the server runs
embedding_model = init_embedding_model()

# Setup OpenAI for DeepSeek
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

if DEEPSEEK_API_KEY:
    openai_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
else:
    openai_client = None


# --- MODELS ---
class NodeBase(BaseModel):
    id: str
    label: str
    type: Optional[str] = "Entity"

class EdgeBase(BaseModel):
    id: str
    source: str
    target: str
    relation: str

class ChatRequest(BaseModel):
    message: str


# --- HELPER FUNCTIONS ---
def get_db_cursor():
    return sqlite_conn.cursor()

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50):
    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start:start+chunk_size])
        start += chunk_size - overlap
    return chunks

def extract_kg_from_text(text: str):
    if not openai_client:
        print("DeepSeek API not configured, skipping KG extraction.")
        return {"nodes": [], "edges": []}

    prompt = f"""
    Analyze the following text and extract a Knowledge Graph.
    Identify key entities (Nodes) and the relationships between them (Edges).
    Respond strictly in JSON format with two keys: "nodes" and "edges".
    Each node should have "id" (unique string), "label" (string), "type" (string).
    Each edge should have "id" (unique string), "source" (node id), "target" (node id), "relation" (string).

    Text: {text[:2000]} # Limit to avoid token overflow
    """
    try:
        response = openai_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a data extraction assistant. Output ONLY valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        print(f"Error calling DeepSeek API: {e}")
        return {"nodes": [], "edges": []}


# --- APIS ---

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename.endswith('.md'):
        raise HTTPException(status_code=400, detail="Only Markdown (.md) files are supported")

    content = await file.read()
    text = content.decode('utf-8', errors='ignore')

    # 1. Chunk Text & Calculate Embeddings
    chunks = chunk_text(text)
    chunk_ids = [str(uuid.uuid4()) for _ in chunks]
    embeddings = embedding_model.encode(chunks).tolist()

    metadata = [{"source": file.filename} for _ in chunks]

    # Store in ChromaDB
    chroma_collection.add(
        ids=chunk_ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadata
    )

    # 2. Extract KG using DeepSeek
    kg_data = extract_kg_from_text(text)

    # 3. Store KG in SQLite
    cursor = get_db_cursor()
    nodes_added = 0
    edges_added = 0
    for node in kg_data.get("nodes", []):
        try:
            cursor.execute("INSERT OR REPLACE INTO nodes (id, label, type) VALUES (?, ?, ?)",
                           (node["id"], node["label"], node.get("type", "Entity")))
            nodes_added += 1
        except Exception as e:
            print(f"Error inserting node: {e}")

    for edge in kg_data.get("edges", []):
        try:
            cursor.execute("INSERT OR REPLACE INTO edges (id, source, target, relation) VALUES (?, ?, ?, ?)",
                           (edge["id"], edge["source"], edge["target"], edge["relation"]))
            edges_added += 1
        except Exception as e:
             print(f"Error inserting edge: {e}")

    sqlite_conn.commit()

    return {"message": "File processed successfully", "chunks": len(chunks), "nodes_added": nodes_added, "edges_added": edges_added}


@app.get("/api/graph")
def get_graph():
    cursor = get_db_cursor()
    cursor.execute("SELECT id, label, type FROM nodes")
    nodes = [{"id": row[0], "label": row[1], "type": row[2]} for row in cursor.fetchall()]

    cursor.execute("SELECT id, source, target, relation FROM edges")
    edges = [{"id": row[0], "source": row[1], "target": row[2], "relation": row[3]} for row in cursor.fetchall()]

    return {"nodes": nodes, "links": edges}

# Node Maintenance
@app.post("/api/nodes")
def add_node(node: NodeBase):
    cursor = get_db_cursor()
    try:
        cursor.execute("INSERT INTO nodes (id, label, type) VALUES (?, ?, ?)", (node.id, node.label, node.type))
        sqlite_conn.commit()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/nodes/{node_id}")
def delete_node(node_id: str):
    cursor = get_db_cursor()
    cursor.execute("DELETE FROM edges WHERE source = ? OR target = ?", (node_id, node_id))
    cursor.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
    sqlite_conn.commit()
    return {"success": True}

# Edge Maintenance
@app.post("/api/edges")
def add_edge(edge: EdgeBase):
    cursor = get_db_cursor()
    try:
        cursor.execute("INSERT INTO edges (id, source, target, relation) VALUES (?, ?, ?, ?)",
                       (edge.id, edge.source, edge.target, edge.relation))
        sqlite_conn.commit()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/edges/{edge_id}")
def delete_edge(edge_id: str):
    cursor = get_db_cursor()
    cursor.execute("DELETE FROM edges WHERE id = ?", (edge_id,))
    sqlite_conn.commit()
    return {"success": True}

# Export for LLM Integration
@app.get("/api/export")
def export_database():
    # Only exporting ChromaDB knowledge chunks as requested by user
    data = chroma_collection.get(include=["documents", "metadatas", "embeddings"])

    export_data = {
        "chunks": []
    }

    for i in range(len(data['ids'])):
        chunk_obj = {
            "id": data['ids'][i],
            "content": data['documents'][i],
            "source": data['metadatas'][i].get("source", ""),
            "vector": data['embeddings'][i] if 'embeddings' in data and data['embeddings'] else []
        }
        export_data["chunks"].append(chunk_obj)

    export_path = os.path.join(os.path.dirname(__file__), "data", "knowledge_base_export.json")
    with open(export_path, "w", encoding="utf-8") as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)

    return FileResponse(export_path, filename="knowledge_base_export.json", media_type="application/json")


# Chat/RAG endpoint
@app.post("/api/chat")
def chat_with_knowledge(req: ChatRequest):
    if not openai_client:
        return {"reply": "DeepSeek API key not configured. Cannot generate response."}

    # Search vector database
    query_vector = embedding_model.encode([req.message]).tolist()
    results = chroma_collection.query(
        query_embeddings=query_vector,
        n_results=3
    )

    context_docs = results['documents'][0] if results['documents'] else []
    context = "\n".join(context_docs)

    prompt = f"""
    Answer the user's question based on the following context retrieved from the knowledge base.
    If the context does not contain the answer, say "I don't have enough information to answer that based on the uploaded documents."

    Context:
    {context}

    Question: {req.message}
    """

    try:
        response = openai_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a helpful knowledge assistant."},
                {"role": "user", "content": prompt}
            ]
        )
        return {"reply": response.choices[0].message.content}
    except Exception as e:
        return {"reply": f"Error calling DeepSeek API: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
