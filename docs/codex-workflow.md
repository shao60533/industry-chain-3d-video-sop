# 一条视频 Workflow：内容与画风独立

workflow-1，2026-10-09。本文件是统一规范入口，`job.json` 是唯一任务与持久状态来源。制作、验收和发布文档是同一 Workflow 的领域契约；不另外安装总控或维护第二份任务台账。原 A–H 和 Q-A–Q-E 保留。

Agent 负责当前步骤内的推理、工具调用、产物和修复。Workflow 负责步骤之间的状态推进、准出、证据、失败回流与暂停恢复。Agent 的“完成了”不是状态转换凭据。

## 内容题材和视觉选择

| 字段 | 值 | 含义 |
|---|---|---|
| `content_kind` | `industry_chain / earnings / catalyst / other` | 内容题材；产业链、财报、催化剂或其他 |
| `visual_style` | `3d / whiteboard` | 画风；3D 或白板 |
| `topic / product` | 实际主题 / 产品（可空） | 产品并非所有题材的必填对象 |
| `job_id / revision_id / producer_id` | 任务身份 / 内容修订 / 制作者 | 开始前填写；公开内容的 content_key 仍按发布契约保持稳定 |

所有题材都可选择任一画风。产业链往往适合 3D，财报与催化剂往往适合白板，这是制作建议。没有“产业链流程 vs 白板流程”。默认题材和画风均为空，需由本期任务明确选择。

所有任务共用完整研究、事实与日期/单位证据、同源脚本、问答对应、声音、字幕、验收和发布状态。产业链脚本沿用途→工艺/门槛→瓶颈→公司→盈利；财报沿业务→同比/环比及口径→驱动→盈利/现金流→风险；催化剂沿事件→机制→证据→公司影响→条件/风险。使用指定完整来源，缺事实保留缺口，不自行扩大研究范围。

## 角色与权限

| 角色 | 职责 | 边界 |
|---|---|---|
| 使用者 | 来源、题材、画风、已接受选择和授权范围 | 制作和公开发布分别授权；现有授权在原范围内持续有效 |
| Codex / Agent | 当前步骤的研究、实现、工具调度、修复和证据整理 | 自检写 self_review；不补造批准、独立复审、实听、设备或平台回执 |
| 本地 Workflow 核心 | 持久状态、版本绑定、准出、失效和恢复 | 不调用制作供应商，不操作浏览器，不签发全片 release_ready |
| 实际工具与复核者 | 专业计算、真实观察及批准 | 工具能力逐项验证；另一模型、自检轮次或进程退出成功不自动构成独立审核 |

成本或权限未知先阻塞。当前核心只接受 `execution_constraints.cost_status=no_paid_calls`、`permission_status=authorized` 和任务内 `{path, sha256}` 授权依据。它没有付费适配器，也不会新增付费调用。将来接付费工具须另验证预算、目的地和权限，不能修改标记绕过。

## 保留 A–H 与五个关口

| 阶段 | 同一 Workflow 的交付 | 准出与适用检查 |
|---|---|---|
| A 研究 | 指定完整来源、brief、来源映射、研究笔记 | 全文范围、事实/单位/日期、缺口与时长/集数预算 |
| B 脚本 | 唯一确认稿、公司判断、问答映射和同源导出 | Q-A；本题材的明确观点与来源依据，不只匹配关键词 |
| C 设计 | 分镜关键帧、shot-plan、design-lock、字体与布局 | Q-B 前置；关键帧批准绑定输入及具体输出版本 |
| D 音轨 | 30–60秒试听、最终音轨、timing、字幕 | 音色、数字/专名、语速和同步；试听批准只覆盖该版本 |
| E 视觉/小样 | 可编辑视觉工程、开场和15–30秒正文难例 | Q-B；连续听看与批准，包含两行字幕、卡片、数字及焦点 |
| F 全片 | 最终媒体、layout、技术与感知报告 | Q-C/Q-D；真实完整 checker 与听看/设备检查 |
| G 冻结 | 同版 spec、12项报告、全发布资产 manifest | Q-E；完整验收和当前依赖均有效才能发布就绪 |
| H 发布/归档 | 唯一草稿、单次 attempt、回执、公开证据与归档 | 独立核授权及原平台门禁；未知提交只读恢复 |

