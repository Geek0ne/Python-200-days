#!/usr/bin/env python3
"""
Day 017 — 输入验证器实战：健壮的用户输入处理

一个完整的输入验证系统，展示如何用异常处理写出健壮的交互式程序。

运行方式：
  python3 02-input-validator.py [--interactive]
  默认运行 demo 模式；加 --interactive 进入交互模式
"""

import sys
import re
from typing import Any, Optional, Callable

SEP = "=" * 60


# ═══════════════════════════════════════════════════════════════
# 自定义验证异常
# ═══════════════════════════════════════════════════════════════

class ValidationError(Exception):
    """验证错误基类"""
    def __init__(self, field: str, message: str, raw_value: Any = None):
        self.field = field
        self.message = message
        self.raw_value = raw_value
        super().__init__(f"[{field}] {message}")


class RequiredFieldError(ValidationError):
    """必填字段缺失"""
    pass


class RangeError(ValidationError):
    """值范围错误"""
    def __init__(self, field: str, value, min_val, max_val):
        self.min_val = min_val
        self.max_val = max_val
        super().__init__(
            field,
            f"值 {value!r} 不在 [{min_val}, {max_val}] 范围内",
            value
        )


class FormatError(ValidationError):
    """格式错误"""
    pass


# ═══════════════════════════════════════════════════════════════
# 验证器类
# ═══════════════════════════════════════════════════════════════

class Validator:
    """可组合的验证器基类"""

    def __call__(self, value: Any) -> Any:
        """验证值，成功返回清洗后的值，失败抛 ValidationError"""
        raise NotImplementedError


class Required(Validator):
    """必填字段验证"""

    def __call__(self, value: Any) -> Any:
        if value is None or (isinstance(value, str) and value.strip() == ""):
            raise RequiredFieldError(self.field_name, "该字段为必填项", value)
        return value

    def __init__(self, field_name: str = "未知"):
        self.field_name = field_name


class Range(Validator):
    """数值范围验证"""

    def __init__(self, min_val: float, max_val: float, field_name: str = "未知"):
        self.min_val = min_val
        self.max_val = max_val
        self.field_name = field_name

    def __call__(self, value: Any) -> float | int:
        try:
            num = float(value)
        except (TypeError, ValueError):
            raise ValidationError(self.field_name, f"无法将 {value!r} 转换为数字", value)
        if num < self.min_val or num > self.max_val:
            raise RangeError(self.field_name, num, self.min_val, self.max_val)
        return int(num) if isinstance(value, int) or (isinstance(value, float) and value == int(value)) else num


class Regex(Validator):
    """正则格式验证"""

    def __init__(self, pattern: str, message: str = "格式不正确", field_name: str = "未知"):
        self.pattern = re.compile(pattern)
        self.message = message
        self.field_name = field_name

    def __call__(self, value: Any) -> str:
        value = str(value).strip()
        if not self.pattern.fullmatch(value):
            raise FormatError(self.field_name, self.message, value)
        return value


class TypeCast(Validator):
    """类型转换验证"""

    def __init__(self, target_type: type, field_name: str = "未知"):
        self.target_type = target_type
        self.field_name = field_name

    def __call__(self, value: Any) -> Any:
        try:
            return self.target_type(value)
        except (ValueError, TypeError) as e:
            raise ValidationError(
                self.field_name,
                f"无法转换为 {self.target_type.__name__}: {e}",
                value
            )


class OneOf(Validator):
    """枚举值验证"""

    def __init__(self, choices: list, field_name: str = "未知"):
        self.choices = choices
        self.field_name = field_name

    def __call__(self, value: Any) -> Any:
        if value not in self.choices:
            raise ValidationError(
                self.field_name,
                f"必须为 {self.choices} 中的一个，收到: {value!r}",
                value
            )
        return value


class Chain(Validator):
    """验证器链 — 顺序执行多个验证"""

    def __init__(self, *validators: Validator):
        self.validators = validators

    def __call__(self, value: Any) -> Any:
        current = value
        for v in self.validators:
            current = v(current)
        return current


# ═══════════════════════════════════════════════════════════════
# 输入收集器
# ═══════════════════════════════════════════════════════════════

class InputCollector:
    """健壮的输入收集器 — 自动重试直到验证通过"""

    def __init__(self, prompt: str = "> ", max_retries: int = 3):
        self.prompt = prompt
        self.max_retries = max_retries

    def ask(self, field: str, validator: Validator, prompt_text: Optional[str] = None) -> Any:
        """向用户询问一个值，使用验证器验证，失败自动重试"""
        display_prompt = prompt_text or f"请输入 {field}"
        attempts = 0

        while attempts < self.max_retries:
            raw = input(f"{display_prompt} {self.prompt}")
            try:
                return validator(raw)
            except RequiredFieldError as e:
                print(f"  ⚠️  {e.message}")
                # 必填不消耗重试次数
                continue
            except ValidationError as e:
                attempts += 1
                remaining = self.max_retries - attempts
                print(f"  ❌ {e}")
                if remaining > 0:
                    print(f"  还可重试 {remaining} 次")
                else:
                    raise ValidationError(field, f"已达最大重试次数，放弃输入", raw)
            except Exception as e:
                # 意料之外的异常 — 立即放弃
                raise RuntimeError(f"输入收集器遇到意外错误: {e}") from e

        raise ValidationError(field, "输入次数用尽")

    def confirm(self, prompt_text: str = "确认?") -> bool:
        """询问 yes/no 确认"""
        return self.ask(
            "confirm",
            OneOf(["y", "yes", "n", "no"], "确认"),
            f"{prompt_text} (y/n)"
        ).lower() in ("y", "yes")


