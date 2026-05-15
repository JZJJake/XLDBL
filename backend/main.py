import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
from fastapi import FastAPI, UploadFile, File, HTTPException, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
import uuid
import json
import sqlite3
import shutil
import tempfile
from typing import List, Optional

from database import init_sqlite, DB_DIR
from document_parser import parse_file, parse_url

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sqlite_conn = init_sqlite()
RAW_DIR = os.path.join(DB_DIR, "raw")
WIKI_DIR = os.path.join(DB_DIR, "wiki")
ROUTING_FILE = os.path.join(WIKI_DIR, "ROUTING.md")

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

openai_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL) if DEEPSEEK_API_KEY else None

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

def get_db_cursor():
    return sqlite_conn.cursor()

def get_routing_tree():
    if os.path.exists(ROUTING_FILE):
        with open(ROUTING_FILE, "r", encoding="utf-8") as f:
            return f.read()
    return "No routes established yet."

def save_raw_document(filename: str, text: str):
    safe_name = "".join([c if c.isalnum() or c in ['_', '-', '.'] else "_" for c in filename])
    if not safe_name.endswith('.md') and not safe_name.endswith('.txt'):
        safe_name += '.md'
    filepath = os.path.join(RAW_DIR, safe_name)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(text)
    return safe_name

def _update_graph_db(kg_data: dict, source_name: str) -> dict:
    cursor = get_db_cursor()
    nodes_added = 0
    edges_added = 0
    id_map = {}

    for node in kg_data.get("nodes", []):
        try:
            label = node["label"].strip()
            cursor.execute("SELECT id, description, source_documents FROM nodes WHERE label = ? COLLATE NOCASE", (label,))
            existing = cursor.fetchone()

            if existing:
                existing_id = existing[0]
                existing_desc = existing[1] or ""
                existing_docs = existing[2] or ""
                new_desc = node.get("description", "")

                merged_docs = existing_docs
                if source_name not in existing_docs:
                    merged_docs += f", {source_name}" if existing_docs else source_name

                if new_desc and new_desc not in existing_desc:
                    merged_desc = existing_desc + "\n" + new_desc if existing_desc else new_desc
                    cursor.execute("UPDATE nodes SET description = ?, source_documents = ?, needs_review = ? WHERE id = ?",
                                   (merged_desc, merged_docs, node.get("needs_review", False), existing_id))
                else:
                    cursor.execute("UPDATE nodes SET source_documents = ?, needs_review = ? WHERE id = ?",
                                   (merged_docs, node.get("needs_review", False), existing_id))
                id_map[node["id"]] = existing_id
            else:
                new_id = node["id"]
                id_map[new_id] = new_id
                cursor.execute("INSERT INTO nodes (id, label, type, description, source_documents, needs_review) VALUES (?, ?, ?, ?, ?, ?)",
                               (new_id, label, node.get("type", "Entity"), node.get("description", ""), source_name, node.get("needs_review", False)))
                nodes_added += 1
        except Exception as e:
            print(f"Error processing node: {e}")

    for edge in kg_data.get("edges", []):
        try:
            source_id = id_map.get(edge["source"], edge["source"])
            target_id = id_map.get(edge["target"], edge["target"])
            if source_id == target_id: continue

            cursor.execute("SELECT id, source_documents FROM edges WHERE source = ? AND target = ? AND relation = ? COLLATE NOCASE",
                           (source_id, target_id, edge["relation"]))
            existing_edge = cursor.fetchone()

            if existing_edge:
                existing_docs = existing_edge[1] or ""
                merged_docs = existing_docs
                if source_name not in existing_docs:
                    merged_docs += f", {source_name}" if existing_docs else source_name
                cursor.execute("UPDATE edges SET source_documents = ?, needs_review = ? WHERE id = ?",
                               (merged_docs, edge.get("needs_review", False), existing_edge[0]))
            else:
                cursor.execute("INSERT INTO edges (id, source, target, relation, description, source_documents, needs_review) VALUES (?, ?, ?, ?, ?, ?, ?)",
                               (edge.get("id", str(uuid.uuid4())), source_id, target_id, edge["relation"], edge.get("description", ""), source_name, edge.get("needs_review", False)))
                edges_added += 1
        except Exception as e:
             print(f"Error processing edge: {e}")

    sqlite_conn.commit()
    return {"nodes": nodes_added, "edges": edges_added}

