#!/usr/bin/env python3
"""Extract likely slide images from a YouTube presentation video.

Requires:
  - yt-dlp
  - ffmpeg / ffprobe

The script downloads one YouTube video, samples frames at a fixed interval,
removes near-duplicate frames with a simple perceptual hash, and writes a
JPEG-backed PDF for quick review.
"""

from __future__ import annotations

import argparse
import glob
import shutil
import struct
import subprocess
from pathlib import Path


def run(cmd: list[str], *, capture: bool = False, echo: bool = True) -> subprocess.CompletedProcess:
    if echo:
        print("+ " + " ".join(cmd))
    return subprocess.run(
        cmd,
        check=True,
        text=False if capture else True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def require_tool(name: str) -> None:
    if shutil.which(name) is None:
        raise SystemExit(f"Missing required tool: {name}")


def download_video(url: str, work_dir: Path, height: int) -> Path:
    out_tpl = str(work_dir / "source.%(ext)s")
    run(
        [
            "yt-dlp",
            "--no-playlist",
            "-f",
            f"bv*[height<={height}]+ba/b[height<={height}]/best",
            "--merge-output-format",
            "mp4",
            "-o",
            out_tpl,
            url,
        ]
    )

    matches = sorted(glob.glob(str(work_dir / "source.*")))
    videos = [Path(p) for p in matches if Path(p).suffix.lower() in {".mp4", ".mkv", ".webm"}]
    if not videos:
        raise SystemExit("Could not find downloaded video.")
    return videos[0]


def extract_interval_frames(video: Path, interval_dir: Path, interval: float, width: int) -> None:
    interval_dir.mkdir(parents=True, exist_ok=True)
    for existing in interval_dir.glob("*.jpg"):
        existing.unlink()

    vf = f"fps=1/{interval},scale={width}:-2"
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-y",
            "-i",
            str(video),
            "-vf",
            vf,
            "-q:v",
            "2",
            str(interval_dir / "sample_%05d.jpg"),
        ]
    )


def frame_time(path: Path) -> float:
    try:
        return float(path.stem.rsplit("_", 1)[1])
    except (IndexError, ValueError):
        return 0.0


def extract_candidate_frames(video: Path, raw_dir: Path, interval: float, width: int) -> None:
    extract_interval_frames(video, raw_dir, interval, width)


def frame_hash(path: Path, hash_size: int) -> int:
    proc = run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(path),
            "-vf",
            f"scale={hash_size}:{hash_size},format=gray",
            "-frames:v",
            "1",
            "-f",
            "rawvideo",
            "pipe:1",
        ],
        capture=True,
        echo=False,
    )
    pixels = proc.stdout
    avg = sum(pixels) / len(pixels)
    value = 0
    for idx, pixel in enumerate(pixels):
        if pixel >= avg:
            value |= 1 << idx
    return value


def frame_stats(path: Path, stat_size: int) -> tuple[float, float]:
    proc = run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(path),
            "-vf",
            f"scale={stat_size}:{stat_size},format=gray",
            "-frames:v",
            "1",
            "-f",
            "rawvideo",
            "pipe:1",
        ],
        capture=True,
        echo=False,
    )
    pixels = proc.stdout
    avg = sum(pixels) / len(pixels)
    variance = sum((pixel - avg) ** 2 for pixel in pixels) / len(pixels)
    return avg, variance ** 0.5


def is_blank_frame(path: Path, stat_size: int, brightness: float, stddev: float) -> bool:
    avg, spread = frame_stats(path, stat_size)
    return avg >= brightness and spread <= stddev


