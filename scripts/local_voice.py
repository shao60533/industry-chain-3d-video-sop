"""Clone an authorized voice on this machine with Qwen3-TTS (Apple Silicon); nothing is uploaded."""

from __future__ import annotations

import argparse
import array
import contextlib
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import shutil
import sys
import wave

from runtime import config, find_tool, run, safe_message
from speech_plan import plan

MODEL_ID = "mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit"
MODEL_REVISION = "e7dd0585652209fa0d7783659aad4e8a324de11c"
SAMPLE_RATE = 24000
MIN_SECONDS, MAX_SECONDS = 10.0, 60.0
UNIT_MAXIMUM = 90
UNIT_PAUSE, PARAGRAPH_PAUSE = 0.45, 0.75
LANGUAGES = ("chinese", "english")


def supported() -> bool:
    return platform.system() == "Darwin" and platform.machine().lower() in ("arm64", "aarch64")


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_wav(path: Path) -> tuple[array.array, int]:
    with wave.open(str(path), "rb") as stream:
        if stream.getnchannels() != 1 or stream.getsampwidth() != 2:
            raise RuntimeError("音频需要是单声道 16 位 WAV")
        rate = stream.getframerate()
        samples = array.array("h")
        samples.frombytes(stream.readframes(stream.getnframes()))
    if sys.byteorder == "big":
        samples.byteswap()
    return samples, rate