def repair_knowledge_base(filename: str, raw_text: str, user_query: str):
    if not openai_client:
        return

    prompt = f"""
    You are an intelligent knowledge base repair agent.
    The user asked a query, but our current knowledge base was insufficient. We have retrieved the raw document '{filename}'.

    Tasks to perform:
    1. Extract new nodes and edges from this raw document that are relevant to answering the user's query.
    2. Generate a markdown supplement summarizing this new information.

    User Query: {user_query}

    OUTPUT FORMAT:
    You MUST output valid JSON ONLY, strictly following this structure:
    {{
       "graph": {{ "nodes": [...], "edges": [...] }},
       "wiki_supplement": "## Supplement relevant to {user_query}\\n\\n..."
    }}

    --- Raw Document Snippet ---
    {raw_text[:15000]}
    --- End Raw Document ---
    """

    try:
        response = openai_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a professional knowledge base repair maintainer. OUTPUT ONLY JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        result = json.loads(response.choices[0].message.content)

        # Append Wiki
        safe_name = "".join([c if c.isalnum() else "_" for c in filename])
        wiki_path = os.path.join(WIKI_DIR, f"{safe_name}.md")
        with open(wiki_path, "a", encoding="utf-8") as f:
            f.write("\n\n" + result.get("wiki_supplement", ""))

        # Update Graph
        kg_data = result.get("graph", {"nodes": [], "edges": []})
        _update_graph_db(kg_data, filename)

    except Exception as e:
        print(f"Repair knowledge base error: {e}")

def ingest_document(source_name: str, text: str):
    if not openai_client:
        return {"nodes": 0, "edges": 0}

    routing_tree = get_routing_tree()
    existing_wiki_context = ""
    existing_graph_context = ""

    # Phase 1: Context Gathering (Routing & Existing Graph)
    try:
        routing_prompt = f"""
        You are a routing agent for ingestion.
        I am about to ingest a new document. Here is a snippet of its content:
        --- Snippet ---
        {text[:2000]}
        --- End Snippet ---

        Review the following ROUTING index tree of available knowledge:
        {routing_tree}

        Output a JSON array of the filenames of existing Wiki pages (e.g. ["topic1.md"]) that might be relevant to this new document.
        If none are relevant, output []. OUTPUT ONLY THE JSON ARRAY.
        """
        route_resp = openai_client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": routing_prompt}],
            temperature=0.1
        )
        pages_to_fetch = json.loads(route_resp.choices[0].message.content.strip("` \n"))

        for page in pages_to_fetch:
            safe_page = "".join([c for c in page if c.isalnum() or c in ['_', '-', '.']])
            if safe_page != page or ".." in page or "/" in page or "\\" in page:
                continue
            page_path = os.path.join(WIKI_DIR, safe_page)
            if os.path.exists(page_path):
                with open(page_path, "r", encoding="utf-8") as f:
                    existing_wiki_context += f"\n--- Existing Wiki Page: {safe_page} ---\n{f.read()}"
    except Exception as e:
        print(f"Ingestion context gathering error: {e}")

    try:
        cursor = get_db_cursor()
        cursor.execute("SELECT label, description FROM nodes")
        all_nodes = cursor.fetchall()
        graph_lines = []
        snippet_lower = text[:2000].lower()
        for label, desc in all_nodes:
            if label.lower() in snippet_lower:
                graph_lines.append(f"- Entity [{label}]: {desc}")
        existing_graph_context = "\n".join(graph_lines)
    except Exception as e:
        print(f"Graph context gathering error: {e}")

    prompt = f"""
    You are an intelligent knowledge base ingestion agent following the LLM Wiki pattern.
    I have just uploaded a new source named '{source_name}'.

    Tasks to perform based on the entire text below:
    1. EXTRACT KNOWLEDGE GRAPH: Extract key entities (nodes) and logical relationships (edges).
       - Cross-reference the new information against the "Existing Wiki Knowledge" and "Existing Graph Knowledge" provided below.
       - Determine if any information in this text contradicts the existing knowledge or previously known general facts (flag `needs_review`: true if so).
       - Output JSON with "nodes" and "edges" lists.
       - Nodes: id, label, type, description, needs_review (bool).
       - Edges: id, source, target, relation, description, needs_review (bool).
    2. GENERATE WIKI: Generate a comprehensive markdown summary for this source.
    3. ROUTING UPDATE: Propose an updated hierarchy for the ROUTING.md tree incorporating this new source.

    OUTPUT FORMAT:
    You MUST output valid JSON ONLY, strictly following this structure:
    {{
       "graph": {{ "nodes": [...], "edges": [...] }},
       "wiki_markdown": "# Title\\n\\nContent...",
       "routing_markdown": "- Topic\\n  - [{source_name}](./{source_name}.md)"
    }}

    --- Existing Wiki Knowledge ---
    {existing_wiki_context}

    --- Existing Graph Knowledge ---
    {existing_graph_context}

    --- Text snippet (Start) ---
    {text[:15000]} # Limit to 15k chars for safety, but large context handles more.
    --- Text snippet (End) ---
    """

    try:
        response = openai_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a professional knowledge base maintainer. OUTPUT ONLY JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        result = json.loads(response.choices[0].message.content)

        # 1. Save Wiki
        safe_name = "".join([c if c.isalnum() else "_" for c in source_name])
        wiki_path = os.path.join(WIKI_DIR, f"{safe_name}.md")
        with open(wiki_path, "w", encoding="utf-8") as f:
            f.write(result.get("wiki_markdown", ""))

        # 2. Update Routing
        with open(ROUTING_FILE, "w", encoding="utf-8") as f:
            f.write(result.get("routing_markdown", ""))

        # 3. Save Graph
        kg_data = result.get("graph", {"nodes": [], "edges": []})
        return _update_graph_db(kg_data, source_name)

    except Exception as e:
        print(f"Ingestion error: {e}")
        return {"nodes": 0, "edges": 0}

