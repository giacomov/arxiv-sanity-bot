import numpy as np
from PIL import Image

from arxiv_sanity_bot.logger import get_logger


logger = get_logger(__name__)


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
