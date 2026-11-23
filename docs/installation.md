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
| Python | 需要 3.11+；已有版本复用。macOS 缺失时下载固定版本的独立 Python 3.13 到技能目录并核 SHA256；Linux 用 apt，Windows 用 winget |
| Blender | 复用 3.6+；缺失时下载官方 4.5.14 LTS 并核 SHA256：macOS 取官方安装包里的应用放进技能目录，Linux x64 / Windows x64、ARM64 用便携版 |
| FFmpeg / ffprobe | 复用可运行版本；macOS 缺失时下载固定版本的静态构建到技能目录并核 SHA256，Linux 用 apt，Windows 用 winget；最后验证 H.264/AAC 实际能力 |
| Pillow | 固定 12.3.0，仅安装在技能的 `.venv`，不修改系统 Python 包 |
| 中文字体 | 固定 Noto Sans CJK SC 原件和 SHA，下载 OFL 许可到本地字体目录；可指定已有字体 |
| 本地配音（可选） | 加 `--with-voice` 才安装；仅 Apple 芯片 Mac；独立 `.venv-voice`、固定版本依赖和约 6 GB 模型，见[本地配音](local-voice.md) |
| 自检 | 中文实际像素及缺字检查、原始Cycles CPU渲染及非空像素、工程重开、24帧 H.264/AAC 编码、BT.709 标记与全解码 |

macOS 上整个安装不使用 Homebrew，也不需要管理员密码：缺少的 Python、FFmpeg 和 Blender 都下载到技能目录的 `.local/tools`，不改动系统软件；已经装好的 Homebrew 版工具会照常复用。Linux 的包管理器可能需要管理员权限，非 root 用户可能收到正常 sudo 提示。安装器不接收或保存管理员密码；没有权限时报告缺口。Windows 的 FFmpeg/Python 安装依赖 App Installer（winget）。

## 支持与验证范围

- macOS：在一台 Apple Silicon Mac 上，用空白用户目录和最小 PATH（没有 Homebrew，系统 Python 为 3.9）实际跑过一条命令的完整安装和重复安装：独立 Python 3.13.18、Blender 4.5.14、FFmpeg 9.1 均下载到技能目录，真实渲染/编码自检通过，全程没有管理员密码提示。Intel Mac 的下载项已固定版本和 SHA256，但没有实机验证；所用 FFmpeg 构建的维护者已说明 2027 年 1 月起不再提供 Intel 发行版。未装命令行工具的全新系统没有实机验证，只按该情况跳过了系统自带的 python3。
- Linux：Debian/Ubuntu 自动依赖安装；Python 应为3.11+，官方便携 Blender 下载支持 x64。Linux ARM64 和其他发行版可配置现有工具后使用 `--skip-system-deps`。
- Windows：PowerShell 入口、winget 依赖和官方便携 Blender；不配置额外模型或账号。代码与跨平台行为测试进入 CI，完整 Windows 渲染安装尚未在本次实机验证。

Blender 与 FFmpeg 来自各自维护者和包管理器；其许可独立于本仓库 MIT。下载来源见 [Blender LTS](https://www.blender.org/download/LTS/)、[python-build-standalone](https://github.com/astral-sh/python-build-standalone)、[Noto CJK](https://github.com/notofonts/noto-cjk)。macOS 的 FFmpeg 来自 [Martin Riedl 的静态构建](https://ffmpeg.martin-riedl.de/)：这是第三方个人维护的构建，FFmpeg 官方只发布源码；安装器固定到具体构建并核对该站公布的 SHA256，不跟随 latest。不想用它的，先自行安装 FFmpeg 或用 `VIDEO_SOP_FFMPEG` / `VIDEO_SOP_FFPROBE` 指定已有文件，安装器就不会下载。这些依赖不会作为二进制文件提交本仓库。

## 已有工具或自定义目录

在下载的仓库根目录执行：

```bash
bash install.sh --dest ./local-skill --skip-system-deps
bash install.sh --dry-run
```

Windows 对应参数为 `-Dest ./local-skill -SkipSystemDeps`、`-DryRun`。`--with-voice` 只在 macOS 入口提供。默认仍会建立独立 Python 环境、获取字体并自检；`--skip-system-deps` 只表示不修改系统软件，缺失依赖会明确失败。`--no-smoke` / `-NoSmoke` 仅检查环境，不执行实际渲染。测试报告据此记录实际范围。

可通过本地环境变量指定工具文件：`VIDEO_SOP_PYTHON`、`VIDEO_SOP_BLENDER`、`VIDEO_SOP_FFMPEG`、`VIDEO_SOP_FFPROBE`、`VIDEO_SOP_FONT`。变量取文件路径，不填密钥；不需要公开配置。

doctor直接读取`VIDEO_SOP_FONT`，优先于`.local/environment.json`里的font；未指定时仍用安装器固定字体。TTC/OTC集合可另设从0开始的`VIDEO_SOP_FONT_INDEX`，或在本地配置保存font_index。字体或索引无效会失败，不静默换字体。该索引用于doctor选择实际字形；制作工具也须显式选择和绑定自己的实际字体版本。

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

## 查看自检的真实输出

```bash
.venv/bin/python scripts/doctor.py --smoke-test --artifacts-dir .local/doctor-artifacts/run-001 --out .local/doctor.json
```

证据目录必须全新，已有目录不会覆盖。保留font.png、64×64 frame.png、smoke.blend和24帧smoke.mp4；应实际打开中文图和CPU帧。摘要记录字体/像素/产物SHA，原件留在忽略目录。未指定`--artifacts-dir`时使用临时目录，验证后清理。

字体检查实际绘制“产业链、中文数字、亿元、帧”等样本文字，逐个排除缺字方框并量像素墨迹；它只证明这组字形，不替代成片全帧glyph检查。CPU探针显式关闭降噪，验证原始Cycles渲染；某些构建缺OpenImageDenoise时仍可完成该基础渲染。报告明确记录denoising为disabled_for_minimal_cpu_probe、GPU为not_tested；生产需要的降噪、GPU与画面品质须另做真实验证，不能继承ready。