@app.post("/api/upload")
async def upload_file(
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = Form(None)
):
    if not file and not url:
        raise HTTPException(status_code=400, detail="Must provide either a file or a URL")

    text = ""
    source_name = ""

    if url:
        text = parse_url(url)
        source_name = url
    else:
        try:
            suffix = os.path.splitext(file.filename)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                shutil.copyfileobj(file.file, tmp)
                tmp_path = tmp.name

            text = parse_file(tmp_path, file.filename)
            source_name = file.filename
        finally:
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                os.remove(tmp_path)

    if not text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from the provided source")

    # Save raw document
    save_raw_document(source_name, text)

    # Ingest directly without chunking
    stats = ingest_document(source_name, text)

    return {"message": "Source processed successfully", "nodes_added": stats["nodes"], "edges_added": stats["edges"]}

@app.get("/api/graph")
def get_graph():
    cursor = get_db_cursor()
    cursor.execute("SELECT id, label, type, description, source_documents, needs_review FROM nodes")
    nodes = [{"id": row[0], "label": row[1], "type": row[2], "description": row[3] or "", "source_documents": row[4] or "", "needs_review": bool(row[5])} for row in cursor.fetchall()]

    cursor.execute("SELECT id, source, target, relation, description, source_documents, needs_review FROM edges")
    edges = [{"id": row[0], "source": row[1], "target": row[2], "relation": row[3], "description": row[4] or "", "source_documents": row[5] or "", "needs_review": bool(row[6])} for row in cursor.fetchall()]

    stats = {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "chunk_count": 0  # Deprecated
    }

    return {"nodes": nodes, "links": edges, "stats": stats}

@app.get("/api/documents")
def get_documents():
    docs = []
    if os.path.exists(RAW_DIR):
        for f in os.listdir(RAW_DIR):
            filepath = os.path.join(RAW_DIR, f)
            if os.path.isfile(filepath):
                with open(filepath, "r", encoding="utf-8") as file:
                    content = file.read(500) # Preview
                docs.append({"id": f, "label": f, "content": content + "..."})
    return docs

@app.get("/api/wiki")
def list_wiki_pages():
    if not os.path.exists(WIKI_DIR):
        return {"pages": []}
    files = [f for f in os.listdir(WIKI_DIR) if f.endswith(".md") and f != "ROUTING.md"]
    return {"pages": files}

@app.get("/api/wiki/{page_name}")
def get_wiki_page(page_name: str):
    safe_page_name = "".join([c for c in page_name if c.isalnum() or c in ['_', '-', '.']])
    if safe_page_name != page_name or ".." in page_name or "/" in page_name or "\\\\" in page_name:
        raise HTTPException(status_code=400, detail="Invalid page name")

    page_path = os.path.join(WIKI_DIR, safe_page_name)
    if not os.path.exists(page_path) or not os.path.isfile(page_path):
        raise HTTPException(status_code=404, detail="Page not found")
    with open(page_path, "r", encoding="utf-8") as f:
        return {"content": f.read()}

