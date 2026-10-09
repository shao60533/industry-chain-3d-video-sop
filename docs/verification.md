# 1.3.0 验证范围与待验项

2026-10-09，基线提交 f6e394c4d1a7cecc53f2ea25b13e43d4a3da629d。结果分别记录规范、代码和真实生产，不能跨层推断。

| 范围 | 实际结果 |
|---|---|
| 修改前既有行为测试 | 18项通过 |
| 最终代码行为测试、模板/链接和技能frontmatter基本契约检查 | 51项通过（18安装、19Workflow、11证据、3仓库检查）；实际字节/SHA与两种画风同流程回归 |
| Python编译、Bash语法、diff空白检查 | 全部通过 |
| Linux环境自检（Python3.12、Blender4.3.2、FFmpeg/ffprobe7.1.5） | 工具版本读取通过；中文字体检查失败，Blender渲染自检退出1；ready=false |
| 完整制作、全帧checker、生成供应商与平台运行器 | 未分发，本次未接入或运行 |
| 真实分镜关键帧/试听/连续样片/全片/设备与公开状态 | 未验证，保持pending |
| macOS/Windows本次实机执行 | 未跑；跨平台行为测试交由现有CI |
| 用户本地同步与实际工具链/样片验证 | 待PR分支同步后在本地执行 |

本次没有新增依赖、调用付费生成工具、使用账号/密钥或发布视频。合成测试在临时目录创建真实字节文件和SHA，用于验证状态与证据的程序行为；其中媒体/感知声明刻意标记synthetic，不可作为生产证明。12项结构校验成功仍返回release_ready=false和production_checks=pending。

复验命令：`python3 -m unittest discover -s tests -v`、`python3 -m compileall -q scripts tests`、`bash -n install.sh`、`python3 scripts/doctor.py --smoke-test`。完整checker与生产验收另按[验收契约](acceptance.md)；本次环境失败未通过安装未知软件或修改权限绕过。

同步时先保留已有本地job、音色、账号和工具配置，获取工作分支并核提交SHA。在途任务继续使用其原policy版本，不复制新模板覆盖旧任务、不改旧pin或补签批准。新建独立任务验证题材/画风选择、关键帧和难例，pending项目以实际观察关闭；本次PR仅为草稿，不自动合并或发布。