def write_wav(path: Path, samples: array.array, rate: int = SAMPLE_RATE) -> None:
    data = array.array("h", samples)
    if sys.byteorder == "big":
        data.byteswap()
    # "xb" keeps an earlier take from being replaced.
    with path.open("xb") as raw, wave.open(raw, "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(rate)
        stream.writeframes(data.tobytes())


def measure(samples: array.array, rate: int) -> dict:
    """Report what can be measured; whether it sounds like the speaker needs a listener."""
    if rate != SAMPLE_RATE:
        raise RuntimeError("参考音频采样率不是 24 kHz")
    seconds = len(samples) / rate
    if not MIN_SECONDS <= seconds <= MAX_SECONDS:
        raise RuntimeError(f"录音需要 {MIN_SECONDS:.0f}–{MAX_SECONDS:.0f} 秒，当前约 {seconds:.0f} 秒")
    rms = math.sqrt(sum(value * value for value in samples) / len(samples)) / 32768
    peak = max(abs(value) for value in samples) / 32768
    clipped = sum(1 for value in samples if abs(value) >= 32700) / len(samples)
    if rms < 0.005:
        raise RuntimeError("录音几乎没有声音，请检查麦克风后重录")
    warnings = []
    if rms < 0.02:
        warnings.append("音量偏小：靠近麦克风一些再录")
    if clipped > 0.001:
        warnings.append("有爆音：离麦克风远一点或降低输入音量")
    if seconds < 20:
        warnings.append("偏短：20–40 秒的录音更稳")
    return {"seconds": round(seconds, 2), "rms": round(rms, 4), "peak": round(peak, 4),
            "clipped_share": round(clipped, 5), "warnings": warnings}


def ffmpeg_convert(source: Path, target: Path) -> None:
    ffmpeg = find_tool("ffmpeg", config().get("tools", {}))
    if ffmpeg is None:
        raise RuntimeError("缺少 FFmpeg，请先运行安装器")
    # Metadata can carry device names and locations; the reference keeps only the sound.
    run([ffmpeg, "-v", "error", "-nostdin", "-i", str(source), "-vn", "-map_metadata", "-1",
         "-ac", "1", "-ar", str(SAMPLE_RATE), "-c:a", "pcm_s16le", str(target)], timeout=300)


def prepare(source: Path, text: str, out: Path, convert=ffmpeg_convert) -> dict:
    text = text.strip()
    if not text:
        raise RuntimeError("需要提供录音里实际念出的文字")
    if not source.is_file():
        raise RuntimeError("找不到录音文件")
    try:
        out.mkdir(parents=True)
    except FileExistsError as exc:
        raise RuntimeError("音色目录已存在，不覆盖；请换一个目录名") from exc
    try:
        audio = out / "reference.wav"
        convert(source, audio)
        measured = measure(*read_wav(audio))
        transcript = out / "reference.txt"
        transcript.write_text(text + "\n", encoding="utf-8")
        record = {"schema": "video-local-voice-reference-1", "audio_sha256": sha256(audio),
                  "text_sha256": sha256(transcript), **measured,
                  "uploaded": False, "transcript_matches_recording": "pending_human_check",
                  "usage_authorization": "pending_human_confirmation"}
        (out / "reference.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except Exception:
        shutil.rmtree(out, ignore_errors=True)
        raise
    return record


def load_voice(directory: Path) -> dict:
    try:
        record = json.loads((directory / "reference.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RuntimeError("音色目录不完整；请先运行 prepare") from exc
    audio, transcript = directory / "reference.wav", directory / "reference.txt"
    if record.get("schema") != "video-local-voice-reference-1" or not audio.is_file() or not transcript.is_file():
        raise RuntimeError("音色目录不完整；请先运行 prepare")
    if sha256(audio) != record.get("audio_sha256") or sha256(transcript) != record.get("text_sha256"):
        raise RuntimeError("参考录音或文字在准备之后被改动；请重新运行 prepare")
    return {"audio": audio, "text": transcript.read_text(encoding="utf-8").strip(), "audio_sha256": record["audio_sha256"]}


def cached_model() -> str:
    from huggingface_hub import snapshot_download
    return snapshot_download(MODEL_ID, revision=MODEL_REVISION, local_files_only=True)


def mlx_synthesizer(voice: dict, temperature: float, language: str):
    if not supported():
        raise RuntimeError("本地配音目前只支持 Apple 芯片的 Mac")
    # Synthesis runs offline: the model is already cached and the recording stays here.
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    try:
        import mlx.core as mx
        import numpy as np
        from mlx_audio.tts.utils import load_model
    except ImportError as exc:
        raise RuntimeError("本地配音环境未安装；请运行安装器并加 --with-voice") from exc
    try:
        # Library banners print the local cache path; keep them out of the console.
        with open(os.devnull, "w") as quiet, contextlib.redirect_stdout(quiet), contextlib.redirect_stderr(quiet):
            model = load_model(cached_model())
    except Exception as exc:
        raise RuntimeError("配音模型未就绪；请运行安装器并加 --with-voice") from exc

    def synthesize(text: str, seed: int) -> array.array:
        mx.random.seed(seed)
        pieces = []
        for result in model.generate(text=text, ref_audio=str(voice["audio"]), ref_text=voice["text"],
                                     lang_code=language, temperature=temperature, max_tokens=4096, verbose=False):
            if result.sample_rate != SAMPLE_RATE:
                raise RuntimeError("模型输出采样率与预期不符")
            pieces.append(np.asarray(result.audio, dtype=np.float32))
        if not pieces:
            raise RuntimeError("模型没有输出声音")
        audio = np.concatenate(pieces)
        if not np.isfinite(audio).all():
            raise RuntimeError("模型输出无效")
        active = np.flatnonzero(np.abs(audio) > 0.002)
        if len(active):
            audio = audio[max(0, active[0] - round(0.05 * SAMPLE_RATE)):active[-1] + round(0.10 * SAMPLE_RATE)]
        samples = array.array("h")
        samples.frombytes((np.clip(audio, -1.0, 1.0) * 32767).astype("<i2").tobytes())
        if sys.byteorder == "big":
            samples.byteswap()
        mx.clear_cache()
        return samples

    return synthesize


def speak(voice_directory: Path, text: str, out: Path, seed: int = 7, temperature: float = 0.6,
          language: str = "chinese", synthesizer=None) -> dict:
    if language not in LANGUAGES:
        raise RuntimeError("language 只接受 chinese 或 english")
    if not 0 < temperature <= 1.5:
        raise RuntimeError("temperature 需要在 0 到 1.5 之间")
    voice = load_voice(voice_directory)
    units = plan(text, UNIT_MAXIMUM)["units"]
    if not units:
        raise RuntimeError("没有可以朗读的正文")
    synthesize = synthesizer or mlx_synthesizer(voice, temperature, language)
    try:
        out.mkdir(parents=True)
    except FileExistsError as exc:
        raise RuntimeError("输出目录已存在，不覆盖；请换一个目录名") from exc
    preview = array.array("h")
    records = []
    for unit in units:
        samples = synthesize(unit["text"], seed)
        if len(samples) < SAMPLE_RATE // 10:
            raise RuntimeError(f"{unit['id']} 输出过短，请换 seed 重试")
        path = out / f"{unit['id']}.wav"
        write_wav(path, samples)
        start = len(preview) / SAMPLE_RATE
        preview.extend(samples)
        pause = PARAGRAPH_PAUSE if unit["boundary_reason"] == "paragraph_end" else UNIT_PAUSE
        preview.extend(array.array("h", bytes(2 * round(pause * SAMPLE_RATE))))
        records.append({"id": unit["id"], "paragraph_id": unit["paragraph_id"], "text": unit["text"],
                        "file": path.name, "sha256": sha256(path), "start_seconds": round(start, 3),
                        "duration_seconds": round(len(samples) / SAMPLE_RATE, 3),
                        "long_unit_warning": unit["long_unit_warning"]})
    write_wav(out / "preview.wav", preview)
    manifest = {"schema": "video-local-voice-take-1", "model": MODEL_ID, "model_revision": MODEL_REVISION,
                "reference_audio_sha256": voice["audio_sha256"], "reference_uploaded": False,
                "language": language, "seed": seed, "temperature": temperature, "sample_rate": SAMPLE_RATE,
                "units": records, "preview": {"file": "preview.wav", "sha256": sha256(out / "preview.wav"),
                                              "duration_seconds": round(len(preview) / SAMPLE_RATE, 3),
                                              "pauses": "audition_only"},
                "listening_review": "pending"}
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def check() -> dict:
    packages = all(importlib.util.find_spec(name) is not None for name in ("mlx", "mlx_audio", "numpy", "huggingface_hub"))
    model = False
    if packages:
        try:
            cached_model()
            model = True
        except Exception:
            model = False
    return {"platform_supported": supported(), "packages": packages, "model_cached": model,
            "model": MODEL_ID, "model_revision": MODEL_REVISION, "ready": supported() and packages and model}


def fetch_model() -> None:
    if not supported():
        raise RuntimeError("本地配音目前只支持 Apple 芯片的 Mac")
    try:
        from huggingface_hub import snapshot_download
        snapshot_download(MODEL_ID, revision=MODEL_REVISION)
    except ImportError as exc:
        raise RuntimeError("本地配音环境未安装；请运行安装器并加 --with-voice") from exc
    except Exception as exc:
        raise RuntimeError("配音模型下载未完成；检查网络后重试，已下载的部分会续传") from exc


def read_text(args: argparse.Namespace) -> str:
    if (args.text is None) == (args.text_file is None):
        raise RuntimeError("--text 与 --text-file 需要二选一")
    return args.text if args.text is not None else args.text_file.read_text(encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="报告本地配音是否就绪")
    commands.add_parser("fetch-model", help="下载固定版本的模型（只下载模型，不上传任何文件）")
    item = commands.add_parser("prepare", help="把一段本人录音整理成音色目录")
    item.add_argument("--input", type=Path, required=True)
    item.add_argument("--text")
    item.add_argument("--text-file", type=Path)
    item.add_argument("--out", type=Path, required=True)
    item = commands.add_parser("speak", help="用音色目录朗读一段文字，供试听")
    item.add_argument("--voice", type=Path, required=True)
    item.add_argument("--text")
    item.add_argument("--text-file", type=Path)
    item.add_argument("--out", type=Path, required=True)
    item.add_argument("--seed", type=int, default=7)
    item.add_argument("--temperature", type=float, default=0.6)
    item.add_argument("--language", choices=LANGUAGES, default="chinese")
    args = parser.parse_args()
    try:
        if args.command == "check":
            result = check()
        elif args.command == "fetch-model":
            fetch_model()
            result = {"model_cached": True}
        elif args.command == "prepare":
            result = prepare(args.input, read_text(args), args.out)
        else:
            result = speak(args.voice, read_text(args), args.out, args.seed, args.temperature, args.language)
    except (RuntimeError, OSError, ValueError, UnicodeError) as exc:
        print("本地配音未完成：" + safe_message(str(exc)))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
