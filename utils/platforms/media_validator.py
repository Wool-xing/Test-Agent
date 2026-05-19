# SPDX-License-Identifier: MIT
"""
音视频校验：FFmpeg 元信息 / 帧抽取 / SSIM / 音画同步
被引用方：13-系统集成测试 agent
依赖：FFmpeg + ffprobe（系统安装）+ ffmpeg-python（pip）
"""
import json
import logging
import os
import subprocess
from fractions import Fraction
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)

FFMPEG = os.getenv("FFMPEG_BIN", "ffmpeg")
FFPROBE = os.getenv("FFPROBE_BIN", "ffprobe")


def get_video_meta(path: str) -> Dict:
    """通过 ffprobe 读取视频元信息"""
    cmd = [
        FFPROBE, "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", path,
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    info = json.loads(out)

    fmt = info.get("format", {})
    video = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), {})
    audio = next((s for s in info.get("streams", []) if s.get("codec_type") == "audio"), {})

    return {
        "duration_sec": float(fmt.get("duration", 0)),
        "size_mb": round(int(fmt.get("size", 0)) / 1024 / 1024, 2),
        "bitrate_kbps": round(int(fmt.get("bit_rate", 0)) / 1000),
        "format_name": fmt.get("format_name"),
        "width": video.get("width"),
        "height": video.get("height"),
        "video_codec": video.get("codec_name"),
        "fps": float(Fraction(video["r_frame_rate"])) if video.get("r_frame_rate") else None,
        "audio_codec": audio.get("codec_name"),
        "audio_sample_rate": audio.get("sample_rate"),
    }


def extract_frame(video: str, timestamp_sec: float, output: str) -> str:
    """抽取指定时间点的帧"""
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        FFMPEG, "-y", "-ss", str(timestamp_sec),
        "-i", video, "-frames:v", "1",
        output,
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return output


def compare_frames(video_a: str, video_b: str, timestamps: List[float],
                   ssim_threshold: float = 0.95,
                   tmp_dir: str = "workspace/执行日志/media-frames") -> List[Dict]:
    """
    在指定时间点抽帧对比两个视频，返回差异帧列表。
    """
    from utils.protocols.visual_helper import compare_images

    Path(tmp_dir).mkdir(parents=True, exist_ok=True)
    diffs = []
    for ts in timestamps:
        f_a = f"{tmp_dir}/a_{ts:.2f}.png"
        f_b = f"{tmp_dir}/b_{ts:.2f}.png"
        extract_frame(video_a, ts, f_a)
        extract_frame(video_b, ts, f_b)
        result = compare_images(f_a, f_b, threshold=ssim_threshold)
        if not result.get("pass"):
            diffs.append({"timestamp": ts, "similarity": result.get("similarity")})
    return diffs


def check_audio_sync(video: str) -> float:
    """
    简化版音画同步检测：返回偏移 ms（正=音频提前，负=视频提前）。
    生产环境建议用 ffmpeg lavfi `astreamselect` + 视频帧亮度脉冲对齐。
    """
    cmd = [
        FFPROBE, "-v", "quiet", "-print_format", "json",
        "-show_streams", "-select_streams", "a:0", video,
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    info = json.loads(out)
    streams = info.get("streams", [])
    if not streams:
        return 0.0
    start_time = float(streams[0].get("start_time", 0))
    return start_time * 1000  # 秒 → ms


# ===== CLI =====

def main():
    import argparse
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="音视频校验工具")
    sub = parser.add_subparsers(dest="cmd")

    meta = sub.add_parser("meta")
    meta.add_argument("video")

    extract = sub.add_parser("extract")
    extract.add_argument("video")
    extract.add_argument("--at", type=float, required=True)
    extract.add_argument("--output", required=True)

    args = parser.parse_args()
    if args.cmd == "meta":
        print(json.dumps(get_video_meta(args.video), indent=2, ensure_ascii=False))
    elif args.cmd == "extract":
        extract_frame(args.video, args.at, args.output)


if __name__ == "__main__":
    main()
