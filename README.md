# AwayGuard

一个可切换模式的 Windows 桌面小工具：离开电脑后检测输入活动、发出警告，并在本地记录时间和应用活动；也可读取 Windows 的锁屏、解锁和交互式登录审计事件。

**支持 Windows 10 / 11、Python 3.10+（包含 Tkinter）。界面图片缩放使用 Pillow。**

## 功能

| 模式 | 记录内容 | 警告方式 |
| --- | --- | --- |
| 桌面监控 | 鼠标或键盘活动摘要、前台进程名/PID/窗口句柄变化 | 当前桌面弹窗，可选系统提示音 |
| 锁屏审计 | 4800 锁屏、4801 解锁、4624/4625 交互式登录成功/失败、1102 安全日志清空 | 捕获本会话解锁事件后，待桌面可访问时弹窗 |
| 双模式 | 同时启用以上功能 | 同上 |

还提供 3–120 秒离开倒计时、立即锁屏、自定义声音和黑白警示图片。主页面隐藏日志，点击“查看操作记录”可在独立窗口查看最近 500 条日志、双击查看详情或导出全部 CSV；关闭记录窗口不会停止监控。停止后可重新选择模式。软件始终以可见桌面程序运行，最小化后继续监控；关闭后停止。

## 快速开始

### 普通用户：双击运行，无需 Python

从本仓库的 **Releases** 下载 `AwayGuard-Windows-x64.zip`，解压后双击 `AwayGuard.exe`。适用于 Windows 10/11 x64，不需要输入命令、安装 Python 或安装依赖。默认图片和 03 警告音已内置。需要读取系统登录记录时，右键 EXE，选择“以管理员身份运行”；系统审计仍需要按下文配置。

首次发布完成之前，Releases 中尚无下载包。开发者可以按下方的一键构建方式生成。

### 源码运行

在仓库目录打开 PowerShell：

```powershell
python -m pip install .
python -m awayguard
```

也可以双击 `start.bat`。如果没有 Python，请先安装包含 Tcl/Tk 的 Windows Python，并把 Python 加入 PATH。

1. 选择模式和离开倒计时。
2. 点击 **我离开了 · 开始监控**。
3. 默认倒计时 10 秒，逐秒显示；结束后主窗口自动最小化，桌面检测开始建立输入基线。之后检测到鼠标或键盘活动，会恢复主页面、弹出警告并播放声音。倒计时中点击停止会取消自动最小化。审计连接立即启动，只读取首次成功连接之后的事件；仅锁屏审计模式仍只在本会话解锁时触发警告。
4. 需要锁屏时点击 **立即锁屏** 或按 `Win + L`。锁屏按钮本身不启动监控。
5. 弹出警告后，每次鼠标或键盘活动都会重新计算空闲时间。连续 10 秒没有新活动，主页面会再次最小化，同时关闭警告弹窗、收起记录窗口并停止当前声音；监控继续运行。再次操作时重新弹出，如此循环，直到点击 **我回来了 · 停止监控**。这 10 秒空闲时间固定，不受首次离开倒计时设置影响。

程序无法判断使用者是不是机主，你返回时也会触发警告。桌面输入每 0.5 秒轮询，活动摘要最多每 10 秒一条。每次检测到新的输入活动都会尝试发出声音：正在播放时不打断、不叠加，也不排队；播放结束后检测到新活动就重新播放，没有 60 秒冷却。没有新活动时不会自行循环播放。关闭警告弹窗不影响后续声音。输入后的 15 秒内记录采样到的前台窗口变化；短暂窗口可能被漏过。审计约每 5 秒查询一次，每次最多 200 条，后续继续读取积压记录。

## 自定义警告声音

默认声音为项目自带的 `awayguard/assets/03.wav`，复制自用户提供的 `F:\project1\alarm\03.wav`，无需原文件夹即可播放。在主界面点击 **选择自定义 WAV**，选择一个非空的 **PCM WAV** 文件，再点 **试听**。可点击 **停止播放** 结束音频，或点击 **恢复默认警告音** 重新使用 03。此前保存的自定义音频仍保留。取消“声音警告”仅关闭自动警告音，仍可手动试听。

