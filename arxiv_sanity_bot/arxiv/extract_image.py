import shutil

import pypdf
import pypdf.errors
import arxiv
import os

from arxiv_sanity_bot.arxiv.extract_graph import extract_graph
from arxiv_sanity_bot.events import InfoEvent


def extract_first_image(arxiv_id):

    pdf_path = download_paper(arxiv_id)
    InfoEvent(f"Downloaded pdf for {arxiv_id}")

    # Find first bitmap (if any)
    image_file, image_page_number = extract_image(pdf_path, arxiv_id)

    # Find first graph (if any)
    graph_file, graph_page_number = extract_graph(pdf_path, arxiv_id)

    # We select whichever comes first.
    if image_file is not None and graph_file is not None:

        InfoEvent("Found both bitmap and graph images. Selecting the one that comes first")
        # If they are on the same page, we pick
        # the bitmap (which is usually nicer ;-) )
        filename = image_file if image_page_number <= graph_page_number else graph_file

    elif image_file is None and graph_file is not None:
        InfoEvent("Only graph found. Selecting that")

        filename = graph_file
    elif image_file is not None and graph_file is None:

        InfoEvent("Only bitmap image found. Selecting that")

        filename = image_file
    else:

        InfoEvent("NO IMAGE NOR GRAPH FOUND")

        filename = None

    if filename is not None:
        ext = os.path.splitext(filename)[-1]
        new_filename = f"{arxiv_id}_image1{ext}"
        shutil.copy(filename, new_filename)

        return new_filename

    else:

        return None


def extract_image(pdf_path, arxiv_id):
    # Open the PDF file in binary mode
    with open(pdf_path, 'rb') as pdf_file:
        # Create a PDF reader object
        pdf_reader = pypdf.PdfReader(pdf_file)

        # Find first  image
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
        else:
            InfoEvent(f"No bitmap image found for {arxiv_id}")
            filename = None
            page_number = -1

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
    return paper.download_pdf()
