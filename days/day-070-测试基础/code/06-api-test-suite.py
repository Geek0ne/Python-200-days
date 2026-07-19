"""
Day 070 — 🧪 API 测试套件（完整实战项目）
为 FastAPI 应用编写完整测试
运行方式：pytest 06-api-test-suite.py -v
"""
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field
from unittest.mock import Mock, patch


# ========== 被测试的 API ==========

app = FastAPI(title="测试示例 API")

items_db: dict[int, dict] = {}
next_id = 1


class ItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    price: float = Field(gt=0)
    description: str = ""
    category: str = "未分类"


class ItemResponse(BaseModel):
    id: int
    name: str
    price: float
    description: str
    category: str


@app.post("/items/", response_model=ItemResponse, status_code=201)
def create_item(item: ItemCreate):
    global next_id
    item_data = {"id": next_id, **item.model_dump()}
    items_db[next_id] = item_data
    next_id += 1
    return item_data


@app.get("/items/", response_model=list[ItemResponse])
def list_items(category: str = None):
    items = list(items_db.values())
    if category:
        items = [i for i in items if i["category"] == category]
    return items


@app.get("/items/{item_id}", response_model=ItemResponse)
def get_item(item_id: int):
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    return items_db[item_id]


@app.put("/items/{item_id}", response_model=ItemResponse)
def update_item(item_id: int, item: ItemCreate):
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    items_db[item_id].update(item.model_dump())
    return items_db[item_id]


@app.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int):
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    del items_db[item_id]


@app.get("/calculate/")
def calculate(a: int, b: int, op: str = "add"):
    if op == "add":
        return {"result": a + b}
    elif op == "multiply":
        return {"result": a * b}
    elif op == "subtract":
        return {"result": a - b}
    else:
        raise HTTPException(status_code=400, detail="Invalid operation")


@app.get("/stats/")
def get_stats():
    return {
        "total_items": len(items_db),
        "categories": list(set(i["category"] for i in items_db.values())),
    }


# ========== Fixture ==========

@pytest.fixture(autouse=True)
def reset_db():
    """每个测试前清空数据库"""
    items_db.clear()
    global next_id
    next_id = 1
    yield
    items_db.clear()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_item():
    return {"name": "测试商品", "price": 99.9, "description": "测试描述"}


@pytest.fixture
def sample_items():
    """创建多个测试商品"""
    items = [
        {"name": "商品A", "price": 10, "category": "电子"},
        {"name": "商品B", "price": 20, "category": "图书"},
        {"name": "商品C", "price": 30, "category": "电子"},
    ]
    created = []
    for item in items:
        resp = client.post("/items/", json=item)
        created.append(resp.json())
    return created


# ========== 创建商品测试 ==========

class TestCreateItem:
    def test_create_success(self, client, sample_item):
        response = client.post("/items/", json=sample_item)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "测试商品"
        assert data["price"] == 99.9
        assert data["id"] == 1

    def test_create_minimal(self, client):
        response = client.post("/items/", json={"name": "A", "price": 1})
        assert response.status_code == 201
        assert response.json()["description"] == ""
        assert response.json()["category"] == "未分类"

    def test_create_with_category(self, client):
        response = client.post("/items/", json={
            "name": "手机", "price": 2999, "category": "电子"
        })
        assert response.status_code == 201
        assert response.json()["category"] == "电子"

    def test_create_invalid_price(self, client):
        response = client.post("/items/", json={"name": "A", "price": -1})
        assert response.status_code == 422

    def test_create_empty_name(self, client):
        response = client.post("/items/", json={"name": "", "price": 1})
        assert response.status_code == 422

    def test_create_multiple(self, client):
        for i in range(5):
            resp = client.post("/items/", json={"name": f"商品{i}", "price": i + 1})
            assert resp.status_code == 201
        assert len(items_db) == 5


# ========== 获取商品测试 ==========