音频路径和声音开关自动保存在 `%LOCALAPPDATA%\AwayGuard\sound-settings.json`，重启后保留。音频不会复制到仓库，请保留原文件位置。文件被移动、删除或播放失败时，会尝试系统提示音并显示错误；监控和弹窗继续工作。停止监控、关闭程序或更改声音设置会停止当前音频。

目前支持 PCM `.wav`，不直接支持 MP3 / M4A；仅修改文件后缀不能转换格式，请先用音频工具导出为 PCM WAV。

## 开启锁屏 / 登录审计

Windows 默认可能不产生所需事件，且读取 Security 日志通常需要管理员权限。**“已连接”只表示读取权限正常，不代表审计策略已开启。** 软件不会自动提权或修改系统策略。

如需要配置，在管理员 PowerShell 中进入仓库目录，明确执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\enable-audit.ps1
python -m awayguard
```

配置脚本先把当前完整审计策略备份到 `%LOCALAPPDATA%\AwayGuard\audit-policy-<随机标识>.csv`，然后开启：

- **审核登录 / Audit Logon**：成功、失败。
- **审核其他登录/注销事件 / Audit Other Logon/Logoff Events**：成功。

脚本使用子类别 GUID，不依赖 Windows 显示语言。域策略或单位管理策略可能覆盖本地设置。若脚本中途失败，应根据输出检查已应用设置。需要恢复时，使用脚本打印的 `auditpol /restore` 命令；该命令恢复的是整个备份策略，应避免覆盖后来有意做出的其他策略修改。

也可在本地安全策略的“高级审核策略配置 → 系统审核策略 → 登录/注销”中手动配置。配置后先停止旧实例，再用管理员终端启动，以避免同会话重复实例。

**锁屏界面无法显示本程序的自定义警告，也不能读取该界面的鼠标/按键操作。** 登录失败是否产生事件取决于 Windows 登录方式与策略，并非所有 PIN / Windows Hello 失败都会产生可读取的 4625。安全事件覆盖本机所有会话，详情标注此范围；解锁弹窗仅针对程序所在会话。桌面监控只覆盖运行程序的会话。

参考：[Windows 4801 解锁事件](https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-10/security/threat-protection/auditing/event-4801)、[GetLastInputInfo 的会话范围](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getlastinputinfo)。

## 日志与记录边界

- SQLite 日志位于 `%LOCALAPPDATA%\AwayGuard\events.sqlite3`，时间以 UTC 保存，界面和 CSV 同时提供带时区的本地时间。
- 不采集具体按键、密码、剪贴板、截图、网页 URL、窗口标题或文件内容；没有联网、上传或远程控制功能。
- “操作”指输入活动、前台应用变化及系统审计事件，不代表完整点击步骤或文件操作记录，也不能证明操作者身份。
- 日志是普通本地文件，没有加密或防篡改保护；同账户用户或管理员可以停止程序、删除或修改记录。实际防止使用电脑请锁屏并设置可靠的账户验证。
- 不自动启动、不作为服务运行。关机、注销或进程退出后不继续采集；睡眠期间不轮询，恢复后仍运行时可读取保留的审计积压。
- 每次启动监控以当前 Security 最新记录为基线，不回填停机期间的记录。日志权限首次恢复时也建立新基线；权限故障前已有基线时会尝试继续读取。
- 日志序号回退会记录重置提示，但日志清空、覆盖或大量积压可能造成无法恢复的缺口。本工具不保证完整取证。
- 本地日志不会自动清理；长期使用请留意磁盘空间。关闭程序后可删除日志文件及同目录的 `-wal` / `-shm` 文件来清空记录。
- `.gitignore` 排除了数据库、CSV、构建产物和 Python 缓存，避免把个人活动日志上传 GitHub。

## 测试与打包

本地一键打包：双击仓库根目录的 `build.bat`。构建电脑需要 Python 和网络；脚本会创建独立的 `.build-venv`、安装构建依赖、运行测试并生成 EXE 和 ZIP。构建完成后，日常使用只需双击 `dist\AwayGuard.exe`。

```powershell
python -m unittest discover -s tests -v
python -m compileall -q awayguard
```

自动化测试覆盖输入节流、计时器回绕、窗口活动筛选、审计 XML、登录类型过滤、游标分页/重置/读取失败及日志持久化/CSV 导出。

生成独立 EXE（仅构建时需要第三方依赖）：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install . pyinstaller==6.16.0
.\scripts\build.ps1
```