本包实现 A–E 的本地证据准出及 F 的产物登记。`accept F`、`start G/H` 明确阻断，完整制作、checker、冻结/发布运行器仍未分发。A–E 通过不等于最终成片通过，最终12项仍默认 pending。现有 ready_to_produce 与 acceptance.release_ready 不由核心补签。

## 画风只切换制作策略和视觉检查

| 关口/报告槽 | 3D | 白板 |
|---|---|---|
| C 关键帧 | 整体/展开/内部图、装配依据、功能近景 | 图表日期/分母/单位/尺度、关系图、图例与阅读顺序 |
| E 小样 | 原生展开、真实环绕、真实合体、保存重开及功能动作 | 渐进揭示、箭头和关系连续、图表解读与可编辑工程 |
| 最终 model_coverage | 原模型/组件覆盖和 opening/body 契约 | 兼容报告槽名，核图示元素/关系/脚本覆盖；不要求原生模型 |
| 最终 opening_motion_rhythm | 原3D开场与音乐/动作落拍 | 所选开场的揭示顺序、连续性、阅读节奏和音画同步 |
| spec 视觉绑定 | model / component_inventory | visual_project / visual_inventory |

封面也保留兼容观察ID：白板的product_readability核主题/图示主体，material_hierarchy核线条/填色/信息层级，cover_narrative核本题材的问题或判断表达；不强制金属材质或“拆开产品”。裁切、缩略图、基准比较与系列排版仍须实际查看。

3D 的[组件契约](component-scope-contract.md)和[视觉基准](visual-quality.md)继续严格适用。白板没有装配展开义务，仍须证明图示正确、解释可见和运动连续。12项报告名称保持兼容，全部有适用检查，不能把整项 status 写成 N/A。混用镜头只增加该镜头真实采用方式的检查，不为纯白板强套3D。

每镜头在 shot-plan 写 `production_method`（native_3d / native_2d / deterministic_composite / image_to_video / provided_clip）、选择依据、输入 SHA、口播窗口与实际动作区间。按镜头需求选工具，不强制图生视频。原生工程适合精确结构与可编辑动作；白板可原生二维合成。图生视频只在结构和时序可控、成本权限已知时作为候选。

数字、单位、日期、关键图表标记和字幕由确定性文字/矢量/图表层独立合成，并对照稿件与来源逐字检查。生成图片/视频中的文字不作最终信息层；不使用可辨识人物头像。字幕仍透明、最多两行，关键字形与解释焦点保留原安全区和间隔。

## 持久状态与依赖

init_job 拒绝覆盖已有目录，把 video-workflow-1 的 A–H 状态写入 job.json.workflow。模板只保存空白底稿，没有第二个 workflow.json。原 E-model 目录名为兼容保留，白板也可在此保存可编辑视觉工程。

- pending：尚未执行。running：已锁输入，Agent 正在执行该步骤。
- generated：已登记当前输出及 SHA，可审阅，尚未准出。
- accepted：该步骤证据、适用观察和所需批准均绑定当前输入/输出；只在该步骤范围有效。
- blocked / paused / invalidated：缺口或失败阻塞 / 主动暂停 / 依赖改变导致旧证据失效。
- 发布另用 not_submitted / submission_unknown / submitted / public_verified。submitted 需实际提交回执；审核中或定时仍不证明公开。public_verified 需当前内容的实际公开页面证据。核心只读这些字段，不执行或编造转换；原平台 scheduled / reviewing / rejected / published 详情仍保存在原始回执。

每步保存 inputs / outputs / evidence / config_sha256 / attempts / retries / failure，历史事件保留前次绑定和失败记录。开始必须先验上游 accepted；下游稿件、分镜、音轨、timing、字体/profile、视觉工程 SHA 必须对应已接受上游。不能用未批准的新稿同时挂上旧稿批准证据。

