import os

import numpy as np
from PIL import Image

from arxiv_sanity_bot.logger import get_logger


logger = get_logger(__name__)


# Twitter-friendly envelope. Short side floor catches degenerate strips that
# pypdf sometimes yields; the aspect cap matches Twitter's safe display ratio;
# the byte cap is well under the 5 MB media/upload limit.
MIN_SHORT_SIDE = 120
MAX_ASPECT_RATIO = 3.0
MAX_FILE_BYTES = 4 * 1024 * 1024


def has_image_content(image_path: str, min_std: float = 10.0) -> bool:
    try:
        with Image.open(image_path) as img:
            img_array = np.array(img.convert("L"))
            std_dev = np.std(img_array)
            if std_dev < min_std:
                logger.info(
                    f"Image {image_path} has low variance (std={std_dev:.2f}), likely empty"
                )
                return False
            return True
    except Exception as e:
        logger.info(f"Failed to validate image content: {str(e)}")
        return False


def is_uploadable(image_path: str) -> bool:
    """Reject images Twitter is likely to refuse: too thin, too elongated, too big."""
    try:
        size_bytes = os.path.getsize(image_path)
        if size_bytes > MAX_FILE_BYTES:
            logger.info(
                f"Image {image_path} too large ({size_bytes} bytes > {MAX_FILE_BYTES})"
            )
            return False
        with Image.open(image_path) as img:
            w, h = img.size
        short = min(w, h)
        if short < MIN_SHORT_SIDE:
            logger.info(f"Image {image_path} short side {short}px < {MIN_SHORT_SIDE}px")
            return False
        ratio = max(w, h) / max(short, 1)
        if ratio > MAX_ASPECT_RATIO:
            logger.info(
                f"Image {image_path} aspect ratio {ratio:.2f} > {MAX_ASPECT_RATIO}"
            )
            return False
        return True
    except Exception as e:
        logger.info(f"Failed to validate image for upload: {str(e)}")
        return False
