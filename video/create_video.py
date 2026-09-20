import os
import subprocess
from pathlib import Path

from PIL import Image


WIDTH = 1080
HEIGHT = 1920
FPS = 30
DURATION = 5


def prepare_image(source, output):
    image = Image.open(source).convert("RGB")

    # Scale image so it completely fits inside the 1080x1920 canvas.
    scale = min(WIDTH / image.width, HEIGHT / image.height)

    new_width = int(image.width * scale)
    new_height = int(image.height * scale)

    image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    canvas = Image.new("RGB", (WIDTH, HEIGHT))
    x = (WIDTH - new_width) // 2
    y = (HEIGHT - new_height) // 2

    canvas.paste(image, (x, y))
    canvas.save(output, quality=95)


def create_video(image_path, video_path):
    command = [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-i",
        str(image_path),
        "-t",
        str(DURATION),
        "-r",
        str(FPS),
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(video_path),
    ]

    subprocess.run(command, check=True)


def main():
    source_dir = Path("work/source")
    output_dir = Path("work/output")

    output_dir.mkdir(parents=True, exist_ok=True)

    images = [
        file
        for file in source_dir.iterdir()
        if file.suffix.lower() in {
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
            ".gif",
        }
    ]

    if not images:
        raise RuntimeError("No source images found.")

    for source in images:
        prepared = output_dir / f"{source.stem}_prepared.jpg"
        video = output_dir / f"{source.stem}.mp4"

        prepare_image(source, prepared)
        create_video(prepared, video)

        prepared.unlink()

        print(f"Created: {video}")


if __name__ == "__main__":
    main()
