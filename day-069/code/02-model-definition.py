"""
Day 069 — 模型定义详解
运行方式：python 02-model-definition.py
"""
from datetime import datetime, date
from sqlalchemy import (
    create_engine, Column, Integer, String, Float,
    Text, Boolean, DateTime, Date, Numeric
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Product(Base):
    """商品模型——展示各种字段类型"""
    __tablename__ = "products"

    # 基础字段
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, comment="商品名称")
    description = Column(Text, default="", comment="商品描述")
    price = Column(Float, nullable=False, comment="价格")
    
    # 精确数字（适合金额）
    # price_decimal = Column(Numeric(10, 2), default=0)
    
    # 布尔值
    is_active = Column(Boolean, default=True, comment="是否上架")
    
    # 日期时间
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 整数
    stock = Column(Integer, default=0, comment="库存")
    
    # 字符串（带长度限制）
    sku = Column(String(50), unique=True, index=True, comment="SKU编号")
    
    # 带约束的字段
    category = Column(String(50), default="未分类", comment="分类")
    rating = Column(Float, default=0.0, comment="评分")

    def __repr__(self):
        return f"<Product(name='{self.name}', price={self.price})>"
    
    def to_dict(self):
        """转为字典（方便序列化）"""
        return {
            "id": self.id,
            "name": self.name,
            "price": self.price,
            "stock": self.stock,
            "category": self.category,
            "is_active": self.is_active,
        }


class Order(Base):
    """订单模型"""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    customer_name = Column(String(100), nullable=False)
    total = Column(Float, default=0)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<Order(id={self.id}, status='{self.status}')>"


def demo():
    engine = create_engine("sqlite:///model_demo.db", echo=False)
    Base.metadata.create_all(engine)

    from sqlalchemy.orm import Session

    with Session(engine) as session:
        # 创建商品
        p1 = Product(
            name="Python编程",
            description="Python入门经典教材",
            price=59.9,
            stock=100,
            sku="BOOK-001",
            category="图书",
            rating=4.8,
        )
        p2 = Product(
            name="机械键盘",
            price=299,
            stock=50,
            sku="KEY-001",
            category="外设",
            rating=4.5,
        )
        session.add_all([p1, p2])
        session.commit()

        # 查询
        products = session.query(Product).all()
        for p in products:
            print(f"{p.name} - ¥{p.price} (库存:{p.stock}, 评分:{p.rating})")

        # 使用 to_dict
        print(f"\n字典输出: {p1.to_dict()}")


if __name__ == "__main__":
    demo()
