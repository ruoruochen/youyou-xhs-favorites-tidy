# 小红书收藏夹采集 · 执行细节

在 `mac_computer_use_tool`（`plane="bu"`，`import seed_browser_use as bu`）里完成本流程。

## 1. 页面与 URL

- 收藏夹地址：`https://www.xiaohongshu.com/user/profile/{user_id}?tab=fav&subTab=note`
- 首屏一进来会渲染一批 `section.note-item`；其余靠滚动懒加载。
- 页面是**虚拟滚动**：离屏卡片节点会被移除回收，DOM 里任何时刻只保留附近几十张。因此必须边滚边存、按 `note_id` 去重，不能等"全部加载完再一次性读 DOM"。

## 2. 登录检查与交接

- 判断未登录：URL 变成 `/login?redirectPath=...`、出现二维码/手机号登录框、或收藏区显示"该用户已设置收藏内容不可见"。
- 处理：直接调用 `interaction.request_action(type="browserControl", display_message=...)`，让用户扫码；交还后 `bu.resync()` 再重新导航到收藏夹。
- 不要读取/输入密码、验证码，不要尝试绕过登录。

## 3. 提取脚本 extract_js

把下面整段作为字符串传给 `bu.js(...)`，返回当前可见卡片数组：

```javascript
(() => {
  const abs = (u) => { try { return new URL(u, location.origin).href; } catch(e){ return u; } };
  const rows = [];
  document.querySelectorAll('section.note-item').forEach(s => {
    const noteId = s.getAttribute('data-note-id') || '';
    const coverA    = s.querySelector('a.cover');
    const coverImg  = s.querySelector('a.cover img');
    const titleA    = s.querySelector('a.title');
    const authorA   = s.querySelector('a.author');
    const avatarImg = s.querySelector('img.author-avatar');
    const nameEl    = s.querySelector('span.name');
    const countEl   = s.querySelector('span.count');
    rows.push({
      note_id: noteId,
      cover_href:     coverA   ? abs(coverA.getAttribute('href')) : '',
      note_link:      noteId   ? abs('/explore/' + noteId) : '',
      cover_src:      coverImg ? coverImg.getAttribute('src') : '',
      title:          titleA   ? titleA.innerText.trim() : '',
      author_href:    authorA  ? abs(authorA.getAttribute('href')) : '',
      author_avatar:  avatarImg? avatarImg.getAttribute('src') : '',
      name:           nameEl   ? nameEl.innerText.trim() : '',
      like_count_text: countEl ? countEl.innerText.trim() : '',
    });
  });
  return rows;
})()
```

### 字段与选择器速查

| 字段 | 选择器 | 说明 |
|---|---|---|
| note_id | `section.note-item` 的 `data-note-id` | 去重主键 |
| 帖子链接 | `a.cover` 的 href | 规范链接另由 note_id 拼 `/explore/{id}` |
| 封面图 | `a.cover img` 的 src | |
| 标题 | `a.title span` 的 innerText | |
| 作者主页 | `a.author` 的 href | |
| 作者头像 | `img.author-avatar` 的 src | |
| 作者名 | `span.name` 的 innerText | |
| 点赞数 | `.like-wrapper span.count` 的 innerText | 文本：`6233`/`1.4万`/`10万+` |

> 选择器随前端改版可能漂移；若某列恒为空，先 `bu.screenshot()` + 打印第一张卡片 `outerHTML` 重新校准。

## 4. 真实滚轮滚动累积（核心，别用 window.scrollTo）

在一个 bu cell 里循环。`bu.scroll` 是 CDP 真实滚轮输入，能触发页面的 IntersectionObserver 懒加载；`window.scrollTo` 不会触发、还会因虚拟回收导致漏抓。

```python
import time, json
store = {}
def collect():
    n = 0
    for r in bu.js(EXTRACT_JS):           # EXTRACT_JS 即上面整段
        if r.get('note_id') and r['note_id'] not in store:
            store[r['note_id']] = r; n += 1
    return n

collect()                                  # 首屏
stale = 0
for i in range(60):
    bu.scroll(500, 500, "down", amount=2) # 视口中央向下滚；amount=2 步小、视野重叠防漏
    time.sleep(1.7)
    new = collect()
    m = bu.js("return {sy:window.scrollY, sh:document.documentElement.scrollHeight, ih:window.innerHeight};")
    bottom = (m['sy'] + m['ih'] >= m['sh'] - 80)
    if bottom:
        time.sleep(2.0); new += collect()
        stale = stale + 1 if new == 0 else 0
        if stale >= 6: break              # 到底且连续无新增
    else:
        stale = 0

rows = list(store.values())
json.dump(rows, open('/tmp/xhs_fav.json','w'), ensure_ascii=False)
```

要点：步长小（amount=2）、每步等待约 1.7s、按 `note_id` 去重、连续多轮无新增才停。

## 5. 计数差异（重要认知）

- 收藏区 tab 显示"笔记·N"，但抓到的有效条数 M 通常 < N。差额来自已被作者删除/设私/下架的笔记——它们仍计入历史计数，却不再渲染。
- 这不是漏抓。判断抓全的信号：连续滚到底无新增；可选下面第 6 节用接口钩子确认 `has_more=false`。

## 6.（可选）CDP 钩子核验是否到底

不直接调接口（需签名会 406），而是让页面自己请求、我们旁路记录：

```python
hook = """/* 见下方：hook fetch 与 XHR，把含 /note/collect/page 的响应存到 window.__cap */"""
bu.cdp("Page.addScriptToEvaluateOnNewDocument", source=hook)   # 注意 bu.cdp 的关键字传参形式
bu.navigate("reload"); bu.wait_for_load(); time.sleep(4)
# 然后照常滚动；滚动后读 window.__cap，解析每页 data.notes 与 data.has_more / data.cursor
```

hook 内容：重写 `window.fetch` 与 `XMLHttpRequest.open/send`，把 URL 含 `/note/collect/page` 的响应文本 push 进 `window.__cap.push({u, b})`。最后 `bu.js("return window.__cap")` 拿回，解析每页 notes 数与 `has_more`，与 DOM 抓取结果交叉核对。

## 7. 导出

```bash
python3 scripts/export_csv.py /tmp/xhs_fav.json -o 小红书收藏夹.csv
```

脚本做：按 note_id 去重、解析点赞数文本为数值、输出 UTF-8-BOM CSV、可选剔除指定作者（自己的笔记）。
