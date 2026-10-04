import pytest
from fastapi.testclient import TestClient
from app.main import app

def test_api_health_and_examples():
    client = TestClient(app)
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

    examples_res = client.get("/api/examples")
    assert examples_res.status_code == 200
    assert len(examples_res.json()) >= 4

def test_api_transpile_python_to_js():
    client = TestClient(app)
    payload = {
        "source_code": "def double(x):\n    return x * 2\n\nval = 21\nprint(double(val))\n",
        "source_lang": "python",
        "target_lang": "javascript"
    }
    res = client.post("/api/transpile", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "function double(x)" in data["target_code"]
    assert "console.log" in data["target_code"]
    assert data["ir_tree"] is not None
    assert data["ir_tree"]["name"] == "Program (IR Root)"

def test_api_scope_rejection_for_classes():
    client = TestClient(app)
    payload = {
        "source_code": "class MyClass:\n    pass\n",
        "source_lang": "python",
        "target_lang": "javascript"
    }
    res = client.post("/api/transpile", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is False
    assert "Scope violation: Classes" in data["error"]
