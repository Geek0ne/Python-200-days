"""
Day 031 — 类与对象：实战案例
======================================================================
图书管理系统完整实现
  1. Book 类
  2. Library 类
  3. Member 类
  4. BorrowRecord 类
  5. 完整的交互演示
======================================================================
"""

from datetime import datetime, timedelta
import json
import os


# ====================================================================
# 1. Book 类
# ====================================================================
class Book:
    """图书类"""

    # 类变量：所有 Book 实例共享
    total_books = 0
    genres = {
        'F': '文学小说',
        'NF': '非虚构',
        'SF': '科幻',
        'P': '编程',
        'H': '历史',
        'M': '悬疑',
        'R': '参考书',
    }

    def __init__(self, title, author, isbn, genre='P', pages=0):
        self.title = title
        self.author = author
        self.isbn = isbn
        self.genre = genre
        self.pages = pages
        self.available = True
        self._borrow_count = 0  # 借阅次数

        Book.total_books += 1

    # ---- 字符串表示 ----
    def __str__(self):
        status = "✅ 可借" if self.available else "❌ 已借出"
        genre_name = self.genres.get(self.genre, self.genre)
        return (f"《{self.title:<20》} {self.author:<12} "
                f"[{genre_name}] {status}  (已借{self._borrow_count}次)")

    def __repr__(self):
        return (f"Book(title={self.title!r}, author={self.author!r}, "
                f"isbn={self.isbn!r}, genre={self.genre!r})")

    # ---- 比较 ----
    def __eq__(self, other):
        if not isinstance(other, Book):
            return NotImplemented
        return self.isbn == other.isbn

    def __hash__(self):
        return hash(self.isbn)

    # ---- 操作 ----
    def borrow(self):
        """借书"""
        if not self.available:
            return False
        self.available = False
        self._borrow_count += 1
        return True

    def return_book(self):
        """还书"""
        self.available = True
        return True

    def get_info(self):
        """获取完整信息"""
        return {
            'title': self.title,
            'author': self.author,
            'isbn': self.isbn,
            'genre': self.genres.get(self.genre, self.genre),
            'pages': self.pages,
            'available': self.available,
            'borrow_count': self._borrow_count,
        }


# ====================================================================
# 2. Member 类
# ====================================================================
class Member:
    """会员类"""

    def __init__(self, member_id, name, email=None):
        self.member_id = member_id
        self.name = name
        self.email = email
        self.borrowed_books = {}  # isbn → borrow_date
        self.max_books = 5
        self.fine = 0.0

    def can_borrow(self):
        """检查是否可以借书"""
        return (len(self.borrowed_books) < self.max_books
                and self.fine < 10.0)

    def borrow_book(self, isbn, book_title):
        """借阅图书"""
        if not self.can_borrow():
            return False
        self.borrowed_books[isbn] = datetime.now()
        print(f"  📖 {self.name} 借出 《{book_title}》于 {self.borrowed_books[isbn].strftime('%Y-%m-%d %H:%M')}")
        return True

    def return_book(self, isbn):
        """归还图书"""
        if isbn in self.borrowed_books:
            borrow_date = self.borrowed_books.pop(isbn)
            overdue_days = (datetime.now() - borrow_date).days - 14
            if overdue_days > 0:
                fine = overdue_days * 0.5
                self.fine += fine
                print(f"  ⏰ 逾期 {overdue_days} 天，罚款 ${fine:.1f}")
            return True
        return False

    def get_borrowed_list(self):
        """获取借阅列表"""
        return list(self.borrowed_books.keys())

    def __str__(self):
        return (f"会员: {self.name} (ID: {self.member_id}) "
                f"| 已借 {len(self.borrowed_books)}/{self.max_books} 本 "
                f"| 罚款: ${self.fine:.1f}")


