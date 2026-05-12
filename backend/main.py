import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
import uuid
import json
import sqlite3
from typing import List, Optional

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
    description: Optional[str] = ""

class EdgeBase(BaseModel):
    id: str
    source: str
    target: str
    relation: str
    description: Optional[str] = ""

class ChatRequest(BaseModel):
    message: str


# --- HELPER FUNCTIONS ---
def get_db_cursor():
    return sqlite_conn.cursor()

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50):
    if "$END$" in text:
        # Split explicitly by user marker, removing empty chunks
        raw_chunks = text.split("$END$")
        return [c.strip() for c in raw_chunks if c.strip()]

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
    Deeply analyze the following text and construct a comprehensive Knowledge Graph.
    Your goal is not just to extract entities, but to provide rich content analysis and detailed definitions.

    Identify key entities (Nodes) and the logical relationships between them (Edges).
    Respond strictly in JSON format with two keys: "nodes" and "edges".

    For each Node, provide:
      - "id": a unique string identifier.
      - "label": the name of the entity.
      - "type": category (e.g., Concept, Person, Technology, Organization). ALL TYPES MUST BE IN CHINESE (e.g., 概念, 人物, 技术, 组织, 申报条件).
      - "description": A rich, detailed textual explanation of what this entity is, based on the text.

    For each Edge, provide:
      - "id": a unique string identifier.
      - "source": the id of the source node.
      - "target": the id of the target node.
      - "relation": a short label for the relationship (e.g., "created_by", "depends_on"). THIS RELATION MUST BE IN CHINESE (e.g., 包含, 属于, 依赖于, 关联条件).
      - "description": A detailed explanation clarifying how and why these two entities are connected in this context.

    Text snippet to analyze:
    {text[:2500]}
    """
    try:
        response = openai_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a professional knowledge extraction analyst. Output ONLY valid JSON."},
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

    # 2. Extract Deep KG using DeepSeek
    kg_data = extract_kg_from_text(text)

    # 3. Deduplicate and Store KG in SQLite
    cursor = get_db_cursor()
    nodes_added = 0
    edges_added = 0

    # ID Mapping for deduplication (Old ID -> New/Existing ID)
    id_map = {}

    for node in kg_data.get("nodes", []):
        try:
            label = node["label"].strip()
            # Check if a node with this exact label already exists
            cursor.execute("SELECT id, description FROM nodes WHERE label = ? COLLATE NOCASE", (label,))
            existing = cursor.fetchone()

            if existing:
                # Merge logic: keep existing ID, append description if it's new and useful
                existing_id = existing[0]
                existing_desc = existing[1] or ""
                new_desc = node.get("description", "")

                # If new description has info not in existing, we append it
                if new_desc and new_desc not in existing_desc:
                    merged_desc = existing_desc + "\n" + new_desc if existing_desc else new_desc
                    cursor.execute("UPDATE nodes SET description = ? WHERE id = ?", (merged_desc, existing_id))

                id_map[node["id"]] = existing_id
            else:
                # Truly new node
                new_id = node["id"]
                id_map[new_id] = new_id
                cursor.execute("INSERT INTO nodes (id, label, type, description) VALUES (?, ?, ?, ?)",
                               (new_id, label, node.get("type", "Entity"), node.get("description", "")))
                nodes_added += 1

        except Exception as e:
            print(f"Error processing node: {e}")

    for edge in kg_data.get("edges", []):
        try:
            # Remap source and target IDs to merged ones
            source_id = id_map.get(edge["source"], edge["source"])
            target_id = id_map.get(edge["target"], edge["target"])

            # Avoid self-loops
            if source_id == target_id:
                continue

            # Check if this exact edge already exists between these two nodes
            cursor.execute("SELECT id FROM edges WHERE source = ? AND target = ? AND relation = ? COLLATE NOCASE",
                           (source_id, target_id, edge["relation"]))
            existing_edge = cursor.fetchone()

            if not existing_edge:
                cursor.execute("INSERT INTO edges (id, source, target, relation, description) VALUES (?, ?, ?, ?, ?)",
                               (edge["id"], source_id, target_id, edge["relation"], edge.get("description", "")))
                edges_added += 1

        except Exception as e:
             print(f"Error processing edge: {e}")

    sqlite_conn.commit()

    return {"message": "File processed successfully", "chunks": len(chunks), "nodes_added": nodes_added, "edges_added": edges_added}


@app.get("/api/graph")
def get_graph():
    cursor = get_db_cursor()
    cursor.execute("SELECT id, label, type, description FROM nodes")
    nodes = [{"id": row[0], "label": row[1], "type": row[2], "description": row[3] or ""} for row in cursor.fetchall()]

    cursor.execute("SELECT id, source, target, relation, description FROM edges")
    edges = [{"id": row[0], "source": row[1], "target": row[2], "relation": row[3], "description": row[4] or ""} for row in cursor.fetchall()]

    # Try getting chunk counts from chromadb
    try:
        chroma_data = chroma_collection.get()
        chunk_count = len(chroma_data.get("ids", []))
    except Exception:
        chunk_count = 0

    stats = {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "chunk_count": chunk_count
    }

    return {"nodes": nodes, "links": edges, "stats": stats}

# Node Maintenance
@app.post("/api/nodes")
def add_node(node: NodeBase):
    cursor = get_db_cursor()
    try:
        cursor.execute("INSERT INTO nodes (id, label, type, description) VALUES (?, ?, ?, ?)",
                       (node.id, node.label, node.type, node.description))
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
        cursor.execute("INSERT INTO edges (id, source, target, relation, description) VALUES (?, ?, ?, ?, ?)",
                       (edge.id, edge.source, edge.target, edge.relation, edge.description))
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
    data = chroma_collection.get(include=["documents", "metadatas", "embeddings"])

    export_data = {
        "chunks": []
    }

    for i in range(len(data['ids'])):
        chunk_obj = {
            "id": data['ids'][i],
            "content": data['documents'][i],
            "source": data['metadatas'][i].get("source", ""),
            "vector": data['embeddings'][i].tolist() if data.get('embeddings') is not None and hasattr(data['embeddings'][i], 'tolist') else data['embeddings'][i] if data.get('embeddings') is not None else []
        }
        export_data["chunks"].append(chunk_obj)

    export_path = os.path.join(os.path.dirname(__file__), "data", "knowledge_base_export.json")
    with open(export_path, "w", encoding="utf-8") as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)

    return FileResponse(export_path, filename="knowledge_base_export.json", media_type="application/json")


# Advanced GraphRAG Chat endpoint
@app.post("/api/chat")
def chat_with_knowledge(req: ChatRequest):
    if not openai_client:
        return {"reply": "DeepSeek API key not configured. Cannot generate response."}

    # 1. Retrieve Raw Text Context from Vector Database
    query_vector = embedding_model.encode([req.message]).tolist()
    results = chroma_collection.query(
        query_embeddings=query_vector,
        n_results=3
    )
    context_docs = results['documents'][0] if results['documents'] else []
    raw_context = "\n".join(context_docs)

    # 2. Retrieve Graph Context (Simple GraphRAG approximation: find nodes matching query terms)
    # In a full-scale GraphRAG, we would vectorize the nodes too, but for speed we do keyword matching here.
    cursor = get_db_cursor()
    cursor.execute("SELECT label, description FROM nodes")
    all_nodes = cursor.fetchall()

    graph_context_lines = []
    for label, desc in all_nodes:
        # If the node label is mentioned in the question or the retrieved docs, we pull its rich info
        if label.lower() in req.message.lower() or (label.lower() in raw_context.lower()):
            graph_context_lines.append(f"- Entity [{label}]: {desc}")

    # Also fetch relationships for those matching nodes to provide logical topology
    for label, _ in all_nodes:
        if label.lower() in req.message.lower():
            cursor.execute('''
                SELECT n2.label, e.relation, e.description
                FROM edges e
                JOIN nodes n1 ON e.source = n1.id
                JOIN nodes n2 ON e.target = n2.id
                WHERE n1.label = ?
            ''', (label,))
            for target_label, rel, rel_desc in cursor.fetchall():
                graph_context_lines.append(f"- Relationship [{label}] -> ({rel}) -> [{target_label}]: {rel_desc}")

    graph_context = "\n".join(graph_context_lines)

    prompt = f"""
    You are an advanced knowledge assistant utilizing a GraphRAG architecture.
    You will answer the user's question by synthesizing information from two sources:
    1. Raw Document Snippets (Semantic Vector Search)
    2. Knowledge Graph Entities and Relationships (Deep logical connections)

    Provide a comprehensive, accurate, and insightful response. If the context does not contain the answer, say "I don't have enough information to answer that based on the uploaded knowledge base."

    IMPORTANT FORMATTING RULES:
    1. The output must strictly follow formal official document (公文) formatting.
    2. Start every paragraph with two full-width Chinese spaces (　　).
    3. Do NOT use markdown symbols (e.g., *, #, -, etc.) or special symbols. Just plain text.
    4. Provide clear, continuous paragraphs.

    --- Raw Document Snippets ---
    {raw_context}

    --- Knowledge Graph Context ---
    {graph_context}

    ---
    User Question: {req.message}
    """

    try:
        response = openai_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a highly intelligent and helpful knowledge assistant utilizing GraphRAG. You MUST answer in formal Chinese official document format with NO markdown symbols and ALWAYS start paragraphs with 2 full-width spaces."},
                {"role": "user", "content": prompt}
            ]
        )
        return {"reply": response.choices[0].message.content}
    except Exception as e:
        return {"reply": f"Error calling DeepSeek API: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

# Tree View / Raw Document API
@app.get("/api/documents")
def get_documents():
    data = chroma_collection.get(include=["metadatas", "documents"])

    # Group chunks by source document
    docs_map = {}

    for i in range(len(data['ids'])):
        source = data['metadatas'][i].get("source", "未知来源")
        if source not in docs_map:
            docs_map[source] = {"id": source, "label": source, "children": []}

        chunk_preview = data['documents'][i][:50].replace('\n', ' ') + "..."
        docs_map[source]["children"].append({
            "id": data['ids'][i],
            "label": f"片段 {len(docs_map[source]['children']) + 1}: {chunk_preview}",
            "content": data['documents'][i]
        })

    return list(docs_map.values())
