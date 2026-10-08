# 小红书视频发布与 DSH 复用 SOP

版本 xhs-video-2.2，2026-10-04。此文件是现行视频发布入口；旧版已保存至复盘 backups/sop。制作见[视频制作SOP](production-sop.md)。历史提交授权只覆盖原片，SOP更新不新增发布权限。

2026-10-07用户纠正复盘：[执行卡](review-checklist.md)。封面可独立制作；原帖封面更新按下节单独归档，不把重新上传视频或新发一篇当作更新。

## 原帖仅更新封面

1. 绑定已授权原note_id、账号、完整标题与新封面SHA；保留原发布manifest、视频与尝试历史。新建cover-update记录和当前资产指针，不修改历史回执。
2. 新封面重新验文字、主题、示意身份、裁切与五项美术观察；不变视频的证据按原依赖有依据复用，不假记新一轮完整听看。用户当次允许待验提交时单独保留授权范围和pending，不改成passed。
3. 打开同一原帖编辑页，回读原视频身份、标题/正文、真实话题chip、群、AI声明与可见性。封面单次上传并确认主编辑页实际应用，再单次保存；绑定该页面后台操作，用户可继续用其他浏览器。
4. 保存后的“更新成功”、后台原帖/新封面资源、审核状态和实际公开图分别留原始证据。URL变化但缩略图naturalWidth为0时，记录资源未显示，不称已看到公开新封面；编辑器预览也不是公开展示证据。
5. 保存结果未知先只读核同一帖子，不盲点第二次、不新建帖子补救。最终写明only_cover_uploaded、video_reuploaded、save_click_count、元数据保留和实际未验范围。

此节仅定义操作纪律；使用者须独立验证自己的发布工具。

## 1. 能力与执行边界

发布工具应支持视频草稿、状态、文案、封面、核验、单次提交及后台回读。原内部工具未随本仓库分发；这里规定行为要求，不承诺自动化能力。

发布适配器需自行配置并验证工具注册、扩展加载、账号和当前平台页面。

正式执行走自行配置的发布入口与共享publisher锁；不抢锁、不杀其他会话。显式 `ZENITH_PUBLISH_SETTINGS_SOURCE` 必须绝对普通文件路径，优先于默认；指定路径无效应在停web前报错，不静默换配置。runtime覆盖最后加载；实际provider/model从运行证据验证，不照抄历史模型名。

**用户可以同时操作其他浏览器或标签。** prepare/backend helper使用active:false，后续绑定真实draftId/native tabId/fingerprint/manifest SHA与新鲜心跳。不激活标签/窗口、不移动系统鼠标、不用当前页猜控制页。局部DOM正常focus可用于真实控件事件；旧原生hover与OS窗口定位不作正常依赖。登录/风控/验证码或结构不支持时保留原稿，返回具体阻断。

## 2. 冻结包

包含content_key、job_id、平台/expected_account、真实授权来源/范围、媒体版本、视频/封面/标题/基础正文/最终含话题全文的绝对路径、字节数与SHA、规格/时长、真实话题顺序、公开/定时/AI声明/原创/合集/群聊设置，以及当前媒体对应的验收报告。新包必须有production_acceptance：acceptance.json/profile绝对路径及SHA，当前视频SHA与12项证据；本地质量门禁不等同平台表单verify。

生成版本和公开内容身份分开；仅换版本号不能重新发布。资产或正文改变须重新审稿与冻结；真实草稿存在后不能改manifest迁就错误表单。经用户明确授权的未提交同稿改时以新manifest、retime receipt及active registry保存旧包，不覆盖历史。

每集独立身份与包。上下集同标题主体须用（上）/（下）精确区分；间隔安排以用户指定锚点为准，原时间错过不能自行改。

## 3. 标准步骤

