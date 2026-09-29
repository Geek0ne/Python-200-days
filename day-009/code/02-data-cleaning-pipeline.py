"""
Day 009 — 实战：数据清洗管道
集合在数据清洗中的经典应用
可独立运行，直接 python3 02-data-cleaning-pipeline.py
"""

import json
import time
import random
from collections import Counter


# ============================================================
# 场景设定：用户数据清洗
# 我们从一个日志文件中解析出用户数据，需要：
# 1. 去重（同一个用户可能被多次记录）
# 2. 过滤异常数据（空值、格式错误）
# 3. 找出黑名单用户
# 4. 统计用户标签分布
# ============================================================

# 模拟原始数据
RAW_DATA = [
    {"id": 1001, "name": "Alice",   "email": "alice@example.com",     "tags": "premium,active"},
    {"id": 1002, "name": "Bob",     "email": "bob@example.com",       "tags": "basic"},
    {"id": 1001, "name": "Alice",   "email": "alice@example.com",     "tags": "premium,active"},  # 重复
    {"id": 1003, "name": "",        "email": "charlie@example.com",   "tags": "basic"},            # 名字为空 → 异常
    {"id": 1004, "name": "David",   "email": "",                      "tags": "basic"},            # 邮箱为空 → 异常
    {"id": 1002, "name": "Bob",     "email": "bob@example.com",       "tags": "basic,vip"},        # 重复 + 标签更新
    {"id": 1005, "name": "Eve",     "email": "eve@example.com",       "tags": "premium"},
    {"id": 1006, "name": "Frank",   "email": "frank@example.com",     "tags": "admin,active"},
    {"id": 1007, "name": "Grace",   "email": "",                      "tags": ""},                  # 全部为空 → 异常
    {"id": 1008, "name": "Heidi",   "email": "heidi@example.com",     "tags": "basic,active"},
    {"id": 1003, "name": "",        "email": "charlie@example.com",   "tags": "basic"},            # 重复异常
    {"id": 1009, "name": "Ivan",    "email": "ivan@example.com",      "tags": "premium,active,vip"},
    {"id": 1010, "name": "Judy",    "email": "judy@example.com",      "tags": "basic"},
    {"id": 1005, "name": "Eve",     "email": "eve@example.com",       "tags": "premium,vip"},      # 重复 + 标签更新
    {"id": 1011, "name": "Mallory", "email": "mallory@example.com",   "tags": "basic"},
]

# 黑名单用户 ID
BLACKLIST = {1006, 1011}  # Frank 和 Mallory 在黑名单中

# 必填字段
REQUIRED_FIELDS = {"id", "name", "email"}


# ============================================================
# 1. 数据去重
# ============================================================

print("=" * 70)
print("阶段一：数据去重")
print("=" * 70)

def deduplicate(data):
    """
    使用集合对数据进行去重。
    
    去重策略：
    - 使用 seen_ids 集合跟踪已出现的用户 ID
    - 对于重复 ID，保留最新一条记录（后面的覆盖前面的）
    - 这样即使标签信息有更新，也不会丢失
    """
    seen_ids = set()
    result = []
    duplicates_found = 0
    
    for record in data:
        uid = record["id"]
        if uid in seen_ids:
            # 找到已存在的记录，替换为更新版本
            for i, existing in enumerate(result):
                if existing["id"] == uid:
                    result[i] = record
                    duplicates_found += 1
                    break
        else:
            seen_ids.add(uid)
            result.append(record)
    
    return result, duplicates_found, seen_ids

cleaned_data, dup_count, all_ids = deduplicate(RAW_DATA)

print(f"原始记录数: {len(RAW_DATA)}")
print(f"去重后记录数: {len(cleaned_data)}")
print(f"发现重复: {dup_count} 条")
print(f"不重复用户 ID: {sorted(all_ids)}")


# ============================================================
# 2. 异常值过滤
# ============================================================

print("\n" + "=" * 70)
print("阶段二：异常值过滤")
print("=" * 70)

def validate_record(record):
    """
    检查单条记录是否有效。
    
    检查规则：
    1. 所有必填字段必须存在（非 None）
    2. name 不能为空字符串
    3. email 不能为空字符串
    4. id 必须为正整数
    
    返回 (is_valid, reason)
    """
    # 检查必填字段是否存在
    for field in REQUIRED_FIELDS:
        if field not in record or record[field] is None:
            return False, f"缺少字段: {field}"
    
    # 检查字段值是否为空
    if not record["name"].strip():
        return False, "姓名为空"
    
    if not record["email"].strip():
        return False, "邮箱为空"
    
    # 检查 id 格式
    if not isinstance(record["id"], int) or record["id"] <= 0:
        return False, "ID 格式异常"
    
    return True, ""

