"""
Day 069 — 🛒 电商数据模型（完整实战项目）
功能：用户、商品、订单管理，关系映射，复杂查询
运行方式：python 06-ecommerce-model.py
"""
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Float,
    Text, Boolean, DateTime, ForeignKey, func, Table
)
from sqlalchemy.orm import DeclarativeBase, relationship, Session, sessionmaker


# ========== 声明基类 ==========
class Base(DeclarativeBase):
    pass


# ========== 多对多关联表 ==========
product_tags = Table(
    "product_tags",
    Base.metadata,
    Column("product_id", Integer, ForeignKey("products.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)


# ========== 模型定义 ==========

class User(Base):
    """用户"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False)
    phone = Column(String(20))
    is_vip = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

    orders = relationship("Order", back_populates="user")

    def __repr__(self):
        return f"<User(username='{self.username}')>"


class Category(Base):
    """商品分类"""
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)

    products = relationship("Product", back_populates="category")

    def __repr__(self):
        return f"<Category(name='{self.name}')>"


class Product(Base):
    """商品"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    price = Column(Float, nullable=False)
    stock = Column(Integer, default=0)
    category_id = Column(Integer, ForeignKey("categories.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)

    category = relationship("Category", back_populates="products")
    tags = relationship("Tag", secondary=product_tags, back_populates="products")
    order_items = relationship("OrderItem", back_populates="product")

    def __repr__(self):
        return f"<Product(name='{self.name}', price={self.price})>"


class Tag(Base):
    """标签（多对多）"""
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)

    products = relationship("Product", secondary=product_tags, back_populates="tags")

    def __repr__(self):
        return f"<Tag(name='{self.name}')>"


class Order(Base):
    """订单"""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(20), default="pending")
    total_amount = Column(Float, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Order(id={self.id}, status='{self.status}')>"


class OrderItem(Base):
    """订单项"""
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=1)
    unit_price = Column(Float)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")

    def __repr__(self):
        return f"<OrderItem(product_id={self.product_id}, qty={self.quantity})>"


# ========== 数据库操作 ==========

class EcommerceDB:
    """电商数据库管理器"""

    def __init__(self, db_path: str = "ecommerce.db"):
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def get_session(self):
        return self.Session()

    def init_data(self):
        """初始化示例数据"""
        with self.get_session() as session:
            if session.query(User).count() > 0:
                print("ℹ️ 数据已存在，跳过初始化")
                return

            # 创建分类
            electronics = Category(name="电子产品")
            books = Category(name="图书")
            clothing = Category(name="服装")
            session.add_all([electronics, books, clothing])
            session.flush()

            # 创建标签
            hot = Tag(name="热销")
            new = Tag(name="新品")
            discount = Tag(name="打折")
            session.add_all([hot, new, discount])
            session.flush()

            # 创建商品
            products = [
                Product(name="iPhone 15", price=7999, stock=50,
                        category=electronics, tags=[hot]),
                Product(name="MacBook Pro", price=14999, stock=20,
                        category=electronics, tags=[hot, new]),
                Product(name="Python编程", price=59.9, stock=100,
                        category=books, tags=[hot, discount]),
                Product(name="三体", price=56, stock=80,
                        category=books, tags=[new]),
                Product(name="T恤", price=99, stock=200,
                        category=clothing, tags=[discount]),
            ]
            session.add_all(products)
            session.flush()

            # 创建用户
            alice = User(username="alice", email="alice@test.com", is_vip=True)
            bob = User(username="bob", email="bob@test.com")
            session.add_all([alice, bob])
            session.flush()

            # 创建订单
            order1 = Order(user=alice, status="paid", total_amount=8058.9)
            order2 = Order(user=bob, status="pending", total_amount=155.9)
            session.add_all([order1, order2])
            session.flush()

            # 创建订单项
            items = [
                OrderItem(order=order1, product=products[0], quantity=1,
                          unit_price=7999),
                OrderItem(order=order1, product=products[2], quantity=1,
                          unit_price=59.9),
                OrderItem(order=order2, product=products[2], quantity=1,
                          unit_price=59.9),
                OrderItem(order=order2, product=products[4], quantity=1,
                          unit_price=99),
            ]
            session.add_all(items)
            session.commit()
            print("✅ 示例数据初始化完成")

    def demo_queries(self):
        """演示各种查询"""
        with self.get_session() as session:
            # 1. 基础查询
            print("=" * 50)
            print("📦 所有商品:")
            for p in session.query(Product).all():
                print(f"  {p.name} - ¥{p.price} (库存:{p.stock})")

            # 2. 条件查询
            print("\n🔍 价格低于 100 的商品:")
            for p in session.query(Product).filter(Product.price < 100).all():
                print(f"  {p.name} - ¥{p.price}")

            # 3. 关联查询
            print("\n👤 Alice 的订单:")
            alice = session.query(User).filter_by(username="alice").first()
            for order in alice.orders:
                print(f"  订单 #{order.id} - ¥{order.total_amount} ({order.status})")
                for item in order.items:
                    print(f"    └─ {item.product.name} x{item.quantity}")

            # 4. 聚合查询
            print("\n📊 分类统计:")
            stats = session.query(
                Category.name,
                func.count(Product.id),
                func.avg(Product.price)
            ).join(Product).group_by(Category.id).all()
            for name, count, avg_price in stats:
                print(f"  {name}: {count} 个商品, 均价 ¥{avg_price:.2f}")

            # 5. 多对多查询
            print("\n🏷️ 带'热销'标签的商品:")
            hot_tag = session.query(Tag).filter_by(name="热销").first()
            for p in hot_tag.products:
                print(f"  {p.name} - ¥{p.price}")

            # 6. 排序 + 分页
            print("\n💰 商品价格排行榜（前 3）:")
            for p in session.query(Product).order_by(
                Product.price.desc()
            ).limit(3).all():
                print(f"  ¥{p.price:.0f} - {p.name}")

            # 7. 复杂过滤
            print("\n🛒 库存充足且价格 < 100 的商品:")
            for p in session.query(Product).filter(
                Product.stock > 50,
                Product.price < 100
            ).all():
                print(f"  {p.name} - ¥{p.price} (库存:{p.stock})")


if __name__ == "__main__":
    db = EcommerceDB()
    db.init_data()
    db.demo_queries()
