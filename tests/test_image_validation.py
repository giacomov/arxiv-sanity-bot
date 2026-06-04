from pathlib import Path

from PIL import Image

from arxiv_sanity_bot.arxiv import image_validation
from arxiv_sanity_bot.arxiv.image_validation import is_uploadable


def _make_image(path: Path, size: tuple[int, int]) -> str:
    img = Image.new("RGB", size, color=(40, 40, 80))
    # Add some pixel variance so anything downstream that grays-out won't flag it
    px = img.load()
    for i in range(0, size[0], 4):
        for j in range(0, size[1], 4):
            px[i, j] = (i % 256, j % 256, (i + j) % 256)
    img.save(path, "JPEG", quality=85)
    return str(path)


def test_is_uploadable_accepts_square_image(tmp_path):
    p = _make_image(tmp_path / "ok.jpg", (300, 300))
    assert is_uploadable(p)


def test_is_uploadable_rejects_short_side_below_floor(tmp_path):
    # 119px short side is just under MIN_SHORT_SIDE (120)
    p = _make_image(tmp_path / "thin.jpg", (400, 119))
    assert not is_uploadable(p)


def test_is_uploadable_rejects_extreme_aspect_ratio(tmp_path):
    # 4:1 — above MAX_ASPECT_RATIO (3.0)
    p = _make_image(tmp_path / "wide.jpg", (800, 200))
    assert not is_uploadable(p)


def test_is_uploadable_accepts_at_aspect_boundary(tmp_path):
    # Exactly 3:1 should pass (cap is strict >, not >=)
    p = _make_image(tmp_path / "3to1.jpg", (600, 200))
    assert is_uploadable(p)


def test_is_uploadable_rejects_oversized_file(tmp_path, monkeypatch):
    monkeypatch.setattr(image_validation, "MAX_FILE_BYTES", 100)
    p = _make_image(tmp_path / "big.jpg", (300, 300))
    assert not is_uploadable(p)


def test_is_uploadable_returns_false_on_missing_file(tmp_path):
    assert not is_uploadable(str(tmp_path / "does_not_exist.jpg"))


def test_is_uploadable_returns_false_on_unreadable_file(tmp_path):
    p = tmp_path / "garbage.jpg"
    p.write_bytes(b"not an image at all")
    assert not is_uploadable(str(p))
