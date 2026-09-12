import io

from PIL import Image

from app.core.images import downscale_for_vision


def _make_jpeg(size: tuple[int, int]) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, color=(200, 120, 90)).save(buffer, format="JPEG", quality=95)
    return buffer.getvalue()


def test_leaves_small_image_untouched():
    content = _make_jpeg((400, 300))
    result, content_type = downscale_for_vision(content, "image/jpeg")
    assert result == content
    assert content_type == "image/jpeg"


def test_downscales_large_image():
    content = _make_jpeg((4000, 3000))
    result, content_type = downscale_for_vision(content, "image/jpeg")
    assert content_type == "image/jpeg"
    assert len(result) < len(content)
    with Image.open(io.BytesIO(result)) as resized:
        assert max(resized.size) <= 1600


def test_converts_png_with_transparency_to_jpeg():
    buffer = io.BytesIO()
    Image.new("RGBA", (2000, 2000), color=(10, 20, 30, 128)).save(buffer, format="PNG")
    content = buffer.getvalue()

    result, content_type = downscale_for_vision(content, "image/png")

    assert content_type == "image/jpeg"
    with Image.open(io.BytesIO(result)) as resized:
        assert resized.mode == "RGB"
        assert max(resized.size) <= 1600


def test_unreadable_bytes_pass_through():
    garbage = b"not an image"
    result, content_type = downscale_for_vision(garbage, "image/jpeg")
    assert result == garbage
    assert content_type == "image/jpeg"