# ═══════════════════════════════════════════════════════════════
# 验证模式 — 预定义验证规则
# ═══════════════════════════════════════════════════════════════

# 用户名：3-20 位字母、数字、下划线
USERNAME_VALIDATOR = Chain(
    Required("用户名"),
    Regex(r"^[a-zA-Z0-9_]{3,20}$", "用户名必须是 3-20 位字母、数字或下划线", "用户名"),
)

# 邮箱：基本格式
EMAIL_VALIDATOR = Chain(
    Required("邮箱"),
    Regex(
        r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
        "邮箱格式不正确（示例: user@example.com）",
        "邮箱",
    ),
)

# 年龄：18-120
AGE_VALIDATOR = Chain(
    Required("年龄"),
    TypeCast(int, "年龄"),
    Range(18, 120, "年龄"),
)

# 手机号（中国）：11 位数字，1 开头
PHONE_VALIDATOR = Chain(
    Required("手机号"),
    Regex(r"^1\d{10}$", "手机号必须是 11 位数字，以 1 开头", "手机号"),
)

# 分数：0-100
SCORE_VALIDATOR = Chain(
    Required("分数"),
    TypeCast(float, "分数"),
    Range(0, 100, "分数"),
)


# ═══════════════════════════════════════════════════════════════
# 应用示例
# ═══════════════════════════════════════════════════════════════

def register_user():
    """模拟用户注册流程"""
    print(SEP)
    print("📝 用户注册 (输入验证演示)")
    print(SEP)

    collector = InputCollector(prompt=": ", max_retries=5)
    user = {}

    try:
        # 收集并验证用户信息
        user["username"] = collector.ask("用户名", USERNAME_VALIDATOR)
        user["email"] = collector.ask("邮箱", EMAIL_VALIDATOR)
        user["age"] = collector.ask("年龄", AGE_VALIDATOR)
        user["phone"] = collector.ask("手机号", PHONE_VALIDATOR)

        print("\n✅ 注册信息验证通过！")
        print("   用户信息:")
        for k, v in user.items():
            print(f"     {k}: {v}")

        if collector.confirm("是否提交?"):
            print("  ✅ 注册成功！")
        else:
            print("  ⏹️  已取消")

    except ValidationError as e:
        print(f"\n❌ 注册失败: {e}")
        return
    except RuntimeError as e:
        print(f"\n💥 系统错误: {e}")
        return


def batch_validate(records: list[dict]) -> list[dict]:
    """批量验证一组记录"""
    valid_records = []
    errors = []

    for i, record in enumerate(records):
        row_num = i + 1
        row_errors = []
        validated = {}

        # 验证用户名
        try:
            validated["username"] = USERNAME_VALIDATOR(record.get("username", ""))
        except ValidationError as e:
            row_errors.append(str(e))

        # 验证邮箱
        try:
            validated["email"] = EMAIL_VALIDATOR(record.get("email", ""))
        except ValidationError as e:
            row_errors.append(str(e))

        # 验证年龄
        try:
            validated["age"] = AGE_VALIDATOR(record.get("age", ""))
        except ValidationError as e:
            row_errors.append(str(e))

        if row_errors:
            errors.append({"row": row_num, "errors": row_errors, "raw": record})
        else:
            valid_records.append(validated)

    return valid_records, errors


def demo_batch_validation():
    """批量验证演示"""
    print(SEP)
    print("📋 批量验证演示")
    print(SEP)

    sample_data = [
        {"username": "alice_2024", "email": "alice@example.com", "age": "28"},
        {"username": "bob", "email": "bob@bad", "age": "17"},
        {"username": "charlie_dev", "email": "charlie@test.org", "age": "35"},
        {"username": "", "email": "dave@example.com", "age": "abc"},
        {"username": "eve", "email": "eve@data.net", "age": "22"},
    ]

    valid, errors = batch_validate(sample_data)

    print(f"\n✅ 验证通过: {len(valid)} 条")
    for rec in valid:
        print(f"   {rec['username']:15s} | {rec['email']:25s} | {rec['age']}")

    print(f"\n❌ 验证失败: {len(errors)} 条")
    for err in errors:
        print(f"   行 {err['row']}:")
        for e in err['errors']:
            print(f"     - {e}")


# ═══════════════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════════════

def main():
    print("🐍 Python 输入验证器实战代码")
    print()

    if "--interactive" in sys.argv or sys.stdin.isatty():
        demo_batch_validation()
        print()
        register_user()
    else:
        demo_batch_validation()


if __name__ == "__main__":
    main()
