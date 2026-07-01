"""
Day 046 — 元类 实战案例：ORM 字段验证

本文件演示：
1. 使用元类实现简单的 ORM 字段系统
2. 字段类型定义（StringField、IntegerField、EmailField）
3. 自动字段收集与验证
4. 实际应用场景
"""


# ============================================================
# 1. 字段类定义
# ============================================================

class Field:
    """字段基类"""
    
    def __init__(self, required=True, default=None, max_length=None):
        self.required = required
        self.default = default
        self.max_length = max_length
        self.name = None  # 由元类设置
    
    def __repr__(self):
        return f"{self.__class__.__name__}(name={self.name!r})"

class StringField(Field):
    """字符串字段"""
    
    def validate(self, value):
        if value is not None and not isinstance(value, str):
            raise TypeError(f"字段 '{self.name}' 必须是字符串，得到 {type(value).__name__}")
        if value is not None and self.max_length and len(value) > self.max_length:
            raise ValueError(f"字段 '{self.name}' 超出最大长度 {self.max_length}")
        return True

class IntegerField(Field):
    """整数字段"""
    
    def validate(self, value):
        if value is not None and not isinstance(value, int):
            raise TypeError(f"字段 '{self.name}' 必须是整数，得到 {type(value).__name__}")
        return True

class EmailField(Field):
    """邮箱字段"""
    
    def __init__(self, required=True, default=None):
        super().__init__(required=required, default=default, max_length=254)
    
    def validate(self, value):
        if value is not None:
            if not isinstance(value, str):
                raise TypeError(f"字段 '{self.name}' 必须是字符串")
            if '@' not in value:
                raise ValueError(f"字段 '{self.name}' 不是有效的邮箱格式")
        return True

class AgeField(IntegerField):
    """年龄字段（带范围验证）"""
    
    def __init__(self, required=True, default=None, min_val=0, max_val=150):
        super().__init__(required=required, default=default)
        self.min_val = min_val
        self.max_val = max_val
    
    def validate(self, value):
        super().validate(value)
        if value is not None:
            if value < self.min_val or value > self.max_val:
                raise ValueError(
                    f"字段 '{self.name}' 的值 {value} 不在范围 "
                    f"[{self.min_val}, {self.max_val}] 内"
                )
        return True


# ============================================================
# 2. 元类：自动收集字段
# ============================================================

class ModelMeta(type):
    """
    ORM 元类：
    - 自动收集所有 Field 实例
    - 为每个字段设置 name 属性
    - 子类自动继承父类的字段
    """
    
    def __new__(mcs, name, bases, attrs):
        # 收集当前类的字段
        fields = {}
        for key, value in attrs.items():
            if isinstance(value, Field):
                value.name = key
                fields[key] = value
        
        # 继承父类的字段
        for base in bases:
            if hasattr(base, '_fields'):
                for field_name, field in base._fields.items():
                    if field_name not in fields:
                        # 复制字段（避免共享）
                        import copy
                        new_field = copy.copy(field)
                        new_field.name = field_name
                        fields[field_name] = new_field
        
        attrs['_fields'] = fields
        return super().__new__(mcs, name, bases, attrs)


# ============================================================
# 3. Model 基类
# ============================================================

class Model(metaclass=ModelMeta):
    """模型基类"""
    
    def __init__(self, **kwargs):
        # 设置字段值
        for name, field in self._fields.items():
            value = kwargs.get(name, field.default)
            setattr(self, name, value)
        
        # 验证必填字段
        missing = [
            name for name, field in self._fields.items()
            if field.required and getattr(self, name) is None
        ]
        if missing:
            raise ValueError(f"缺少必填字段: {', '.join(missing)}")
    
    def validate(self):
        """验证所有字段"""
        errors = []
        for name, field in self._fields.items():
            value = getattr(self, name)
            try:
                field.validate(value)
            except (TypeError, ValueError) as e:
                errors.append(str(e))
        if errors:
            raise ValidationError('\n'.join(errors))
        return True
    
    def to_dict(self):
        """转为字典"""
        return {
            name: getattr(self, name)
            for name in self._fields
        }
    
    def __repr__(self):
        fields = ', '.join(
            f'{name}={getattr(self, name)!r}'
            for name in self._fields
        )
        return f'{self.__class__.__name__}({fields})'


class ValidationError(Exception):
    """验证错误"""
    pass


# ============================================================
# 4. 定义模型
# ============================================================

class User(Model):
    """用户模型"""
    name = StringField(required=True, max_length=50)
    email = EmailField(required=True)
    age = AgeField(required=False, default=18, min_val=0, max_val=150)

class Post(Model):
    """文章模型"""
    title = StringField(required=True, max_length=200)
    content = StringField(required=True)
    author = StringField(required=True, max_length=50)


# ============================================================
# 5. 使用示例
# ============================================================

print("=== 1. 创建并验证 User ===")

# 正常创建
user = User(name="Alice", email="alice@example.com", age=25)
print(f"用户: {user}")
print(f"字典: {user.to_dict()}")
user.validate()
print("✅ 验证通过")

print("\n=== 2. 字段验证 ===")

# 测试必填字段
print("\n--- 测试必填字段 ---")
try:
    User()  # 缺少必填字段
except ValueError as e:
    print(f"  ❌ {e}")

# 测试邮箱格式
print("\n--- 测试邮箱格式 ---")
try:
    user_bad_email = User(name="Bob", email="invalid-email")
    user_bad_email.validate()
except ValidationError as e:
    print(f"  ❌ {e}")

# 测试年龄范围
print("\n--- 测试年龄范围 ---")
try:
    user_old = User(name="Old", email="old@test.com", age=200)
    user_old.validate()
except ValidationError as e:
    print(f"  ❌ {e}")

# 测试字符串长度
print("\n--- 测试字符串长度 ---")
try:
    user_long = User(name="A" * 100, email="long@test.com")  # 名字超过50
    user_long.validate()
except ValidationError as e:
    print(f"  ❌ {e}")


# ============================================================
# 6. 继承测试
# ============================================================

print("\n=== 3. 模型继承 ===")

class Admin(User):
    """管理员模型（继承 User）"""
    role = StringField(required=True, default="admin")
    permissions = StringField(required=False, default="read")

admin = Admin(
    name="Admin",
    email="admin@test.com",
    role="superadmin",
    permissions="read,write,delete"
)
print(f"管理员: {admin}")
print(f"字段列表: {list(admin._fields.keys())}")
admin.validate()
print("✅ 验证通过")


# ============================================================
# 7. 批量验证
# ============================================================

print("\n=== 4. 批量验证 ===")

users_data = [
    {"name": "Alice", "email": "alice@test.com", "age": 25},
    {"name": "Bob", "email": "bob@test.com"},
    {"name": "", "email": "charlie@test.com"},  # 空名字
    {"name": "Dave", "email": "invalid"},        # 无效邮箱
]

for i, data in enumerate(users_data):
    try:
        user = User(**data)
        user.validate()
        print(f"  ✅ 用户 {i+1}: {user.name} — 验证通过")
    except (ValueError, ValidationError) as e:
        print(f"  ❌ 用户 {i+1}: {data.get('name', '未知')} — {e}")


print("\n✅ 所有测试通过！")
print("\n💡 实战要点：")
print("  1. 元类自动收集字段，开发者只需声明式定义")
print("  2. 字段验证逻辑封装在字段类中，符合单一职责")
print("  3. 子类自动继承父类字段，方便扩展")
print("  4. 这就是 Django ORM 的核心原理！")
