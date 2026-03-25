# 爬取小蜥蜴

`爬取小蜥蜴` 是一个面向 `OpenClaw` 使用场景的本地批量抓取工具。

当前版本支持：
- URL 列表批量抓取
- 关键词搜索后自动展开帖子链接再抓取
- 保存到本地目录
- 写入飞书文档
- 浏览器 relay / extension 配置包

## 当前支持

### 站点

- `ChaseDream`
  - `https://www.chasedream.com/article/<id>`
  - 支持正文和评论抓取
- `1point3acres`
  - `https://www.1point3acres.com/home/pins/<id>`
  - 当前走浏览器 relay 专用抓取链

### 本地导出格式

- `json`
- `html`
- `docx`
- `pdf`

### 飞书写入模式

- 写入已有飞书文档
- 自动创建一篇新的飞书文档并持续写入

## 目录说明

- [batch_chasedream_scraper.py](D:/openclaw/爬取小蜥蜴/batch_chasedream_scraper.py)
  - 主抓取脚本
- [server.py](D:/openclaw/爬取小蜥蜴/server.py)
  - 本地网页交互界面
- [feishu_doc_helper.cjs](D:/openclaw/爬取小蜥蜴/feishu_doc_helper.cjs)
  - 飞书文档创建与追加写入 helper
- [openclaw-browser-pack](D:/openclaw/爬取小蜥蜴/openclaw-browser-pack)
  - 浏览器 relay / 扩展快速配置包

## Browser Pack

仓库里已经包含一套浏览器配置包：
- [openclaw-browser-pack](D:/openclaw/爬取小蜥蜴/openclaw-browser-pack)

这个包适合：
- 机器上已经安装 `clawdbot`
- 当前版本仍保留旧 `browser extension / relay` 接入链
- 仍使用当前这套 `~/.openclaw/openclaw.json` 配置结构

这套包不保证适用于所有 OpenClaw 版本。
如果版本已经完全切到 `existing-session`，或者移除了旧扩展驱动，就不一定能直接用。

更详细的兼容性说明见：
- [openclaw-browser-pack/README.md](D:/openclaw/爬取小蜥蜴/openclaw-browser-pack/README.md)

## 运行环境

- Windows
- Python 3.12
- Node.js
- 如果需要导出 `docx` 或 `pdf`
  - 本机需要安装 `Microsoft Word`
- 如果需要抓取 `1point3acres home/pins`
  - 本机需要已配置好 `OpenClaw`
  - Chrome 需要安装并启用 `OpenClaw Browser Relay`

## OpenClaw / Chrome Relay 前置条件

抓取 `1point3acres home/pins` 之前，需要先完成这些准备：

1. 本机 `OpenClaw Gateway` 可用
2. Chrome 已加载 `OpenClaw Browser Relay`
3. 扩展已配置本地 relay 端口和 gateway token
4. 如果是浏览器接管模式
   - 当前标签页需要允许 remote debugging
   - 扩展图标应显示 `ON`

## 网页界面启动

直接双击：

```text
start_ui.cmd
```

或者手动运行：

```powershell
python server.py
```

启动后打开：

```text
http://127.0.0.1:8765/
```

## 网页界面功能

网页界面支持：
- 粘贴 URL 列表
- 上传 `txt/csv` 文件
- 输入关键词
- 勾选关键词搜索站点
- 设置每站抓取上限
- 查看 OpenClaw Frontend / Gateway 状态
- 选择输出模式

## 输出模式

当前前端已经把“本地导出”和“飞书写入”拆开了。

### 1. 保存到本地目录

只有勾选 `保存到本地目录` 时，才会：
- 使用 `Output Folder`
- 使用 `HTML / JSON / DOCX / PDF` 这些格式选项

### 2. 写入飞书文档

只有勾选 `写入飞书文档` 时，才会使用飞书相关输入框。

支持两种方式：
- 写入已有文档
  - 在 `Feishu Doc URL / Token` 填已有文档链接或 `doc_token`
- 自动创建新文档
  - 留空 `Feishu Doc URL / Token`
  - 在 `Feishu Folder URL / Token` 填目标文件夹
  - 脚本会自动创建一篇新文档，并把所有帖子写到同一篇里

### 3. 组合使用

- 只勾 `保存到本地目录`
  - 只导出本地文件
- 只勾 `写入飞书文档`
  - 只写飞书，不落本地文件
- 两个都勾
  - 同时保存本地和写入飞书

## 关键词模式

关键词模式会先搜索，再自动展开成帖子链接，然后按普通 URL 模式批量抓取。

### 当前实现

- `ChaseDream`
  - 优先通过搜索结果展开 `article/<id>` 链接
- `1point3acres`
  - 优先通过站内搜索结果展开 `home/pins/<id>` 链接
  - 再通过 Chrome relay 自动打开并抓取

## 飞书文档格式

飞书文档当前规则：
- 只有 `正文：` 和 `评论内容：` 使用二级标题
- 其它字段都用普通文本段落
- 评论与评论之间使用
  - `------------------------------------`
- 帖子与帖子之间使用
  - `===========================================`

## 当前已实现的输出规则

- 只保留你勾选的本地格式
- 只选飞书时，不会默认落本地文件
- Word / PDF 样式尽量接近飞书文档风格
- `1point3acres` 正文会清洗页面壳子噪音
  - 如 `来自APP`
  - 楼层数字
  - `回复 / 分享 / 道具`

## 已知限制

- `1point3acres` 当前稳定支持 `home/pins/<id>`
- `1point3acres` 依赖浏览器 relay，不是纯 HTTP 抓取
- 如果 Chrome 没有成功附着 relay，抓取会失败
- 关键词模式下，搜索结果数量仍可能受站点搜索和页面结构影响
- `docx` / `pdf` 导出依赖本机 Word COM
- 飞书写入依赖本机 OpenClaw 中已配置可用的飞书应用
