import shutil

import pypdf
import pypdf.errors
import arxiv
import os

from arxiv_sanity_bot.arxiv.extract_graph import extract_graph
from arxiv_sanity_bot.config import ARXIV_NUM_RETRIES
from arxiv_sanity_bot.events import InfoEvent


def extract_first_image(arxiv_id: str):
    """
    Extract the first image from the PDF.

    If the PDF contains both an image and a graph, the first that is encountered is returned. If both the image and
    the graph are on the same page, the image is returned.

    :param arxiv_id: the arxiv ID
    :return: the path to the first image as a local file, or None if none was found
    """

    pdf_path = download_paper(arxiv_id)

    if pdf_path is None:
        return None

    # Find first bitmap (if any)
    image_file, image_page_number = extract_image(pdf_path, arxiv_id)

    # Find first graph (if any)
    graph_file, graph_page_number = extract_graph(pdf_path, arxiv_id)

    # We select whichever comes first.
    filename = _select_image_or_graph(graph_file, graph_page_number, image_file, image_page_number)

    if filename is not None:
        ext = os.path.splitext(filename)[-1]
        new_filename = f"{arxiv_id}_image1{ext}"
        shutil.copy(filename, new_filename)

        return new_filename

    else:

        return None


def select_first_image(graph_file, graph_page_number, image_file, image_page_number):
    InfoEvent("Found both bitmap and graph images. Selecting the one that comes first")
    return image_file if image_page_number <= graph_page_number else graph_file


def select_graph(graph_file, graph_page_number, image_file, image_page_number):
    InfoEvent("Only graph found. Selecting that")
    return graph_file


def select_image(graph_file, graph_page_number, image_file, image_page_number):
    InfoEvent("Only bitmap image found. Selecting that")
    return image_file


def no_image_or_graph(graph_file, graph_page_number, image_file, image_page_number):
    InfoEvent("NO IMAGE NOR GRAPH FOUND")
    return None


def _select_image_or_graph(graph_file, graph_page_number, image_file, image_page_number):

    # My logic
    if image_file is not None and graph_file is not None:
        return select_first_image(graph_file, graph_page_number, image_file, image_page_number)
    if image_file is None and graph_file is not None:
        return select_graph(graph_file, graph_page_number, image_file, image_page_number)
    if image_file is not None and graph_file is None:
        return select_image(graph_file, graph_page_number, image_file, image_page_number)

    return no_image_or_graph(graph_file, graph_page_number, image_file, image_page_number)


def extract_image(pdf_path, arxiv_id):
    # Open the PDF file in binary mode
    with open(pdf_path, 'rb') as pdf_file:
        # Create a PDF reader object
        pdf_reader = pypdf.PdfReader(pdf_file)

        # Find first  image
        filename, page_number = _search_first_image_in_pages(arxiv_id, pdf_reader)

    return filename, page_number


def _search_first_image_in_pages(arxiv_id, pdf_reader):

    filename = None
    page_number = -1

    for page_number, page in enumerate(pdf_reader.pages):

        # pypdf does not support non-rectangular images
        # if one is found, we skip that page
        try:

            images = page.images

        except pypdf.errors.PyPdfError:

            continue

        if len(images) > 0:
            filename = _save_first_image(arxiv_id, page)

            break

    return filename, page_number


def _save_first_image(arxiv_id, page):
    first_image = page.images[0]
    InfoEvent(f"Found first bitmap image for {arxiv_id}")
    # Write the image data and caption text to files
    extension = os.path.splitext(first_image.name)[-1]
    filename = f'{arxiv_id}_first_image{extension}'
    with open(filename, 'wb') as image_file:
        image_file.write(first_image.data)
    InfoEvent(f"Bitmap image saved in {filename}")
    return filename


def download_paper(arxiv_id):
    search = arxiv.Search(id_list=[arxiv_id])
    paper = next(search.results())
    InfoEvent(msg=f"Downloading paper {arxiv_id}")

    filename = None
    for _ in range(ARXIV_NUM_RETRIES):

        try:
            filename = paper.download_pdf()
        except Exception:
            continue
        else:
            InfoEvent(f"Downloaded pdf for {arxiv_id}")
            break

    return filename