class TestGetItem:
    def test_get_success(self, client, sample_item):
        create_resp = client.post("/items/", json=sample_item)
        item_id = create_resp.json()["id"]

        response = client.get(f"/items/{item_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "测试商品"

    def test_get_not_found(self, client):
        response = client.get("/items/999")
        assert response.status_code == 404

    def test_list_items(self, client, sample_item):
        client.post("/items/", json=sample_item)
        response = client.get("/items/")
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_list_empty(self, client):
        response = client.get("/items/")
        assert response.status_code == 200
        assert len(response.json()) == 0


# ========== 更新商品测试 ==========

class TestUpdateItem:
    def test_update_success(self, client, sample_item):
        create_resp = client.post("/items/", json=sample_item)
        item_id = create_resp.json()["id"]

        update_data = {"name": "更新后", "price": 199.9}
        response = client.put(f"/items/{item_id}", json=update_data)
        assert response.status_code == 200
        assert response.json()["name"] == "更新后"
        assert response.json()["price"] == 199.9

    def test_update_not_found(self, client, sample_item):
        response = client.put("/items/999", json=sample_item)
        assert response.status_code == 404


# ========== 删除商品测试 ==========

class TestDeleteItem:
    def test_delete_success(self, client, sample_item):
        create_resp = client.post("/items/", json=sample_item)
        item_id = create_resp.json()["id"]

        response = client.delete(f"/items/{item_id}")
        assert response.status_code == 204

        # 验证已删除
        get_resp = client.get(f"/items/{item_id}")
        assert get_resp.status_code == 404

    def test_delete_not_found(self, client):
        response = client.delete("/items/999")
        assert response.status_code == 404


# ========== 计算器测试（参数化） ==========

@pytest.mark.parametrize("a,b,op,expected", [
    (1, 2, "add", 3),
    (5, 3, "add", 8),
    (0, 0, "add", 0),
    (-1, 1, "add", 0),
    (2, 3, "multiply", 6),
    (5, 0, "multiply", 0),
    (10, 4, "subtract", 6),
    (3, 7, "subtract", -4),
])
def test_calculate(client, a, b, op, expected):
    response = client.get(f"/calculate/?a={a}&b={b}&op={op}")
    assert response.status_code == 200
    assert response.json()["result"] == expected


def test_calculate_invalid_op(client):
    response = client.get("/calculate/?a=1&b=2&op=divide")
    assert response.status_code == 400


# ========== 统计接口测试 ==========

class TestStats:
    def test_stats_empty(self, client):
        response = client.get("/stats/")
        assert response.status_code == 200
        data = response.json()
        assert data["total_items"] == 0
        assert data["categories"] == []

    def test_stats_with_items(self, client):
        client.post("/items/", json={"name": "A", "price": 1, "category": "电子"})
        client.post("/items/", json={"name": "B", "price": 2, "category": "图书"})
        client.post("/items/", json={"name": "C", "price": 3, "category": "电子"})

        response = client.get("/stats/")
        data = response.json()
        assert data["total_items"] == 3
        assert "电子" in data["categories"]
        assert "图书" in data["categories"]


# ========== 集成测试 ==========

def test_full_crud_workflow(client):
    """完整 CRUD 工作流测试"""
    # 1. 创建
    resp = client.post("/items/", json={"name": "商品A", "price": 10})
    item_id = resp.json()["id"]

    # 2. 读取
    resp = client.get(f"/items/{item_id}")
    assert resp.json()["name"] == "商品A"

    # 3. 更新
    resp = client.put(f"/items/{item_id}", json={"name": "商品A-更新", "price": 20})
    assert resp.json()["name"] == "商品A-更新"

    # 4. 删除
    resp = client.delete(f"/items/{item_id}")
    assert resp.status_code == 204

    # 5. 验证删除
    resp = client.get(f"/items/{item_id}")
    assert resp.status_code == 404


# ========== 运行 ==========
# pytest 06-api-test-suite.py -v
# pytest 06-api-test-suite.py -v --cov=. --cov-report=term-missing
