"""Deteccion de fuga de contacto fuera de la plataforma.

Basado en la seccion 13 del estudio de investigacion: el chat interno
debe detectar y bloquear suavemente numeros de telefono, correos,
enlaces externos y menciones de redes sociales -- incluyendo
variaciones ofuscadas ("cinco cinco cinco", "arroba", espaciado
irregular) -- mientras el contacto real no se ha desbloqueado.

El diseno es deliberadamente tolerante (pocos falsos positivos) en vez
de agresivo: el propio estudio advierte que un sistema anti-fuga
demasiado estricto empuja a los usuarios experimentados a evadirlo con
mas sofisticacion en vez de reducir la fuga real.
"""

import re

_MASK = "[contenido oculto]"

_DIGIT_WORDS = "cero|uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve"

_EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
_OBFUSCATED_EMAIL_RE = re.compile(
    r"\b[a-zA-Z0-9_.+-]+\s*(?:arroba|\(arroba\)|\[at\])\s*[a-zA-Z0-9-]+\s*"
    r"(?:punto|\.|dot)\s*(?:com|mx|net|org)\b",
    re.IGNORECASE,
)
_URL_RE = re.compile(r"\b(?:https?://|www\.)\S+", re.IGNORECASE)
_SOCIAL_RE = re.compile(
    r"\b(whats\s?app|wsp|wa\.me|instagram|\bIG\b|facebook|fb\.com|telegram|t\.me)\b",
    re.IGNORECASE,
)
_SPELLED_PHONE_RE = re.compile(
    rf"(?:\b(?:{_DIGIT_WORDS})\b[\s,]*){{6,}}", re.IGNORECASE
)
_DIGIT_SEQUENCE_RE = re.compile(r"\+?\d[\d\-.\s()]{5,}\d")

_PHONE_MIN_DIGITS = 8
_PHONE_MAX_DIGITS = 15


def _mask_phone_sequences(text: str) -> tuple[str, bool]:
    found = False

    def _replace(match: re.Match) -> str:
        nonlocal found
        digits = re.sub(r"\D", "", match.group())
        if _PHONE_MIN_DIGITS <= len(digits) <= _PHONE_MAX_DIGITS:
            found = True
            return _MASK
        return match.group()

    return _DIGIT_SEQUENCE_RE.sub(_replace, text), found


def detect_and_redact(text: str) -> tuple[str, bool, list[str]]:
    """Devuelve (texto_redactado, fue_marcado, razones)."""
    redacted = text
    reasons: list[str] = []

    if _EMAIL_RE.search(redacted):
        reasons.append("correo_electronico")
        redacted = _EMAIL_RE.sub(_MASK, redacted)

    if _OBFUSCATED_EMAIL_RE.search(redacted):
        reasons.append("correo_ofuscado")
        redacted = _OBFUSCATED_EMAIL_RE.sub(_MASK, redacted)

    if _URL_RE.search(redacted):
        reasons.append("enlace_externo")
        redacted = _URL_RE.sub(_MASK, redacted)

    if _SOCIAL_RE.search(redacted):
        reasons.append("red_social_o_mensajeria")
        redacted = _SOCIAL_RE.sub(_MASK, redacted)

    if _SPELLED_PHONE_RE.search(redacted):
        reasons.append("telefono_deletreado")
        redacted = _SPELLED_PHONE_RE.sub(_MASK, redacted)

    redacted, phone_found = _mask_phone_sequences(redacted)
    if phone_found:
        reasons.append("telefono")

    return redacted, len(reasons) > 0, reasons
