#!/usr/bin/env python3
"""videos/ 의 원본 영상을 웹용으로 변환해서 site/assets/media/ 로 복사한다. (폴더 구조 유지)

  .gif                  → H.264 mp4 (용량이 수 배 줄고 재생이 부드럽다). 프레임이 1장뿐이면 → png
  .mp4 / .mov / ...     → H.264 mp4, faststart
                          이미 H.264 이고 1920px · 30fps · 30MB 이하면 재인코딩 없이 remux,
                          아니면 폭 1920px / 30fps 이하로 줄여서 재인코딩 (GitHub 100MB 제한 대비)
  파일명의 공백 등은 '-' 로 바꾼다. 원본이 사라진 사본은 지운다.

    uv run python scripts/build_media.py      # 또는 make media
"""

from __future__ import annotations

import json
import re
import subprocess
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "videos"
DST = ROOT / "site" / "assets" / "media"
EXTS = {".gif", ".mp4", ".mov", ".webm", ".mkv", ".m4v"}
MAX_W, MAX_FPS, MAX_REMUX_BYTES = 1920, 30, 30 << 20


def probe(path: Path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=codec_name,width,height,avg_frame_rate", "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    )  # fmt: skip
    streams = json.loads(out.stdout).get("streams", [])
    return streams[0] if streams else {}


def frame_count(path: Path) -> int:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
         "-show_entries", "stream=nb_read_frames", "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    )  # fmt: skip
    streams = json.loads(out.stdout).get("streams", [])
    return int(streams[0].get("nb_read_frames", 0)) if streams else 0


def slug(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-")


def target(src: Path) -> Path:
    ext = ".png" if src.suffix.lower() == ".gif" and frame_count(src) <= 1 else ".mp4"
    rel = src.relative_to(SRC)
    return DST / rel.parent / (slug(rel.stem) + ext)


def convert(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    base = ["ffmpeg", "-loglevel", "error", "-y", "-i", str(src)]
    if dst.suffix == ".png":  # 정지 이미지
        subprocess.run(base + ["-frames:v", "1", str(dst)], check=True)
        return

    info = probe(src)
    w = int(info.get("width", 0))
    fps = float(Fraction(info.get("avg_frame_rate", "0/1") or "0/1")) if info.get("avg_frame_rate") != "0/0" else 0
    remux_ok = (
        src.suffix.lower() != ".gif"
        and info.get("codec_name") == "h264"
        and w <= MAX_W
        and fps <= MAX_FPS + 0.5
        and src.stat().st_size <= MAX_REMUX_BYTES
    )
    if remux_ok:
        cmd = base + ["-c", "copy", "-an", "-movflags", "+faststart", str(dst)]
    else:
        vf = [f"scale='min({MAX_W},iw)':-2", "scale=trunc(iw/2)*2:trunc(ih/2)*2"]  # H.264 는 짝수 해상도만
        if fps > MAX_FPS + 0.5:
            vf.append(f"fps={MAX_FPS}")
        cmd = base + [
            "-an", "-c:v", "libx264", "-crf", "22", "-preset", "medium", "-pix_fmt", "yuv420p",
            "-vf", ",".join(vf), "-movflags", "+faststart", str(dst),
        ]  # fmt: skip
    subprocess.run(cmd, check=True)


def main() -> None:
    files = sorted(p for p in SRC.rglob("*") if p.is_file() and p.suffix.lower() in EXTS)
    produced = set()
    for src in files:
        dst = target(src)
        produced.add(dst)
        if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
            continue
        convert(src, dst)
        print(f"  {src.relative_to(ROOT)}  →  {dst.relative_to(ROOT)}  ({src.stat().st_size >> 10} KB → {dst.stat().st_size >> 10} KB)")

    # 원본이 사라진 사본 정리
    for f in sorted(DST.rglob("*")):
        if f.is_file() and f not in produced:
            print(f"  (stale) removing {f.relative_to(ROOT)}")
            f.unlink()
    for d in sorted((d for d in DST.rglob("*") if d.is_dir()), reverse=True):
        if not any(d.iterdir()):
            d.rmdir()
    print(f"✔ {len(files)} files in {DST.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
