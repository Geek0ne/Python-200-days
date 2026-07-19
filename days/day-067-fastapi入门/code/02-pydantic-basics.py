"""
Day 067 — Pydantic 数据验证基础
运行方式：python 02-pydantic-basics.py
"""
from pydantic import BaseModel, Field, field_validator, model_validator


# ========== 基础模型 ==========

class Book(BaseModel):
    """
    图书模型——展示 Pydantic 的基本字段约束
    
    每个字段都有类型注解 + Field 约束：
    - 类型注解：str, int, float, list 等
    - Field 约束：min_length, gt, ge, pattern 等
    """
    title: str = Field(..., min_length=1, max_length=200)
    # ... 表示必填（没有默认值的字段都是必填的）
    
    author: str = Field(..., min_length=1)
    
    isbn: str = Field(..., pattern=r"^\d{10,13}$")
    # pattern: 正则表达式，ISBN 必须是 10-13 位数字
    
    price: float = Field(gt=0)
    # gt=0: 大于 0（Greater Than）
    
    published_year: int = Field(ge=1000, le=2100)
    # ge=greater than or equal, le=less than or equal
    
    description: str = ""  # 可选，有默认值
    tags: list[str] = []   # 可选，列表类型


# ========== 带自定义验证器的模型 ==========

class UserRegister(BaseModel):
    """用户注册模型——包含字段级和模型级验证"""
    
    username: str = Field(..., min_length=3, max_length=20)
    email: str
    password: str = Field(..., min_length=8)
    confirm_password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """
        字段级验证器：验证邮箱格式
        
        @field_validator 装饰器标记一个类方法为验证器
        参数名 "email" 表示验证哪个字段
        """
        if "@" not in v:
            raise ValueError("邮箱格式不正确，必须包含 @ 符号")
        return v.lower()  # 验证通过后自动转小写

    @model_validator(mode="after")
    def check_passwords_match(self):
        """
        模型级验证器：验证多个字段之间的关系
        
        mode="after" 表示所有字段都验证完后再执行
        可以访问 self 的所有字段
        """
        if self.password != self.confirm_password:
            raise ValueError("两次输入的密码不一致")
        return self


# ========== 嵌套模型 ==========

class Address(BaseModel):
    """地址模型"""
    city: str
    street: str
    zip_code: str = Field(pattern=r"^\d{6}$")


class UserWithAddress(BaseModel):
    """带地址的用户——模型嵌套"""
    name: str
    age: int = Field(ge=0, le=150)
    address: Address  # 嵌套另一个 Pydantic 模型


# ========== 测试代码 ==========

if __name__ == "__main__":
    print("=" * 50)
    print("📚 测试 Book 模型")
    print("=" * 50)

    # ✅ 正确数据
    book = Book(
        title="Python编程从入门到实践",
        author="Eric Matthes",
        isbn="9787111636663",
        price=59.9,
        published_year=2023,
        tags=["Python", "编程", "入门"]
    )
    print("✅ 图书创建成功!")
    print(f"   标题: {book.title}")
    print(f"   作者: {book.author}")
    print(f"   价格: ¥{book.price}")
    print(f"   标签: {book.tags}")
    print(f"   字典输出: {book.model_dump()}")

    # ❌ 错误数据——验证失败
    print("\n" + "=" * 50)
    print("❌ 测试错误数据")
    print("=" * 50)
    
    try:
        bad_book = Book(
            title="",              # 空标题——违反 min_length=1
            author="李四",
            isbn="123",            # 只有 3 位——不符合 10-13 位要求
            price=-10,             # 负价格——违反 gt=0
            published_year=3000    # 超出范围——违反 le=2100
        )
    except Exception as e:
        print("❌ 验证失败（预期结果）:")
        print(e)

    print("\n" + "=" * 50)
    print("👤 测试 UserRegister 模型")
    print("=" * 50)

    # ✅ 正确注册
    user = UserRegister(
        username="alice",
        email="Alice@Example.com",  # 会自动转小写
        password="secure123",
        confirm_password="secure123"
    )
    print(f"✅ 注册成功!")
    print(f"   用户名: {user.username}")
    print(f"   邮箱: {user.email}")  # 注意：自动转为小写

    # ❌ 密码不匹配
    try:
        bad_user = UserRegister(
            username="bob",
            email="bob@test.com",
            password="pass1234",
            confirm_password="different"
        )
    except Exception as e:
        print(f"\n❌ 注册失败: {e}")

    # ❌ 邮箱格式错误
    try:
        bad_email_user = UserRegister(
            username="charlie",
            email="not-an-email",
            password="pass1234",
            confirm_password="pass1234"
        )
    except Exception as e:
        print(f"❌ 邮箱错误: {e}")

    print("\n" + "=" * 50)
    print("🏠 测试嵌套模型")
    print("=" * 50)

    user_addr = UserWithAddress(
        name="张三",
        age=25,
        address=Address(
            city="北京",
            street="朝阳区建国路88号",
            zip_code="100022"
        )
    )
    print(f"✅ 用户创建成功!")
    print(f"   姓名: {user_addr.name}")
    print(f"   城市: {user_addr.address.city}")
    print(f"   完整数据: {user_addr.model_dump()}")
