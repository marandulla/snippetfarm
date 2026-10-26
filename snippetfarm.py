"""snippetfarm —— 把常用提示词片段整理成可检索的片段库。

设计原则：
1. **片段的价值取决于能被复用**。所以要能检索、能组合、能对照版本。
2. **片段是纯文本文件**。所有片段都能直接读，不藏在看不见的地方。
3. **版本对照要能看出改了哪几个字**。复用别人的片段时，得知道它变过。

仅依赖 Python 标准库。

用法:
    python snippetfarm.py --help
    python snippetfarm.py --dir snippets --list
    python snippetfarm.py --dir snippets --search 角色
    python snippetfarm.py --dir snippets --compose 角色,约束 --out combined.md
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sys

# ---------------------------------------------------------------------------
# 片段文件格式
# ---------------------------------------------------------------------------

# 每个片段是一个 Markdown 文件，头部带元信息：
# ---
# name: 角色设定-客服
# tags: [角色, 客服]
# version: 2
# ---
# 正文……

FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.S)


def parse_snippet(path: str) -> dict:
    """读一个片段文件，拆出元信息与正文。"""
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()

    meta: dict = {}
    body = raw
    m = FRONT_MATTER_RE.match(raw)
    if m:
        meta_block, body = m.group(1), m.group(2)
        for line in meta_block.splitlines():
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            key = key.strip().lower()
            value = value.strip()
            if value.startswith("[") and value.endswith("]"):
                meta[key] = [v.strip() for v in value[1:-1].split(",") if v.strip()]
            else:
                meta[key] = value

    return {
        "path": path,
        "name": meta.get("name") or os.path.splitext(os.path.basename(path))[0],
        "tags": meta.get("tags") or [],
        "version": meta.get("version", "1"),
        "body": body.strip(),
        "meta": meta,
    }


def load_snippets(dirpath: str) -> list[dict]:
    """读目录下所有片段。"""
    out: list[dict] = []
    if not os.path.isdir(dirpath):
        raise ValueError(f"目录不存在：{dirpath}")
    for fn in sorted(os.listdir(dirpath)):
        if not fn.endswith((".md", ".txt")):
            continue
        path = os.path.join(dirpath, fn)
        try:
            out.append(parse_snippet(path))
        except OSError as e:
            print(f"跳过 {fn}：{e}", file=sys.stderr)
    return out


# ---------------------------------------------------------------------------
# 检索
# ---------------------------------------------------------------------------

def search(snippets: list[dict], keyword: str, tag: str = "") -> list[dict]:
    """按关键词与标签检索片段。"""
    kw = keyword.lower().strip()
    tag_lower = tag.lower().strip()

    hits: list[dict] = []
    for s in snippets:
        score = 0
        reasons: list[str] = []

        if kw:
            if kw in s["name"].lower():
                score += 3
                reasons.append("名称命中")
            if kw in s["body"].lower():
                score += 1
                reasons.append("正文命中")
            for t in s["tags"]:
                if kw in str(t).lower():
                    score += 2
                    reasons.append(f"标签「{t}」命中")
        if tag_lower:
            if any(tag_lower == str(t).lower() for t in s["tags"]):
                score += 3
                reasons.append(f"标签「{tag}」精确匹配")
            else:
                continue

        if score > 0:
            hits.append({"snippet": s, "score": score, "reasons": reasons})

    hits.sort(key=lambda h: (-h["score"], h["snippet"]["name"]))
    return hits


# ---------------------------------------------------------------------------
# 组合
# ---------------------------------------------------------------------------

def compose(snippets: list[dict], names: list[str]) -> tuple[str, list[str]]:
    """把几个片段拼成一条完整提示词。"""
    by_name = {s["name"]: s for s in snippets}
    by_path = {os.path.basename(s["path"]): s for s in snippets}

    chunks: list[str] = []
    missing: list[str] = []
    for name in names:
        s = by_name.get(name) or by_path.get(name)
        if s is None:
            missing.append(name)
            continue
        chunks.append(f"<!-- 片段：{s['name']} v{s['version']} -->")
        chunks.append(s["body"])

    return "\n\n".join(chunks), missing


# ---------------------------------------------------------------------------
# 版本对照
# ---------------------------------------------------------------------------

def diff_versions(snippets: list[dict]) -> list[dict]:
    """同名片段（不同文件）之间的版本对照。"""
    groups: dict[str, list[dict]] = {}
    for s in snippets:
        groups.setdefault(s["name"], []).append(s)

    out: list[dict] = []
    for name, items in groups.items():
        if len(items) < 2:
            continue
        items = sorted(items, key=lambda s: str(s["version"]))
        for i in range(len(items) - 1):
            a, b = items[i], items[i + 1]
            sm = difflib.SequenceMatcher(None, a["body"], b["body"])
            ratio = sm.ratio()
            changes = []
            for tag, i1, i2, j1, j2 in sm.get_opcodes():
                if tag == "equal":
                    continue
                changes.append({
                    "op": tag,
                    "old": a["body"][i1:i2][:120],
                    "new": b["body"][j1:j2][:120],
                })
            out.append({
                "name": name,
                "from_version": a["version"],
                "to_version": b["version"],
                "from_file": os.path.basename(a["path"]),
                "to_file": os.path.basename(b["path"]),
                "similarity": round(ratio, 4),
                "changes": changes,
            })
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def render_list(snippets: list[dict]) -> str:
    out: list[str] = []
    out.append(f"片段库（{len(snippets)} 个片段）")
    out.append("=" * 60)
    if not snippets:
        out.append("片段库是空的。")
        return "\n".join(out)

    # 按标签分组
    by_tag: dict[str, list[dict]] = {}
    for s in snippets:
        for t in (s["tags"] or ["（无标签）"]):
            by_tag.setdefault(str(t), []).append(s)

    for tag in sorted(by_tag):
        out.append(f"[{tag}]")
        for s in sorted(by_tag[tag], key=lambda x: x["name"]):
            preview = s["body"].splitlines()[0][:60] if s["body"] else ""
            out.append(f"  {s['name']}  v{s['version']}  {preview}")
        out.append("")
    return "\n".join(out).rstrip()


def render_search(hits: list[dict]) -> str:
    out: list[str] = []
    out.append(f"检索到 {len(hits)} 个片段")
    out.append("=" * 60)
    for h in hits:
        s = h["snippet"]
        out.append(f"{s['name']}  v{s['version']}  （相关度 {h['score']}："
                   f"{'、'.join(h['reasons'])}）")
        out.append(f"  文件：{os.path.basename(s['path'])}")
        tags = "、".join(str(t) for t in s["tags"]) or "（无标签）"
        out.append(f"  标签：{tags}")
        for line in s["body"].splitlines()[:3]:
            out.append(f"  | {line}")
        out.append("")
    return "\n".join(out).rstrip()


def render_diff(diffs: list[dict]) -> str:
    out: list[str] = []
    out.append("片段版本对照")
    out.append("=" * 60)
    if not diffs:
        out.append("没有发现同名片段的多个版本。")
        return "\n".join(out)

    for d in diffs:
        out.append(f"{d['name']}  v{d['from_version']} → v{d['to_version']}")
        out.append(f"  {d['from_file']} → {d['to_file']}  "
                   f"相似度 {d['similarity']:.2f}")
        for c in d["changes"]:
            out.append(f"  [{c['op']}]")
            if c["old"]:
                out.append(f"    - {c['old']}")
            if c["new"]:
                out.append(f"    + {c['new']}")
        out.append("")
    return "\n".join(out).rstrip()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="snippetfarm",
        description="把常用提示词片段整理成可检索的片段库（仅依赖标准库）",
        epilog=(
            "片段文件格式：\n"
            "  ---\n  name: 角色-客服\n  tags: [角色, 客服]\n  version: 1\n  ---\n"
            "  你是……\n"
            "  python snippetfarm.py --dir snippets --list\n"
            "  python snippetfarm.py --dir snippets --search 角色\n"
            "  python snippetfarm.py --dir snippets --compose 角色-客服,约束-长度\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--dir", required=True, help="片段目录")
    ap.add_argument("--list", action="store_true", help="列出所有片段")
    ap.add_argument("--search", help="按关键词检索")
    ap.add_argument("--tag", default="", help="按标签精确过滤")
    ap.add_argument("--compose", help="按名称用逗号分隔地组合片段")
    ap.add_argument("--out", help="组合结果写到文件")
    ap.add_argument("--diff", action="store_true", help="版本对照")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    args = ap.parse_args(argv)

    try:
        snippets = load_snippets(args.dir)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2

    if args.compose:
        names = [n.strip() for n in args.compose.split(",") if n.strip()]
        text, missing = compose(snippets, names)
        if missing:
            print(f"找不到片段：{'、'.join(missing)}", file=sys.stderr)
            return 2
        if args.out:
            try:
                with open(args.out, "w", encoding="utf-8") as f:
                    f.write(text + "\n")
            except OSError as e:
                print(f"写不了文件：{e}", file=sys.stderr)
                return 2
            print(f"已组合 {len(names)} 个片段 → {args.out}")
        else:
            print(text)
        return 0

    if args.search:
        hits = search(snippets, args.search, args.tag)
        if args.json:
            print(json.dumps([{"name": h["snippet"]["name"],
                               "score": h["score"],
                               "reasons": h["reasons"],
                               "tags": h["snippet"]["tags"]} for h in hits],
                             ensure_ascii=False, indent=2))
        else:
            print(render_search(hits))
        return 0 if hits else 1

    if args.diff:
        diffs = diff_versions(snippets)
        if args.json:
            print(json.dumps(diffs, ensure_ascii=False, indent=2))
        else:
            print(render_diff(diffs))
        return 0

    if args.json:
        print(json.dumps([{"name": s["name"], "tags": s["tags"],
                           "version": s["version"], "file": s["path"]}
                          for s in snippets], ensure_ascii=False, indent=2))
    else:
        print(render_list(snippets))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
