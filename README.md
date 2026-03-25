# 爬取小蜥蜴

这是一个给 `OpenClaw` 配套使用的批量抓取工具，当前第一版专门支持 `ChaseDream` 文章页。

## 能力

- 批量读取 URL 列表
- 抓取文章标题、作者、日期、正文
- 抓取全部评论（自动翻分页）
- 输出 `json`、`html`
- 可选输出 `pdf`（Windows + 已安装 Word）

## 使用方式

1. 把链接放到 `urls.txt`
2. 运行：

```powershell
python batch_chasedream_scraper.py --input urls.txt --output "D:\openclaw\文案内容" --pdf
```

或者双击：

```text
run_batch.cmd
```

## 输入格式

一行一个链接，例如：

```text
https://www.chasedream.com/article/18692
https://www.chasedream.com/article/12345
```

## 输出

每篇文章会生成：

- `*_正文评论整理.json`
- `*_正文评论整理.html`
- `*_正文评论整理.pdf`（如果使用 `--pdf`）

另外会生成：

- `batch_index.json`

## 说明

- 当前版本只针对 `https://www.chasedream.com/article/<id>` 这种页面做了适配。
- 如果你后面要抓别的网站，可以继续往脚本里加站点适配器。
