"""
Day 068 — 📇 通讯录管理系统（完整实战项目）
功能：CRUD、分类、搜索、数据持久化
运行方式：python 06-contacts-manager.py
"""
import sqlite3
from datetime import datetime


class ContactManager:
    """通讯录管理器——封装所有数据库操作"""

    def __init__(self, db_path: str = "contacts.db"):
        """初始化数据库连接并创建表"""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row  # 启用 Row 工厂
        self._create_tables()
        print(f"📂 数据库已连接: {db_path}")

    def _create_tables(self):
        """创建数据库表和索引"""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT DEFAULT '',
                category TEXT DEFAULT '朋友',
                note TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_contacts_name ON contacts(name);
            CREATE INDEX IF NOT EXISTS idx_contacts_category ON contacts(category);
            CREATE INDEX IF NOT EXISTS idx_contacts_phone ON contacts(phone);
        """)
        self.conn.commit()

    def add_contact(self, name: str, phone: str, email: str = "",
                    category: str = "朋友", note: str = "") -> int:
        """添加联系人，返回新联系人的 ID"""
        now = datetime.now().isoformat()
        cursor = self.conn.execute(
            """INSERT INTO contacts 
               (name, phone, email, category, note, created_at, updated_at) 
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (name, phone, email, category, note, now, now)
        )
        self.conn.commit()
        contact_id = cursor.lastrowid
        print(f"✅ 添加成功: {name} (ID: {contact_id})")
        return contact_id

    def get_contact(self, contact_id: int) -> dict | None:
        """根据 ID 获取单个联系人"""
        cursor = self.conn.execute(
            "SELECT * FROM contacts WHERE id = ?", (contact_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def list_contacts(self, category: str = None,
                      search: str = None) -> list[dict]:
        """
        获取联系人列表
        
        参数：
            category: 按分类过滤
            search: 模糊搜索（姓名、电话、邮箱）
        """
        sql = "SELECT * FROM contacts WHERE 1=1"
        params = []

        if category:
            sql += " AND category = ?"
            params.append(category)

        if search:
            sql += " AND (name LIKE ? OR phone LIKE ? OR email LIKE ?)"
            search_pattern = f"%{search}%"
            params.extend([search_pattern] * 3)

        sql += " ORDER BY name"

        cursor = self.conn.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]

    def update_contact(self, contact_id: int, **kwargs) -> bool:
        """
        更新联系人
        
        参数：
            contact_id: 联系人 ID
            **kwargs: 要更新的字段（name, phone, email, category, note）
        """
        allowed_fields = {"name", "phone", "email", "category", "note"}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not updates:
            print("❌ 没有要更新的字段")
            return False

        updates["updated_at"] = datetime.now().isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [contact_id]

        cursor = self.conn.execute(
            f"UPDATE contacts SET {set_clause} WHERE id = ?", values
        )
        self.conn.commit()

        if cursor.rowcount > 0:
            print(f"✅ 更新成功 (ID: {contact_id})")
            return True
        else:
            print(f"❌ 未找到联系人 (ID: {contact_id})")
            return False

    def delete_contact(self, contact_id: int) -> bool:
        """删除联系人"""
        contact = self.get_contact(contact_id)
        if not contact:
            print(f"❌ 未找到联系人 (ID: {contact_id})")
            return False

        cursor = self.conn.execute(
            "DELETE FROM contacts WHERE id = ?", (contact_id,)
        )
        self.conn.commit()
        print(f"✅ 已删除: {contact['name']}")
        return True

    def get_statistics(self) -> dict:
        """获取统计信息"""
        cursor = self.conn.execute("SELECT COUNT(*) FROM contacts")
        total = cursor.fetchone()[0]

        cursor = self.conn.execute("""
            SELECT category, COUNT(*) as count
            FROM contacts GROUP BY category ORDER BY count DESC
        """)
        categories = {row["category"]: row["count"] for row in cursor.fetchall()}

        cursor = self.conn.execute(
            "SELECT COUNT(DISTINCT category) FROM contacts"
        )
        category_count = cursor.fetchone()[0]

        return {
            "total": total,
            "categories": categories,
            "category_count": category_count,
        }

    def close(self):
        """关闭数据库连接"""
        self.conn.close()
        print("🔒 数据库连接已关闭")


def main():
    """命令行交互界面"""
    manager = ContactManager()

    # 添加一些示例数据
    if manager.get_statistics()["total"] == 0:
        print("\n📝 添加示例数据...")
        manager.add_contact("张三", "13800138000", "zhangsan@email.com", "同事")
        manager.add_contact("李四", "13900139000", "lisi@email.com", "朋友")
        manager.add_contact("王五", "13700137000", "wangwu@email.com", "家人")
        manager.add_contact("赵六", "13600136000", "zhaoliu@email.com", "同事")
        print()

    while True:
        print("\n" + "=" * 40)
        print("📇 通讯录管理系统")
        print("=" * 40)
        print("1. 添加联系人")
        print("2. 查看联系人")
        print("3. 搜索联系人")
        print("4. 更新联系人")
        print("5. 删除联系人")
        print("6. 统计信息")
        print("0. 退出")
        print("-" * 40)

        choice = input("请选择操作 (0-6): ").strip()

        if choice == "1":
            name = input("姓名: ").strip()
            if not name:
                print("❌ 姓名不能为空")
                continue
            phone = input("电话: ").strip()
            if not phone:
                print("❌ 电话不能为空")
                continue
            email = input("邮箱 (可选): ").strip()
            category = input("分类 (朋友/同事/家人，默认朋友): ").strip() or "朋友"
            note = input("备注 (可选): ").strip()
            manager.add_contact(name, phone, email, category, note)

        elif choice == "2":
            category = input("按分类过滤 (直接回车显示全部): ").strip() or None
            contacts = manager.list_contacts(category=category)
            if not contacts:
                print("📭 没有找到联系人")
            else:
                print(f"\n📋 共 {len(contacts)} 个联系人:")
                for c in contacts:
                    print(f"  [{c['id']:3d}] {c['name']:<6} {c['phone']:<13} "
                          f"({c['category']})")

        elif choice == "3":
            keyword = input("搜索关键词 (姓名/电话/邮箱): ").strip()
            if not keyword:
                print("❌ 关键词不能为空")
                continue
            contacts = manager.list_contacts(search=keyword)
            if not contacts:
                print("🔍 没有找到匹配的联系人")
            else:
                print(f"\n🔍 找到 {len(contacts)} 个匹配:")
                for c in contacts:
                    print(f"  [{c['id']:3d}] {c['name']} - {c['phone']} "
                          f"({c['category']})")

        elif choice == "4":
            try:
                cid = int(input("联系人 ID: ").strip())
            except ValueError:
                print("❌ 无效的 ID")
                continue

            # 显示当前信息
            contact = manager.get_contact(cid)
            if not contact:
                print(f"❌ 未找到联系人 (ID: {cid})")
                continue
            print(f"当前信息: {contact['name']} | {contact['phone']} | "
                  f"{contact['email']} | {contact['category']}")
            print("留空表示不修改该字段")

            name = input("新姓名: ").strip() or None
            phone = input("新电话: ").strip() or None
            email = input("新邮箱: ").strip() or None
            category = input("新分类: ").strip() or None

            updates = {}
            if name: updates["name"] = name
            if phone: updates["phone"] = phone
            if email: updates["email"] = email
            if category: updates["category"] = category

            if updates:
                manager.update_contact(cid, **updates)
            else:
                print("ℹ️ 没有修改")

        elif choice == "5":
            try:
                cid = int(input("要删除的联系人 ID: ").strip())
            except ValueError:
                print("❌ 无效的 ID")
                continue

            contact = manager.get_contact(cid)
            if not contact:
                print(f"❌ 未找到联系人 (ID: {cid})")
                continue

            confirm = input(f"确认删除 '{contact['name']}'? (y/N): ").strip()
            if confirm.lower() == "y":
                manager.delete_contact(cid)

        elif choice == "6":
            stats = manager.get_statistics()
            print(f"\n📊 统计信息:")
            print(f"  总联系人数: {stats['total']}")
            print(f"  分类数量: {stats['category_count']}")
            for cat, count in stats["categories"].items():
                print(f"  {cat}: {count} 人")

        elif choice == "0":
            print("👋 再见！")
            break

        else:
            print("❌ 无效选择，请重试")

    manager.close()


if __name__ == "__main__":
    main()