def filter_valid(data):
    """过滤出有效记录和异常记录"""
    valid = []
    invalid = []
    
    for record in data:
        is_valid, reason = validate_record(record)
        if is_valid:
            valid.append(record)
        else:
            invalid.append((record, reason))
    
    return valid, invalid

valid_data, invalid_data = filter_valid(cleaned_data)

print(f"有效记录: {len(valid_data)}")
print(f"异常记录: {len(invalid_data)}")

print("\n异常记录详情:")
for record, reason in invalid_data:
    print(f"  ❌ ID {record['id']} ({record.get('name', '?')}) — {reason}")


# ============================================================
# 3. 黑名单过滤
# ============================================================

print("\n" + "=" * 70)
print("阶段三：黑名单过滤")
print("=" * 70)

def filter_blacklist(valid_data, blacklist):
    """
    使用集合运算从有效数据中移除黑名单用户。
    
    set - set = 差集运算，O(len(set)) 复杂度
    """
    # 提取有效用户的 ID 集合
    valid_ids = {record["id"] for record in valid_data}
    
    # 找出哪些有效用户命中黑名单
    blocked = valid_ids & blacklist  # 交集运算
    safe = valid_ids - blacklist     # 差集运算
    
    # 过滤
    result = [record for record in valid_data if record["id"] in safe]
    blocked_records = [record for record in valid_data if record["id"] in blocked]
    
    return result, blocked_records

final_data, blocked_users = filter_blacklist(valid_data, BLACKLIST)

print(f"黑名单 ID: {BLACKLIST}")
print(f"命中黑名单的用户:")
for user in blocked_users:
    print(f"  🚫 {user['name']} (ID: {user['id']})")
print(f"最终有效用户数: {len(final_data)}")


# ============================================================
# 4. 标签分析
# ============================================================

print("\n" + "=" * 70)
print("阶段四：用户标签分析")
print("=" * 70)

def analyze_tags(data):
    """
    使用集合和 Counter 分析用户标签。
    
    分析内容：
    1. 所有出现的标签（去重）
    2. 各标签的用户数
    3. 具有特定标签组合的用户
    """
    # 提取所有标签（每个用户的标签以逗号分隔）
    all_tags = set()          # 所有标签的集合
    user_tags = {}            # 每个用户的标签集合
    
    for record in data:
        tags_str = record.get("tags", "")
        if tags_str.strip():
            tags = {tag.strip() for tag in tags_str.split(",") if tag.strip()}
        else:
            tags = set()
        
        user_tags[record["name"]] = tags
        all_tags.update(tags)
    
    # 统计每个标签的用户数
    tag_counts = Counter()
    for tags in user_tags.values():
        tag_counts.update(tags)
    
    # 找出具有特定标签组合的用户
    premium_users = {
        name for name, tags in user_tags.items()
        if "premium" in tags
    }
    
    vip_users = {
        name for name, tags in user_tags.items()
        if "vip" in tags
    }
    
    # 同时是 premium 和 vip 的用户
    premium_and_vip = premium_users & vip_users
    # 是 premium 但不是 vip 的用户
    premium_only = premium_users - vip_users
    
    return all_tags, tag_counts, premium_users, vip_users, premium_and_vip, premium_only

all_tags, tag_counts, premium_users, vip_users, p_and_v, p_only = analyze_tags(final_data)

print("所有标签:")
for tag in sorted(all_tags):
    print(f"  #{tag} ({tag_counts[tag]} 人)")

print(f"\nPremium 用户: {premium_users}")
print(f"VIP 用户: {vip_users}")
print(f"同时是 Premium 和 VIP: {p_and_v}")
print(f"仅 Premium（非 VIP）: {p_only}")


# ============================================================
# 5. 完整数据清洗管道
# ============================================================

print("\n" + "=" * 70)
print("阶段五：完整管道输出")
print("=" * 70)