# ====================================================================
# 3. BorrowRecord 类
# ====================================================================
class BorrowRecord:
    """借阅记录类"""

    def __init__(self, book, member):
        self.book_title = book.title
        self.book_isbn = book.isbn
        self.member_name = member.name
        self.borrow_date = datetime.now()
        self.due_date = self.borrow_date + timedelta(days=14)
        self.return_date = None
        self.fine = 0.0

    def return_book(self):
        """归还并计算罚款"""
        self.return_date = datetime.now()
        overdue = (self.return_date - self.due_date).days
        if overdue > 0:
            self.fine = overdue * 0.5
        return self.fine

    def is_overdue(self):
        """是否逾期"""
        if self.return_date:
            return False
        return datetime.now() > self.due_date

    def __str__(self):
        status = "已归还" if self.return_date else "借阅中"
        due = self.due_date.strftime('%Y-%m-%d')
        return (f"{self.book_title:<20} → {self.member_name:<10} "
                f"到期: {due} [{status}]")


# ====================================================================
# 4. Library 类
# ====================================================================
class Library:
    """图书馆主类"""

    def __init__(self, name="Python 图书馆"):
        self.name = name
        self.books = {}  # isbn → Book
        self.members = {}  # member_id → Member
        self.records = []  # BorrowRecord 列表

    # ---- 图书管理 ----
    def add_book(self, book):
        """添加图书"""
        self.books[book.isbn] = book
        print(f"  📚 添加图书: 《{book.title}》{book.author}")
        return True

    def remove_book(self, isbn):
        """移除图书"""
        if isbn in self.books:
            book = self.books.pop(isbn)
            Book.total_books -= 1
            print(f"  🗑️ 移除图书: 《{book.title}》")
            return True
        return False

    # ---- 会员管理 ----
    def register_member(self, member):
        """注册会员"""
        self.members[member.member_id] = member
        print(f"  👤 注册会员: {member.name} (ID: {member.member_id})")
        return True

    def get_member(self, member_id):
        """获取会员"""
        return self.members.get(member_id)

    # ---- 借阅管理 ----
    def borrow_book(self, isbn, member_id):
        """借书"""
        book = self.books.get(isbn)
        member = self.members.get(member_id)

        if not book:
            return f"❌ 图书不存在 (ISBN: {isbn})"
        if not member:
            return f"❌ 会员不存在 (ID: {member_id})"
        if member.fine >= 10.0:
            return f"❌ {member.name} 欠款 ${member.fine:.1f}，不能借书"
        if len(member.borrowed_books) >= member.max_books:
            return f"❌ {member.name} 已借满 {member.max_books} 本"
        if not book.available:
            return f"❌ 《{book.title}》已被借出"

        # 执行借书
        book.borrow()
        member.borrow_book(isbn, book.title)

        # 创建记录
        record = BorrowRecord(book, member)
        self.records.append(record)

        return f"✅ 借书成功: 《{book.title}》→ {member.name}"

    def return_book(self, isbn, member_id):
        """还书"""
        book = self.books.get(isbn)
        member = self.members.get(member_id)

        if not book:
            return f"❌ 图书不存在 (ISBN: {isbn})"
        if not member:
            return f"❌ 会员不存在 (ID: {member_id})"

        if isbn not in member.borrowed_books:
            return f"❌ {member.name} 未借阅《{book.title}》"

        # 执行还书
        book.return_book()
        fine = member.return_book(isbn)

        # 更新记录
        for record in self.records:
            if (record.book_isbn == isbn
                    and record.member_name == member.name
                    and record.return_date is None):
                fine = record.return_book()
                break

        return f"✅ 还书成功: 《{book.title}》← {member.name}"

    # ---- 查询 ----
    def search_books(self, keyword):
        """搜索图书"""
        results = []
        for book in self.books.values():
            if (keyword.lower() in book.title.lower()
                    or keyword.lower() in book.author.lower()):
                results.append(book)
        return results

    def get_available_books(self):
        """获取可借图书"""
        return [b for b in self.books.values() if b.available]

    def get_overdue_books(self):
        """获取逾期图书"""
        overdue = []
        for record in self.records:
            if record.is_overdue():
                overdue.append(record)
        return overdue

    # ---- 统计 ----
    def stats(self):
        """图书馆统计"""
        total = len(self.books)
        available = len(self.get_available_books())
        borrowed = total - available
        overdue = len(self.get_overdue_books())
        members = len(self.members)
        records = len(self.records)

        return {
            'total_books': total,
            'available': available,
            'borrowed': borrowed,
            'overdue': overdue,
            'members': members,
            'total_records': records,
        }

    def display_stats(self):
        """显示统计信息"""
        s = self.stats()
        print(f"\n  📊 {self.name} 统计")
        print(f"  {'='*40}")
        print(f"  总藏书:     {s['total_books']} 本")
        print(f"  可借:       {s['available']} 本 ({s['available']/max(s['total_books'],1)*100:.0f}%)")
        print(f"  已借出:     {s['borrowed']} 本")
        print(f"  逾期:       {s['overdue']} 本")
        print(f"  注册会员:   {s['members']} 人")
        print(f"  总借阅记录: {s['total_records']} 条")


