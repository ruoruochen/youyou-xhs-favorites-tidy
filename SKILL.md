---
name: youyou-xhs-favorites-tidy
description: 一键整理小红书"我的收藏夹"闭环：输入收藏夹链接 → 用已登录浏览器抓取全部收藏（封面/标题/链接/作者/点赞）→ 自动按主题动态分类（一级分类/收藏用途/处理建议）→ 生成多巴胺风多 Sheet 整理表（分类总览/按分类浏览/定时推送清单/重复与待确认，带"处理状态"打卡列与已完成自动统计）→ 建每日定时推送（默认每天中午12点从清单挑3个待办推给用户）。当用户要求整理、盘点、分类自己的小红书收藏夹，或想把收藏变成每日可打卡的待办清单、每天推送要学要做的收藏时使用。
---

# 小红书收藏夹一键整理闭环

从一个收藏夹链接，一路做到"分类清楚 + 每天推 3 条 + 对话打卡"。

## 前置依赖

- 采集用 `browser-use-automation-mac`：`mac_computer_use_tool` 里 `plane="bu"`、`import seed_browser_use as bu`。
- 报表渲染是本地确定性脚本：`scripts/build_report.py`（openpyxl）。
- 去重/点赞解析/导出 CSV：`scripts/export_csv.py`。
- 采集踩坑（登录/虚拟滚动/406 签名）：动手前先读 `references/xhs-collect.md`。
- 怎么动态分类：读 `references/classification.md`。

## 工作流

### 1. 拿到收藏夹链接
用户给形如 `https://www.xiaohongshu.com/user/profile/{user_id}?tab=fav&subTab=note` 的链接；没给就请用户在小红书网页版"我的-收藏"里复制链接。

### 2. 抓取
按 `references/xhs-collect.md` 在浏览器里：导航到收藏夹页 → 登录就 `interaction.request_action(type="browserControl")` 让用户扫码（不要绕登录、不要输密码）→ 注入 extract_js → 用 `bu.scroll` 真实滚轮滚到底（**禁止 `window.scrollTo`**，本页是虚拟滚动）→ 按 `note_id` 去重累积 → 存成 JSON。

### 3. 清洗
```bash
python3 scripts/export_csv.py 抓取.json -o 收藏.csv --exclude-author 自己昵称 小号昵称
```
此步去重、把"1.4万"解析成数值、输出 CSV。同时保留一份抓取 JSON 给下一步。

### 4. 动态分类（核心，别套固定类别）
读 `references/classification.md`，扫全部标题，给每条打 `category / sub / purpose / advice` 四个标签；按主题现建分类，标题信息不足的一律进 `待确认`。产出 `classified.json`（形状见该文件末尾）。

### 5. 渲染多巴胺风报表
```bash
python3 scripts/build_report.py classified.json -o 收藏夹整理分析.xlsx
```
产出 4 个 Sheet，已内置：
- **分类总览**：统计块（原始/去重样本/已完成=COUNTIF/重复）+ 马卡龙分类行按数量降序 + 右侧整理原则。
- **按分类浏览**：每条明细 + 第 9 列「处理状态」默认"待处理"；已完成的行用条件格式自动整行变灰+删除线。
- **定时推送清单**：`advice` 为 `优先查看` / `15分钟可试` 的条目，优先查看排前。
- **重复与待确认**。

用 `present_files` 把 xlsx 交给用户。

### 6. 建每日推送任务
用 `doubao-cron-scheduler` 的 `create_cron_job` 建一个每日任务，**默认 schedule_type=cron、`schedule="0 12 * * *"`（每天 12:00，Asia/Tokyo；用户在别处就改对应时区，别默认整点 9 点）**。`query` 里写清：
- 开头必须是"本次请求是由「每日收藏推送」定时任务到时触发的"。
- 用 openpyxl 读这份 xlsx，从「定时推送清单」里挑 3 个「处理状态」不是"已完成"的待办（优先查看优先），把标题/作者/建议/链接推给用户。
- 提醒用户做完一条就在对话里说"XX完成了"。
- 若清单全部完成，告知收藏夹已清理完、可暂停任务。
- 只读不改、不重新抓小红书、不登录网站。

## 打卡闭环（用户后续说"完成了"）

用户在对话里说"XX看完了/完成了"时：
1. 用 openpyxl 打开同一份 xlsx，在「按分类浏览」按标题/note_link 定位那一行。
2. 把第 9 列「处理状态」改成 `已完成`。
3. 保存；分类总览的"已完成"COUNTIF 自动 +1，那行自动变灰。
4. 用 `present_files` 重新交付。
**不要重跑 build_report.py**——它会把所有状态重置成"待处理"；打卡只改那一格。

## 关键认知（避免重复踩坑）

- tab 显示的收藏数 ≠ 实际抓到的条数：被作者删除/设私/下架的仍计数但不渲染，以实际去重条数为准并说明差异。
- 点赞是文本（`6233`/`1.4万`/`10万+`），脚本已转数值。
- 不要直接 fetch `/api/sns/web/v2/note/collect/page`，需 X-s 签名会 406。
- 虚拟滚动必须 `bu.scroll` 真实滚轮，离屏节点会被回收。
