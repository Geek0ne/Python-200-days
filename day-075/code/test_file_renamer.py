"""
Day 075 — 文件批量重命名工具：测试代码
运行方式：pytest test_file_renamer.py -v
"""
import pytest
import tempfile
import os
from pathlib import Path
from file_renamer import Renamer, RenameResult, DirectoryNotFoundError, PatternError


@pytest.fixture
def temp_dir():
    """创建临时目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建测试文件
        for i in range(5):
            (Path(tmpdir) / f"file{i}.txt").touch()
        yield tmpdir


class TestRenamer:
    """重命名器测试"""

    def test_init(self, temp_dir):
        """初始化"""
        renamer = Renamer(temp_dir)
        assert renamer.directory == Path(temp_dir)
        assert renamer.dry_run is False

    def test_init_nonexistent(self):
        """初始化不存在的目录"""
        with pytest.raises(DirectoryNotFoundError):
            Renamer("/nonexistent/path")

    def test_add_prefix(self, temp_dir):
        """添加前缀"""
        renamer = Renamer(temp_dir)
        result = renamer.add_prefix("test_")

        assert result.success_count == 5
        assert result.failure_count == 0

        # 验证文件已重命名
        files = list(Path(temp_dir).glob("test_*.txt"))
        assert len(files) == 5

    def test_add_suffix(self, temp_dir):
        """添加后缀"""
        renamer = Renamer(temp_dir)
        result = renamer.add_suffix("_backup")

        assert result.success_count == 5

        files = list(Path(temp_dir).glob("*_backup.txt"))
        assert len(files) == 5

    def test_replace(self, temp_dir):
        """替换字符串"""
        renamer = Renamer(temp_dir)
        result = renamer.replace("file", "doc")

        assert result.success_count == 5

        files = list(Path(temp_dir).glob("doc*.txt"))
        assert len(files) == 5

    def test_sequence(self, temp_dir):
        """序号重命名"""
        renamer = Renamer(temp_dir)
        result = renamer.sequence("item_{index:03d}.txt")

        assert result.success_count == 5

        files = list(Path(temp_dir).glob("item_*.txt"))
        assert len(files) == 5

    def test_dry_run(self, temp_dir):
        """预览模式"""
        renamer = Renamer(temp_dir, dry_run=True)
        result = renamer.add_prefix("test_")

        assert result.success_count == 5

        # 文件不应该被重命名
        files = list(Path(temp_dir).glob("file*.txt"))
        assert len(files) == 5

    def test_regex_replace(self, temp_dir):
        """正则替换"""
        renamer = Renamer(temp_dir)
        result = renamer.regex_replace(r"(\d+)", r"num_\1")

        assert result.success_count == 5

    def test_invalid_regex(self, temp_dir):
        """无效正则"""
        renamer = Renamer(temp_dir)
        with pytest.raises(PatternError):
            renamer.regex_replace(r"[invalid", "test")

    def test_case_lower(self, temp_dir):
        """小写转换"""
        # 创建大写文件名
        (Path(temp_dir) / "TestFile.TXT").touch()

        renamer = Renamer(temp_dir)
        result = renamer.case转换("lower", "*.TXT")

        assert result.success_count == 1
        assert (Path(temp_dir) / "testfile.txt").exists()

    def test_case_upper(self, temp_dir):
        """大写转换"""
        renamer = Renamer(temp_dir)
        result = renamer.case转换("upper")

        assert result.success_count == 5

        files = list(Path(temp_dir).glob("FILE*.TXT"))
        assert len(files) == 5


class TestRenameResult:
    """重命名结果测试"""

    def test_empty_result(self):
        """空结果"""
        result = RenameResult()
        assert result.total == 0
        assert result.success_count == 0
        assert result.failure_count == 0

    def test_to_json(self):
        """转换为 JSON"""
        result = RenameResult()
        result.finish()
        json_str = result.to_json()
        assert "start_time" in json_str
        assert "total" in json_str


if __name__ == "__main__":
    print("=" * 60)
    print("🧪 文件重命名工具测试")
    print("=" * 60)
    print()
    pytest.main([__file__, "-v"])