# ====================================================================
# 5. 完整的交互演示
# ====================================================================
print("=" * 60)
print("📚 图书管理系统 — 完整演示")
print("=" * 60)

# 创建图书馆
lib = Library("Python 编程图书馆")
print(f"\n🏛️  欢迎来到 {lib.name}!")
print()

# 添加图书
print("─── 添加图书 ───")
books_data = [
    ("Python编程从入门到实践", "Eric Matthes", "978-7-115-54608-9", 'P', 400),
    ("流畅的Python", "Luciano Ramalho", "978-7-115-54609-6", 'P', 550),
    ("三体", "刘慈欣", "978-7-5366-9293-0", 'SF', 380),
    ("百年孤独", "加西亚·马尔克斯", "978-7-5442-5500-8", 'F', 360),
    ("人类简史", "尤瓦尔·赫拉利", "978-7-5086-5847-6", 'NF', 410),
    ("Python算法教程", "Magnus Lie Hetland", "978-7-115-42999-3", 'P', 320),
]

for title, author, isbn, genre, pages in books_data:
    book = Book(title, author, isbn, genre, pages)
    lib.add_book(book)

# 注册会员
print(f"\n─── 注册会员 ───")
members_data = [
    (1001, "张三", "zhang@example.com"),
    (1002, "李四", "li@example.com"),
    (1003, "王五", "wang@example.com"),
]

for mid, name, email in members_data:
    member = Member(mid, name, email)
    lib.register_member(member)

# 搜索图书
print(f"\n─── 搜索 'Python' ───")
results = lib.search_books("Python")
for book in results:
    print(f"  📖 {book}")

# 借书操作
print(f"\n─── 借书操作 ───")
# 张三借两本
print(f"  {lib.borrow_book('978-7-115-54608-9', 1001)}")
print(f"  {lib.borrow_book('978-7-115-54609-6', 1001)}")

# 李四借一本
print(f"  {lib.borrow_book('978-7-5366-9293-0', 1002)}")

# 试图借已借出的书
print(f"  {lib.borrow_book('978-7-115-54608-9', 1003)}")  # 已被借

# 还书
print(f"\n─── 还书操作 ───")
print(f"  {lib.return_book('978-7-115-54608-9', 1001)}")

# 统计
lib.display_stats()

# 列出可借图书
print(f"\n─── 当前可借图书 ───")
for book in lib.get_available_books():
    print(f"  📖 {book}")

# 列出所有图书
print(f"\n─── 全部馆藏 ───")
for book in lib.books.values():
    print(f"  {'📖' if book.available else '📕'} {book}")

# 会员信息
print(f"\n─── 会员信息 ───")
for member in lib.members.values():
    print(f"  👤 {member}")

# 借阅记录
print(f"\n─── 借阅记录 ───")
for record in lib.records:
    print(f"  📋 {record}")

# 系统概况
print(f"\n" + "=" * 60)
print(f"🏆  图书管理系统运行完毕!")
print(f"    {lib.name}")
print(f"    {Book.total_books} 本图书, {len(lib.members)} 位会员")
print(f"    {len(lib.records)} 条借阅记录")
print("=" * 60)
