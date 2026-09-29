"""
Day 074 — 集成测试 vs 单元测试
运行方式：python 03-integration-test.py
"""
import pytest
import tempfile
import os
import json


# ========== 单元测试 ==========


def calculate_discount(price, discount_percent):
    """计算折扣后的价格"""
    if discount_percent < 0 or discount_percent > 100:
        raise ValueError("折扣百分比必须在 0-100 之间")
    return price * (1 - discount_percent / 100)


class TestCalculateDiscount:
    """折扣计算单元测试"""

    def test_no_discount(self):
        """无折扣"""
        assert calculate_discount(100, 0) == 100

    def test_full_discount(self):
        """全额折扣"""
        assert calculate_discount(100, 100) == 0

    def test_half_discount(self):
        """半价折扣"""
        assert calculate_discount(100, 50) == 50

    def test_invalid_discount_negative(self):
        """负数折扣"""
        with pytest.raises(ValueError):
            calculate_discount(100, -10)

    def test_invalid_discount_over_100(self):
        """超过100%的折扣"""
        with pytest.raises(ValueError):
            calculate_discount(100, 150)


# ========== 集成测试 ==========


class TestFileProcessing:
    """文件处理集成测试"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_read_write_file(self, temp_dir):
        """测试文件读写"""
        filepath = os.path.join(temp_dir, "test.txt")

        # 写入文件
        with open(filepath, "w") as f:
            f.write("Hello, World!")

        # 读取文件
        with open(filepath, "r") as f:
            content = f.read()

        assert content == "Hello, World!"

    def test_process_multiple_files(self, temp_dir):
        """测试处理多个文件"""
        # 创建多个文件
        for i in range(5):
            filepath = os.path.join(temp_dir, f"file_{i}.txt")
            with open(filepath, "w") as f:
                f.write(f"Content {i}")

        # 读取所有文件
        contents = []
        for filename in sorted(os.listdir(temp_dir)):
            filepath = os.path.join(temp_dir, filename)
            with open(filepath, "r") as f:
                contents.append(f.read())

        assert len(contents) == 5
        assert contents[0] == "Content 0"

    def test_json_processing(self, temp_dir):
        """测试 JSON 处理"""
        filepath = os.path.join(temp_dir, "data.json")

        # 写入 JSON
        data = {"name": "test", "values": [1, 2, 3]}
        with open(filepath, "w") as f:
            json.dump(data, f)

        # 读取并验证
        with open(filepath, "r") as f:
            loaded = json.load(f)

        assert loaded == data


# ========== 测试分类标记 ==========


@pytest.mark.unit
def test_unit_example():
    """单元测试"""
    assert 1 + 1 == 2


@pytest.mark.integration
def test_integration_example():
    """集成测试"""
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "test.txt")
        with open(filepath, "w") as f:
            f.write("test")
        with open(filepath, "r") as f:
            assert f.read() == "test"


# ========== 运行测试 ==========

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 集成测试 vs 单元测试")
    print("=" * 60)
    print()
    pytest.main([__file__, "-v"])
