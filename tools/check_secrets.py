#!/usr/bin/env python3
"""Secret 扫描 gate（CI governance-gates 阻塞项）—— BUG-003 ①.

确保**被 git 跟踪的文件**里不含厂商 API key 字面量（厂商 key 只能在网关运行时经 env 注入，
代码/配置/Agent 路径不得持有）。允许：`os.environ/...` 引用、`${VAR}` 插值、占位符
（change-me/example/your-/<>/xxx/空值）。.env 等真实密钥文件本就 gitignored，不在跟踪范围。

退出码：0 干净；1 命中疑似密钥。
"""
from __future__ import annotations
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SELF = "tools/check_secrets.py"
# 这些文件按设计含 key 模式/占位（说明文档、模板、本脚本），豁免
ALLOW = {SELF, "infra/.env.example"}
ALLOW_PREFIX = ("harness/tasks/bugs/",)  # bug 单会描述 key 模式

PLACEHOLDER = re.compile(r"change[-_]?me|example|your[-_]|xxx+|<[^>]*>|\.\.\.|placeholder|dev[-_]", re.I)
# 高置信厂商 key 字面量
SK_KEY = re.compile(r"\bsk-[A-Za-z0-9]{16,}\b")
KEYNAME = re.compile(
    r"\b(?:DEEPSEEK|KIMI|MOONSHOT|ANTHROPIC|OPENAI|GROQ|GEMINI|GOOGLE)_API_KEY\b(.*)"
)


def assigned_value(line: str) -> str | None:
    """提取 *_API_KEY 的赋值右侧（兼容 python `K: str = v` / yaml `K: v` / env `K=v`）。"""
    m = KEYNAME.search(line)
    if not m:
        return None
    rest = m.group(1)
    if "=" in rest:          # python/env 赋值（跳过 `: type` 注解）
        return rest.split("=", 1)[1].strip()
    if ":" in rest:          # yaml
        return rest.split(":", 1)[1].strip()
    return None              # 仅引用名（如 os.environ/DEEPSEEK_API_KEY）


def is_placeholder(val: str) -> bool:
    v = val.strip().strip("'\"")
    if not v:
        return True
    if v.startswith("os.environ/") or v.startswith("${") or v.startswith("$"):
        return True
    return bool(PLACEHOLDER.search(v))


def main() -> int:
    files = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True
    ).stdout.splitlines()
    hits: list[str] = []
    for rel in files:
        if rel in ALLOW or rel.startswith(ALLOW_PREFIX):
            continue
        p = ROOT / rel
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError):
            continue
        for i, line in enumerate(text.splitlines(), 1):
            for m in SK_KEY.finditer(line):
                if not is_placeholder(m.group(0)):
                    hits.append(f"{rel}:{i} 疑似 sk- 密钥：{m.group(0)[:12]}…")
            val = assigned_value(line)
            if val is not None and not is_placeholder(val):
                hits.append(f"{rel}:{i} 厂商 key 字面量：{line.strip()[:50]}")

    if hits:
        print("✗ secret 扫描命中（厂商 key 不得进代码/配置，BUG-003 ①）：")
        for h in hits:
            print(f"  - {h}")
        return 1
    print(f"✓ secret 扫描通过（{len(files)} 个跟踪文件，无厂商 key 字面量）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
