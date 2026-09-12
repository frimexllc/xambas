"""Utilidades de imagen para módulos que llaman a un modelo de visión."""
from __future__ import annotations

import io

from PIL import Image, ImageOps

_MAX_DIMENSION = 1600
_JPEG_QUALITY = 82
# Si la foto ya pesa poco, evitamos re-comprimir aunque supere _MAX_DIMENSION
# por poco — no vale la pena perder calidad para ahorrar unos KB.
_SKIP_THRESHOLD_BYTES = 900 * 1024


def downscale_for_vision(content: bytes, content_type: str) -> tuple[bytes, str]:
    """Reduce una foto antes de mandarla a un modelo de visión (p. ej. Groq).

    Los proveedores de visión cobran y limitan por tokens de imagen, que
    escalan con la resolución: una foto de celular a 12+ MP no mejora la
    estimación de IA, solo el costo y la latencia. Si la imagen ya es
    razonablemente chica se deja tal cual. El original subido se sigue
    guardando sin tocar (esta función solo afecta lo que se le manda al
    modelo, no lo que se persiste en storage).

    Devuelve (bytes, content_type); el content_type puede cambiar a JPEG si
    hubo que re-codificar (por ejemplo un PNG con transparencia).
    """
    if len(content) <= _SKIP_THRESHOLD_BYTES:
        try:
            with Image.open(io.BytesIO(content)) as probe:
                if max(probe.size) <= _MAX_DIMENSION:
                    return content, content_type
        except Exception:  # noqa: BLE001 — imagen no legible, se manda tal cual
            return content, content_type

    try:
        with Image.open(io.BytesIO(content)) as image:
            image = ImageOps.exif_transpose(image)
            image.thumbnail((_MAX_DIMENSION, _MAX_DIMENSION), Image.LANCZOS)
            if image.mode not in ("RGB", "L"):
                image = image.convert("RGB")
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=_JPEG_QUALITY, optimize=True)
            return buffer.getvalue(), "image/jpeg"
    except Exception:  # noqa: BLE001 — si el re-encode falla, mandamos el original
        return content, content_type
