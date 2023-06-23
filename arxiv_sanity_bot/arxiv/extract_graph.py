import fitz

from arxiv_sanity_bot.events import InfoEvent


PADDING = 7


def _enlarge_rect(p):
    # import pdb;pdb.set_trace()
    w = p["width"]
    # print(p)
    # print(f"{w} {p['rect'].width}")

    color = None
    if p["color"]:
        color = p["color"]
    elif p["fill"]:
        color = p["fill"]

    return p["rect"] + (-PADDING, -PADDING, PADDING, PADDING), color  # + (-w, -w, w, w)


def is_grayish_or_blackish(rgb, threshold=20):
    r, g, b = rgb
    if (max(r, g, b) - min(r, g, b)) <= (threshold / 255):
        # If all values are equal, the color is a shade of gray
        return True
    elif r < 10 / 255 and g < 10 / 255 and b < 10 / 255:
        # If all values are very low (close to 0), the color is black
        return True
    else:
        # Otherwise, the color is not grayish or blackish
        return False


def _good_aspect_ratio_gray(ratio):

    return 1 < ratio < 10


def _good_width_and_height(r):

    return r.width > 50 and r.height > 50


def _is_not_noise(r, color):
    ratio = r.width / (r.height + 1e-3)
    area = r.width * r.height

    # Black lines
    if color is not None and is_grayish_or_blackish(color):
        good_or_bad = _good_aspect_ratio_gray(ratio) and _good_width_and_height(r) and area > 1000

        # print(f"{ratio} {area} {r.width} {r.height} -> {good_or_bad}")
        return good_or_bad
    else:
        return (ratio > 1) and (r.width > 1) and (r.height > 1) and (area > 0)


def _union_all_rectangles(new_rects):
    # for r in new_rects:
    #     print(f"{r}: ratio: {r.width / r.height} area: {r.width * r.height}, w: {r.width}, h: {r.height}")

    x0 = min([r.x0 for r in new_rects])
    x1 = max([r.x1 for r in new_rects])
    y0 = min([r.y0 for r in new_rects])
    y1 = max([r.y1 for r in new_rects])

    x0, x1, y0, y1 = _regularize_box(x0, x1, y0, y1)

    return fitz.fitz.Rect(x0, y0, x1, y1)


def _regularize_box(x0, x1, y0, y1):
    """
    Make sure the box is not too crazy in terms of aspect ratio
    """
    w = x1 - x0
    h = y1 - y0
    ratio = w / (h + 1e-3)
    max_ratio = 5
    if ratio > max_ratio:
        w = h * max_ratio
        c = x0 + w / 2
        x0 = c - w / 2 - PADDING / 2
        x1 = c + w / 2 + PADDING / 2
    if 1 / ratio > max_ratio:
        h = w * max_ratio
        c = y0 + h / 2
        y0 = c - h / 2 - PADDING / 2
        y1 = c + h / 2 + PADDING / 2
    return x0, x1, y0, y1


def extract_graph(pdf_path, arxiv_id):

    try:
        return _extract_graph(pdf_path, arxiv_id)
    except Exception as e:
        InfoEvent(msg="Extraction of graph failed with an exception", context={"exception": str(e)})
        return None, None


def _extract_graph(pdf_path, arxiv_id):
    doc = fitz.open(pdf_path)

    for page in doc:

        new_rects = _get_bounding_boxes(page)

        if len(new_rects) == 0:
            continue

        image_path = _save_cutout(arxiv_id, new_rects, page)

        InfoEvent(f"Found first graph for {arxiv_id}")
        return image_path, page.number

    InfoEvent(f"No graph found for {arxiv_id}")
    return None, None


def _save_cutout(arxiv_id, new_rects, page):
    all_r = _union_all_rectangles(new_rects)
    mat = fitz.Matrix(3, 3)
    pix = page.get_pixmap(matrix=mat, clip=all_r)
    image_path = f"graph-{arxiv_id}-page{page.number}.png"
    pix.save(image_path)
    return image_path


def _get_bounding_boxes(page):
    new_rects = []

    for p in page.get_drawings():
        r, remainder, color = _process_drawing(new_rects, p)

        if remainder == [] and _is_not_noise(r, color):
            new_rects.append(r)

    return new_rects


def _process_drawing(new_rects, p):
    r, color = _enlarge_rect(p)
    for i in range(len(new_rects)):
        if abs(r & new_rects[i]) > 0:
            new_rects[i] |= r
            break
    remainder = [s for s in new_rects if r in s]
    return r, remainder, color
