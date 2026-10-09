# 安装到 Codex

统一安装器会安装技能本体、缺少的基础工具、独立 Python 环境和中文字体，再检查实际渲染与编码。它不需要 API key，不读取账号凭证，不上传音色。

## 推荐：把这段发给 Codex

```text
请安装 https://github.com/shao60533/industry-chain-3d-video-sop 为 industry-chain-3d-video 技能。
读取仓库根目录 SKILL.md，运行统一安装入口，复用已有依赖，安装缺少的 Blender、FFmpeg、Python 环境与中文字体。
运行实际渲染/编码自检；失败就修复或报告具体缺口，不把仅下载文档当安装成功。
不读取或上传个人录音、账号配置、token 和 API key。
```

Codex 可先下载仓库到临时目录，macOS/Linux 执行 `bash install.sh`，Windows 执行 `./install.ps1`。如通过 Codex 技能安装器先下载根目录技能，随后在该技能目录运行 `python3 scripts/setup.py`（Windows 使用合适的 Python 命令）即可原地配置。

## 终端一条命令

macOS、Debian、Ubuntu：

```bash
curl -fsSL https://raw.githubusercontent.com/shao60533/industry-chain-3d-video-sop/main/install.sh | bash
```

Windows PowerShell：

```powershell
& ([scriptblock]::Create((Invoke-RestMethod https://raw.githubusercontent.com/shao60533/industry-chain-3d-video-sop/main/install.ps1)))
```

脚本从公开仓库下载完整技能包，校验压缩包路径后安装。指定发布版本时，设置 `VIDEO_SOP_REF` 为标签或完整提交 SHA。入口脚本 URL 也可把 `main` 换成同一标签/SHA。

## 安装内容

| 内容 | 安装方式 |
|---|---|
| Codex 技能 | 默认 `${CODEX_HOME:-~/.codex}/skills/industry-chain-3d-video`；支持自定义目录 |
| Python | 需要 3.11+；已有版本复用，缺失由 Homebrew/apt/winget 准备 |
| Blender | 复用 3.6+；缺失时 macOS 用 Homebrew，Linux x64 / Windows x64、ARM64 下载官方 4.5.14 LTS 便携版并核 SHA256 |
| FFmpeg / ffprobe | 复用可运行版本；缺失通过 Homebrew、apt 或 winget 安装，最后验证 H.264/AAC 实际能力 |
| Pillow | 固定 12.3.0，仅安装在技能的 `.venv`，不修改系统 Python 包 |
| 中文字体 | 固定 Noto Sans CJK SC 原件和 SHA，下载 OFL 许可到本地字体目录；可指定已有字体 |
| 自检 | 中文字形、CPU 渲染、工程重开、24帧 H.264/AAC 编码、BT.709 标记与全解码 |

包管理器可能需要操作系统管理员权限。安装器不接收或保存管理员密码；没有权限时报告缺口。Homebrew 的初次安装需按其系统要求完成，Linux 非 root 用户可能收到正常 sudo 提示。Windows 的 FFmpeg/Python 安装依赖 App Installer（winget）。

## 支持与验证范围

- macOS：Apple Silicon 实机验证过完整安装、重复安装、Blender 4.5.14 与 FFmpeg 8.1 的真实渲染/编码；Intel 由 Homebrew 当前支持范围决定。
- Linux：Debian/Ubuntu 自动依赖安装；Python 应为3.11+，官方便携 Blender 下载支持 x64。Linux ARM64 和其他发行版可配置现有工具后使用 `--skip-system-deps`。
- Windows：PowerShell 入口、winget 依赖和官方便携 Blender；不配置额外模型或账号。代码与跨平台行为测试进入 CI，完整 Windows 渲染安装尚未在本次实机验证。

Blender 与 FFmpeg 来自各自维护者和包管理器；其许可独立于本仓库 MIT。下载来源见 [Blender LTS](https://www.blender.org/download/LTS/)、[Homebrew Blender](https://formulae.brew.sh/cask/blender)、[Homebrew FFmpeg](https://formulae.brew.sh/formula/ffmpeg)、[Noto CJK](https://github.com/notofonts/noto-cjk)。这些依赖不会作为二进制文件提交本仓库。

## 已有工具或自定义目录

在下载的仓库根目录执行：

```bash
bash install.sh --dest ./local-skill --skip-system-deps
bash install.sh --dry-run
```

Windows 对应参数为 `-Dest ./local-skill -SkipSystemDeps`、`-DryRun`。默认仍会建立独立 Python 环境、获取字体并自检；`--skip-system-deps` 只表示不修改系统软件，缺失依赖会明确失败。`--no-smoke` / `-NoSmoke` 仅检查环境，不执行实际渲染。测试报告据此记录实际范围。

可通过本地环境变量指定工具文件：`VIDEO_SOP_PYTHON`、`VIDEO_SOP_BLENDER`、`VIDEO_SOP_FFMPEG`、`VIDEO_SOP_FFPROBE`、`VIDEO_SOP_FONT`。变量取文件路径，不填密钥；不需要公开配置。

重复安装会更新本安装器管理的文件，保留 `.venv`、`.local` 和自己的生产任务。未知目录和符号链接不会被直接覆盖；不用通过删除其他技能来解决冲突。

在途任务另锁Workflow实现/规范的policy_sha256；安装更新不会改旧job或迁移旧批准。需继续在途任务时使用原固定提交/技能副本，不能编辑pin绕过。新任务使用新规范，见[统一Workflow](codex-workflow.md)。状态/证据核心只需Python标准库，可先验证代码；基础渲染自检与真实成片验收仍分开。

## 安装后

技能在下一个 Codex 回合可用，使用：

```text
使用 $industry-chain-3d-video，先检查环境，再根据我指定的完整原稿制作一期产品拆解视频的稿件和样片。
```

在技能目录内可复查并建立新任务：

```bash
.venv/bin/python scripts/doctor.py --smoke-test
.venv/bin/python scripts/init_job.py --output ./jobs/my-first-product
.venv/bin/python scripts/workflow.py --job ./jobs/my-first-product status
```

Windows 把 `.venv/bin/python` 换成 `.venv\Scripts\python.exe`。新目录默认 `produce_only`，原始来源、音色、账号和验收由本次任务实际填写；不会发布。

本机可执行文件与字体的绝对路径只保存在 `.local/environment.json`；`.local/doctor.json` 是不含私人路径的摘要。两个目录和生产任务均被忽略，不推送公开仓库。环境自检通过不等于成片验收通过，GPU、配音服务、对齐工具与发布适配需要本次任务另行配置和验证。
