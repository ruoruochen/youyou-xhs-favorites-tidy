#!/usr/bin/env python3
"""把 bu.js 抓回的小红书收藏 JSON 整理成 CSV。

用法:
    python3 export_csv.py input.json [-o out.csv] [--exclude-author 昵称 ...]

输入 JSON: list[dict]，每项至少含 note_id/title/name/like_count_text/note_link/
cover_src/author_href/author_avatar/cover_href。
输出: UTF-8-BOM CSV（Excel 直接打开中文不乱码），按点赞数值降序。
"""
import argparse, csv, json, sys, os


def parse_count(text: str):
    """'6233' -> 6233; '1.4万' -> 14000; '10万+' -> 100000; '3亿' -> 300000000。无法解析返回 ''。"""
    t = (text or "").strip().replace("+", "")
    if not t:
        return ""
    try:
        if t.endswith("万"):
            return int(float(t[:-1]) * 10000)
        if t.endswith("亿"):
            return int(float(t[:-1]) * 100000000)
        return int(float(t))
    except ValueError:
        return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="bu.js 导出的 JSON 文件路径")
    ap.add_argument("-o", "--output", default="小红书收藏夹.csv")
    ap.add_argument("--exclude-author", nargs="*", default=[],
                    help="要剔除的作者昵称（如自己/小号），可多个")
    args = ap.parse_args()

    with open(args.input, encoding="utf-8") as f:
        rows = json.load(f)

    exclude = set(a.strip() for a in args.exclude_author if a.strip())
    seen, kept, dropped_self = set(), 0, 0
    for r in rows:
        nid = r.get("note_id")
        if not nid or nid in seen:
            continue
        if r.get("name", "").strip() in exclude:
            dropped_self += 1
            continue
        seen.add(nid)
        r["_like_num"] = parse_count(r.get("like_count_text", ""))
        kept += 1

    rows = [r for r in rows if r.get("note_id") in seen and r.get("name", "").strip() not in exclude]
    rows.sort(key=lambda r: (r["_like_num"] == "", -(r["_like_num"] or 0)))

    cols = [
        ("title", "标题"), ("name", "作者"),
        ("like_count_text", "点赞数(原文)"), ("_like_num", "点赞数(数值)"),
        ("note_link", "帖子链接"), ("cover_src", "封面图"),
        ("author_href", "作者主页"), ("author_avatar", "作者头像"),
        ("cover_href", "封面链接(原)"), ("note_id", "笔记ID"),
    ]
    with open(args.output, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow([c[1] for c in cols])
        for r in rows:
            w.writerow(["" if r.get(k) is None else r.get(k, "") for k, _ in cols])

    print(f"去重后 {kept} 条；剔除自己/指定作者 {dropped_self} 条；写出 {args.output} "
          f"({os.path.getsize(args.output)} bytes)", file=sys.stderr)


if __name__ == "__main__":
    main()