每次推进重算任务配置、所有实际文件、报告和证明 SHA；文件名不变也重算。更改输入、输出、证明或 job 配置使最早受影响步骤及后续已执行步骤 invalidated，旧报告与历史保留。当前核心采用保守的顺序依赖；领域工具可按[重验矩阵](acceptance.md#改动后重验范围)生成新版复用记录，不能篡改旧报告 SHA。

status 不写文件，会给出当前有效状态与 dependencies_stale；失效在下一次推进时持久化。独占 .workflow.lock、写入前配置比对、原子替换和回读防止两个推进者覆盖状态。锁无法自动抢占；进程异常遗留锁时先确认原进程结束并保留现场，再由本地维护者处理。

在途任务绑定实现和领域规范的 policy_sha256。技能更新使其不一致时仅可 status，不自动改 pin 或迁移。使用原固定提交/技能副本完成在途任务；需迁移时另做明确版本的恢复/交接，保留原任务及证据，旧批准不自动继承。旧2.2任务不会自动添加或覆盖状态，继续使用其原工具只读恢复。

## 本地命令与证据格式

以下命令仅操纵本地状态；python3 可换成已安装技能的 .venv/bin/python；Windows 使用 .venv\Scripts\python.exe。

```bash
python3 scripts/init_job.py --output ./jobs/episode --content-kind industry_chain --visual-style whiteboard
python3 scripts/workflow.py --job ./jobs/episode status
python3 scripts/workflow.py --job ./jobs/episode start --step A --manifest A-reference/inputs.json
python3 scripts/workflow.py --job ./jobs/episode record --step A --manifest A-reference/outputs.json
python3 scripts/workflow.py --job ./jobs/episode accept --step A --report A-reference/review.json
python3 scripts/workflow.py --job ./jobs/episode pause --step B --reason source_gap
python3 scripts/workflow.py --job ./jobs/episode resume --step B
```

先填 job 的主题、题材/画风、修订、制作者和执行条件。输入/输出 manifest 是 `{名称: {path, sha256}}`，早期路径相对 job 根；输入可显式引用外部普通文件，输出、报告、批准与证明必须在 job 内，禁止符号链接。

| 阶段 | 必填输入名（此外自动绑定上游输出/报告） | 必填输出名 |
|---|---|---|
| A | source_full、brief | source_map、research_notes |
| B | source_full、brief | script、company_judgments、question_answers |
| C | script、font、profile | keyframes、shot_plan、design_lock |
| D | script、voice_reference | voice_preview、audio、timing、captions |
| E | script、shot_plan、audio、timing、font、profile | visual_project、opening_sample、difficult_sample |
| F | 同E，加 visual_project | video、layout |

复制 step-evidence.template.json 为实际报告。inputs/outputs 是持久状态各名称到 SHA 的映射，含自动加入的 A.source_map、A.evidence 等上游项；同时绑定 job/revision/config/policy。scope 和 observations 必须覆盖当前阶段及画风的全部 ID（见脚本 BASE_REQUIREMENTS / STYLE_REQUIREMENTS），每项写 id/status/detail/artifacts，证明是 `{path, sha256}`。报告需实际时间、检查者/能力、真实观察，未验范围或阻断非空均不准出。

C/D/E 另引用 step-approval.template.json 的实际批准记录，绑定同一组输入、输出及版本。basis 引用实际用户批准或获授权复核依据。已经明确接受的选择可用原依据按当前文件建立绑定，勿重复索要批准；self_review 不能补造用户同意。结构校验无法证明记录者诚实或实际具备所声明感知能力。

## 失败回流与恢复

```bash
python3 scripts/workflow.py --job ./jobs/episode fail --step E --record E-model/badcase.json
python3 scripts/workflow.py --job ./jobs/episode resume --step C --resolution C-design/recovery.json
```

badcase绑定job/revision/step/config/policy和输入/输出SHA，必填预期、实际、最早根因、漏检原因、最小修复、回归用例和恢复条件，并引用现场证明。fact_error → A、script_error → B、visual_error → C、audio_error → D、sample_error → E；工具、能力、成本和权限失败留在当前步。回流目的地不得晚于失败步。修根因并复查全期同类问题，不能只修点名镜头。报告、证明和badcase使用版本化文件名，保留原件，不覆盖历史失败现场。

失败阻塞根因步骤，使依赖步骤失效。recovery-evidence 须绑定原 badcase SHA 和恢复条件，所有回归结果 passed 且有证明，至少包含 original_failure 和 previous_success。每步最多一次失败恢复重试；再次失败继续 blocked，回到根因与工具能力，不自动开新任务清零。暂停恢复也重验依赖；输入变更不能恢复为旧 generated/accepted。

submission_unknown 或任何已有 attempt/result 一律生产状态只读，不删除原 attempt，不重建稿、不补签、不重发。[发布 SOP](publication-sop.md)保留现有锁、唯一原稿、账号、质量前置和单次提交要求。归档失败不触发重发。

## 12项报告的最小校验边界

```bash
python3 scripts/workflow.py --job ./jobs/episode check-release-bindings \
  --evidence G-package/acceptance.json --video F-film/final.mp4 --profile C-design/safe-layout.json
```

该只读检查重读 spec、全部12项独立 typed reports、实际媒体/profile/全依赖/证明 SHA、身份、时间、观察覆盖、检查能力和未验/阻断字段；技术结果须明确 true 且扫描帧数匹配，设备声明须是 actual_platform_playback。缺报告、pending、旧 SHA、错类型、跨 job、未来时间、伪独立身份均退出非零。报告增加 spec_sha256，spec 增加实际 layout 绑定。相对 spec/report/proof 路径均以 acceptance 所在包为基准；显式命名的原件依赖可引用包外文件。

退出0只表示 evidence_bindings_valid=true，始终返回 release_ready=false / production_checks=pending / external_checker_required=true。它没有完整全帧 glyph/focus、组件分类、PNG尺寸、播放覆盖、最终 ffprobe、内容真实性或美术判断实现。完整[验收契约](acceptance.md)保持不变，外部 checker 与人工须验证上述领域要求。不能将这个命令替换为 publisher 的完整质量 preflight。

## 启动任务与工作目录

```text
请按本仓库 AGENTS.md 和统一 Workflow 制作本期视频。
主题/内容题材：[实际主题；industry_chain / earnings / catalyst / other]
画风：[3d / whiteboard；独立选择]
完整来源/版本/日期：[指定可访问原文或本地文件]
工作目录：[新的本地 job 目录]
品牌问候/获授权音色：[实际选择；个人音频不上传未授权目的地]
画幅/预算/工具：[默认1080×1920、24fps；实际可用能力与成本权限]
模式：produce_only；已有接受选择及依据：[当前授权范围]
先完整读源、给出本题材具体判断和全期结构，后做分镜关键帧、试听及难例样片。
按镜头选择制作方式，文字/数字/字幕独立确定性合成，禁用可辨识人物头像。
Agent执行步骤内部工作；Workflow凭当前版本证据推进。待验项保持pending。
不上传私人手册、音色、账号、凭据、历史数据或原始平台回执到公开仓库。
```

jobs/<job-id>/ 保留 A-reference、B-script、C-design、D-audio、E-model、F-film、G-package、H-publish；全部生产资料默认忽略。工具实现边界见[工具适配](tool-adapters.md)，交接见[单阶段契约](handoff.md)。

## 方法参考与复用边界

- [Spec Kit](https://github.com/github/spec-kit)及其[Workflow文档](https://github.github.io/spec-kit/reference/workflows.html)：规范→计划→任务→实现/收敛，以及持久状态、条件、关口和暂停恢复。当前已提供 Workflow 引擎，不能说它没有状态机。
- [Matt Pocock skills](https://github.com/mattpocock/skills)：需求术语、端到端任务和测试审查的小型可组合技能。
- [Superpowers](https://github.com/obra/superpowers)：先找根因、用失败回归驱动修复、完成声明前获得新证据。
- [Treeloop作者方法文](https://blog.51cto.com/aioldsix/14909117)：作为方法论线索；本次页面读取未成功，未核实可执行框架，不宣称安装或运行。

这里只借鉴机制，不执行或整套安装上游，不复制上游代码/大段文字。若后续实质复用 MIT 内容，保留对应版权、许可和来源。规则更新、代码验证、真实样片、全片验收和发布效果分别记录。
