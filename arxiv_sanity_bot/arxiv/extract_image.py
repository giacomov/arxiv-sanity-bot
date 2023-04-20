import shutil

import pypdf
import pypdf.errors
import arxiv
import os
import fitz

from arxiv_sanity_bot.events import InfoEvent


def extract_first_image(arxiv_id):

    pdf_path = download_paper(arxiv_id)
    InfoEvent(f"Downloaded pdf for {arxiv_id}")

    # Find first bitmap (if any)
    image_file, image_page_number = _extract_image(pdf_path, arxiv_id)

    # Find first graph (if any)
    graph_file, graph_page_number = _extract_graph(pdf_path, arxiv_id)

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


def _extract_image(pdf_path, arxiv_id):
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
                first_image = page.images[0]
                InfoEvent(f"Found first bitmap image for {arxiv_id}")

                # Write the image data and caption text to files
                extension = os.path.splitext(first_image.name)[-1]
                filename = f'{arxiv_id}_first_image{extension}'
                with open(filename, 'wb') as image_file:
                    image_file.write(first_image.data)
                InfoEvent(f"Bitmap image saved in {filename}")

                break
        else:
            InfoEvent(f"No bitmap image found for {arxiv_id}")
            filename = None
            page_number = -1

    return filename, page_number


def _extract_graph(pdf_path, arxiv_id):

    # This code is taken from
    # https://github.com/pymupdf/PyMuPDF-Utilities/blob/master/examples/extract-vector-graphics/separate-figures.py
    # with additional modifications

    doc = fitz.open(pdf_path)
    for page in doc:

        new_rects = []  # resulting rectangles

        for p in page.get_drawings():
            w = p["width"]  # thickness of the border line
            r = p["rect"] + (-w, -w, w, w)  # enlarge each rectangle by width value
            for i in range(len(new_rects)):
                if abs(r & new_rects[i]) > 0:  # touching one of the new rects?
                    new_rects[i] |= r  # enlarge it
                    break
            # now look if contained in one of the new rects
            remainder = [s for s in new_rects if r in s]
            if remainder == []:  # no ==> add this rect to new rects
                area = (r.x1 - r.x0) * (r.y1 - r.y0)
                ratio = (r.width / (r.height + 1e-3))
                # Ignore regions that are too small or too elongated
                # (to cut out lines)
                print(f"area: {area}, ratio: {ratio}")
                if ratio > 10 or ratio < 0.1:
                    continue

                new_rects.append(r)

        new_rects = list(set(new_rects))  # remove any duplicates
        new_rects.sort(key=lambda r: abs(r), reverse=True)
        remove = []
        for j in range(len(new_rects)):
            for i in range(len(new_rects)):
                if new_rects[j] in new_rects[i] and i != j:
                    remove.append(j)
        remove = list(set(remove))
        for i in reversed(remove):
            try:
                del new_rects[i]
            except IndexError:
                continue
        new_rects.sort(key=lambda r: (r.tl.y, r.tl.x))  # sort by location

        if len(new_rects) == 0:
            continue

        # Union all intersections
        x0 = min([r.x0 for r in new_rects])
        x1 = max([r.x1 for r in new_rects])
        y0 = min([r.y0 for r in new_rects])
        y1 = max([r.y1 for r in new_rects])

        all_r = fitz.fitz.Rect(x0, y0, x1, y1)

        mat = fitz.Matrix(3, 3)  # high resolution matrix

        pix = page.get_pixmap(matrix=mat, clip=all_r)
        image_path = f"graph-{arxiv_id}-page{page.number}.png"

        pix.save(image_path)

        InfoEvent(f"Found first graph for {arxiv_id}")

        # We return the first graph we find
        return image_path, page.number

    # We end up here if there are no pages to loop over
    InfoEvent(f"No graph found for {arxiv_id}")
    return None, None

def download_paper(arxiv_id):
    search = arxiv.Search(id_list=[arxiv_id])
    paper = next(search.results())
    InfoEvent(msg=f"Downloading paper {arxiv_id}")
    return paper.download_pdf()
