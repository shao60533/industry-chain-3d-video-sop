# 下一集启动包

2026-10-04。制作准备模板已完成，选题与指定完整来源尚未填；不是已启动的一期视频，也没有发布授权。既有光/存储成片保持原状。

现行[制作SOP](../../docs/production-sop.md)、[发布SOP](../../docs/publication-sop.md)、复盘（内部案例未分发）。

2026-10-07：先读[用户纠正执行卡](../../docs/review-checklist.md)，复制user-corrections-checklist.template.json作为工作底稿。每项留实际观察、产物及未验范围，汇入原12项报告；不新增自动通过，也不修改已确认旧稿。共同错误按全期受影响项返工。

1. 复制模板到新的job目录，填写topic/product、完整来源URL/版本/哈希、集数和约5分钟预算。不要运行旧v24或光互连固定帧脚本。
2. script.template.md只提供段落骨架。先写一层完整观点，用company-judgments表检查用途、门槛、具体卡点、公司竞争位置、证据和赚钱机制，再完成整稿。
3. approved.md为唯一确认源。TXT与JSON从同一源导出；script_bundle只导出文本与检查漂移，不负责确认、事实审稿、TTS或渲染。
4. 在 job.voice_lock 填入自行提供并获授权的本地音色参考及实际SHA。先做30–60秒试听，接受后再填speed。
5. 做同一母产品的整体/拆解/内部功能图，封面独立设计，可另设模型镜头或使用生成式封面；按[视觉基准](../../docs/visual-quality.md)与实际光模块、用户指定的相关封面及编码近景作200/390px同宽对照。填写visual-review.template.json的具体判断，再分件建模；封面不充当模型交付，不能直接套用最大展开图或只验标题可读。
6. opening-cues按帧号做独立9.5秒无口播样片：真实展开、短悬停环绕、真实合体，节奏音乐带动展开/环绕/合体，轻音效跟动作落点，接第一句本人旁白。BPM按本期选，不照搬120；当前cue是设计，尚未渲染/实听。
7. 样片含两行长字幕、财务卡、问答、部件图注和结构动作。先锁safe-layout.template.json及字体SHA测bounds，360/390宽带遮罩和实际界面验收，再长渲染；子模块有参考和成片可见近景。
8. 全片导出layout.jsonl，绑定当前视频/profile SHA填acceptance.template.json的12项证据。缺项pending；可交本地审阅包，release_ready=true才冻结发布包。
9. H manifest含production_acceptance，用video_publish_preflight.py退出0后才启动原publisher；原授权/话题/群/封面/AI/定时/单次attempt不省。

同源导出/校验命令（仅在具体稿件完成后使用，替换绝对路径占位符）：

> 原内部命令未随本仓库分发。工具对接要求见工具适配说明；不可将这里的流程当作已安装的一键命令。

上述工具已用一致导出、旧TXT、源稿改变三种行为验证。不是通用video run，不会发布、配音或覆盖历史任务。

共用[验收规则](../../docs/acceptance.md)及三期复盘（内部案例未分发）。不复制旧y1662、过期验收SHA或仅文件存在的缓存规则。

2.2：先填写production-spec所有实际内容与焦点窗口，生成全部requirements，再分别真实完成check-report（不得复制测试fixture）；acceptance仅引用逐项报告。H按质量优先launcher，只读check-only先验；缺UI/实听即审阅包，不冻结为发布就绪。

新一期先建立component-inventory与独立opening-assembly，按原稿/模型语义节点/镜头填写，不能复制测试fixture或省略正文设备。stage由分类推导，焦点/12项typed报告仍需真实完成；空模板不能放行。

2026-10-05：五项封面美术观察已进入production-spec.template.json的requirements.cover_crop，使用既有2.2覆盖校验。视觉底稿的观察和实际对照图引用到cover_crop，不新增第13项，也不把模板填满当通过。镜头按功能口播记录原生动作/末帧保持/静态与二维区间；结构过程和卡片段分别判断。

script.template.md已补开场具体问题和结尾同序答案；company-judgments补产品分类、全链位置、公司比较结论；芯片基板与晶圆按可见功能分区、器件/互连和尺度核图。执行卡修的是既有流程的实际内容，不是另一套口播方法论。
