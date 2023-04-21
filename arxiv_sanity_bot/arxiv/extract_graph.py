import fitz

from arxiv_sanity_bot.events import InfoEvent


def _enlarge_rect(p):
    w = p["width"]
    return p["rect"] + (-w, -w, w, w)


def _good_aspect_ratio(r):
    ratio = r.width / (r.height + 1e-3)
    return not (ratio > 10 or ratio < 0.1)


def _union_all_rectangles(new_rects):
    x0 = min([r.x0 for r in new_rects])
    x1 = max([r.x1 for r in new_rects])
    y0 = min([r.y0 for r in new_rects])
    y1 = max([r.y1 for r in new_rects])

    return fitz.fitz.Rect(x0, y0, x1, y1)


def extract_graph(pdf_path, arxiv_id):
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
        r, remainder = _process_drawing(new_rects, p)

        if remainder == [] and _good_aspect_ratio(r):
            new_rects.append(r)

    return new_rects


def _process_drawing(new_rects, p):
    r = _enlarge_rect(p)
    for i in range(len(new_rects)):
        if abs(r & new_rects[i]) > 0:
            new_rects[i] |= r
            break
    remainder = [s for s in new_rects if r in s]
    return r, remainder
