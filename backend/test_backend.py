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

    # In new architecture, manual node adding is deprecated and does nothing but return success
    # So we just test that the endpoints still exist and return 200 to not break old UI
    res = client.post("/api/nodes", json={"id": "test_n1", "label": "Node 1", "type": "Entity", "description": "Desc 1"})
    assert res.status_code == 200

    res = client.get("/api/graph")
    assert res.status_code == 200
    data = res.json()
    assert "nodes" in data
    assert "links" in data

def test_export():
    res = client.get("/api/export")
    assert res.status_code == 200
