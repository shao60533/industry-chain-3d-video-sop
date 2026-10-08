# 产业链视频单阶段交接模板

> 本文规定 Codex 和适配器应执行的行为。文中的原内部程序/插件名称未随仓库分发，接入责任见[工具适配说明](tool-adapters.md)。

video-2.2，2026-10-04。现行规则见[制作SOP](production-sop.md)及[视频发布SOP](publication-sop.md)。模板不是启动命令或发布授权。

```text
任务：<本阶段具体交付>
job_id / content_key：<唯一任务 / 稳定公开内容身份>
目录：<绝对路径>
模式/阶段：<produce_only / prepare_draft / publish；A–H>
唯一输入：<来源版本/哈希、确认稿、当前资产、实际工具入口>
已有接受选择：<不重复问；本人音色、主副题、时长/画幅、确认依据>
制作复核执行卡：<本阶段相关项、实际观察与全期受影响范围；不复制全部历史>
稿件逻辑：<用途先于实现；具体公司/卡点/盈利观点；开场问题ID与结尾答案/画面对应>
封面：<独立设计/生成或模型另设机位；实际像素/参考/文字/示意身份；与正文模型验收分开>
声音：<video-preferences.json、voice-lock；仅本地引用，不附密钥/用户原录音>
开场：<真实展开/悬停环绕/合体与节奏音乐/轻音效共用帧号；样片验收状态>
公司段：<观点/来源、部件/动作/揭晓时间>
布局：<profile/字体SHA，全帧bounds，360/390遮罩图，实际设备证据>
质量状态：<12项状态/范围/证据SHA；technical/layout/release_ready分开，pending阻断>
输出/验收：<可审阅文件与具体通过条件，不靠exit0>
分工：<用户本任务指定；默认Codex统筹并实现，专业工具执行；自检与实际独立复核分别记录>
发布授权：<直接用户依据与平台/账号/内容/时间范围；没有填未授权>
冻结包：<当前manifest路径/SHA；验收必须同媒体哈希>
发布前置：<production_acceptance及本地preflight；非零不启动publisher>
发布恢复：<active registry、原draft/tab/指纹、attempt/result、未知历史>
停止条件：<来源/能力/身份/资产/选中值未知、风控、提交未知>
回传：<result.json；实际状态、原始证据、未验范围、blocker/next_action、可得usage>
```

发布只做冻结包装配、verify、单次提交和只读后台，不重新写稿/生图。由 Codex 调度自行配置并验证的适配器；视频上传、封面、即时/定时和归档能力逐项实测，仓库不承诺无人值守。发布页不必前台，保持原稿页打开并在跨轮结束时标记handoff。已有attempt/结果未知只读核验；明确新增重发授权另建恢复包且保留旧unknown。

下一集模板：[README](../templates/next-episode/README.md)。新片无题目/来源/公开授权时不把占位稿作为成片或发布内容。

质量验收2.2：生产spec覆盖全期，12项typed报告核内容/范围/实际时间/观察能力、全资产与依赖SHA；全帧字形、timing、卡片及功能焦点重算，最终编码每镜头边界/中部、360/390与真实设备分开。技术通过不等于release_ready。实际prepare/publish在网页写入前及上传/attempt前强制复查，缺证据阻断；旧status/focus只读。具体工具实现必须在当前环境验证。

交接附production-spec、逐公司/逐组件审阅表、12项check-report、真实感知待验项、缓存依赖与重验范围；不把旧无关proof文件作为放行证据。