def data_cleaning_pipeline(raw_data, blacklist=None):
    """
    完整的数据清洗管道。
    
    流程：
    raw_data
      → 去重（保留最新记录）
      → 异常过滤（空值、格式错误）
      → 黑名单过滤（可选）
      → 输出清洗结果
    """
    if blacklist is None:
        blacklist = set()
    
    print("📥 输入: {} 条原始记录".format(len(raw_data)))
    
    # Step 1: 去重
    step1, dup_count, _ = deduplicate(raw_data)
    print(f"  Step 1 去重: {len(step1)} 条（移除 {dup_count} 条重复）")
    
    # Step 2: 异常过滤
    step2, step2_invalid = filter_valid(step1)
    print(f"  Step 2 异常过滤: {len(step2)} 条有效（移除 {len(step2_invalid)} 条异常）")
    
    # Step 3: 黑名单过滤
    if blacklist:
        step3, step3_blocked = filter_blacklist(step2, blacklist)
        print(f"  Step 3 黑名单过滤: {len(step3)} 条（过滤 {len(step3_blocked)} 条黑名单）")
    else:
        step3 = step2
        step3_blocked = []
    
    # 统计
    stats = {
        "total_raw": len(raw_data),
        "after_dedup": len(step1),
        "duplicates_removed": dup_count,
        "invalid_removed": len(step2_invalid),
        "blocked_removed": len(step3_blocked),
        "final_count": len(step3),
        "invalid_records": [(r["id"], r.get("name", ""), reason) for r, reason in step2_invalid],
        "blocked_records": [(r["id"], r.get("name", "")) for r in step3_blocked],
    }
    
    return step3, stats

final_result, stats = data_cleaning_pipeline(RAW_DATA, BLACKLIST)

print("\n📊 清洗统计:")
print(f"  原始数据:      {stats['total_raw']} 条")
print(f"  去重移除:      {stats['duplicates_removed']} 条")
print(f"  异常移除:      {stats['invalid_removed']} 条")
print(f"  黑名单过滤:    {stats['blocked_removed']} 条")
print(f"  最终有效:      {stats['final_count']} 条")
print(f"  清洗率:        {(1 - stats['final_count']/stats['total_raw']) * 100:.1f}%")


# ============================================================
# 6. 性能演示：集合 vs 列表在大数据清洗中的差异
# ============================================================

print("\n" + "=" * 70)
print("性能演示：集合 vs 列表在大数据清洗中的差异")
print("=" * 70)

# 模拟 10 万条用户数据
print("\n生成 10 万条模拟数据...")
N = 100_000
large_data = []
for i in range(N):
    large_data.append({
        "id": random.randint(1, N // 2),  # 大量重复
        "name": f"User_{i}",
        "email": f"user{i}@example.com",
    })

# 黑名单大小
blacklist_size = 10_000
large_blacklist = set(random.sample(range(1, N // 2 + 1), blacklist_size))

# 场景 1：多次重复成员检查（集合 vs 列表黑名单）
print("\n场景 1：黑名单过滤（黑名单用集合 vs 列表）")

# 用列表作为黑名单（O(n) 查找）
large_blacklist_list = list(large_blacklist)

start = time.perf_counter()
result_list = [record for record in large_data if record["id"] not in large_blacklist_list]
list_time = time.perf_counter() - start

# 用集合作为黑名单（O(1) 查找）
start = time.perf_counter()
result_set = [record for record in large_data if record["id"] not in large_blacklist]
set_time = time.perf_counter() - start

print(f"  数据量: {N} 条黑名单查询 × {len(large_data)} 次检查 = {N * len(large_data):,} 次操作")
print(f"  列表黑名单 (O(n)):  {list_time*1000:.1f} ms")
print(f"  集合黑名单 (O(1)):  {set_time*1000:.1f} ms")
print(f"  集合快约 {list_time/set_time:.1f} 倍")

# 场景 2：去重性能对比（集合 vs 列表）
print("\n场景 2：大数据去重（集合 vs 手动列表去重）")

start = time.perf_counter()
seen_set = set()
result = []
for record in large_data:
    uid = record["id"]
    if uid not in seen_set:
        seen_set.add(uid)
        result.append(record)
set_dedup_time = time.perf_counter() - start

start = time.perf_counter()
seen_list = []
result2 = []
for record in large_data:
    uid = record["id"]
    if uid not in seen_list:  # O(n) 列表查找
        seen_list.append(uid)
        result2.append(record)
list_dedup_time = time.perf_counter() - start

print(f"  数据量: {len(large_data)} 条")
print(f"  集合去重 (O(1) 检查): {set_dedup_time*1000:.1f} ms")
print(f"  列表去重 (O(n) 检查): {list_dedup_time*1000:.1f} ms")
print(f"  集合快约 {list_dedup_time/set_dedup_time:.0f} 倍")

print("\n✅ 数据清洗管道运行完成！")
