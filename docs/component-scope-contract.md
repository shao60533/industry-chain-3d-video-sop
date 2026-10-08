# 组件阶段契约：严格旧版与 SHA 绑定分类清单

> 本文规定 Codex 和适配器应执行的行为。文中的原内部程序/插件名称未随仓库分发，接入责任见[工具适配说明](tool-adapters.md)。

此文定义 video-2.2 验收适配器应遵守的组件契约。原内部验收代码未分发，字段规则供 Codex 和工具实现者对接。

## 阶段只由有效分类推导

没有 `spec.bindings.component_inventory` 时，继续要求 **全部 components 的 opening + body** 焦点、可见性描述和见证帧。旧版没有正文豁免。无效、缺文件、旧 SHA 或不完整的清单直接阻断，不能降级到宽松路径。

清单只能通过 `bindings.component_inventory = {path, sha256}` 引用，文件须在验收包内。顶层未绑定的 `component_inventory` 拒绝。所有 typed reports 的 `bindings` 必须包含该清单的当前 SHA；原有全部依赖绑定仍保留。

| classification | 必验阶段 | 额外约束 |
|---|---|---|
| `product_part` | opening、body | 属于本期开场装配，ID 与节点须与装配表一致，包含开场及正文镜头 |
| `upstream_material` | body | 与开场产品装配无成员、节点或装配 ID 重合 |
| `manufacturing_equipment` | body | 同上 |
| `external_system` | body | 同上 |
| `alternate_product_example` | body | 同上；例如与本期开场通用组件不同的 BC 电池示例 |

`required_stages` 在 spec、分类清单、所引用的 film-plan / 开场装配及模型报告中均禁止；不能覆盖上述规则。缺分类、未知分类、重复 ID、漏项、额外组件均失败。开场装配表中的产品内件不能改成任何正文分类；删除 spec 与清单中的产品 ID 也不能绕过独立装配表。

## 分类文件字段

`video-component-inventory-1` 必须包含：

- `schema`、与 spec 一致的 `job_id`、`revision_id`。
- `source_script_sha256`：与 `bindings.script.sha256` 一致，并重算当前稿件实际字节 SHA。
- `film_plan: {path, sha256}`、`opening_assembly: {path, sha256}`：都是实际文件引用，不能用文件名代替 SHA。
- `components`：完整且唯一的条目列表，ID 集合必须等于 spec 的全部 `components`。每项必填 `id`、`classification`、`assembly_id`、`semantic_nodes`、`script_anchor`、`shot_ids`。

`semantic_nodes` 和 `shot_ids` 是非空、无重复的字符串列表。`script_anchor` 是当前绑定稿件中确实出现的非空原句；字符串匹配只确认原句存在，不自动证明它支持该分类。

film-plan 使用本地现行字段：`source_script_sha256`、`fps`、`frames`、`shots[]`；每镜头有 `shot_id`、`start_frame`、`end_frame`。全部镜头 ID/帧区间必须与 spec.shots 一致，媒体参数及稿件 SHA 也须一致。

独立开场装配 JSON 使用：

```text
schema: video-opening-assembly-1
source_script_sha256: 当前稿件 SHA
assembly_id: 本期开场产品装配 ID
model: {path, sha256}
shot_ids: 开场镜头 ID 列表
parts: [{component_id, semantic_nodes}, ...]
```

开场镜头须组成 film-plan 从帧 0 开始的连续前缀，且保留后续正文。装配表必须有产品内件；模型引用也重算 SHA。它是独立的装配成员声明，不能仅用分类清单自述“我不是内件”获得豁免。

清单、稿件、film-plan、开场装配、装配模型全部进入依赖快照；release gate 和 preflight 在检查结束后重新核对字节 SHA，包括 ffprobe 运行期间的变化。

## 焦点与见证

所有 focus 必填正数、有限且非布尔的 `min_width`、`min_height`；缺值不再默认为 1。旧版同样严格核尺寸。原有全帧安全区、字形、字幕时点、遮挡和卡片碰撞检查保持。

有有效清单时，focus 额外必填 `shot_id`、`semantic_nodes`：镜头属于该组件，窗口完全位于对应镜头，开场/正文阶段与开场镜头集合一致，节点属于分类条目。全帧 layout 的该 focus 必须匹配 spec 的 `component_id / stage / shot_id / semantic_nodes`，同时保留实际投影 `rect`。这些字段不得用手补的框冒充真实渲染记录。

模型报告中，每个必验阶段仍需具体的 `*_visibility` 描述和整数 `*_frame`。见证帧必须位于观察帧段及对应的 **role=focus** 窗口；卡片、标签或装饰不能提供见证。所有组件均需 `connection`，正文均需 `body_visibility / body_frame` 与证明文件。

## 受控 opening N/A

只有有效清单推导为正文资产时允许如下字段；这是字段说明，不是真实报告：

```text
opening_frame: null
opening_visibility:
  status: not_applicable
  classification: 与该组件清单完全一致的正文分类
  component_inventory_sha256: 当前 bindings.component_inventory.sha256
```

结构必须完全匹配，不能用裸字符串 `N/A`，不能保留一个伪开场帧，不能引用旧清单 SHA。产品内件与无清单旧版不接受此值。body 与 connection 不可因此标 N/A。

12 项仍全部必需；N/A 只针对正文资产的 opening 字段，不针对任何检查项的 status。连续播放、完整实听、本人音色、真实设备、最终编码、几何、封面等门槛没有豁免。

## 光伏边界及仍需人工核读的内容

以通用光伏组件为例，开场装配可列出玻璃、胶膜、硅电池、金属互连、接线盒与直流输出、边框；这些产品装配部件必须在 opening/body 分别验证。硅料、拉晶切片、BC 专用背电极、工艺设备、逆变器，以及 film-plan 中的玻璃生产线，是正文资产。玻璃片与玻璃窑炉不是同一个组件；通用双玻璃开场也不是 BC 产品。

机器只核对文件、哈希、集合、原句存在、帧区间和声明一致性。人工仍须读源稿、film-plan、装配依据及真实画面，判断分类是否正确、节点是否真实属于该产品、框是否来自可见功能结构。若源稿、装配表和清单一起填错但互相一致，程序不能证明其语义真实性；同步漏掉所有清单中的正文资产也仍需要人工完整性复核。不得把此契约或 synthetic 测试写成真实观看、实听或分类审读已通过。

未输出真实分类清单及原生焦点日志的工具，需先适配再建立实际 release_ready。

## 实现验证要求

> 原内部命令未随本仓库分发。工具对接要求见工具适配说明；不可将这里的流程当作已安装的一键命令。

适配器测试应在临时目录生成 synthetic 契约与短测试媒体，覆盖旧版双阶段、绑定分类的受控 N/A、来源/清单/组件/装配错误、正文见证、尺寸、非 focus 见证、播放/实听/设备/几何阻断和 preflight 期间依赖变更；这些记录不可复制为生产验收。