1. 先运行video-acceptance/video_publish_preflight.py --manifest <本期H manifest> --out <production-preflight.json>，非零退出立即停止，不启动DSH、不触碰web/bridge。通过后核有效授权、当前包、账号、锁和工具能力。其他publisher持锁等待或返回busy；拿到锁再设置时间，不提前计算导致排队消耗提前量。
2. 后台精确完整标题查重，核ready与found。只有ready=true且found=false可初建；超时/未知不能解释为不存在。已有attempt/result只读回查。
3. prepare一次，持久保存content_key、draftId、tabId、fingerprint与manifest SHA。后续只在唯一原稿继续，不刷新未提交稿、不新建、不重上传。跨轮需要保留浏览器页时标记handoff，不把未提交页当临时研究页清理。
4. 区分文件票据交付、传输、转码、可播放。懒加载记录真实video的readyState/duration/error和原稿身份，再有限复读；状态变化或诊断介入有依据才恢复，不能拿另一video节点或exit0证明就绪。只接受真实时长、可播放且无错误/处理中；100%或“重新上传”按钮存在都不能替代此判断。当前平台限制现场读取，本地适配器限制另行记录，不照搬旧HANDOFF。
5. fill冻结基础正文。话题前空行在绑定前装配，回读规范化全文；换行必须是真实字符。已绑定chips后fill会清空，应只在未提交同稿局部修复时重绑全部原话题。
6. 用真实候选逐项绑定话题，每项读chip文本、数量和顺序。输入一次、选择一次、检查一次；候选未就绪只观察，不重复输入词或用普通#文本代替chip。高层一键话题绑定尚未实现，不能省掉这项现场检查。
7. 用xhs_video_open_cover打开唯一真实编辑器；cover单次交付冻结PNG，staged后通过平台“完成”应用。回读编辑器关闭、新主预览、SHA关联及实际图像。基线未知、图没加载、弹窗图/头像/推荐图都不算应用成功。
8. 指定群聊选择准确已有候选，表单与笔记预览双回读；不新建群或关联无关活动。设置并回读：真实AI主description、permission公开值、原创、群聊/合集；定时读真实checkbox checked和picker值。候选/标签/正文含AI/隐藏默认值不能代表当前选中。透明input只在精确真实卡片及可见祖先链内操作。
9. verify全部硬门禁：同页身份、账号、媒体可播放/时长、资产、完整标题/正文/chips、封面、AI、公开与精确时间、可提交、未尝试。每项未知都阻断，不能降低expected迁就页面。
10. 独占持久attempt先写成功，再在最终页面MAIN同步复核全部门禁并点击一次，中间不await。即时只接受“发布”，定时只接受“定时发布”。页面marker和result写失败保留原错误，不报假成功。
11. 后台按精确标题、账号、时间及真实卡片核验。保留原始DOM/工具回执；点击、审核、定时、公开分别记录。结果页`published=true`不是公开证明。
12. 用active registry归档当前包与全部尝试历史，写台账和离线NAS队列。审核中/已定时可以结束本次提交任务；不自动首评、传播观测或开启新自动任务。

## 4. 定时与状态

“最新时间晚一个小时”在实际设置动作开始时取系统时间+1小时，按平台分钟精度向上取整；记录anchor、target、picker实际值、manifest与后台值。原生控件默认时间或自动clamp不能冒充目标。明确改时仅适用于未提交原稿；有attempt/result禁止自动改时重试。

| 平台/回执信号 | 正确记录与恢复 |
|---|---|
| 未知/超时/空回执 | clicked=null，后台只读；不改false、不删attempt、不重建 |
| 确定发生点击、后台读取失败 | clicked=true及真实clickedAt保留；审核/公开未知 |
| 审核中 | submitted_reviewing，published=false；保留实际卡片时间 |
| 定时发布+审核中 | status=scheduled、reviewStatus=reviewing、scheduleAt准确；未来时间不是submittedAt |
| 定时后已发布列表 | status=published；旧manifest含schedule不应将其重新判unknown |
| 未通过 | rejected优先；保留原文，不复制重发规避 |
| 已发布列表、完整标题命中 | published；公开URL/后台ID拿不到则null |

只接受机器实际采集时间和原始clickedAt；模型补写的未来/非法时间或文件mtime不作事件时间。审核未出现不能凭absence宣称审核通过。

## 5. 断点与有限修复

- 同一明确错误最多一次定点重试，失败回到工具根因；新会话只带短恢复契约。桥接缓存按相同tab的最新lastSeen选择，不能让helper页或旧token抢路由；后台body ready而非整页无关网络完成作读取条件。
- 在途封面标记先于File赋值；同SHA在途不重复交付。状态持久化及回读成功后才能推进applied，弹窗未关一律阻断。
- 已有attempt无通用续点/重发规则。存储上集MAIN变量作用域故障仅在固定源码、同指纹无页面marker、后台无匹配共同证明后完成同attempt的首次实际点击；这是已知事件例外，不能用于其他timeout。
- 原标签关闭且原提交未知：只读查后台，保留unknown。无法恢复不自行重建；只有用户明确要求重新发布时，建立独立恢复包、记录新增授权、保留原未知历史，重新查重并单次提交。不能把新稿成功推成原稿没点过。
- 扩展管理页被浏览器策略拒绝时由用户重载现有扩展，不绕过；与发布授权不同，无需重问已有发布许可。
- 归档失败不重发。最新两集包、active registry、原unknown与恢复证据进入本地队列；NAS连通/实际传输证据取得前只写queued。

## 6. 归档与恢复记录

按当前任务的 active registry 与实际 attempt/manifest SHA 归档，保留 unknown 历史，提交时间与定时时间分别记录。归档失败不能触发重新发布。

## 2026-10-04 质量前置2.2

H manifest增加revision_id与production_acceptance，绑定2.2 spec及12项独立类型报告；最终封面/标题/正文亦同版。video_publisher_run.py --check-only可只读验收；非零不启动publisher。实际xhs_video_prepare在浏览器前、创建prepare记录/上传票据前双查；xhs_video_publish在verify前、claim attempt前双查固定本地checker，缺证据不写页、不生成attempt。不提供关闭开关，不复用旧全局passed。status/focus保留旧包只读恢复，未知/已有attempt不重发。

制作质量通过不授予发布权，账号/话题chip/群/封面/AI/时间/单次提交原门禁全部保留。本轮只完成离线阻断和本地媒体等价检查，真实新包授权全链仍待验证；不拿已发布三期补测。详情见视频video-acceptance/验收规则.md。
