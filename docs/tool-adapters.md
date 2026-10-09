# 工具适配说明

本仓库已提供安装、自检、任务初始化及本地Workflow/证据最小核心；完整制作、checker和发布运行器未分发。以[统一规范](codex-workflow.md)和唯一job.json为入口，按[安装指南](installation.md)准备基础工具链，再对接具体能力。

| 本包工具 | 实际职责 |
|---|---|
| install.sh / install.ps1 / scripts/setup.py | 安装 Codex 技能、基础依赖、独立 Python 环境和中文字体 |
| scripts/doctor.py | 验依赖与字形，实际 CPU 渲染、重开工程、编码与解码；不签发成片质量 |
| scripts/init_job.py | 建立新任务目录和 pending 模板，拒绝覆盖已有任务 |
| scripts/workflow.py | job.json内的A–E版本准出、F产物登记、暂停/失败回流/有限恢复；不执行生成工具，不推进最终G/H |
| scripts/evidence.py（由workflow命令调用） | 实际文件/报告/证明SHA、类型、身份、时间、声明覆盖与阻断字段的最小校验；始终不签发release_ready |

| 原系统名称 | 需要实现或人工完成的责任 |
|---|---|
| script_bundle.py | 从确认稿同源导出 TXT/JSON，检测源稿及导出漂移；不负责事实确认 |
| video_acceptance.py | 核 production-spec、逐项类型报告、依赖 SHA 和全帧 glyph/focus 日志，独立探测最终编码 |
| video_publish_preflight.py | 发布前核 manifest、资产、当前验收版本和哈希；缺项阻断 |
| video_publisher_run.py | 先验质量，再核授权并调度具体平台发布适配器 |
| xhs_video_prepare/status/fill/cover/verify/publish | 绑定唯一原稿、真实控件回读、单次提交、后台只读核验 |
| active registry / archive-publication-records.py | 维护当前包、原始 attempt/result 和未知记录，归档失败不重发 |
| Codex / Agent | 当前步骤内部的推理、实现、调度、修复和证据整理；跨步骤推进交给同一Workflow，实际独立复核与自检分开 |

`check-release-bindings`不是video_acceptance.py或video_publish_preflight.py的完整替代。它只验证所提交证据的结构与版本，未实现全帧glyph/focus重算、完整组件分类、PNG尺寸、播放覆盖或最终ffprobe，也不证明事实/听看/审美真实。外部checker尚未接入时F/G/H与对应领域检查保持pending，不可因该命令退出0启动publisher。

content_kind与visual_style不得在适配器硬绑定。相同研究/脚本/音轨/最终验收接口下，3D保留原生模型、装配、功能焦点和开场动作；白板使用可编辑二维工程、visual_inventory、图表口径/尺度、箭头关系与渐进揭示。12项槽名兼容，按画风输出实际适用检查，不能把整项N/A。第三方工具接入必须绑定版本与实际SHA，在途任务不可静默换实现。

## 配置顺序

1. 创建本地 job 目录，按 A-reference、B-script、C-design、D-audio、E-model、F-film、G-package、H-publish 分阶段保存产物。
2. 独立填content_kind/visual_style、修订、制作者、完整来源、品牌、字体和获授权音色；平台账号只在实际授权发布时本地配置。成本/权限依据未知时阻塞，核心不增加付费调用。音色仅本地引用，不提交公开仓库。
3. 复制布局 profile 并记录真实文件 SHA。使用最终实际字体测量字形墨迹，输出连续帧日志；不能只填矩形或场景名字。
4. 先关键帧/试听/难例并保存版本批准；按镜头记录production_method，不强制图生视频。数字/单位/字幕独立确定性合成，禁用可辨识人物头像。spec写实际章节、镜头、公司、适用视觉元素、字幕/焦点及layout绑定；typed报告绑定spec_sha256与全依赖，缺失保持pending。
5. 检查最终 MP4 的解码、时间线、颜色、听感和连续运动，并在真实设备查看正常播放界面。
6. 平台实现先验证只读与草稿行为，再在明确授权范围内测试提交。页面变化须重新验证；历史内部测试不算当前平台验证。

Blender 工程保存后重开并复核闭合、最大展开、环绕与合体；渲染输出、合成与最终编码分别验。实际 GPU、系统架构和渲染耗时按使用者环境确认。

## 原内部材料的替代

内部回顾、已发布基准图、产品学习笔记和生产实例没有随仓库分发。按规范用自己有权使用的产品官网资料、同宽对照图和实际成片建立本地替代。不要把历史认可、手机免验或某次工具测试通过继承到新任务。
