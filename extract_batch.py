#!/usr/bin/env python3
"""Run slide extraction for a list of YouTube URLs sequentially."""

from __future__ import annotations

import argparse
import math
import subprocess
from pathlib import Path
from urllib.parse import parse_qs, urlparse


def video_id(url: str) -> str:
    parsed = urlparse(url)
    query_id = parse_qs(parsed.query).get("v", [None])[0]
    if query_id:
        return query_id

    parts = [part for part in parsed.path.split("/") if part]
    if parts and parts[0] in {"embed", "shorts", "live"} and len(parts) > 1:
        return parts[1]
    if parts:
        return parts[-1]
    return "youtube_video"


def run(cmd: list[str]) -> None:
    print("+ " + " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def page_count(pdf_path: Path) -> int:
    data = pdf_path.read_bytes()
    return data.count(b"/Type /Page ")


def make_overview(out_dir: Path) -> None:
    slides_dir = out_dir / "slides"
    count = len(list(slides_dir.glob("slide_*.jpg")))
    if count == 0:
        return
    cols = 5
    rows = math.ceil(count / cols)
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-y",
            "-framerate",
            "1",
            "-i",
            str(slides_dir / "slide_%03d.jpg"),
            "-vf",
            f"scale=320:-1,tile={cols}x{rows}",
            "-frames:v",
            "1",
            "-update",
            "1",
            str(out_dir / "slides_overview.jpg"),
        ]
    )


def load_urls(args: argparse.Namespace) -> list[str]:
    urls = list(args.urls)
    if args.urls_file:
        lines = Path(args.urls_file).read_text(encoding="utf-8").splitlines()
        urls.extend(line.strip() for line in lines if line.strip() and not line.startswith("#"))
    if not urls:
        raise SystemExit("Provide at least one URL or --urls-file.")
    return urls


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("urls", nargs="*")
    parser.add_argument("--urls-file", help="Text file containing one URL per line.")
    parser.add_argument("--output-root", default="output")
    args = parser.parse_args()

    urls = load_urls(args)
    output_root = Path(args.output_root)
    rows: list[tuple[int, str, int, Path]] = []
    for index, url in enumerate(urls, 1):
        vid = video_id(url)
        out_dir = output_root / vid
        pdf_path = out_dir / "slides_reference.pdf"
        print(f"\n[{index:02d}/{len(urls):02d}] {vid}", flush=True)
        if not pdf_path.exists():
            run(["python3", "extract_youtube_slides.py", "--out", str(out_dir), url])
        else:
            print(f"Skip existing PDF: {pdf_path}", flush=True)

        make_overview(out_dir)
        pages = page_count(pdf_path)
        rows.append((index, vid, pages, pdf_path))
        print(f"Done {vid}: {pages} pages", flush=True)

    report = output_root / "batch_index.md"
    lines = ["# YouTube slide extraction results", ""]
    lines.append("| # | Video ID | Pages | PDF | Overview |")
    lines.append("|---:|---|---:|---|---|")
    for index, vid, pages, pdf_path in rows:
        out_dir = pdf_path.parent
        lines.append(
            f"| {index} | `{vid}` | {pages} | "
            f"[PDF]({pdf_path.as_posix()}) | "
            f"[Overview]({(out_dir / 'slides_overview.jpg').as_posix()}) |"
        )
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nReport: {report}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
