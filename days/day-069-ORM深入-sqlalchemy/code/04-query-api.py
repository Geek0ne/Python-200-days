"""
Day 069 — 查询 API 详解
运行方式：python 04-query-api.py
"""
from sqlalchemy import create_engine, Column, Integer, String, Float, func
from sqlalchemy.orm import DeclarativeBase, Session


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    category = Column(String(50))
    price = Column(Float)
    stock = Column(Integer)


def demo():
    engine = create_engine("sqlite:///query_demo.db", echo=False)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        # 插入测试数据
        products = [
            Product(name="Python书", category="图书", price=59.9, stock=100),
            Product(name="Java书", category="图书", price=69.9, stock=50),
            Product(name="机械键盘", category="外设", price=299, stock=30),
            Product(name="鼠标", category="外设", price=99, stock=200),
            Product(name="显示器", category="外设", price=1999, stock=10),
            Product(name="Python进阶", category="图书", price=79.9, stock=80),
            Product(name="耳机", category="外设", price=199, stock=150),
            Product(name="笔记本", category="文具", price=15, stock=500),
        ]
        session.add_all(products)
        session.commit()

        # ========== 1. 基础查询 ==========
        print("=" * 50)
        print("📦 所有产品:")
        all_products = session.query(Product).all()
        for p in all_products:
            print(f"  {p.name} - ¥{p.price} (库存:{p.stock})")

        # ========== 2. 条件过滤 ==========
        print("\n🔍 图书类产品:")
        books = session.query(Product).filter(Product.category == "图书").all()
        for p in books:
            print(f"  {p.name} - ¥{p.price}")

        # 多条件（AND）
        print("\n🔍 价格 50-200 之间的产品:")
        filtered = session.query(Product).filter(
            Product.price >= 50,
            Product.price <= 200
        ).all()
        for p in filtered:
            print(f"  {p.name} - ¥{p.price}")

        # filter_by（简洁写法）
        print("\n🔍 filter_by 用法:")
        results = session.query(Product).filter_by(category="外设").all()
        print(f"  外设产品: {len(results)} 个")

        # OR 条件
        from sqlalchemy import or_
        print("\n🔍 价格 < 20 或 > 1000:")
        results = session.query(Product).filter(
            or_(Product.price < 20, Product.price > 1000)
        ).all()
        for p in results:
            print(f"  {p.name} - ¥{p.price}")

        # ========== 3. 排序 ==========
        print("\n📊 按价格从高到低:")
        sorted_products = session.query(Product).order_by(Product.price.desc()).all()
        for p in sorted_products:
            print(f"  ¥{p.price:.0f} - {p.name}")

        print("\n📊 按库存从少到多:")
        by_stock = session.query(Product).order_by(Product.stock).limit(3).all()
        for p in by_stock:
            print(f"  库存:{p.stock} - {p.name}")

        # ========== 4. 限制和偏移 ==========
        print("\n📄 分页（第 2 页，每页 3 个）:")
        page2 = session.query(Product).offset(3).limit(3).all()
        for p in page2:
            print(f"  {p.name} - ¥{p.price}")

        # ========== 5. 聚合查询 ==========
        print("\n📈 统计信息:")
        total = session.query(func.count(Product.id)).scalar()
        print(f"  总产品数: {total}")

        avg_price = session.query(func.avg(Product.price)).scalar()
        print(f"  平均价格: ¥{avg_price:.2f}")

        max_price = session.query(func.max(Product.price)).scalar()
        min_price = session.query(func.min(Product.price)).scalar()
        print(f"  最高价: ¥{max_price:.0f}")
        print(f"  最低价: ¥{min_price:.0f}")

        # 按分类统计
        print("\n📊 按分类统计:")
        stats = session.query(
            Product.category,
            func.count(Product.id),
            func.sum(Product.price),
            func.avg(Product.price)
        ).group_by(Product.category).all()
        for cat, count, total_price, avg in stats:
            print(f"  {cat}: {count} 个, 总价 ¥{total_price:.0f}, 均价 ¥{avg:.2f}")

        # HAVING（分组后过滤）
        print("\n📊 商品数 > 2 的分类:")
        having = session.query(
            Product.category,
            func.count(Product.id)
        ).group_by(Product.category).having(
            func.count(Product.id) > 2
        ).all()
        for cat, count in having:
            print(f"  {cat}: {count} 个")

        # ========== 6. 子查询 ==========
        print("\n🔍 价格高于平均价的产品:")
        avg_subquery = session.query(func.avg(Product.price)).scalar_subquery()
        expensive = session.query(Product).filter(
            Product.price > avg_subquery
        ).all()
        for p in expensive:
            print(f"  {p.name} - ¥{p.price}")

        # ========== 7. 判断存在 ==========
        has_expensive = session.query(
            session.query(Product).filter(Product.price > 1000).exists()
        ).scalar()
        print(f"\n有超过 1000 元的产品: {has_expensive}")

        # ========== 8. 提取值 ==========
        print("\n所有分类名称（去重）:")
        categories = session.query(Product.category).distinct().all()
        for cat in categories:
            print(f"  {cat[0]}")

        # ========== 9. 更新和删除 ==========
        print("\n📦 批量更新：图书打九折")
        from sqlalchemy import update
        session.execute(
            update(Product).where(Product.category == "图书").values(
                price=Product.price * 0.9
            )
        )
        session.commit()

        print("\n更新后的图书:")
        for p in session.query(Product).filter_by(category="图书").all():
            print(f"  {p.name} - ¥{p.price:.1f}")


if __name__ == "__main__":
    demo()
