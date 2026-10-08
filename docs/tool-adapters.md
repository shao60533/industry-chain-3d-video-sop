# 工具适配说明

本仓库已提供统一安装器、环境检测与任务初始化工具；原内部完整制作/发布运行器未分发。先按[安装指南](installation.md)准备基础工具链，再对接具体任务所需能力。

| 本包工具 | 实际职责 |
|---|---|
| install.sh / install.ps1 / scripts/setup.py | 安装 Codex 技能、基础依赖、独立 Python 环境和中文字体 |
| scripts/doctor.py | 验依赖与字形，实际 CPU 渲染、重开工程、编码与解码；不签发成片质量 |
| scripts/init_job.py | 建立新任务目录和 pending 模板，拒绝覆盖已有任务 |

| 原系统名称 | 需要实现或人工完成的责任 |
|---|---|
| script_bundle.py | 从确认稿同源导出 TXT/JSON，检测源稿及导出漂移；不负责事实确认 |
| video_acceptance.py | 核 production-spec、逐项类型报告、依赖 SHA 和全帧 glyph/focus 日志，独立探测最终编码 |
| video_publish_preflight.py | 发布前核 manifest、资产、当前验收版本和哈希；缺项阻断 |
| video_publisher_run.py | 先验质量，再核授权并调度具体平台发布适配器 |
| xhs_video_prepare/status/fill/cover/verify/publish | 绑定唯一原稿、真实控件回读、单次提交、后台只读核验 |
| active registry / archive-publication-records.py | 维护当前包、原始 attempt/result 和未知记录，归档失败不重发 |
| Codex | 主执行者，贯穿规划、实现、调度、修复和证据整理；实际独立复核与自检分开记录 |

## 配置顺序

1. 创建本地 job 目录，按 A-reference、B-script、C-design、D-audio、E-model、F-film、G-package、H-publish 分阶段保存产物。
2. 填自己的完整来源、账号、品牌、字体文件和获授权音色。音色文件只在本地引用；不要提交到公开仓库。
3. 复制布局 profile 并记录真实文件 SHA。使用最终实际字体测量字形墨迹，输出连续帧日志；不能只填矩形或场景名字。
4. 在 production-spec 写实际章节、镜头、公司、组件、字幕和焦点窗口。报告以真实观察和原件 SHA 为依据，缺失保持 pending。
5. 检查最终 MP4 的解码、时间线、颜色、听感和连续运动，并在真实设备查看正常播放界面。
6. 平台实现先验证只读与草稿行为，再在明确授权范围内测试提交。页面变化须重新验证；历史内部测试不算当前平台验证。

Blender 工程保存后重开并复核闭合、最大展开、环绕与合体；渲染输出、合成与最终编码分别验。实际 GPU、系统架构和渲染耗时按使用者环境确认。

## 原内部材料的替代

内部回顾、已发布基准图、产品学习笔记和生产实例没有随仓库分发。按规范用自己有权使用的产品官网资料、同宽对照图和实际成片建立本地替代。不要把历史认可、手机免验或某次工具测试通过继承到新任务。
