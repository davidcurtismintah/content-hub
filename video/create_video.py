import subprocess
from pathlib import Path

from PIL import Image


# ============================================================
# VIDEO SETTINGS
# ============================================================

WIDTH = 1080
HEIGHT = 1920
FPS = 30
DURATION = 3

# Match the positioning used in the video editor.
IMAGE_ZOOM = 0.90
IMAGE_X = 0
IMAGE_Y = -60

# Background behind the source image.
BACKGROUND = (0, 0, 0)


# ============================================================
# PREPARE IMAGE
# ============================================================

def prepare_image(source_path, output_path):
    image = Image.open(source_path).convert("RGB")

    source_width, source_height = image.size

    # --------------------------------------------------------
    # First calculate the largest size that fits the complete
    # source image inside the 1080x1920 canvas.
    # --------------------------------------------------------

    fit_scale = min(
        WIDTH / source_width,
        HEIGHT / source_height
    )

    fitted_width = source_width * fit_scale
    fitted_height = source_height * fit_scale

    # --------------------------------------------------------
    # Apply the 90% zoom.
    # --------------------------------------------------------

    final_width = int(fitted_width * IMAGE_ZOOM)
    final_height = int(fitted_height * IMAGE_ZOOM)

    image = image.resize(
        (final_width, final_height),
        Image.Resampling.LANCZOS
    )

    # --------------------------------------------------------
    # Create the 1080x1920 Shorts canvas.
    # --------------------------------------------------------

    canvas = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        BACKGROUND
    )

    # --------------------------------------------------------
    # X = 0 means horizontally centered.
    #
    # Y = -60 means move the image 60 pixels upward.
    # --------------------------------------------------------

    x = int((WIDTH - final_width) / 2) + IMAGE_X
    y = int((HEIGHT - final_height) / 2) + IMAGE_Y

    canvas.paste(image, (x, y))

    canvas.save(
        output_path,
        format="JPEG",
        quality=95
    )


# ============================================================
# CREATE VIDEO
# ============================================================

def create_video(image_path, video_path):

    command = [
        "ffmpeg",
        "-y",

        # Turn the image into a video stream.
        "-loop",
        "1",

        "-i",
        str(image_path),

        # Exact 3-second duration.
        "-t",
        str(DURATION),

        # Shorts frame rate.
        "-r",
        str(FPS),

        # H.264 video.
        "-c:v",
        "libx264",

        # Good quality while keeping the file reasonable.
        "-preset",
        "veryfast",
        "-crf",
        "20",

        # Required for broad compatibility.
        "-pix_fmt",
        "yuv420p",

        # Helps with web/video platforms.
        "-movflags",
        "+faststart",

        str(video_path)
    ]

    subprocess.run(
        command,
        check=True
    )


# ============================================================
# MAIN
# ============================================================

def main():

    source_dir = Path("work/source")
    output_dir = Path("work/output")

    source_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    supported_extensions = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".gif"
    }

    images = [
        file
        for file in source_dir.iterdir()
        if file.is_file()
        and file.suffix.lower() in supported_extensions
    ]

    if not images:
        raise RuntimeError(
            "No source images found in work/source."
        )

    for source in images:

        prepared_image = (
            output_dir /
            f"{source.stem}_prepared.jpg"
        )

        video_file = (
            output_dir /
            f"{source.stem}.mp4"
        )

        print(f"Processing: {source.name}")

        prepare_image(
            source,
            prepared_image
        )

        create_video(
            prepared_image,
            video_file
        )

        # Remove temporary prepared image.
        prepared_image.unlink()

        print(
            f"Created: {video_file}"
        )


if __name__ == "__main__":
    main()
