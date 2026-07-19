"""
Day 069 — Session 管理详解
运行方式：python 05-session-management.py
"""
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker, joinedload


class Base(DeclarativeBase):
    pass


class Author(Base):
    __tablename__ = "authors"
    id = Column(Integer, primary_key=True)
    name = Column(String(50))

    def __repr__(self):
        return f"<Author(name='{self.name}')>"


class Book(Base):
    __tablename__ = "books"
    id = Column(Integer, primary_key=True)
    title = Column(String(100))
    author_id = Column(Integer)

    def __repr__(self):
        return f"<Book(title='{self.title}')>"


def demo():
    engine = create_engine("sqlite:///session_demo.db", echo=False)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    # ========== 1. with 语句管理（推荐） ==========
    print("=" * 50)
    print("🔧 方式 1: with 语句")
    with Session(engine) as session:
        author = Author(name="张三")
        session.add(author)
        session.commit()
        print(f"  创建: {author}")

    # ========== 2. 手动管理 ==========
    print("\n🔧 方式 2: 手动管理")
    session = SessionLocal()
    try:
        author = Author(name="李四")
        session.add(author)
        session.commit()
        print(f"  创建: {author}")
    except Exception as e:
        session.rollback()
        print(f"  失败: {e}")
    finally:
        session.close()

    # ========== 3. 懒加载 vs 预加载 ==========
    print("\n🔧 懒加载 vs 预加载")
    with Session(engine) as session:
        # 添加测试数据
        a1 = Author(name="Alice")
        a2 = Author(name="Bob")
        session.add_all([a1, a2])
        session.flush()

        books = [
            Book(title="Python书", author_id=a1.id),
            Book(title="Java书", author_id=a1.id),
            Book(title="Go书", author_id=a2.id),
        ]
        session.add_all(books)
        session.commit()

        # 懒加载：每次访问都查数据库（N+1 问题）
        print("\n  懒加载（可能 N+1）:")
        all_books = session.query(Book).all()
        for book in all_books:
            # 每次循环都查一次数据库！
            author = session.query(Author).filter_by(id=book.author_id).first()
            print(f"    {book.title} → {author.name}")

        # 预加载：一次性加载所有关联数据
        print("\n  预加载（joinedload）:")
        all_books = session.query(Book).options(joinedload(Author)).all()
        for book in all_books:
            # 不再查询数据库
            print(f"    {book.title} → {book.author.name}")

    # ========== 4. 常见陷阱演示 ==========
    print("\n⚠️ 常见陷阱:")

    # 陷阱 1: 忘记 commit
    print("\n  陷阱 1: 忘记 commit")
    session = SessionLocal()
    session.add(Author(name="测试用户"))
    session.close()  # 数据没有保存！
    count = session.query(Author).filter_by(name="测试用户").count()
    print(f"    查询结果: {count} 条（应该是 0）")

    # 陷阱 2: 批量操作优化
    print("\n  批量操作优化:")
    import time

    # 慢：逐条插入
    session = SessionLocal()
    start = time.time()
    for i in range(100):
        session.add(Author(name=f"用户{i}"))
        session.commit()  # 每次都 commit，很慢！
    slow_time = time.time() - start
    session.close()

    # 快：批量插入
    session = SessionLocal()
    start = time.time()
    for i in range(100):
        session.add(Author(name=f"批量用户{i}"))
    session.commit()  # 一次 commit
    fast_time = time.time() - start
    session.close()

    print(f"    逐条 commit: {slow_time:.3f}秒")
    print(f"    批量 commit: {fast_time:.3f}秒")
    print(f"    加速: {slow_time / fast_time:.1f}倍")


if __name__ == "__main__":
    demo()
