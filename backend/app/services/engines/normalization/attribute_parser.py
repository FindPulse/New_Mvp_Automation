import re
from typing import Any, Dict, Optional


def clean_text(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    text = text.replace("\u200b", "")
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)

    return text


def parse_wheel_size(text: Any) -> Dict[str, Optional[str]]:
    """
    Extract wheel size like:
    20X9
    20 x 9
    20x9.5
    22X10.5
    """

    text = clean_text(text)

    pattern = re.compile(
        r"(?<!\d)(1[3-9]|2[0-9]|3[0-2])\s*[xX]\s*(\d{1,2}(?:\.\d+)?)",
        re.IGNORECASE,
    )

    match = pattern.search(text)

    if not match:
        return {
            "size": None,
            "wheel_diameter": None,
            "wheel_width": None,
        }

    diameter = match.group(1)
    width = match.group(2)

    return {
        "size": f"{diameter}x{width}",
        "wheel_diameter": diameter,
        "wheel_width": width,
    }


def parse_bolt_pattern(text: Any) -> Optional[str]:
    """
    Extract bolt pattern like:
    5X120
    5 x 114.3
    6X139.7
    """

    text = clean_text(text)

    pattern = re.compile(
        r"(?<!\d)([4-8])\s*[xX]\s*(98|100|108|110|112|114\.3|115|118|120|127|130|135|139\.7|150|165\.1)(?!\d)",
        re.IGNORECASE,
    )

    match = pattern.search(text)

    if not match:
        return None

    lug_count = match.group(1)
    pcd = match.group(2)

    return f"{lug_count}x{pcd}"


def parse_offset(text: Any) -> Optional[str]:
    """
    Extract offset like:
    ET35
    +35
    -12
    OFFSET 20
    """

    text = clean_text(text).upper()

    patterns = [
        r"\bET\s*([+-]?\d{1,3})\b",
        r"\bOFFSET\s*([+-]?\d{1,3})\b",
        r"(?<!\d)([+-]\d{1,3})(?!\d)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if match:
            return match.group(1)

    return None


def parse_center_bore(text: Any) -> Optional[str]:
    """
    Extract center bore like:
    CB73.1
    HUB 72.6
    BORE 106.1
    """

    text = clean_text(text).upper()

    patterns = [
        r"\bCB\s*([0-9]{2,3}(?:\.[0-9]+)?)\b",
        r"\bHUB\s*([0-9]{2,3}(?:\.[0-9]+)?)\b",
        r"\bBORE\s*([0-9]{2,3}(?:\.[0-9]+)?)\b",
        r"\bCENTER\s*BORE\s*([0-9]{2,3}(?:\.[0-9]+)?)\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if match:
            return match.group(1)

    return None


def normalize_finish_text(text: Any) -> Optional[str]:
    """
    Basic finish detection from common words.
    This is not final AI logic. This is deterministic first-pass parsing.
    """

    text = clean_text(text).upper()

    finish_aliases = {
        "SB": "Satin Black",
        "SATIN BLACK": "Satin Black",
        "MATTE BLACK": "Matte Black",
        "MATT BLACK": "Matte Black",
        "GB": "Gloss Black",
        "GLOSS BLACK": "Gloss Black",
        "BLACK": "Black",
        "GUNMETAL": "Gunmetal",
        "GUN METAL": "Gunmetal",
        "BRONZE": "Bronze",
        "CHROME": "Chrome",
        "SILVER": "Silver",
        "MACHINED": "Machined",
        "GLOSS GREY": "Gloss Grey",
        "GLOSS GRAY": "Gloss Grey",
        "GREY": "Grey",
        "GRAY": "Grey",
    }

    # Longer keys first, so "GLOSS BLACK" matches before "BLACK"
    for raw_value in sorted(finish_aliases.keys(), key=len, reverse=True):
        if raw_value in text:
            return finish_aliases[raw_value]

    return None


def parse_wheel_attributes_from_text(text: Any) -> Dict[str, Optional[str]]:
    """
    Main parser used by vendor product draft builder.
    """

    text = clean_text(text)

    size_result = parse_wheel_size(text)

    return {
        "size": size_result.get("size"),
        "wheel_diameter": size_result.get("wheel_diameter"),
        "wheel_width": size_result.get("wheel_width"),
        "bolt_pattern": parse_bolt_pattern(text),
        "offset": parse_offset(text),
        "center_bore": parse_center_bore(text),
        "finish": normalize_finish_text(text),
    }