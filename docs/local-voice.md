# 本地配音：用自己的声音

录一段自己的声音，在自己的电脑上做成音色，再用它念稿。录音、音色和成品都留在本机，不需要注册账号、充值或 API key。

这是可选组件。已有获授权配音工具的，继续用自己的；[语义配音](speech-production.md)里的计划、试听和连听要求对两种做法都一样。

## 适用范围

| 项目 | 要求 |
|---|---|
| 电脑 | Apple 芯片的 Mac（M 系列）。Intel Mac、Windows、Linux 暂不支持 |
| 内存 | 建议 16 GB 及以上 |
| 硬盘 | 模型约 6 GB，另加约 1 GB 的 Python 依赖 |
| 网络 | 只在安装时下载模型和依赖；合成时离线运行 |

模型是 `mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit`，安装器固定到一个具体版本。模型与依赖的许可由各自维护者规定，独立于本仓库的 MIT。

## 安装

把这句话发给 Codex：

```text
请给 industry-chain-3d-video 技能加装本地配音：在技能目录运行统一安装入口并加上 --with-voice，装好后运行 scripts/local_voice.py check 并把结果告诉我。不读取或上传我的录音。
```

或在终端执行：

```bash
curl -fsSL https://raw.githubusercontent.com/shao60533/industry-chain-3d-video-sop/main/install.sh | bash -s -- --with-voice
```

安装器先完成基础环境，再建立独立的 `.venv-voice`、安装固定版本的依赖并下载模型。模型下载可能要几十分钟，期间没有进度条；中断后重跑同一条命令会续传。基础环境不受影响，本地配音失败时会单独报告。

下载慢时，可以先在终端设置自己信任的镜像地址（环境变量 `HF_ENDPOINT`）再安装。

## 第一步：录音

用手机自带的录音 App 就够。

1. 找一个安静的房间，关掉风扇和空调，关上窗。
2. 手机离嘴大约一拳，放稳，不要手持晃动。
3. 用平时说话的语气和速度，念 [朗读稿](../templates/voice/reading-script.zh.txt)。约 30 秒，里面有数字、英文缩写和一句判断，后面试听正好对照。朗读稿里的数字是练习用的，不是事实。
4. 念错了就整段重录，不要中途停下再接。
5. 把录音文件传到电脑上。m4a、mp3、wav 都可以。

录音时长需要在 10–60 秒之间，20–40 秒最稳。

## 第二步：做成音色

以下命令在技能目录内执行。把这句话发给 Codex 也可以：「用 scripts/local_voice.py 把我的录音 <文件> 做成音色，文字用朗读稿。」

```bash
.venv-voice/bin/python scripts/local_voice.py prepare --input ~/Downloads/my-recording.m4a --text-file templates/voice/reading-script.zh.txt --out voice-references/my-voice
```

工具把录音转成 24 kHz 单声道 WAV，去掉文件里的设备与位置信息，量出时长、音量和爆音比例，并记下录音与文字的 SHA。音量偏小、有爆音或偏短时会给出提示；几乎无声或时长不合要求会直接失败。`voice-references/` 在忽略目录里，不会进入公开仓库。

## 第三步：试听

```bash
.venv-voice/bin/python scripts/local_voice.py speak --voice voice-references/my-voice --text-file templates/voice/reading-script.zh.txt --out voice-references/my-voice-preview-01
```

输出目录里有每个语义单元的 WAV、一条连起来的 `preview.wav` 和 `manifest.json`。`preview.wav` 的停顿只为试听方便；正片的停顿和语速按[语义配音](speech-production.md)另行处理。

不满意时换一个 `--seed`（任意整数）再生成，输出目录要换新名字，旧的不会被覆盖。`--temperature` 默认 0.6，调高语气更活、也更容易念错。念英文稿时加 `--language english`。

## 这里必须由人来听

工具能量音量和时长，不能判断像不像、对不对。下面几项要本人戴耳机听完再决定，`manifest.json` 里的 `listening_review` 在听之前保持 `pending`。

| 检查 | 怎么判断 | 不合格怎么办 |
|---|---|---|
| 录音里念的和文字一致吗 | 对着文字听一遍原录音 | 改文字或重录，再重新 prepare |
| 像不像自己 | 拿原录音和 `preview.wav` 交替听 | 换安静环境重录；换 seed |
| 数字念对了吗 | 「零点三毫米」「百分之十五」「四百多颗」 | 换 seed；仍不对就把数字写成想要的读法 |
| 英文念对了吗 | 「GPU」「OLED」 | 每个新英文词先出两三种写法的短对比片再挑 |
| 句尾有没有吞字、多字 | 每句最后两个字 | 换 seed 重做该单元 |
| 有没有怪声、电音、突然变调 | 从头到尾连续听 | 换 seed；降低 temperature |

转写软件识别正确不等于读音正确，这一步不能用自动识别代替。

## 已知局限

- 在我们自己的对比里，这个模型克隆出的声音辨识度够，但比真人偏闷，语调起伏偏小，句内小停顿偏少。要更接近真人，可以换用自己获授权的其他配音工具。
- 不常见的英文名和型号不稳定，同一个词多生成几遍结果不同，需要挑。
- 每次只适合念一个完整语义段。工具按句末把长段切成不超过 90 字的单元。
- 只验证过中文普通话。英文和其他语言没有做过听感验证。

## 授权与隐私

- 只克隆自己的声音，或已拿到本人明确同意的声音。`reference.json` 里的 `usage_authorization` 由使用者本人确认，工具不会替你填。
- 录音、音色目录和合成结果不要提交到任何公开仓库。`*.wav`、`voice-references/` 和 `recordings/` 已在 `.gitignore` 中。
- 合成时工具强制离线运行。安装阶段只下载模型和依赖，不上传文件。
- 把克隆声音用于冒充他人或误导听众，由使用者自己承担责任；平台对合成声音有标注要求的，按平台规则标注。

## 常见问题

| 现象 | 处理 |
|---|---|
| 提示只支持 Apple 芯片的 Mac | 这台电脑用不了本地配音，改用自己获授权的配音工具 |
| 提示配音模型未就绪 | 重跑带 `--with-voice` 的安装命令，等下载完成 |
| 提示录音需要 10–60 秒 | 按朗读稿重录一段 |
| 提示目录已存在 | 换一个新的 `--out` 目录名；工具不覆盖旧文件 |
| 提示参考录音被改动 | 录音或文字在 prepare 之后变了，重新 prepare |
| 合成很慢或电脑发烫 | 正常现象，关掉其他占内存的软件；内存不足 16 GB 时可能失败 |

## 验证范围

在一台 Apple 芯片 Mac 上实际跑过：建立 `.venv-voice`、安装固定依赖、`check`、`prepare` 和 `speak`，合成结果用本地转写核过文字一致。当时模型已在本机缓存，约 6 GB 的首次下载没有重新走一遍；带 `--with-voice` 的一条命令完整安装、以及 16 GB 以下内存的机器也没有验证。CI 只运行不依赖模型的单元测试，不下载模型，也不做听感判断。
