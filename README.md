# YouTube Slide Extractor

YouTube presentation videos often contain useful reference slides, but taking
screenshots one by one is slow. This project downloads a YouTube video, samples
frames at a fixed interval, removes near-duplicate frames, and exports the
remaining slide-like frames as individual JPEG images and a single PDF.

The tool is designed for personal reference workflows such as preparing a
presentation or reviewing a recorded talk.

## Features

- Download a single YouTube video with `yt-dlp`.
- Extract candidate frames with `ffmpeg`.
- Remove blank and near-duplicate frames.
- Save extracted slides as numbered JPEG files.
- Create a lightweight PDF from the extracted slide images.
- Process multiple URLs sequentially with a batch script.

## Requirements

- Python 3.10 or newer
- `yt-dlp`
- `ffmpeg`

On macOS with Homebrew:

```bash
brew install yt-dlp ffmpeg
```

No third-party Python packages are required.

## Important: keep yt-dlp updated

YouTube frequently changes its player and download behavior. When that happens,
older `yt-dlp` versions may fail to download videos, produce extractor errors,
or require extra challenge-solving support.

If downloads start failing, update `yt-dlp` first:

```bash
brew upgrade yt-dlp
```

Also update Homebrew packages when needed:

```bash
brew update
brew upgrade
```

If you installed `yt-dlp` by another method, follow that method's update
command. For example, standalone `yt-dlp` installs often use:

```bash
yt-dlp -U
```

Homebrew-managed `yt-dlp` should be updated with `brew upgrade yt-dlp`, not
`yt-dlp -U`.

## Usage

### Extract slides from one video

```bash
python3 extract_youtube_slides.py "https://youtu.be/VIDEO_ID"
```

By default, output is written to:

```text
output/youtube_slides/
```

The main files are:

```text
output/youtube_slides/slides_reference.pdf
output/youtube_slides/slides/
output/youtube_slides/work/raw_frames/
```

Use a custom output folder:

```bash
python3 extract_youtube_slides.py \
  --out output/my_video \
  "https://youtu.be/VIDEO_ID"
```

### Process multiple videos

Pass URLs directly:

```bash
python3 extract_batch.py \
  "https://youtu.be/VIDEO_ID_1" \
  "https://youtu.be/VIDEO_ID_2"
```

Or use a text file with one URL per line:

```bash
python3 extract_batch.py --urls-file urls.example.txt
```

Batch output is written under `output/<video_id>/`, and a summary file is
created at:

```text
output/batch_index.md
```

## Tuning

The default frame sampling interval is 1 second. This is conservative enough
for most presentation videos and reduces the chance of missing slowly appearing
title slides.

For even more aggressive capture:

```bash
python3 extract_youtube_slides.py --sample-interval 0.5 "https://youtu.be/VIDEO_ID"
```

For fewer candidate frames and faster processing:

```bash
python3 extract_youtube_slides.py --sample-interval 2.0 "https://youtu.be/VIDEO_ID"
```

If too many similar slides are kept, increase `--dedupe-distance`. If distinct
slides are being merged, decrease it.

## GitHub notes

Generated results are intentionally ignored by Git:

```text
output/
```

This keeps PDFs, extracted images, raw frames, and downloaded video cache files
out of the repository. Commit the scripts and documentation only.

## Copyright and usage

This tool extracts images from videos for reference workflows. Make sure you
have the right to download, store, and use the extracted material for your
intended purpose. Avoid redistributing extracted slides unless you have
permission.