产物是 `dist\AwayGuard.exe`、`dist\AwayGuard-Windows-x64.zip` 和 `dist\SHA256SUMS.txt`。ZIP 中含 EXE、说明文档、素材来源和审计配置脚本。EXE 未签名，Windows 可能显示 SmartScreen 提示。需要审计权限时使用“以管理员身份运行”。

### GitHub 网页一键构建与发布

上传仓库后，无需在自己的电脑上安装构建工具：

1. 打开仓库 **Actions → Windows checks → Run workflow**。
2. 等待测试和构建成功，在该次运行的 **Artifacts** 中下载 `AwayGuard-Windows`。
3. 解压下载包，再解压其中的 `AwayGuard-Windows-x64.zip`，双击 EXE 即可运行。

正式发布给其他人：在仓库 **Releases → Draft a new release** 中选择版本标签（例如 `v0.1.0`）并发布。发布事件会自动运行测试、构建并将 ZIP 和校验文件附加到该 Release；构建完成前不会出现 EXE 下载包。用户只需在 Releases 下载，无需查看源码或使用命令行。仓库需启用 Actions；若组织策略禁止工作流写入 Releases，上传附件步骤会失败，可从 Actions 下载产物后手动附加。

普通推送和 PR 只运行检查，不自动发布。Windows 桌面监控需要在用户电脑本地运行，不能通过 GitHub Pages 网页部署来监控 Windows 输入。

### 手动验收

1. 桌面模式，倒计时结束后不操作，确认无输入警告；移动鼠标，确认弹窗与活动日志。
2. 切换记事本和资源管理器，确认进程记录；确认不记录输入文字或窗口标题。
3. 停止后确认不再采集；重新开始不会把旧记录误报成新活动。
4. 普通权限运行双模式，若无法读 Security，应看到权限错误，桌面检测仍可工作。
5. 管理员配置审计并启动双模式，锁屏再解锁，确认 4800/4801 时间与系统事件查看器一致，以及解锁后的警告。
6. 导出 CSV，确认中文、时间和历史记录正常；关闭再启动，确认历史保留。

## 仓库结构

```text
awayguard/
  __main__.py    Tkinter 界面、日志展示和警告
  windows.py     Win32 输入/进程/桌面/锁屏接口
  monitor.py     后台监控与输入节流
  events.py      Windows Security XML 查询和游标
  storage.py     SQLite 与 CSV
scripts/        审计配置和 EXE 打包
tests/          标准库 unittest 测试
.github/        Windows CI 与手动构建
```

## 上传到 GitHub

本目录可直接作为独立仓库使用。先在 GitHub 创建一个空仓库，然后替换下面的账号和仓库地址：

```powershell
git add .
git commit -m "Initial AwayGuard implementation"
git remote add origin https://github.com/YOUR_USERNAME/AwayGuard.git
git push -u origin main
```

如果 Git 尚未配置提交身份，先配置自己的 `user.name` 和 `user.email`。不要把个人日志或审计备份强制加入版本控制。

## License

代码使用 [MIT](LICENSE)。主页面的电影图片不属于 MIT 授权范围，尚未确认再分发授权；公开上传 GitHub 或分发包含图片的 EXE 前需获得授权或替换图片。图片来源见 [SOURCE.md](awayguard/assets/SOURCE.md)。删除该图片后，程序会显示文字占位提示。
