---
name: industry-chain-3d-video
description: 用 Codex 制作产业链产品拆解 3D 视频，完成完整读源、观点稿、分件建模、动效、配音调度和质量交付；支持安装与环境自检。适用于产业链讲解与产品功能拆解，不自动授权平台发布。
---

# 产业链 3D 视频

Codex 是主执行者，专业工具按实际环境执行。保留用户指定产品、来源、品牌、音色和已接受选择。

## 首次安装或依赖问题

在本技能目录运行 `python3 scripts/setup.py`（Windows 可用 `py -3`），安装缺失依赖、隔离 Python 环境及字体。脚本默认安装到 `${CODEX_HOME:-~/.codex}/skills/industry-chain-3d-video`。当已通过技能安装器下载到该目录时，直接原地配置。

安装后使用 `.venv/bin/python scripts/doctor.py --smoke-test`；Windows 使用 `.venv\Scripts\python.exe`。本机工具绝对路径仅保存在 `.local/environment.json`，不写入公开文件。缺失依赖或测试失败不能宣布环境就绪；具体支持、权限与离线配置见 [安装指南](docs/installation.md)。

## 开始一期视频

1. 阅读 [Codex 工作流](docs/codex-workflow.md)、[制作 SOP](docs/production-sop.md)与[质量验收](docs/acceptance.md)。视觉决策另读[视觉质量](docs/visual-quality.md)，组件覆盖另读[组件契约](docs/component-scope-contract.md)。
2. 用 `.venv/bin/python scripts/init_job.py --output <新目录>` 建立本地任务，填写来源、题目和已授权条件。所有模板保持 pending；默认 produce_only。
3. 完整读源，先交付具体公司/卡点/盈利判断、配音试听、三类产品图、真实展开/环绕/合体和难例样片，再全片渲染。修改只重做受依赖影响部分。
4. 使用真实文件及 SHA 完成证据。自检记 self_review；没有实际听看能力、连续播放或设备证据的项目保持 pending。工具退出成功和模板填满不能替代真实质量检查。
5. 发布前另读[发布 SOP](docs/publication-sop.md)，核已有授权与当前冻结包；提交未知只读恢复。安装环境不配置账号，不上传音色，不产生发布权限。

本包提供安装、自检和任务初始化工具；配音供应商、复杂模型生成及平台发布适配由当前任务按实际能力接入，见[工具适配](docs/tool-adapters.md)。不虚构一键出完整成片。
