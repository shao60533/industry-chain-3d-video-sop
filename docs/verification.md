# 1.3.0 验证范围与待验项

2026-10-09，基线提交 f6e394c4d1a7cecc53f2ea25b13e43d4a3da629d。结果分别记录规范、代码和真实生产，不能跨层推断。

| 范围 | 实际结果 |
|---|---|
| 修改前既有行为测试 | 18项通过 |
| 首轮代码行为测试、模板/链接和技能frontmatter基本契约检查 | 51项通过（18安装、19Workflow、11证据、3仓库检查）；对应首轮提交638a103 |
| 独立审查修复后的完整回归 | 61项通过（18安装、29Workflow、11证据、3仓库检查）；包括原成功案、授权/恢复失效及保存边界竞态 |
| doctor修复后的完整回归 | 70项通过（新增9项doctor回归，含缺字、实际像素、可选降噪、缺失Pillow、产物防覆盖）；CI按最新SHA核验 |
| Python编译、Bash语法、diff空白检查 | 全部通过 |
| Linux环境自检首次执行（Python3.12、Blender4.3.2、FFmpeg/ffprobe7.1.5） | 工具版本读取通过；中文字体检查失败，Blender渲染自检退出1；当时ready=false |
| Linux doctor修复后真实执行 | 中文像素及实际查看、64×64 Cycles CPU渲染、工程重开、24帧H.264/AAC/BT.709与全解码通过；ready=true，film_acceptance=pending |
| 完整制作、全帧checker、生成供应商与平台运行器 | 未分发，本次未接入或运行 |
| 真实分镜关键帧/试听/连续样片/全片/设备与公开状态 | 未验证，保持pending |
| macOS/Windows本次实机执行 | 未跑；跨平台行为测试交由现有CI |
| 用户本地同步与实际工具链/样片验证 | 待PR分支同步后在本地执行 |

云端复用已有Python/Pillow/Blender/FFmpeg/Noto，没有安装新软件、调用付费生成工具、使用账号/密钥或发布视频。CI仅增加安装已有requirements.txt固定的Pillow以运行像素回归。合成测试在临时目录创建真实字节文件和SHA，用于验证状态与证据的程序行为；其中媒体/感知声明刻意标记synthetic，不可作为生产证明。12项结构校验成功仍返回release_ready=false和production_checks=pending。

## 独立审查后的复现与修复

授权原件撤销、恢复后原件失效，以及准出后/保存前新attempt/result竞态均在638a103上复现；删除badcase.artifacts原失败证明后resume也错误放行。修复前新增断言失败，修复后Workflow定向29项通过，包括20个“恢复依赖×pending/generated/accepted/paused”删除子例、授权变化、失败证明、提交竞态和共享锁。重试测试改用版本化badcase/recovery原件，保留历史现场。

该轮修复完整61项回归、Python编译、Bash语法与diff检查均通过；对应d8fd37a的三平台CI通过。真实制作、全帧checker和平台发布未因这些离线测试得到验证；当轮未重跑制作环境自检，后续实际修复结果另记如下。

## 中文字体与Blender自检修复

真实日志确认：Pillow12.3.0和系统Noto已安装，但本地字体配置未建立，doctor也未读取VIDEO_SOP_FONT；Blender4.3.2继承默认降噪，其构建没有OpenImageDenoise而退出1。保留失败日志与旧ready=false，没有将原失败改写为通过。

先补回归：在d8fd37a上执行同一断言，拉丁缺字方框和只有bbox却无实际绘制这两例错误通过，CPU探针在“无OpenImageDenoise且默认降噪开启”条件下失败；修复后三例均通过。修复后复用系统Noto SC集合index2，持久配置只保存在忽略目录；环境变量与无覆盖变量的默认调用均真实通过。实际查看中文PNG（self_review），“产业链 3D · 中文数字 123.45 亿元 / 24 帧”显示正确，10个中文样本字形与缺字方框不同，墨迹9053像素；实际查看CPU PNG，能见立方体和阴影。另用实际DejaVu拉丁字体执行反例，缺字方框被拒绝、退出1、ready=false。

| 本地原件的实际绑定 | SHA256 |
|---|---|
| 已安装Noto字体集合 | b76b0433203017ca80401b2ee0dd69350349871c4b19d504c34dbdd80541690a |
| 中文PNG | 5e68f8db766d51b15311b9b56c0294e474a3ea9530b22a695f357b03582f7099 |
| 64×64 CPU帧RGB像素 | ef3acc10ab4426320fe7a5598baf55d403c2a74b4cd380cc1f96634ddb848abc |
| 24帧自检MP4 | 7216d01bb2e3cd78dfa182ece82042f18313a6ef4ab1b80fbbe0f64584870767 |

实际命令为`python3 scripts/doctor.py --smoke-test`；需查看原件时另加`--artifacts-dir`指定全新本地目录和`--out`保存摘要，见[安装指南](installation.md#查看自检的真实输出)。自检原件/日志/工具路径均留在.local，不上传公开仓库。CPU探针保留实际渲染/重开/编码/解码全部门禁，只明确关闭非该探针验证范围的降噪；报告也记录该范围，不宣称降噪支持。GPU、降噪生产能力、真实样片及成片/听看/设备仍未验证，Workflow仍不签发release_ready。

复验命令：`python3 -m unittest discover -s tests -v`、`python3 -m compileall -q scripts tests`、`bash -n install.sh`、`python3 scripts/doctor.py --smoke-test`。完整checker与生产验收另按[验收契约](acceptance.md)；本次环境失败未通过安装未知软件或修改权限绕过。

同步时先保留已有本地job、音色、账号和工具配置，获取工作分支并核提交SHA。在途任务继续使用其原policy版本，不复制新模板覆盖旧任务、不改旧pin或补签批准。新建独立任务验证题材/画风选择、关键帧和难例，pending项目以实际观察关闭；本次PR仅为草稿，不自动合并或发布。
