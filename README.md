# youyou-xhs-favorites-tidy

一键把小红书"我的收藏夹"整理成**可打卡的每日待办清单**：抓取 → 动态分类 → 多巴胺风报表 → 每日定时推 3 条 → 对话打卡。

## 它做什么

丢给它一个小红书收藏夹链接，它会：

1. **抓取**：在已登录的浏览器里滚到底，收集每条收藏的封面、标题、帖子链接、作者、点赞数（不调需签名的后端接口）。
2. **清洗**：自动剔除自己/小号的笔记，把"1.4万"这类点赞文本转成数值。
3. **动态分类**：按标题语义给每条打四个标签——一级分类（主题）、子分类、收藏用途（当时为啥收藏）、处理建议（下次怎么办）；标题信息不足的不硬猜，进"待确认"。
4. **生成报表**：一个多巴胺风 `.xlsx`，4 个 Sheet：
   - **分类总览**：原始/样本/已完成/重复四块统计，马卡龙分类行按占比降序。
   - **按分类浏览**：每条明细 + 「处理状态」列；已完成的行自动整行变灰、加删除线。
   - **定时推送清单**：优先查看 + 15 分钟可试。
   - **重复与待确认**。
5. **每日推送**：每天定时（默认中午 12:00）从清单挑 3 个没完成的推给你。
6. **对话打卡**：你说"XX完成了"，它把那条标成已完成，总览计数自动 +1。

## 目录结构

```
youyou-xhs-favorites-tidy/
├── SKILL.md                  # 主流程（给 agent 读）
├── scripts/
│   ├── export_csv.py         # 去重 + 点赞解析 + 导出 CSV
│   └── build_report.py       # 把已分类数据渲染成多巴胺风 xlsx
└── references/
    ├── xhs-collect.md        # 浏览器采集细节（登录/虚拟滚动/选择器）
    └── classification.md     # 动态分类方法论与输入 JSON 格式
```

## 用法

这是一个为 AI agent（豆包办公）设计的 skill：把整个目录放进 agent 的 `.user_skills/` 目录，然后对 agent 说

> 整理我的小红书收藏夹：https://www.xiaohongshu.com/user/profile/<你的id>?tab=fav&subTab=note

agent 会按 `SKILL.md` 跑完整条链路。

也可以单独用脚本：

```bash
# 抓取后导出 CSV
python3 scripts/export_csv.py 收藏.json -o 收藏.csv --exclude-author 你的昵称

# 把已分类 JSON 渲染成报表
python3 scripts/build_report.py classified.json -o 收藏夹整理分析.xlsx
```

`classified.json` 的格式见 `references/classification.md` 末尾。

## 依赖

- Python 3 + `openpyxl`
- 浏览器采集需要 agent 环境内置的 Browser Use（mac，`plane="bu"`）
- 每日推送用 agent 的定时任务能力

## 说明

- 只在你自己已登录的浏览器里读你的收藏页，不调用任何需签名的私有接口。
- 分类基于标题语义，标题信息不足的笔记会被放进"待确认"而不是强行归类。
