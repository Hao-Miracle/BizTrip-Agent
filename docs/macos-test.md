# macOS 一键测试版

macOS 测试版不需要用户安装 Python 或 Git。下载并解压后，打开 `BizTrip-Agent-Mac.app` 即可启动本地 Web 工作台。

## 下载

1. 打开项目 GitHub 页面的 **Actions**。
2. 选择最新的 **macOS Test Build**。
3. Apple 芯片（M1/M2/M3/M4 等）下载 **BizTrip-Agent-Mac-Apple-Silicon**；Intel 芯片下载 **BizTrip-Agent-Mac-Intel**。
4. 解压 ZIP，得到 `BizTrip-Agent-Mac.app`。

不确定芯片时，点击屏幕左上角 Apple 菜单，选择“关于本机”，查看“芯片”或“处理器”一项。

GitHub Actions 构建产物需要登录 GitHub 才能下载。正式发布时会把经过签名和公证的版本放入 GitHub Release。

## 首次启动

当前测试版尚未进行 Apple 签名和公证。确认文件来自本项目后：

1. 在 Finder 中按住 Control 点击 `BizTrip-Agent-Mac.app`。
2. 选择“打开”，再次确认运行。
3. 浏览器自动打开后，配置邮箱账号和授权码。
4. 填写模型接口地址、API Key 和模型名称。
5. 选择报销日期并开始生成。

程序只绑定 `127.0.0.1`，其他电脑不能访问这个本地页面。

## 文件位置

- 邮箱和模型配置、运行日志：`~/Library/Application Support/BizTripAgent`
- Excel 和凭证原件：`~/Documents/BizTrip Agent`

## 隐私与反馈

- 不要在 Issue 或聊天中发送邮箱授权码和 API Key。
- 测试版使用用户自己的模型接口，模型费用由用户选择的服务商收取。
- 启动失败时，可以检查 `~/Library/Application Support/BizTripAgent/biztrip-agent.log`，发送前先确认其中不含敏感信息。
