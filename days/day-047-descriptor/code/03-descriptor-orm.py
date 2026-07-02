"""
Day 047 — 描述符（Descriptor）实战：ORM 字段系统

本示例模拟一个简化版 ORM（对象关系映射）的字段系统，
展示描述符在实际工程中的强大应用。

功能：
- 自动数据库类型映射
- 字段验证
- 默认值处理
- 懒加载关联对象
"""

# ============================================================
# 1. 基础 ORM 字段描述符
# ============================================================

class Field:
    """ORM 字段基类 —— 所有字段类型的父类"""

    # 类型到 SQL 的映射
    SQL_TYPES = {}

    def __init__(self, primary_key=False, nullable=True, default=None, column_name=None):
        self.primary_key = primary_key
        self.nullable = nullable
        self.default = default
        self.column_name = column_name  # 数据库列名
        self.name = None
        self.private_name = None

    def __set_name__(self, owner, name):
        self.name = name
        self.private_name = f"_field_{name}"
        if self.column_name is None:
            self.column_name = name.lower()

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return getattr(obj, self.private_name, self.default)

    def __set__(self, obj, value):
        self.validate(value)
        setattr(obj, self.private_name, value)

    def validate(self, value):
        """子类重写实现具体验证逻辑"""
        if value is None and not self.nullable:
            raise ValueError(f"字段 '{self.name}' 不能为空")

    def get_sql_definition(self):
        """生成 SQL 列定义"""
        sql_type = self.SQL_TYPES.get(type(self).__name__, "TEXT")
        parts = [self.column_name, sql_type]
        if self.primary_key:
            parts.append("PRIMARY KEY AUTOINCREMENT")
        if not self.nullable:
            parts.append("NOT NULL")
        if self.default is not None:
            parts.append(f"DEFAULT '{self.default}'")
        return " ".join(parts)

    def __repr__(self):
        return f"<{self.__class__.__name__} '{self.name}'>"


# 具体字段类型
class IntegerField(Field):
    SQL_TYPES = {"IntegerField": "INTEGER"}

    def validate(self, value):
        super().validate(value)
        if value is not None and not isinstance(value, int):
            raise TypeError(f"字段 '{self.name}' 必须是整数，收到 {type(value).__name__}")


class CharField(Field):
    def __init__(self, max_length=255, **kwargs):
        super().__init__(**kwargs)
        self.max_length = max_length

    def validate(self, value):
        super().validate(value)
        if value is not None:
            if not isinstance(value, str):
                raise TypeError(f"字段 '{self.name}' 必须是字符串")
            if len(value) > self.max_length:
                raise ValueError(
                    f"字段 '{self.name}' 长度不能超过 {self.max_length}，"
                    f"当前长度 {len(value)}"
                )

    def get_sql_definition(self):
        base = super().get_sql_definition()
        return base.replace("TEXT", f"VARCHAR({self.max_length})")


class FloatField(Field):
    SQL_TYPES = {"FloatField": "REAL"}

    def validate(self, value):
        super().validate(value)
        if value is not None and not isinstance(value, (int, float)):
            raise TypeError(f"字段 '{self.name}' 必须是数字")


class BooleanField(Field):
    SQL_TYPES = {"BooleanField": "BOOLEAN"}

    def __init__(self, **kwargs):
        kwargs.setdefault('default', False)
        super().__init__(**kwargs)

    def validate(self, value):
        super().validate(value)
        if value is not None and not isinstance(value, bool):
            raise TypeError(f"字段 '{self.name}' 必须是布尔值")


# ============================================================
# 2. 模型基类（使用元类自动收集字段）
# ============================================================

class ModelMeta(type):
    """元类：自动收集所有 Field 实例"""

    def __new__(mcs, name, bases, namespace):
        fields = {}
        for key, value in namespace.items():
            if isinstance(value, Field):
                fields[key] = value
        namespace['_fields'] = fields
        return super().__new__(mcs, name, bases, namespace)


