"""
Day 045 - 简易 ORM 框架
面向对象实战项目：通过元类、描述符、属性装饰器等技术实现简易 ORM
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type


class Field:
    """字段基类"""
    def __init__(self, primary_key=False):
        self.primary_key = primary_key
        self.value = None

    def validate(self, value: Any) -> Any:
        """验证字段值"""
        return value


class CharField(Field):
    """字符串字段"""
    def __init__(self, max_length: int = 100, **kwargs):
        super().__init__(**kwargs)
        self.max_length = max_length

    def validate(self, value: Any) -> str:
        if not isinstance(value, str):
            raise TypeError(f"Expected str, got {type(value)}")
        if len(value) > self.max_length:
            raise ValueError(f"Length {len(value)} exceeds max {self.max_length}")
        return value


class IntegerField(Field):
    """整数字段"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def validate(self, value: Any) -> int:
        if not isinstance(value, int):
            raise TypeError(f"Expected int, got {type(value)}")
        return value


class FloatField(Field):
    """浮点数字段"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def validate(self, value: Any) -> float:
        if not isinstance(value, (int, float)):
            raise TypeError(f"Expected float, got {type(value)}")
        return float(value)


class BooleanField(Field):
    """布尔字段"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def validate(self, value: Any) -> bool:
        if not isinstance(value, bool):
            raise TypeError(f"Expected bool, got {type(value)}")
        return value


class ForeignKey(Field):
    """外键字段"""
    def __init__(self, related_model: Type, **kwargs):
        super().__init__(**kwargs)
        self.related_model = related_model

    def validate(self, value: Any) -> int:
        if not isinstance(value, int):
            raise TypeError(f"Expected int (foreign key), got {type(value)}")
        return value


class ModelMeta(type):
    """元类：自动处理字段映射"""
    def __new__(cls, name: str, bases: tuple, attrs: dict):
        # 跳过基类
        if not bases:
            return super().__new__(cls, name, bases, attrs)

        # 收集所有 Field 实例
        fields: Dict[str, Field] = {}
        for key, value in attrs.items():
            if isinstance(value, Field):
                fields[key] = value

        # 存储到类属性
        attrs['_fields'] = fields
        attrs['_table_name'] = name.lower() + 's'

        return super().__new__(cls, name, bases, attrs)


class Model(metaclass=ModelMeta):
    """模型基类"""
    _id_counter = 0  # 模拟自增 ID

    def __init__(self, **kwargs):
        Model._id_counter += 1
        self.id = Model._id_counter

        # 设置字段值
        for field_name, field in self._fields.items():
            if field_name in kwargs:
                value = kwargs[field_name]
                field.validate(value)
                setattr(self, field_name, value)
            else:
                # 跳过 primary_key 字段的默认值设置
                if not field.primary_key:
                    setattr(self, field_name, None)

    def save(self) -> bool:
        """保存到数据库"""
        # 验证所有字段
        for field_name, field in self._fields.items():
            value = getattr(self, field_name)
            if value is not None:
                field.validate(value)

        # 生成 SQL（示例）
        sql = self._generate_insert_sql()
        print(f"[SAVE] {sql}")
        return True

    def _generate_insert_sql(self) -> str:
        """生成 INSERT SQL"""
        fields = []
        values = []
        for field_name, field in self._fields.items():
            value = getattr(self, field_name)
            if value is not None:
                fields.append(field_name)
                if isinstance(value, str):
                    values.append(f"'{value}'")
                else:
                    values.append(str(value))

        return f"INSERT INTO {self._table_name} ({', '.join(fields)}) VALUES ({', '.join(values)})"

    @classmethod
    def get(cls, id: int) -> 'Model':
        """获取单条记录"""
        sql = f"SELECT * FROM {cls._table_name} WHERE id = {id}"
        print(f"[GET] {sql}")
        return cls(id=id)

    @classmethod
    def filter(cls, **kwargs) -> list:
        """过滤查询"""
        conditions = []
        for k, v in kwargs.items():
            if isinstance(v, str):
                conditions.append(f"{k} = '{v}'")
            else:
                conditions.append(f"{k} = {v}")

        sql = f"SELECT * FROM {cls._table_name} WHERE {' AND '.join(conditions)}"
        print(f"[FILTER] {sql}")
        return []

    @classmethod
    def all(cls) -> list:
        """获取所有记录"""
        sql = f"SELECT * FROM {cls._table_name}"
        print(f"[ALL] {sql}")
        return []

    def __repr__(self):
        return f"<{self.__class__.__name__}(id={self.id})>"


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("=" * 60)
    print("Day 045 - 简易 ORM 框架演示")
    print("=" * 60)

    # 定义模型
    class User(Model):
        id = IntegerField(primary_key=True)
        name = CharField(max_length=50)
        age = IntegerField()
        email = CharField(max_length=100)

    class Article(Model):
        id = IntegerField(primary_key=True)
        title = CharField(max_length=200)
        content = CharField(max_length=2000)
        author_id = IntegerField()
        published = BooleanField()

    print("\n1. 创建用户实例")
    print("-" * 40)
    user1 = User(name="张三", age=25, email="zhangsan@example.com")
    print(f"用户: {user1.name}, 年龄: {user1.age}")
    print(f"用户 ID: {user1.id}")

    print("\n2. 保存用户到数据库")
    print("-" * 40)
    user1.save()

    print("\n3. 创建文章实例")
    print("-" * 40)
    article = Article(
        title="Python 面向对象实战",
        content="通过 ORM 框架学习 OOP 核心概念...",
        author_id=user1.id,
        published=True
    )
    print(f"文章: {article.title}")
    print(f"作者 ID: {article.author_id}")

    print("\n4. 保存文章")
    print("-" * 40)
    article.save()

    print("\n5. 查询操作")
    print("-" * 40)
    # 模拟查询
    found_user = User.get(1)
    print(f"查询用户: {found_user}")

    # 过滤查询
    users = User.filter(name="张三")
    print(f"过滤结果: {users}")

    # 获取所有
    all_users = User.all()
    print(f"所有用户: {all_users}")

    print("\n6. 字段验证演示")
    print("-" * 40)
    try:
        # 测试字符串长度验证
        invalid_user = User(name="A" * 101, age=25)
        invalid_user.save()
    except ValueError as e:
        print(f"验证错误: {e}")

    try:
        # 测试整数类型验证
        invalid_article = Article(title="测试", content="内容", author_id="abc")
        invalid_article.save()
    except TypeError as e:
        print(f"类型错误: {e}")

    print("\n" + "=" * 60)
    print("ORM 框架演示完成！")
    print("=" * 60)
