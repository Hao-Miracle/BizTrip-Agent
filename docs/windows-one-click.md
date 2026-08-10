# Windows 一键测试版

Windows 一键版不需要安装 Python、Git，也不需要打开 PowerShell。测试人员只需下载一个 EXE 文件并双击运行。

## 下载

1. 打开项目 GitHub 页面中的 **Actions**。
2. 选择最新的 **Windows One-Click Build**。
3. 在页面底部下载构建产物 **BizTrip-Agent-Windows**。
4. 解压 ZIP，得到 `BizTrip-Agent-Windows.exe`。

GitHub Actions 构建产物需要登录 GitHub 才能下载。正式发布时，可以把同一个 EXE 添加到 GitHub Release，供测试人员直接下载。

## 首次启动

1. 双击 `BizTrip-Agent-Windows.exe`。
2. Windows SmartScreen 可能提示“Windows 已保护你的电脑”。测试版尚未购买代码签名证书，确认文件来自本项目后，点击“更多信息”再点击“仍要运行”。
3. 等待浏览器自动打开 BizTrip Agent。
4. 按页面指引填写测试人员自己的邮箱和授权码。
5. 填写模型接口地址、API Key 和模型名称。
6. 选择报销日期并点击“开始生成”。

程序只绑定 `127.0.0.1`，其他电脑不能访问这个本地页面。

## 文件位置

- 邮箱配置和运行日志：`%LOCALAPPDATA%\BizTripAgent`
- Excel、审阅报告和凭证原件：`文档\BizTrip Agent`

可以在页面“维护工具”中点击“打开报销文件夹”。

## 停止和再次使用

完成测试后，在页面“维护工具”中点击“安全停止程序”。关闭浏览器标签页本身不会停止后台程序。

再次使用时，重新双击 `BizTrip-Agent-Windows.exe`。邮箱账号只需配置一次，每次重新选择报销日期即可。

## 隐私与反馈

- 不要发送邮箱登录密码、邮箱授权码或 LLM API Key。
- 邮件、配置和报销文件保存在测试人员自己的电脑上。
- 测试版使用测试人员自己的模型接口，模型费用由所选服务商收取。
- 启动失败时，把 `%LOCALAPPDATA%\BizTripAgent\biztrip-agent.log` 发给维护者，并先检查其中是否含敏感信息。
