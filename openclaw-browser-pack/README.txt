OpenClaw Browser Pack

这个包用于在另一台 Windows 电脑上快速恢复当前这套浏览器接管配置。

前提：
1. 目标电脑已经安装好 OpenClaw / clawdbot
2. 目标电脑可以正常执行 clawdbot 命令
3. 目标电脑已经安装 Google Chrome

推荐使用顺序：
1. 双击 setup-openclaw-browser.cmd
2. 按脚本提示，在 Chrome 里加载已解压扩展
3. 双击 start-openclaw-browser.cmd
4. 在扩展设置里填：
   Port: 18792
   Gateway token: 读取 %USERPROFILE%\.openclaw\openclaw.json 里的 gateway.auth.token
5. 打开目标网页，点击浏览器工具栏上的 OpenClaw Browser Relay 扩展

说明：
- 这个包会自动写入 browser profile: my-chrome
- 这个包不会覆盖你原有的其他 OpenClaw 配置
- Chrome 的“加载已解压扩展程序”这一步，普通脚本无法替你绕过，仍需要人工点一次
