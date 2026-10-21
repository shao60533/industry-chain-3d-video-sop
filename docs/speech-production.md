# 语义段落配音与时轴

配音按完整意思组织。字幕分页、字数目标、片长与供应商倍率不能替代实际试听。下列方法用于所有画风，沿用本期获授权音色，不上传个人录音或自动选择供应商。

## B之后规划，D之前试听

`scripts/speech_plan.py`将确认稿按自然段规划；默认长段尽量在句末分组，单句超出预算时保留完整句并标记warning。标题不参与旁白；正文段落之间空一行。它不调用TTS、不调整音频、不自动批准。

```bash
python3 scripts/speech_plan.py --script jobs/example/B-script/script.md --out jobs/example/D-audio/speech-plan.json
```

每单元记录id、paragraph_id、text、实际prior_context/next_context、boundary_reason、boundary_review和tempo_review。重复句按原稿顺序计算上下文，不能用首次同文位置代替。需要手动拆分时保留单元顺序与覆盖；完整句用complete_sentence，实际听过并接受的语义分句用approved_semantic_clause，每段最后单元为paragraph_end。

先对同稿中的叙述、数字密集、名词解释和问答试听，再选speed。优先一个完整语义段落共合成；过长才在完整句或审听接受的分句处切。产品名、型号、数字+单位和“分类→作用→技术解释”不能机械切开。缓存依赖原稿、实际读法、前后文、获选音色SHA、语速、seed与pause_policy。

## 停顿和证据

测两段首尾已有留白后，补停顿=max(0，目标语义停顿−已有留白)。不固定给每句再加一段静音，不把自然呼吸当噪声删除。ASR提示错读/漏字候选，强制对齐提供时点，两者都不评自然度。

实际合成和对齐后：

1. 绑定当前script_sha256、audio_sha256、timing_sha256。
2. 逐单元实际审听边界与最终语速，填写boundary_review/tempo_review；完成前保持pending。
3. paragraph_listening逐段记录paragraph_id、真实音频起止秒、continuous=true、状态与证据路径/SHA；一段不漏、不重复补齐。
4. 计划status=reviewed只在这些工作真实完成后填写，将speech_plan作为D的必需输出登记。
5. D步骤证据须包含semantic_phrase_boundaries和paragraph_prosody_listening观察；E及最终voice_music_listening保留narration_join_continuity，实听最终混音中的转场、问答、公司数字与拼接点。

校验器拒绝原稿覆盖/顺序错误、假段落、错上下文、未审阅、错误SHA、漏/重复段落和无效时段，并将嵌套证明加入失效依赖。它只核记录，不读取音频判断音色或韵律，也不能从一份证明文件自动认定其中真的有连续审听。

改配音、停顿或语速后重新对齐并重验字幕/镜头/标注/混音与编码。只改变阿拉伯数字显示时保留自然中文旁白和原字符时点，按[制作复盘](production-lessons.md)检查显示映射。完整验收仍按[acceptance](acceptance.md)。
