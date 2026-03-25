# 爬取小蜥蜴

`爬取小蜥蜴` 是一个面向 `OpenClaw` 使用场景的本地批量抓取工具。

当前版本提供两种使用方式：

- 网页交互界面：启动后在浏览器里选择链接、输出目录和导出格式
- 命令行批量模式：读取 `txt` 链接清单，按批次抓取并导出

## 当前支持

- `ChaseDream`
  - `https://www.chasedream.com/article/<id>`
  - 支持正文和评论抓取
- `1point3acres`
  - `https://www.1point3acres.com/home/pins/<id>`
  - 当前走浏览器 relay 专用抓取路径
  - 需要目标页面先在 Chrome 中打开并附着到 OpenClaw Browser Relay

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
4. 目标帖子已经在 Chrome 中打开
5. 已点击扩展图标，让当前标签页显示 `ON`

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

## 输入格式

输入文件是一行一个链接，例如：

```text
https://www.chasedream.com/article/18692
https://www.1point3acres.com/home/pins/1169843
```

脚本读取文件时支持 `utf-8` 和 `utf-8-sig`。

## 输出格式

支持这些导出格式：

- `json`
- `html`
- `docx`
- `pdf`

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

- 关键词批量搜索后自动抓取
- 扩展更多站点适配器
- 将结果自动写入飞书文档
- 增加历史任务列表和抓取进度展示