def hamming_distance(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def dedupe_frames(
    raw_dir: Path,
    slides_dir: Path,
    distance: int,
    hash_size: int,
    blank_brightness: float,
    blank_stddev: float,
) -> list[Path]:
    slides_dir.mkdir(parents=True, exist_ok=True)
    for existing in slides_dir.glob("*.jpg"):
        existing.unlink()

    kept: list[Path] = []
    last_hash: int | None = None
    for frame in sorted(raw_dir.glob("*.jpg"), key=lambda item: (frame_time(item), item.name)):
        if is_blank_frame(frame, hash_size, blank_brightness, blank_stddev):
            continue

        current_hash = frame_hash(frame, hash_size)
        if last_hash is not None and hamming_distance(last_hash, current_hash) <= distance:
            continue

        out = slides_dir / f"slide_{len(kept) + 1:03d}.jpg"
        shutil.copyfile(frame, out)
        kept.append(out)
        last_hash = current_hash

    return kept


def jpeg_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    idx = 2
    while idx < len(data):
        if data[idx] != 0xFF:
            idx += 1
            continue
        marker = data[idx + 1]
        idx += 2
        if marker in {0xD8, 0xD9}:
            continue
        length = struct.unpack(">H", data[idx : idx + 2])[0]
        if marker in {
            0xC0,
            0xC1,
            0xC2,
            0xC3,
            0xC5,
            0xC6,
            0xC7,
            0xC9,
            0xCA,
            0xCB,
            0xCD,
            0xCE,
            0xCF,
        }:
            height, width = struct.unpack(">HH", data[idx + 3 : idx + 7])
            return width, height
        idx += length
    raise ValueError(f"Could not read JPEG dimensions: {path}")


def write_pdf(images: list[Path], pdf_path: Path) -> None:
    if not images:
        raise SystemExit("No slides were extracted.")

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    objects: list[bytes] = []
    pages: list[int] = []

    catalog_id = 1
    pages_id = 2
    next_id = 3

    for image_path in images:
        image_data = image_path.read_bytes()
        width, height = jpeg_size(image_path)
        image_id = next_id
        content_id = next_id + 1
        page_id = next_id + 2
        next_id += 3

        image_obj = (
            f"<< /Type /XObject /Subtype /Image /Width {width} /Height {height} "
            f"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode "
            f"/Length {len(image_data)} >>\nstream\n"
        ).encode("ascii") + image_data + b"\nendstream"
        objects.append(image_obj)

        content = f"q {width} 0 0 {height} 0 0 cm /Im0 Do Q".encode("ascii")
        content_obj = (
            f"<< /Length {len(content)} >>\nstream\n".encode("ascii")
            + content
            + b"\nendstream"
        )
        objects.append(content_obj)

        page_obj = (
            f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 {width} {height}] "
            f"/Resources << /XObject << /Im0 {image_id} 0 R >> >> "
            f"/Contents {content_id} 0 R >>"
        ).encode("ascii")
        objects.append(page_obj)
        pages.append(page_id)

    kids = " ".join(f"{page_id} 0 R" for page_id in pages)
    page_tree = f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode("ascii")
    catalog = f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode("ascii")

    ordered = [catalog, page_tree] + objects
    offsets: list[int] = []
    with pdf_path.open("wb") as pdf:
        pdf.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        for obj_id, obj in enumerate(ordered, start=1):
            offsets.append(pdf.tell())
            pdf.write(f"{obj_id} 0 obj\n".encode("ascii"))
            pdf.write(obj)
            pdf.write(b"\nendobj\n")

        xref = pdf.tell()
        pdf.write(f"xref\n0 {len(ordered) + 1}\n".encode("ascii"))
        pdf.write(b"0000000000 65535 f \n")
        for offset in offsets:
            pdf.write(f"{offset:010d} 00000 n \n".encode("ascii"))
        pdf.write(
            (
                f"trailer\n<< /Size {len(ordered) + 1} /Root {catalog_id} 0 R >>\n"
                f"startxref\n{xref}\n%%EOF\n"
            ).encode("ascii")
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--out", default="output/youtube_slides")
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--sample-interval", type=float, default=1.0)
    parser.add_argument("--dedupe-distance", type=int, default=7)
    parser.add_argument("--hash-size", type=int, default=16)
    parser.add_argument("--blank-brightness", type=float, default=238.0)
    parser.add_argument("--blank-stddev", type=float, default=12.0)
    parser.add_argument("--keep-video", action="store_true")
    args = parser.parse_args()

    require_tool("yt-dlp")
    require_tool("ffmpeg")

    out_dir = Path(args.out)
    work_dir = out_dir / "work"
    raw_dir = work_dir / "raw_frames"
    slides_dir = out_dir / "slides"
    work_dir.mkdir(parents=True, exist_ok=True)

    video = download_video(args.url, work_dir, args.height)
    extract_candidate_frames(video, raw_dir, args.sample_interval, args.width)
    slides = dedupe_frames(
        raw_dir,
        slides_dir,
        args.dedupe_distance,
        args.hash_size,
        args.blank_brightness,
        args.blank_stddev,
    )
    pdf_path = out_dir / "slides_reference.pdf"
    write_pdf(slides, pdf_path)

    if not args.keep_video:
        video.unlink(missing_ok=True)

    print()
    print(f"Extracted slides: {len(slides)}")
    print(f"Images: {slides_dir}")
    print(f"PDF: {pdf_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
