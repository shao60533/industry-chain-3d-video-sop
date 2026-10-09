---
name: industry-chain-3d-video
description: 用 Codex 在统一视频 Workflow 中完成研究、事实证据、脚本、分镜、小样和质量交付；内容题材与 3D/白板画风独立。支持安装、自检、持久步骤状态和版本绑定证据校验，不自动授权平台发布。
---

# 视频 Workflow（3D / 白板）

Codex 是主执行者，专业工具按实际环境执行。保留用户指定产品、来源、品牌、音色和已接受选择。Agent负责当前步骤内部工作，Workflow负责状态推进与证据准出。产业链是题材，3D和白板是独立画风选择；技能安装名称保留兼容。

## 首次安装或依赖问题

在本技能目录运行 `bash install.sh`（macOS/Linux）或 `./install.ps1`（Windows），复用已有工具并安装缺失的 Python、Blender、FFmpeg、隔离 Python 环境及字体。已有 Python 3.11+ 时也可运行 `python3 scripts/setup.py`。默认安装到 `${CODEX_HOME:-~/.codex}/skills/industry-chain-3d-video`；已下载到该目录时直接原地配置。

安装后使用 `.venv/bin/python scripts/doctor.py --smoke-test`；Windows 使用 `.venv\Scripts\python.exe`。本机工具绝对路径仅保存在 `.local/environment.json`，不写入公开文件。缺失依赖或测试失败不能宣布环境就绪；具体支持、权限与离线配置见 [安装指南](docs/installation.md)。

## 开始一期视频

1. 阅读 [Codex 工作流](docs/codex-workflow.md)、[制作 SOP](docs/production-sop.md)与[质量验收](docs/acceptance.md)。视觉决策另读[视觉质量](docs/visual-quality.md)，组件覆盖另读[组件契约](docs/component-scope-contract.md)。
2. 用 `.venv/bin/python scripts/init_job.py --output <新目录> --content-kind <题材> --visual-style <画风>` 建立本地任务，独立填写来源、题目、修订和成本/权限依据。job.json是唯一任务/状态源；所有模板保持pending，默认produce_only，拒绝覆盖。
3. 完整读源，先交付具体判断、分镜关键帧、配音试听与难例样片；3D保留三类产品图、真实展开/环绕/合体，白板检查图表口径、图示关系和渐进揭示。批准绑定版本，再全片。数字/单位/字幕独立确定性合成，禁用可辨识人物头像；按镜头选方法，不强制图生视频。
4. 使用真实文件及 SHA 完成证据。自检记 self_review；没有实际听看能力、连续播放或设备证据的项目保持 pending。工具退出成功和模板填满不能替代真实质量检查。
5. 发布前另读[发布 SOP](docs/publication-sop.md)，核已有授权与当前冻结包；提交未知只读恢复。安装环境不配置账号，不上传音色，不产生发布权限。

本包另提供scripts/workflow.py的A–E状态准出、F产物登记及12项报告结构/SHA校验；完整checker、制作/发布运行器未分发，核心始终保留release_ready=false。失败须记badcase并测原失败案与旧成功案，在途任务锁规范/实现版本；成本/权限未知阻塞。具体边界见[工具适配](docs/tool-adapters.md)，不虚构一键出完整成片。
