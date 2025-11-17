import os
from typing import Any

import arxiv  # type: ignore
import pypdf  # type: ignore
import pypdf.errors  # type: ignore
from PIL import Image

from arxiv_sanity_bot.arxiv.extract_graph import extract_graph
from arxiv_sanity_bot.arxiv.image_validation import has_image_content
from arxiv_sanity_bot.config import ARXIV_NUM_RETRIES
from arxiv_sanity_bot.logger import get_logger


logger = get_logger(__name__)


def extract_first_image(arxiv_id: str, pdf_path: str | None = None) -> str | None:
    """
    Extract the first image from the PDF.

    If the PDF contains both an image and a graph, the first that is encountered is returned. If both the image and
    the graph are on the same page, the image is returned.

    :param arxiv_id: the arxiv ID
    :return: the path to the first image as a local file, or None if none was found
    """

    if pdf_path is None:
        pdf_path = download_paper(arxiv_id)

    if pdf_path is None:
        return None

    # Find first bitmap (if any)
    image_file, image_page_number = extract_image(pdf_path, arxiv_id)

    # Find first graph (if any)
    graph_file, graph_page_number = extract_graph(pdf_path, arxiv_id)

    # We select whichever comes first.
    filename = _select_image_or_graph(
        graph_file, graph_page_number, image_file, image_page_number
    )

    if filename is not None:
        new_filename = f"{arxiv_id}_image1.jpg"
        _convert_to_jpeg(filename, new_filename)
        return new_filename

    else:
        return None


def _convert_to_jpeg(input_path: str, output_path: str):
    with Image.open(input_path) as img:
        max_size = 500
        if max(img.size) > max_size:
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        img.convert("RGB").save(output_path, "JPEG", quality=85)


def select_first_image(graph_file: str | None, graph_page_number: int | None, image_file: str | None, image_page_number: int | None) -> str | None:
    logger.info("Found both bitmap and graph images. Selecting the one that comes first")
    if image_page_number is not None and graph_page_number is not None:
        return image_file if image_page_number <= graph_page_number else graph_file
    return image_file or graph_file


def select_graph(graph_file: str | None, graph_page_number: int | None, image_file: str | None, image_page_number: int | None) -> str | None:
    logger.info("Only graph found. Selecting that")
    return graph_file


def select_image(graph_file: str | None, graph_page_number: int | None, image_file: str | None, image_page_number: int | None) -> str | None:
    logger.info("Only bitmap image found. Selecting that")
    return image_file


def no_image_or_graph(graph_file: str | None, graph_page_number: int | None, image_file: str | None, image_page_number: int | None) -> str | None:
    logger.info("NO IMAGE NOR GRAPH FOUND")
    return None


def _select_image_or_graph(
    graph_file: str | None, graph_page_number: int | None, image_file: str | None, image_page_number: int | None
) -> str | None:
    # My logic
    if image_file is not None and graph_file is not None:
        return select_first_image(
            graph_file, graph_page_number, image_file, image_page_number
        )
    if image_file is None and graph_file is not None:
        return select_graph(
            graph_file, graph_page_number, image_file, image_page_number
        )
    if image_file is not None and graph_file is None:
        return select_image(
            graph_file, graph_page_number, image_file, image_page_number
        )

    return no_image_or_graph(
        graph_file, graph_page_number, image_file, image_page_number
    )


def extract_image(pdf_path: str, arxiv_id: str) -> tuple[str | None, int]:
    # Open the PDF file in binary mode
    with open(pdf_path, "rb") as pdf_file:
        # Create a PDF reader object
        pdf_reader = pypdf.PdfReader(pdf_file)

        # Find first  image
        filename, page_number = _search_first_image_in_pages(arxiv_id, pdf_reader)

    return filename, page_number


def _search_first_image_in_pages(arxiv_id: str, pdf_reader: Any) -> tuple[str | None, int]:
    filename: str | None = None
    page_number: int = -1

    for page_number, page in enumerate(pdf_reader.pages):
        # pypdf does not support non-rectangular images
        # if one is found, we skip that page
        try:
            images = page.images

        except (pypdf.errors.PyPdfError, OSError):
            continue

        if len(images) > 0:
            filename = _save_first_image(arxiv_id, page)
            if filename is not None:
                break

    return filename, page_number


def _save_first_image(arxiv_id: str, page: Any) -> str | None:
    for image in page.images:
        if len(image.data) < 1024:
            continue
        logger.info(f"Found first bitmap image for {arxiv_id}")
        extension = os.path.splitext(image.name)[-1]
        filename = f"{arxiv_id}_first_image{extension}"
        with open(filename, "wb") as image_file:
            image_file.write(image.data)
        logger.info(f"Bitmap image saved in {filename}")
        if not has_image_content(filename):
            os.remove(filename)
            continue
        return filename
    return None


def download_paper(arxiv_id: str) -> str | None:
    search = arxiv.Search(id_list=[arxiv_id])
    paper = next(search.results())
    logger.info(f"Downloading paper {arxiv_id}")

    filename: str | None = None
    for _ in range(ARXIV_NUM_RETRIES):
        try:
            filename = paper.download_pdf()
        except Exception:
            continue
        else:
            logger.info(f"Downloaded pdf for {arxiv_id}")
            break

    return filename