# Two-Step Agentic Chat Endpoint
@app.post("/api/chat")
@app.post("/api/wiki/chat_manage")
def agentic_chat(req: ChatRequest, background_tasks: BackgroundTasks):
    if not openai_client:
        return {"reply": "DeepSeek API key not configured."}

    routing_tree = get_routing_tree()

    # Step 1: Routing Decision
    routing_prompt = f"""
    You are an intelligent knowledge agent answering a user query.
    Based on the user's question, determine if you need to fetch specific Wiki pages to answer it.
    Review the following ROUTING index tree of available knowledge:

    {routing_tree}

    User Query: {req.message}

    If you need specific wiki pages, output a JSON array of the filenames (e.g. ["topic1.md", "topic2.md"]).
    If you don't need any or can answer generally, output an empty JSON array [].
    OUTPUT ONLY THE JSON ARRAY.
    """

    try:
        route_resp = openai_client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": routing_prompt}],
            temperature=0.1
        )
        try:
            pages_to_fetch = json.loads(route_resp.choices[0].message.content.strip("` \n"))
        except:
            pages_to_fetch = []
    except Exception as e:
        print(f"Routing error: {e}")
        pages_to_fetch = []

    # Step 2: Fetch context
    wiki_context = ""
    for page in pages_to_fetch:
        page_path = os.path.join(WIKI_DIR, page)
        if os.path.exists(page_path):
            with open(page_path, "r", encoding="utf-8") as f:
                wiki_context += f"\n--- Wiki Page: {page} ---\n{f.read()}"

    # Also fetch minimal graph topology related to terms in query
    cursor = get_db_cursor()
    cursor.execute("SELECT label, description, needs_review, source_documents FROM nodes")
    all_nodes = cursor.fetchall()
    graph_context_lines = []
    for label, desc, needs_review, source_documents in all_nodes:
        if label.lower() in req.message.lower():
            review_flag = " (NEEDS REVIEW - Contradiction)" if needs_review else ""
            graph_context_lines.append(f"- Entity [{label}]{review_flag} (Sources: {source_documents}): {desc}")

    graph_context = "\n".join(graph_context_lines)

    # Step 3: Final Answer
    final_prompt = f"""
    You are an advanced knowledge assistant utilizing an Agentic LLM Wiki architecture.
    Answer the user's query comprehensively using the provided Wiki context and Knowledge Graph context.
    If the context doesn't contain the answer, you may state that or use your general knowledge, but clarify the source.

    AGENTIC FALLBACK RULE:
    If the provided Wiki and Graph context is insufficient to answer the query, but a relevant source file is mentioned in the Graph Context (Sources), you can request to read the raw file. To do so, output EXACTLY AND ONLY:
    READ_RAW: <filename>
    (replace <filename> with the actual filename from the source_documents).

    IMPORTANT FORMATTING RULES (If answering directly):
    1. Output strictly in formal Chinese official document (公文) formatting.
    2. Start every paragraph with two full-width Chinese spaces (　　).
    3. Do NOT use markdown symbols (e.g., *, #, -, etc.). Just plain text.

    --- Wiki Context ---
    {wiki_context}

    --- Knowledge Graph Context ---
    {graph_context}

    ---
    User Question: {req.message}
    """

    try:
        response = openai_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a professional knowledge assistant. Adhere strictly to the requested formatting rules."},
                {"role": "user", "content": final_prompt}
            ]
        )
        reply = response.choices[0].message.content.strip()

        # Check for Agentic Fallback
        if reply.startswith("READ_RAW:"):
            filename = reply.replace("READ_RAW:", "").strip()
            safe_filename = "".join([c for c in filename if c.isalnum() or c in ['_', '-', '.']])
            if safe_filename != filename or ".." in filename or "/" in filename or "\\" in filename:
                safe_filename = "" # Invalid, skip to avoid Path Traversal

            if safe_filename:
                # Attempt to read raw file
                raw_path = os.path.join(RAW_DIR, safe_filename)
                if not os.path.exists(raw_path):
                     # Try appending .md if not present
                     if not safe_filename.endswith('.md') and not safe_filename.endswith('.txt'):
                         safe_filename += '.md'
                         raw_path = os.path.join(RAW_DIR, safe_filename)

                raw_text = ""
                if os.path.exists(raw_path):
                    with open(raw_path, "r", encoding="utf-8") as f:
                        raw_text = f.read()

                if raw_text:
                    # Trigger background repair task
                    background_tasks.add_task(repair_knowledge_base, safe_filename, raw_text, req.message)

                    # Re-prompt for final answer with raw text
                    fallback_prompt = final_prompt + f"\n\n--- Retrieved Raw Document ({safe_filename}) ---\n{raw_text[:15000]}\n--- End Raw Document ---"

                    fallback_response = openai_client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[
                            {"role": "system", "content": "You are a professional knowledge assistant. Adhere strictly to the requested formatting rules."},
                            {"role": "user", "content": fallback_prompt}
                        ]
                    )
                    reply = fallback_response.choices[0].message.content

        return {"reply": reply}
    except Exception as e:
        return {"reply": f"Error calling DeepSeek API: {str(e)}"}

# Deprecated endpoints stubbed to not break UI instantly if they call them
@app.post("/api/nodes")
def add_node(node: NodeBase): return {"success": True}
@app.delete("/api/nodes/{node_id}")
def delete_node(node_id: str): return {"success": True}
@app.post("/api/edges")
def add_edge(edge: EdgeBase): return {"success": True}
@app.delete("/api/edges/{edge_id}")
def delete_edge(edge_id: str): return {"success": True}
@app.get("/api/export")
def export_database(): return {"error": "Deprecated"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
