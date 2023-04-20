import fitz

from arxiv_sanity_bot.events import InfoEvent


def _enlarge_rect(p):
    w = p["width"]
    return p["rect"] + (-w, -w, w, w)


def _good_aspect_ratio(r):
    # area = (r.x1 - r.x0) * (r.y1 - r.y0)
    ratio = (r.width / (r.height + 1e-3))
    return not (ratio > 10 or ratio < 0.1)


def _union_all_rectangles(new_rects):
    x0 = min([r.x0 for r in new_rects])
    x1 = max([r.x1 for r in new_rects])
    y0 = min([r.y0 for r in new_rects])
    y1 = max([r.y1 for r in new_rects])

    return fitz.fitz.Rect(x0, y0, x1, y1)


# def _remove_overlaps(new_rects):
#
#     remove = set()
#     for j in range(len(new_rects)):
#         for i in range(len(new_rects)):
#             if new_rects[j] in new_rects[i] and i != j:
#                 remove.add(j)
#
#     remove = list(remove)
#
#     for i in reversed(remove):
#         try:
#             del new_rects[i]
#         except IndexError:
#             continue


def extract_graph(pdf_path, arxiv_id):
    doc = fitz.open(pdf_path)
    for page in doc:
        new_rects = []

        for p in page.get_drawings():
            r = _enlarge_rect(p)
            for i in range(len(new_rects)):
                if abs(r & new_rects[i]) > 0:
                    new_rects[i] |= r
                    break
            remainder = [s for s in new_rects if r in s]
            if remainder == [] and _good_aspect_ratio(r):
                new_rects.append(r)

        # new_rects = list(set(new_rects))
        # new_rects.sort(key=lambda r: abs(r), reverse=True)
        # _remove_overlaps(new_rects)
        # new_rects.sort(key=lambda r: (r.tl.y, r.tl.x))
        #
        # if len(new_rects) == 0:
        #     continue

        all_r = _union_all_rectangles(new_rects)
        mat = fitz.Matrix(3, 3)
        pix = page.get_pixmap(matrix=mat, clip=all_r)
        image_path = f"graph-{arxiv_id}-page{page.number}.png"
        pix.save(image_path)

        InfoEvent(f"Found first graph for {arxiv_id}")
        return image_path, page.number

    InfoEvent(f"No graph found for {arxiv_id}")
    return None, None
