# 爬取小蜥蜴

`爬取小蜥蜴` 是一个面向 `OpenClaw` 使用场景的本地批量抓取工具。

当前版本提供三种能力：

- 直接输入 URL 列表后批量抓取
- 在网页交互界面里选择输出目录和导出格式
- 输入关键词后，自动搜索、展开帖子链接，再批量抓取

## 当前支持

### 站点

- `ChaseDream`
  - `https://www.chasedream.com/article/<id>`
  - 支持正文和评论抓取
- `1point3acres`
  - `https://www.1point3acres.com/home/pins/<id>`
  - 当前走浏览器 relay 专用抓取路径
  - 需要目标页面先在 Chrome 中打开，或允许脚本通过 relay 自动打开页面

### 导出格式

- `json`
- `html`
- `docx`
- `pdf`

## 目录说明

- [batch_chasedream_scraper.py](D:/openclaw/爬取小蜥蜴/batch_chasedream_scraper.py)
  - 主抓取脚本
- [server.py](D:/openclaw/爬取小蜥蜴/server.py)
  - 本地网页交互界面
- [start_ui.cmd](D:/openclaw/爬取小蜥蜴/start_ui.cmd)
  - 启动网页交互界面
- [run_batch.cmd](D:/openclaw/爬取小蜥蜴/run_batch.cmd)
  - 启动命令行交互模式
- [interactive_launcher.ps1](D:/openclaw/爬取小蜥蜴/interactive_launcher.ps1)
  - 命令行交互启动脚本
- [urls.txt](D:/openclaw/爬取小蜥蜴/urls.txt)
  - 示例输入文件

## 运行环境

- Windows
- Python 3.12
- 如果需要导出 `docx` 或 `pdf`
  - 本机需要安装 Microsoft Word
- 如果需要抓取 `1point3acres home/pins`
  - 本机需要已经配置好 `OpenClaw`
  - Chrome 需要安装并启用 `OpenClaw Browser Relay`

## OpenClaw / Chrome Relay 前置条件

抓取 `1point3acres home/pins` 之前，需要先完成下面这些准备：

1. 本机 `OpenClaw Gateway` 可用
2. Chrome 已加载 `OpenClaw Browser Relay`
3. 扩展已经配置好本地 relay 端口和 gateway token
4. 如果是手动模式
   - 目标帖子已经在 Chrome 中打开
   - 当前标签页已经点击扩展图标，显示 `ON`
5. 如果是关键词模式
   - relay 正常即可，脚本会尝试自动打开结果页

如果 relay 没有附着成功，抓取器会提示你先打开页面并挂接当前标签页。

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

网页界面支持：

- 粘贴 URL 列表
- 上传 `txt/csv` 文件
- 输入关键词
- 勾选关键词搜索站点
- 设置每站抓取上限
- 选择输出目录
- 选择输出格式：`html` / `json` / `docx` / `pdf`
- 查看 OpenClaw Frontend / Gateway 状态

## 命令行模式启动

直接双击：

```text
run_batch.cmd
```

或者手动运行：

```powershell
python batch_chasedream_scraper.py --input urls.txt --output "D:\openclaw\文案内容" --formats html,json,pdf
```

## 输入 URL 模式

输入文件是一行一个链接，例如：

```text
https://www.chasedream.com/article/18692
https://www.1point3acres.com/home/pins/1169843
```

脚本读取文件时支持：

- `utf-8`
- `utf-8-sig`

## 关键词模式

关键词模式会先搜索，再自动展开成帖子链接，然后按普通 URL 模式批量抓取。

### 当前实现

- `ChaseDream`
  - 通过站点搜索结果页展开 `article/<id>` 链接
- `1point3acres`
  - 通过站点限定搜索展开 `home/pins/<id>` 链接
  - 再通过 Chrome relay 自动打开并抓取

### 网页界面使用方式

1. `URL List` 可以留空
2. 在 `Keyword Mode` 输入关键词
3. 勾选要搜索的站点
4. 设置 `Keyword Limit / Site`
5. 选择输出格式
6. 点击 `Start`

### 命令行使用方式

```powershell
python batch_chasedream_scraper.py ^
  --input urls.txt ^
  --output "D:\openclaw\文案内容" ^
  --formats json,html ^
  --keyword "MBA" ^
  --keyword-sites chasedream,1point3acres ^
  --keyword-limit 10
```

说明：

- `--keyword`
  - 关键词文本
- `--keyword-sites`
  - 可选：`chasedream,1point3acres`
- `--keyword-limit`
  - 每个站点最多展开多少条链接

### 结果展示

关键词模式运行时会在结果里显示：

- 当前关键词
- 实际搜索站点
- 实际展开到的链接数量
- 每条被展开出的 URL

## 输出内容结构

导出内容结构统一为：

- 网址
- 标题
- 作者
- 日期
- 正文
- 评论数
- 评论内容

评论内容默认使用这种结构：

```text
-作者：用户名
-发布时间：时间
发布内容：评论正文
------
```

## 目前已实现的输出规则

- 只保留你勾选的导出格式
- 不再默认保留中间 HTML 文件
- Word / PDF 样式尽量接近飞书文档风格
- 评论内容之间使用 `------` 分隔

## 已知限制

- `1point3acres` 当前只稳定支持 `home/pins/<id>`
- `1point3acres` 依赖浏览器 relay，不是纯 HTTP 抓取
- 如果 Chrome 没有附着到 relay，脚本会抓取失败
- 关键词模式下，`1point3acres` 的展开结果仍然会受到外部搜索引擎返回质量影响
- 某些评论时间在页面中只显示相对时间，当前会优先尝试抓绝对时间
- `docx` / `pdf` 导出依赖本机 Word COM

## Git 说明

当前仓库已经排除了这些运行时产物：

- `uploads/`
- `out/`
- `__pycache__/`
- `*.pyc`

所以推送到 GitHub 时，默认只会带脚本和说明文件，不会带临时抓取结果。

## 下一步可扩展方向

- 优化关键词模式在中文词上的结果质量
- 扩展更多站点适配器
- 将结果自动写入飞书文档
- 增加历史任务列表和抓取进度展示
