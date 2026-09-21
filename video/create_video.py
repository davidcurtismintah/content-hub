import subprocess
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps


# ============================================================
# VIDEO SETTINGS
# ============================================================

WIDTH = 1080
HEIGHT = 1920
FPS = 30
DURATION = 3

# Match the user's editor positioning.
IMAGE_ZOOM = 0.90
IMAGE_X = 0
IMAGE_Y = -120

BACKGROUND = (0, 0, 0)


# ============================================================
# BRIGHT BACKGROUND DETECTION
# ============================================================

def get_background_brightness(image):
    """
    Estimate the background brightness by sampling the edges
    and corners of the image.

    Text-heavy screenshots normally have relatively large
    areas of background around the text, so edge sampling
    gives us a useful approximation without needing OCR.
    """

    image = image.convert("RGB")

    width, height = image.size

    sample_points = [
        (0.02, 0.02),
        (0.50, 0.02),
        (0.98, 0.02),
        (0.02, 0.50),
        (0.98, 0.50),
        (0.02, 0.98),
        (0.50, 0.98),
        (0.98, 0.98),
    ]

    brightness_values = []

    for x_ratio, y_ratio in sample_points:
        x = min(width - 1, int(width * x_ratio))
        y = min(height - 1, int(height * y_ratio))

        r, g, b = image.getpixel((x, y))

        # Perceived brightness.
        brightness = (
            0.299 * r +
            0.587 * g +
            0.114 * b
        )

        brightness_values.append(brightness)

    return sum(brightness_values) / len(brightness_values)


def should_apply_gray_filter(image):
    """
    Return True when the image background appears too bright
    for the white Shorts interface controls.
    """

    brightness = get_background_brightness(image)

    # Bright backgrounds get the grayscale treatment.
    return brightness >= 175


# ============================================================
# IMAGE FILTER
# ============================================================

def apply_gray_filter(image):
    """
    Convert a bright screenshot to grayscale while improving
    contrast so text remains easy to read.
    """

    gray = ImageOps.grayscale(image)

    # Slight contrast boost keeps text crisp.
    gray = ImageEnhance.Contrast(gray).enhance(1.15)

    # Convert back to RGB for video encoding.
    return gray.convert("RGB")


# ============================================================
# PREPARE IMAGE
# ============================================================

def prepare_image(source_path, output_path):

    image = Image.open(source_path).convert("RGB")

    # --------------------------------------------------------
    # Decide whether the background needs treatment.
    # --------------------------------------------------------

    brightness = get_background_brightness(image)

    print(
        f"Background brightness: {brightness:.1f}"
    )

    if should_apply_gray_filter(image):

        print(
            "Bright background detected. "
            "Applying grayscale filter."
        )

        image = apply_gray_filter(image)

    else:

        print(
            "Dark background detected. "
            "Keeping original colors."
        )

    # --------------------------------------------------------
    # Fit the complete image inside the Shorts canvas.
    # --------------------------------------------------------

    source_width, source_height = image.size

    fit_scale = min(
        WIDTH / source_width,
        HEIGHT / source_height
    )

    fitted_width = source_width * fit_scale
    fitted_height = source_height * fit_scale

    # --------------------------------------------------------
    # Apply 90% zoom.
    # --------------------------------------------------------

    final_width = int(
        fitted_width * IMAGE_ZOOM
    )

    final_height = int(
        fitted_height * IMAGE_ZOOM
    )

    image = image.resize(
        (final_width, final_height),
        Image.Resampling.LANCZOS
    )

    # --------------------------------------------------------
    # Create Shorts canvas.
    # --------------------------------------------------------

    canvas = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        BACKGROUND
    )

    # X = 0 means no horizontal adjustment.
    x = int(
        (WIDTH - final_width) / 2
    ) + IMAGE_X

    # Y = -120 moves the image upward.
    y = int(
        (HEIGHT - final_height) / 2
    ) + IMAGE_Y

    canvas.paste(
        image,
        (x, y)
    )

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
        "20",

        "-pix_fmt",
        "yuv420p",

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
        and file.suffix.lower()
        in supported_extensions
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

        print(
            f"Processing: {source.name}"
        )

        prepare_image(
            source,
            prepared_image
        )

        create_video(
            prepared_image,
            video_file
        )

        prepared_image.unlink()

        print(
            f"Created: {video_file}"
        )


if __name__ == "__main__":
    main()