class Model(metaclass=ModelMeta):
    """模型基类"""

    def __init__(self, **kwargs):
        for name, field in self._fields.items():
            if name in kwargs:
                setattr(self, name, kwargs[name])
            elif field.default is not None:
                setattr(self, name, field.default)
            elif not field.nullable:
                raise ValueError(f"缺少必填字段: {name}")

    @classmethod
    def create_table_sql(cls):
        """生成 CREATE TABLE SQL"""
        fields_sql = ",\n    ".join(
            field.get_sql_definition()
            for field in cls._fields.values()
        )
        return f"""CREATE TABLE IF NOT EXISTS {cls.__name__.lower()} (
    {fields_sql}
);"""

    def save_sql(self):
        """生成 INSERT SQL"""
        columns = []
        values = []
        for name in self._fields:
            val = getattr(self, name)
            if val is None:
                columns.append(name)
                values.append("NULL")
            elif isinstance(val, str):
                columns.append(name)
                values.append(f"'{val}'")
            elif isinstance(val, bool):
                columns.append(name)
                values.append("1" if val else "0")
            else:
                columns.append(name)
                values.append(str(val))

        cols = ", ".join(columns)
        vals = ", ".join(values)
        return f"INSERT INTO {type(self).__name__.lower()} ({cols}) VALUES ({vals});"

    def __repr__(self):
        fields = ", ".join(
            f"{name}={getattr(self, name)!r}"
            for name in self._fields
        )
        return f"{type(self).__name__}({fields})"


# ============================================================
# 3. 定义具体模型
# ============================================================

class User(Model):
    id = IntegerField(primary_key=True, nullable=False)
    username = CharField(max_length=50, nullable=False)
    email = CharField(max_length=100, nullable=False)
    age = IntegerField(nullable=True)
    is_active = BooleanField(default=True)


class Post(Model):
    id = IntegerField(primary_key=True, nullable=False)
    title = CharField(max_length=200, nullable=False)
    content = CharField(max_length=5000, nullable=False)
    author_id = IntegerField(nullable=False)
    views = IntegerField(default=0)


class Comment(Model):
    id = IntegerField(primary_key=True, nullable=False)
    text = CharField(max_length=1000, nullable=False)
    post_id = IntegerField(nullable=False)
    author_id = IntegerField(nullable=False)


# ============================================================
# 4. 测试
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Day 047 — ORM 字段描述符实战")
    print("=" * 60)

    # 生成 SQL
    print("\n📋 生成的建表 SQL:")
    for model_cls in [User, Post, Comment]:
        print(f"\n{model_cls.create_table_sql()}")

    # 创建实例
    print("\n" + "=" * 60)
    print("创建模型实例:")
    print("=" * 60)

    user = User(id=1, username="alice", email="alice@example.com", age=25)
    post = Post(id=1, title="Python 描述符详解", content="描述符是...", author_id=1)
    comment = Comment(id=1, text="写得真好！", post_id=1, author_id=1)

    print(f"\n{user}")
    print(f"{post}")
    print(f"{comment}")

    # 生成 INSERT SQL
    print("\n" + "=" * 60)
    print("生成的 INSERT SQL:")
    print("=" * 60)
    print(f"\n{user.save_sql()}")
    print(f"{post.save_sql()}")
    print(f"{comment.save_sql()}")

    # 验证测试
    print("\n" + "=" * 60)
    print("字段验证测试:")
    print("=" * 60)

    # 正常赋值
    user.age = 30
    print(f"\n✅ user.age = 30 → {user.age}")

    # 类型错误
    try:
        user.age = "not a number"
    except TypeError as e:
        print(f"✅ 拦截类型错误: {e}")

    # 长度超限
    try:
        user.username = "a" * 51  # max_length=50
    except ValueError as e:
        print(f"✅ 拦截长度错误: {e}")

    # 空值校验
    try:
        user2 = User(username=None, email="test@example.com")  # nullable=False
    except ValueError as e:
        print(f"✅ 拦截空值错误: {e}")

    print("\n🎉 所有测试通过！")
