# OpenClaw Browser Pack

这个目录是给旧版浏览器扩展接入链准备的快速配置包。

## 作用

用于在另一台 Windows 电脑上快速恢复这套浏览器 relay / extension 配置，包括：

- 浏览器扩展目录
- `my-chrome` browser profile 写入
- 启动 relay 的脚本
- 打开扩展目录的脚本

## 使用方式

1. 先确保目标电脑已经安装：
   - `OpenClaw / clawdbot`
   - `Google Chrome`
2. 运行：
   - `setup-openclaw-browser.cmd`
3. 在 Chrome 里手动加载已解压扩展
4. 再运行：
   - `start-openclaw-browser.cmd`
5. 在扩展设置里填写：
   - `Port: 18792`
   - `Gateway token: %USERPROFILE%\\.openclaw\\openclaw.json` 里的 `gateway.auth.token`

## 兼容性说明

这套包不是所有 OpenClaw 版本都通用。

它更适合这些情况：

- 本机已经可以执行 `clawdbot`
- 当前版本仍然保留旧的 browser extension / relay 接入链
- `~/.openclaw/openclaw.json` 仍然使用当前这套配置结构

它不一定适合这些情况：

- 新版本已经完全迁移到 `existing-session`
- 旧的 extension driver 已经被移除
- browser profile 或 relay 配置结构已经变化

一句话：

- 这套包适合“旧扩展接入链恢复”
- 不保证对所有 OpenClaw 版本都直接可用

## 备注

Chrome 的“加载已解压扩展程序”这一步仍然需要人工点击，脚本不能完全替代。
