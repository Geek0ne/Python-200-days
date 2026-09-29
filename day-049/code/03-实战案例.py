"""
Day 049 - 抽象基类(ABC) - 实战案例
构建一个完整的插件系统 + 数据验证框架
"""
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Type


# ============================================
# Part 1: 数据验证框架
# ============================================

class Validator(ABC):
    """验证器抽象基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def validate(self, value: Any) -> Optional[str]:
        """验证数据，返回错误信息（None 表示通过）"""
        pass

    def __repr__(self):
        return f"{self.__class__.__name__}(name='{self.name}')"


class RequiredValidator(Validator):
    """必填验证器"""

    def __init__(self, field_name: str = "field"):
        self.field_name = field_name

    @property
    def name(self) -> str:
        return f"required({self.field_name})"

    def validate(self, value: Any) -> Optional[str]:
        if value is None or (isinstance(value, str) and not value.strip()):
            return f"{self.field_name} 不能为空"
        return None


class TypeValidator(Validator):
    """类型验证器"""

    def __init__(self, expected_type: Type, field_name: str = "field"):
        self.expected_type = expected_type
        self.field_name = field_name

    @property
    def name(self) -> str:
        return f"type({self.field_name}: {self.expected_type.__name__})"

    def validate(self, value: Any) -> Optional[str]:
        if value is not None and not isinstance(value, self.expected_type):
            return (
                f"{self.field_name}: 期望 {self.expected_type.__name__}, "
                f"实际 {type(value).__name__}"
            )
        return None


class RangeValidator(Validator):
    """范围验证器"""

    def __init__(self, min_val: float = None, max_val: float = None,
                 field_name: str = "field"):
        self.min_val = min_val
        self.max_val = max_val
        self.field_name = field_name

    @property
    def name(self) -> str:
        range_str = ""
        if self.min_val is not None:
            range_str += f">={self.min_val}"
        if self.max_val is not None:
            range_str += f" <={self.max_val}"
        return f"range({self.field_name}: {range_str})"

    def validate(self, value: Any) -> Optional[str]:
        if value is None:
            return None
        if self.min_val is not None and value < self.min_val:
            return f"{self.field_name}: 不能小于 {self.min_val}"
        if self.max_val is not None and value > self.max_val:
            return f"{self.field_name}: 不能大于 {self.max_val}"
        return None


class PatternValidator(Validator):
    """正则验证器"""

    def __init__(self, pattern: str, field_name: str = "field"):
        self.pattern = pattern
        self.field_name = field_name

    @property
    def name(self) -> str:
        return f"pattern({self.field_name})"

    def validate(self, value: Any) -> Optional[str]:
        if value is None:
            return None
        import re
        if not re.match(self.pattern, str(value)):
            return f"{self.field_name}: 格式不正确"
        return None


# ============================================
# Part 2: Schema 定义
# ============================================

class Schema:
    """数据模式 — 定义验证规则"""

    def __init__(self):
        self._fields: Dict[str, List[Validator]] = {}

    def field(self, name: str, *validators: Validator):
        """添加字段验证规则"""
        if name not in self._fields:
            self._fields[name] = []
        self._fields[name].extend(list(validators))
        return self  # 支持链式调用

    def validate(self, data: dict) -> List[str]:
        """验证数据，返回所有错误"""
        errors = []

        for field_name, validators in self._fields.items():
            value = data.get(field_name)
            for validator in validators:
                error = validator.validate(value)
                if error:
                    errors.append(error)

        return errors

    def is_valid(self, data: dict) -> bool:
        """检查数据是否有效"""
        return len(self.validate(data)) == 0


# ============================================
# Part 3: 使用示例
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("Day 049 - 抽象基类(ABC) 实战：数据验证框架")
    print("=" * 60)

    # 定义用户 Schema
    user_schema = Schema()
    user_schema.field("name",
        RequiredValidator("姓名"),
        TypeValidator(str, "姓名"),
        PatternValidator(r"^.{2,50}$", "姓名")
    )
    user_schema.field("email",
        RequiredValidator("邮箱"),
        TypeValidator(str, "邮箱"),
        PatternValidator(r"^[\w\.-]+@[\w\.-]+\.\w+$", "邮箱")
    )
    user_schema.field("age",
        RequiredValidator("年龄"),
        TypeValidator(int, "年龄"),
        RangeValidator(min_val=1, max_val=150, field_name="年龄")
    )

    # 测试验证
    print("\n--- 用户 Schema 验证 ---")

    valid_data = {"name": "张三", "email": "zhangsan@example.com", "age": 28}
    errors = user_schema.validate(valid_data)
    print(f"有效数据: {errors if errors else '✅ 验证通过'}")

    invalid_data = {"name": "", "email": "invalid", "age": -5}
    errors = user_schema.validate(invalid_data)
    print(f"无效数据: {errors}")

    missing_data = {"name": "李四"}
    errors = user_schema.validate(missing_data)
    print(f"缺失字段: {errors}")

    # 链式调用
    print("\n--- 链式调用 ---")
    product_schema = (
        Schema()
        .field("name", RequiredValidator("商品名"), TypeValidator(str, "商品名"))
        .field("price", RequiredValidator("价格"), RangeValidator(min_val=0.01, field_name="价格"))
        .field("stock", TypeValidator(int, "库存"), RangeValidator(min_val=0, field_name="库存"))
    )

    product_valid = {"name": "Python教程", "price": 59.9, "stock": 100}
    print(f"有效商品: {product_schema.validate(product_valid) or '✅ 验证通过'}")

    product_invalid = {"name": "", "price": -10}
    print(f"无效商品: {product_schema.validate(product_invalid)}")
