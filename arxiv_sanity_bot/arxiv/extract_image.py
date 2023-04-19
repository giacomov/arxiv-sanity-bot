import pypdf
import arxiv
import os

from arxiv_sanity_bot.events import InfoEvent


def extract_first_image(arxiv_id):

    pdf_path = download_paper(arxiv_id)
    InfoEvent(f"Downloaded pdf for {arxiv_id}")

    filename = _extract_image(pdf_path, arxiv_id)

    return filename


def _extract_image(pdf_path, arxiv_id):
    # Open the PDF file in binary mode
    with open(pdf_path, 'rb') as pdf_file:
        # Create a PDF reader object
        pdf_reader = pypdf.PdfReader(pdf_file)

        # Find first  image
        for page in pdf_reader.pages:
            import pdb;pdb.set_trace()

            if len(page.images) > 0:
                first_image = page.images[0]
                InfoEvent(f"Found first image for {arxiv_id}")

                # Write the image data and caption text to files
                extension = os.path.splitext(first_image.name)[-1]
                filename = f'{arxiv_id}_first_image{extension}'
                with open(filename, 'wb') as image_file:
                    image_file.write(first_image.data)
                InfoEvent(f"Image saved in {filename}")

                break
        else:
            InfoEvent(f"No first image found for {arxiv_id}")
            filename = None

    return filename

def download_paper(arxiv_id):
    search = arxiv.Search(id_list=[arxiv_id])
    paper = next(search.results())
    return paper.download_pdf()
