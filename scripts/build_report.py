#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把"已分类"的小红书收藏数据渲染成多巴胺风整理报表 xlsx。

用法:
    python3 build_report.py classified.json -o 收藏夹整理.xlsx

输入 classified.json 结构:
{
  "meta": {"note_total": 47, "self_removed": 3},
  "categories": [
    {"name":"包包与穿搭好物", "main":"一句话概括", "how":"建议怎么用", "color":"FBD5B0"}
  ],
  "notes": [
    {"title":"...", "name":"作者", "like_count_text":"1.4万", "_like_num":14000,
     "note_link":"https://www.xiaohongshu.com/explore/xxx",
     "category":"包包与穿搭好物", "sub":"二级分类", "purpose":"当时为什么收藏",
     "advice":"优先查看 | 15分钟可试 | ..."}
  ]
}

本脚本不做分类——分类由 agent 在运行时按标题语义完成（见 references/classification.md），
这里只负责把结果渲染成固定版式的 4-Sheet 报表，并内置"处理状态"打卡闭环。
"""
import argparse, json, os, re, sys
from collections import defaultdict
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.formatting.rule import FormulaRule

# ---- 多巴胺配色 ----
BANNER = PatternFill('solid', fgColor='F8CBAD')
BANNER_FONT = Font(bold=True, size=14, color='C55A11')
SUB_FONT = Font(size=9, color='999999')
HEAD_FILL = PatternFill('solid', fgColor='FFF2CC')
HEAD_FONT = Font(bold=True, size=10)
thin = Side(style='thin', color='D9D9D9')
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)
CENTER = Alignment(horizontal='center', vertical='center', wrap_text=True)
LEFT = Alignment(horizontal='left', vertical='center', wrap_text=True)

# 马卡龙调色板：categories 未给 color 时按分类出现顺序轮询
PALETTE = ['FBD5B0', 'FCE4EC', 'FCE4D6', 'E4DFEC', 'DDEBF7',
           'E2EFDA', 'FFE6F0', 'E8DAEF', 'FFF2CC', 'D9E1F2']
PRIORITY = ('优先查看', '15分钟可试')


def fill(h): return PatternFill('solid', fgColor=h)


def norm_title(t):
    return re.sub(r'[\s\W#＃！!？?~～]', '', t or '').lower()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input', help='已分类的 JSON 文件路径')
    ap.add_argument('-o', '--output', default='收藏夹整理分析.xlsx')
    args = ap.parse_args()

    doc = json.load(open(args.input, encoding='utf-8'))
    meta = doc.get('meta', {})
    notes = doc['notes']
    cat_meta = {c['name']: c for c in doc.get('categories', [])}

    # 点赞数值：优先用输入里的 _like_num，否则尝试解析 like_count_text
    def like_num(n):
        if n.get('_like_num') not in (None, ''):
            return n['_like_num']
        t = (n.get('like_count_text') or '').strip().replace('+', '')
        try:
            if t.endswith('万'): return int(float(t[:-1]) * 10000)
            if t.endswith('亿'): return int(float(t[:-1]) * 100000000)
            return int(float(t))
        except Exception:
            return 0

    for n in notes:
        n['_num'] = like_num(n)
        n.setdefault('_status', '待处理')

    # 重复检测（标题归一化）
    g = defaultdict(list)
    for n in notes:
        g[norm_title(n['title'])].append(n)
    dup_groups = [v for v in g.values() if len(v) > 1]
    dup_extra = sum(len(v) - 1 for v in dup_groups)

    # 分类按数量降序
    cnt = defaultdict(int)
    for n in notes:
        cnt[n['category']] += 1
    order = sorted(cnt.keys(), key=lambda c: (-cnt[c], c))

    def color_of(cat):
        if cat in cat_meta and cat_meta[cat].get('color'):
            return cat_meta[cat]['color']
        return PALETTE[order.index(cat) % len(PALETTE)]

    wb = Workbook()

    def banner(ws, text, sub, span):
        ws.merge_cells(f'A1:{span}1')
        c = ws['A1']; c.value = text; c.fill = BANNER; c.font = BANNER_FONT; c.alignment = CENTER
        ws.row_dimensions[1].height = 30
        ws.merge_cells(f'A2:{span}2')
        c2 = ws['A2']; c2.value = sub; c2.font = SUB_FONT; c2.alignment = CENTER

    def headrow(ws, row, heads, startcol=1):
        for j, h in enumerate(heads, startcol):
            c = ws.cell(row=row, column=j, value=h)
            c.fill = HEAD_FILL; c.font = HEAD_FONT; c.border = BORDER; c.alignment = CENTER

    # ===== Sheet1 分类总览 =====
    ws = wb.active; ws.title = '分类总览'
    banner(ws, '我的小红书收藏夹｜分类总览',
           '先看清自己收藏了什么,再决定学什么;完成一条收藏后在明细页把状态改成"已完成"。', 'H')
    stats = [
        ('原始收藏', meta.get('note_total', len(notes) + meta.get('self_removed', 0)), 'FCE4D6'),
        ('去重后样本', len(notes), 'FFF2CC'),
        ('已完成', '=COUNTIF(\'按分类浏览\'!$I:$I,"已完成")', 'C6EFCE'),
        ('重复', dup_extra, 'DDEBF7'),
    ]
    for i, (lab, val, col) in enumerate(stats):
        c0 = 1 + i * 2
        lc = ws.cell(row=4, column=c0, value=lab); lc.fill = fill(col); lc.alignment = CENTER
        lc.font = Font(size=9, color='666666')
        vc = ws.cell(row=5, column=c0, value=val); vc.fill = fill(col); vc.alignment = CENTER
        vc.font = Font(bold=True, size=16)
        ws.merge_cells(start_row=4, start_column=c0, end_row=4, end_column=c0 + 1)
        ws.merge_cells(start_row=5, start_column=c0, end_row=5, end_column=c0 + 1)
    hr = 7
    headrow(ws, hr, ['一级分类', '数量', '占比', '主要内容', '建议怎么用'])
    r = hr + 1
    for cat in order:
        f = fill(color_of(cat))
        cm = cat_meta.get(cat, {})
        vals = [cat, cnt[cat], None, cm.get('main', ''), cm.get('how', '')]
        for j, v in enumerate(vals, 1):
            c = ws.cell(row=r, column=j, value=v); c.fill = f; c.border = BORDER
            c.alignment = LEFT if j in (4, 5) else CENTER
            if j == 1: c.font = Font(bold=True)
        pc = ws.cell(row=r, column=3, value=f'=B{r}/$C$5'); pc.number_format = '0%'
        pc.fill = f; pc.border = BORDER; pc.alignment = CENTER
        r += 1
    ws.cell(row=r, column=1, value='合计').font = Font(bold=True)
    ws.cell(row=r, column=2, value=f'=SUM(B{hr+1}:B{r-1})').font = Font(bold=True)
    ws.cell(row=r, column=3, value=f'=B{r}/$C$5').number_format = '0%'
    rules = ['1. 一级分类:它属于什么主题?', '2. 收藏用途:当时为什么会收藏?',
             '3. 处理建议:下一次该怎么处理?', '4. 标题信息不足不强行分类,统一放进「重复与待确认」',
             '5. 从「定时推送清单」每天挑 3 条,做完对话里说一声']
    ws.cell(row=7, column=7, value='整理原则').font = Font(bold=True)
    for i, t in enumerate(rules):
        c = ws.cell(row=8 + i, column=7, value=t); c.alignment = LEFT; c.font = Font(size=9)
    for col, w in zip('ABCDE', [18, 8, 8, 40, 26]):
        ws.column_dimensions[col].width = w
    ws.column_dimensions['G'].width = 34

    # ===== Sheet2 按分类浏览 =====
    ws2 = wb.create_sheet('按分类浏览')
    banner(ws2, '按分类浏览收藏',
           '每条标题保留原笔记跳转;已完成的行会自动变灰;做完一条把"处理状态"改成已完成。', 'I')
    r = 4
    for cat in order:
        items = [n for n in notes if n['category'] == cat]
        if not items:
            continue
        f = fill(color_of(cat))
        ws2.merge_cells(start_row=r, start_column=1, end_row=r, end_column=9)
        c = ws2.cell(row=r, column=1, value=f'{cat}｜{len(items)}条')
        c.fill = f; c.font = Font(bold=True); c.alignment = LEFT
        r += 1
        headrow(ws2, r, ['收藏标题', '子分类', '收藏用途', '处理建议', '作者',
                         '点赞(原文)', '点赞(数值)', '帖子链接', '处理状态'])
        r += 1
        items.sort(key=lambda d: (0 if d.get('_status') != '已完成' else 1, -(d['_num'] or 0)))
        for d in items:
            vals = [d.get('title', ''), d.get('sub', ''), d.get('purpose', ''),
                    d.get('advice', ''), d.get('name', ''), d.get('like_count_text', ''),
                    d['_num'], d.get('note_link', ''), d['_status']]
            for j, v in enumerate(vals, 1):
                c = ws2.cell(row=r, column=j, value=v); c.border = BORDER
                c.alignment = LEFT if j in (1, 8) else CENTER
            r += 1
    for col, w in zip(['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I'],
                      [34, 12, 16, 16, 14, 10, 10, 42, 10]):
        ws2.column_dimensions[col].width = w
    gray_fill = PatternFill('solid', fgColor='F2F2F2')
    gray_font = Font(color='AAAAAA', strike=True)
    ws2.conditional_formatting.add(f'A4:I{r-1}',
        FormulaRule(formula=['$I4="已完成"'], fill=gray_fill, font=gray_font))

    # ===== Sheet3 定时推送清单 =====
    ws3 = wb.create_sheet('定时推送清单')
    banner(ws3, '定时推送 / 优先查看清单', '按"服务你当前事项"的优先级排序,每天从中挑 3 个待办。', 'E')
    headrow(ws3, 4, ['优先级', '收藏标题', '作者', '处理建议', '帖子链接'])
    prio = [n for n in notes if n.get('advice') in PRIORITY]
    prio.sort(key=lambda d: (0 if d['advice'] == '优先查看' else 1, -(d['_num'] or 0)))
    r = 5
    for d in prio:
        f = fill('FFF2CC' if d['advice'] == '优先查看' else 'E2EFDA')
        vals = [d['advice'], d.get('title', ''), d.get('name', ''), d.get('advice', ''), d.get('note_link', '')]
        for j, v in enumerate(vals, 1):
            c = ws3.cell(row=r, column=j, value=v); c.border = BORDER; c.fill = f
            c.alignment = LEFT if j in (2, 5) else CENTER
        r += 1
    for col, w in zip('ABCDE', [14, 34, 14, 16, 42]):
        ws3.column_dimensions[col].width = w

    # ===== Sheet4 重复与待确认 =====
    ws4 = wb.create_sheet('重复与待确认')
    banner(ws4, '重复与待确认',
           '重复项已在总库保留一条;待确认内容因标题信息不足,不做强行推断。', 'F')
    ws4.merge_cells('A4:F4')
    c = ws4.cell(row=4, column=1, value=f'重复内容｜共多出 {dup_extra} 条')
    c.fill = fill('F4B183'); c.font = Font(bold=True, color='FFFFFF'); c.alignment = LEFT
    headrow(ws4, 5, ['收藏标题', '出现次数', '一级分类', '作者', '点赞', '帖子链接'])
    r = 6
    if dup_groups:
        for v in dup_groups:
            vals = [v[0].get('title', ''), len(v), v[0].get('category', ''),
                    v[0].get('name', ''), v[0].get('like_count_text', ''), v[0].get('note_link', '')]
            for j, x in enumerate(vals, 1):
                c = ws4.cell(row=r, column=j, value=x); c.border = BORDER
                c.alignment = LEFT if j in (1, 6) else CENTER
            r += 1
    else:
        ws4.merge_cells(start_row=r, start_column=1, end_row=r, end_column=6)
        c = ws4.cell(row=r, column=1, value='按笔记ID去重并比对标题后,未发现重复收藏。')
        c.font = Font(italic=True, color='888888')
        r += 1
    pending = [n for n in notes if n.get('category') == '待确认']
    r += 1
    ws4.merge_cells(start_row=r, start_column=1, end_row=r, end_column=6)
    c = ws4.cell(row=r, column=1, value=f'待确认｜{len(pending)} 条')
    c.fill = fill('F4B183'); c.font = Font(bold=True, color='FFFFFF'); c.alignment = LEFT
    r += 1
    headrow(ws4, r, ['收藏标题', '当前判断', '建议动作', '作者', '点赞', '帖子链接'])
    r += 1
    for d in pending:
        vals = [d.get('title', ''), d.get('sub', '标题信息不足'),
                d.get('purpose', '打开原文后重新分类'), d.get('name', ''),
                d.get('like_count_text', ''), d.get('note_link', '')]
        for j, x in enumerate(vals, 1):
            c = ws4.cell(row=r, column=j, value=x); c.border = BORDER
            c.alignment = LEFT if j in (1, 6) else CENTER
        r += 1
    for col, w in zip('ABCDEF', [34, 16, 18, 14, 10, 42]):
        ws4.column_dimensions[col].width = w

    wb.save(args.output)
    print(f"saved {args.output} {os.path.getsize(args.output)} bytes | 样本 {len(notes)} | "
          f"剔自己 {meta.get('self_removed',0)} | 重复组 {len(dup_groups)}", file=sys.stderr)


if __name__ == '__main__':
    main()
