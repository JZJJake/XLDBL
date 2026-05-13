import pytest
from fastapi.testclient import TestClient
from main import app, init_sqlite, sqlite_conn, chroma_collection

client = TestClient(app)

def test_graph_endpoints():
    # 1. Clear db for test
    cursor = sqlite_conn.cursor()
    cursor.execute("DELETE FROM edges")
    cursor.execute("DELETE FROM nodes")
    sqlite_conn.commit()

    # 2. Add Node (With new description field)
    res = client.post("/api/nodes", json={"id": "test_n1", "label": "Node 1", "type": "Entity", "description": "Desc 1"})
    assert res.status_code == 200
    assert res.json() == {"success": True}

    # 3. Add second Node
    res = client.post("/api/nodes", json={"id": "test_n2", "label": "Node 2", "type": "Entity", "description": "Desc 2"})

    # 4. Add Edge
    res = client.post("/api/edges", json={"id": "test_e1", "source": "test_n1", "target": "test_n2", "relation": "connected_to", "description": "Connection desc"})
    assert res.status_code == 200

    # 5. Get Graph
    res = client.get("/api/graph")
    assert res.status_code == 200
    data = res.json()
    assert len(data["nodes"]) == 2
    assert len(data["links"]) == 1
    assert data["nodes"][0]["description"] == "Desc 1"
    assert data["links"][0]["source"] == "test_n1"
    assert data["links"][0]["description"] == "Connection desc"

    # 6. Delete Node (cascade)
    res = client.delete("/api/nodes/test_n1")
    assert res.status_code == 200

    # 7. Verify Graph
    res = client.get("/api/graph")
    data = res.json()
    assert len(data["nodes"]) == 1
    assert len(data["links"]) == 0  # Edge should be deleted

def test_export():
    res = client.get("/api/export")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/json"

def test_get_documents():
    # Clear existing documents
    data = chroma_collection.get()
    if data['ids']:
        chroma_collection.delete(ids=data['ids'])

    # Add mock documents
    chroma_collection.add(
        ids=["chunk1", "chunk2", "chunk3"],
        documents=[
            "This is chunk 1 content that is a bit long so we can test the preview.",
            "This is chunk 2 content.\nIt has a newline.",
            "Chunk 3 has no known source."
        ],
        metadatas=[{"source": "doc1.txt"}, {"source": "doc1.txt"}, {"source": "未知来源"}]
    )

    res = client.get("/api/documents")
    assert res.status_code == 200

    resp_data = res.json()
    assert len(resp_data) == 2

    doc1 = next((item for item in resp_data if item["id"] == "doc1.txt"), None)
    assert doc1 is not None
    assert doc1["label"] == "doc1.txt"
    assert len(doc1["children"]) == 2
    assert doc1["children"][0]["id"] == "chunk1"
    assert "片段 1:" in doc1["children"][0]["label"]
    assert "This is chunk 1 content that is a bit long so we c..." in doc1["children"][0]["label"]
    assert doc1["children"][0]["content"] == "This is chunk 1 content that is a bit long so we can test the preview."

    doc2 = next((item for item in resp_data if item["id"] == "未知来源"), None)
    assert doc2 is not None
    assert doc2["label"] == "未知来源"
    assert len(doc2["children"]) == 1
    assert doc2["children"][0]["id"] == "chunk3"
