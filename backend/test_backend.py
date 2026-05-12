import pytest
from fastapi.testclient import TestClient
from main import app, init_sqlite, sqlite_conn

client = TestClient(app)

def test_graph_endpoints():
    # 1. Clear db for test
    cursor = sqlite_conn.cursor()
    cursor.execute("DELETE FROM edges")
    cursor.execute("DELETE FROM nodes")
    sqlite_conn.commit()

    # 2. Add Node
    res = client.post("/api/nodes", json={"id": "test_n1", "label": "Node 1", "type": "Entity"})
    assert res.status_code == 200
    assert res.json() == {"success": True}

    # 3. Add second Node
    res = client.post("/api/nodes", json={"id": "test_n2", "label": "Node 2", "type": "Entity"})

    # 4. Add Edge
    res = client.post("/api/edges", json={"id": "test_e1", "source": "test_n1", "target": "test_n2", "relation": "connected_to"})
    assert res.status_code == 200

    # 5. Get Graph
    res = client.get("/api/graph")
    assert res.status_code == 200
    data = res.json()
    assert len(data["nodes"]) == 2
    assert len(data["links"]) == 1
    assert data["links"][0]["source"] == "test_n1"

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
