import glob
import os
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
from PIL import Image

from arxiv_sanity_bot.arxiv.extract_image import (
    extract_first_image,
    _select_image_or_graph,
)
from arxiv_sanity_bot.arxiv.image_validation import has_image_content


def check_image_content(new_image, reference_image_path):
    # Open both images using PIL.Image
    reference_image = Image.open(reference_image_path)
    test_image = Image.open(new_image)

    # Compare the images
    assert reference_image.size == test_image.size, "Image sizes do not match"

    # Convert images to numpy arrays
    reference_array = np.asarray(reference_image)
    test_array = np.asarray(test_image)

    # Compare pixel data using numpy arrays
    assert np.array_equal(reference_array, test_array), "Pixel data does not match"


def get_resource(resource):
    current_file_dir = Path(__file__).parent

    # Create the path to the resource file
    return current_file_dir / "resources" / resource


@pytest.fixture
def paper_with_no_figures():
    return get_resource("compressed-2304.09167v1.pdf")


@pytest.fixture
def paper_with_only_graph():
    return get_resource("compressed-2304.09116v1.pdf")


@pytest.fixture
def paper_with_both_graph_and_bitmap():
    return get_resource("compressed-2101.00027v1.pdf")


def test_extract_first_image_no_image_nor_graph(paper_with_no_figures):
    with patch(
        "arxiv_sanity_bot.arxiv.extract_image.download_paper",
        return_value=paper_with_no_figures,
    ):
        image = extract_first_image("one")

        # Check if the image is not None
        assert image is None

        assert len(glob.glob("one_*.jpg")) == 0


def test_extract_first_image_only_graph(paper_with_only_graph):
    with patch(
        "arxiv_sanity_bot.arxiv.extract_image.download_paper",
        return_value=paper_with_only_graph,
    ):
        image = extract_first_image("two")

        # Check if the image is not None
        assert image is not None

        assert os.path.exists(image)
        assert image == "two_image1.jpg"

        check_image_content(
            new_image=image, reference_image_path=get_resource("two_image1.jpg")
        )


def test_extract_first_image_both_bitmap_and_graph(paper_with_both_graph_and_bitmap):
    with patch(
        "arxiv_sanity_bot.arxiv.extract_image.download_paper",
        return_value=paper_with_both_graph_and_bitmap,
    ):
        image = extract_first_image("three")

        # Check if the image is not None
        assert image is not None

        assert os.path.exists(image)
        assert image == "three_image1.jpg"

        check_image_content(
            new_image=image, reference_image_path=get_resource("three_image1.jpg")
        )


def test_select_image_or_graph():
    # If both are present and on the same page, we should return the image
    graph_file = "graph"
    graph_page_number = 1
    image_file = "image"
    image_page_number = 1

    assert (
        _select_image_or_graph(
            graph_file, graph_page_number, image_file, image_page_number
        )
        == "image"
    )

    # If both are present and on different pages, we should return the first one
    graph_file = "graph"
    graph_page_number = 1
    image_file = "image"
    image_page_number = 2

    assert (
        _select_image_or_graph(
            graph_file, graph_page_number, image_file, image_page_number
        )
        == "graph"
    )

    # If only the graph is present, we should return the graph
    graph_file = "graph"
    graph_page_number = 1
    image_file = None
    image_page_number = None

    assert (
        _select_image_or_graph(
            graph_file, graph_page_number, image_file, image_page_number
        )
        == "graph"
    )

    # If only the image is present, we should return the image
    graph_file = None
    graph_page_number = None
    image_file = "image"
    image_page_number = 1

    assert (
        _select_image_or_graph(
            graph_file, graph_page_number, image_file, image_page_number
        )
        == "image"
    )

    # If neither is present, we should return None
    graph_file = None
    graph_page_number = None
    image_file = None
    image_page_number = None

    assert (
        _select_image_or_graph(
            graph_file, graph_page_number, image_file, image_page_number
        )
        is None
    )


def test_has_image_content_with_blank_image():
    blank_image = Image.new('RGB', (100, 100), color='white')
    blank_image.save('test_blank.png')

    assert not has_image_content('test_blank.png')

    os.remove('test_blank.png')


def test_has_image_content_with_actual_content():
    content_image = Image.new('RGB', (100, 100))
    pixels = content_image.load()
    for i in range(100):
        for j in range(100):
            pixels[i, j] = (i * 2, j * 2, (i + j) % 256)
    content_image.save('test_content.png')

    assert has_image_content('test_content.png')

    os.remove('test_content.png')
