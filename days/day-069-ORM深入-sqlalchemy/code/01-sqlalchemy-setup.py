"""
Day 069 — SQLAlchemy 基础配置
运行方式：python 01-sqlalchemy-setup.py
"""
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import DeclarativeBase, sessionmaker


# ========== 1. 声明基类 ==========
class Base(DeclarativeBase):
    """所有模型的基类"""
    pass


# ========== 2. 定义模型 ==========
class User(Base):
    """用户模型"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    age = Column(Integer, default=0)
    email = Column(String(100), unique=True)

    def __repr__(self):
        return f"<User(id={self.id}, name='{self.name}')>"


# ========== 3. 创建引擎 ==========
# SQLite: sqlite:///filename.db
# echo=True 会打印生成的 SQL（调试用）
engine = create_engine("sqlite:///setup_demo.db", echo=False)

# ========== 4. 创建表 ==========
Base.metadata.create_all(engine)
print("✅ 表创建成功")

# ========== 5. 创建会话 ==========
SessionLocal = sessionmaker(bind=engine)

# ========== 6. CRUD 操作 ==========
with SessionLocal() as session:
    # 创建
    user1 = User(name="张三", age=25, email="zhang@test.com")
    user2 = User(name="李四", age=30, email="li@test.com")
    session.add_all([user1, user2])
    session.commit()
    print(f"✅ 创建用户: {user1}, {user2}")

    # 读取
    users = session.query(User).all()
    print(f"\n所有用户: {users}")

    # 条件查询
    user = session.query(User).filter_by(name="张三").first()
    print(f"查询张三: {user}")

    # 更新
    user.age = 26
    session.commit()
    print(f"\n✅ 更新后: {user}")

    # 删除
    session.delete(user2)
    session.commit()
    print(f"\n✅ 删除李四后剩余: {session.query(User).all()}")
