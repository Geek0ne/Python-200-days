"""
Day 074 — 实战：为 Flask API 写完整测试套件
运行方式：pytest test_flask_api.py -v
"""
import pytest
from flask import Flask, jsonify, request


# ========== 应用代码 ==========


def create_app():
    """创建 Flask 应用"""
    app = Flask(__name__)
    app.config["TESTING"] = True

    # 内存数据库
    users = {}
    next_id = 1

    @app.route("/users", methods=["GET"])
    def get_users():
        """获取所有用户"""
        return jsonify(list(users.values()))

    @app.route("/users/<int:user_id>", methods=["GET"])
    def get_user(user_id):
        """获取单个用户"""
        user = users.get(user_id)
        if not user:
            return jsonify({"error": "用户不存在"}), 404
        return jsonify(user)

    @app.route("/users", methods=["POST"])
    def create_user():
        """创建用户"""
        nonlocal next_id
        data = request.get_json()

        if not data or "name" not in data:
            return jsonify({"error": "缺少 name 字段"}), 400

        user = {
            "id": next_id,
            "name": data["name"],
            "email": data.get("email", ""),
        }
        users[next_id] = user
        next_id += 1

        return jsonify(user), 201

    @app.route("/users/<int:user_id>", methods=["PUT"])
    def update_user(user_id):
        """更新用户"""
        user = users.get(user_id)
        if not user:
            return jsonify({"error": "用户不存在"}), 404

        data = request.get_json()
        if "name" in data:
            user["name"] = data["name"]
        if "email" in data:
            user["email"] = data["email"]

        return jsonify(user)

    @app.route("/users/<int:user_id>", methods=["DELETE"])
    def delete_user(user_id):
        """删除用户"""
        if user_id not in users:
            return jsonify({"error": "用户不存在"}), 404

        del users[user_id]
        return "", 204

    return app


# ========== 测试 Fixtures ==========


@pytest.fixture
def app():
    """创建测试应用"""
    app = create_app()
    yield app


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()


# ========== 测试类 ==========


class TestGetUsers:
    """测试获取用户列表"""

    def test_empty_list(self, client):
        """空列表"""
        response = client.get("/users")
        assert response.status_code == 200
        assert response.get_json() == []

    def test_with_users(self, client):
        """有用户时"""
        # 先创建用户
        client.post("/users", json={"name": "Alice"})
        client.post("/users", json={"name": "Bob"})

        response = client.get("/users")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2


class TestGetUser:
    """测试获取单个用户"""

    def test_existing_user(self, client):
        """存在的用户"""
        # 创建用户
        response = client.post("/users", json={"name": "Alice"})
        user_id = response.get_json()["id"]

        # 获取用户
        response = client.get(f"/users/{user_id}")
        assert response.status_code == 200
        assert response.get_json()["name"] == "Alice"

    def test_nonexistent_user(self, client):
        """不存在的用户"""
        response = client.get("/users/999")
        assert response.status_code == 404
        assert "用户不存在" in response.get_json()["error"]


class TestCreateUser:
    """测试创建用户"""

    def test_create_success(self, client):
        """成功创建"""
        response = client.post("/users", json={
            "name": "Alice",
            "email": "alice@example.com"
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data["name"] == "Alice"
        assert data["email"] == "alice@example.com"
        assert "id" in data

    def test_create_without_name(self, client):
        """缺少 name 字段"""
        response = client.post("/users", json={"email": "test@example.com"})
        assert response.status_code == 400
        assert "缺少 name 字段" in response.get_json()["error"]

    def test_create_empty_body(self, client):
        """空请求体"""
        response = client.post("/users", json={})
        assert response.status_code == 400

    def test_create_multiple_users(self, client):
        """创建多个用户"""
        for i in range(3):
            response = client.post("/users", json={"name": f"User{i}"})
            assert response.status_code == 201

        response = client.get("/users")
        assert len(response.get_json()) == 3


class TestUpdateUser:
    """测试更新用户"""

    def test_update_name(self, client):
        """更新名字"""
        # 创建用户
        response = client.post("/users", json={"name": "Alice"})
        user_id = response.get_json()["id"]

        # 更新名字
        response = client.put(f"/users/{user_id}", json={"name": "Bob"})
        assert response.status_code == 200
        assert response.get_json()["name"] == "Bob"

    def test_update_nonexistent_user(self, client):
        """更新不存在的用户"""
        response = client.put("/users/999", json={"name": "Bob"})
        assert response.status_code == 404


class TestDeleteUser:
    """测试删除用户"""

    def test_delete_success(self, client):
        """成功删除"""
        # 创建用户
        response = client.post("/users", json={"name": "Alice"})
        user_id = response.get_json()["id"]

        # 删除用户
        response = client.delete(f"/users/{user_id}")
        assert response.status_code == 204

        # 验证已删除
        response = client.get(f"/users/{user_id}")
        assert response.status_code == 404

    def test_delete_nonexistent_user(self, client):
        """删除不存在的用户"""
        response = client.delete("/users/999")
        assert response.status_code == 404


# ========== 运行测试 ==========

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 Flask API 测试套件")
    print("=" * 60)
    print()
    print("运行测试...")
    print()
    pytest.main([__file__, "-v"])
