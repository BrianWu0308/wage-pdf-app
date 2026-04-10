import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext

_RE_SPACE = re.compile(r"\s+")
_RE_MIXED_CN = re.compile(r"(\d+)又(\d+)分之(\d+)")       # 12又5分之1
_RE_MIXED_ASCII = re.compile(r"(\d+)又(\d+)\s*/\s*(\d+)") # 12又1/5
_RE_CN_FRACTION = re.compile(r"(\d+)分之(\d+)")            # 5分之1
_RE_ASCII_FRACTION = re.compile(r"(\d+)\s*/\s*(\d+)")      # 1/5


def _format_decimal(value: Decimal, max_places: int = 4) -> str:
    quant = Decimal("1." + ("0" * max_places))
    value = value.quantize(quant, rounding=ROUND_HALF_UP)
    s = format(value, "f").rstrip("0").rstrip(".")
    return s if s else "0"


def _safe_fraction_to_decimal(num: str, den: str) -> str:
    try:
        denominator = Decimal(den)
        if denominator == 0:
            return f"{num}/{den}"
        with localcontext() as ctx:
            ctx.prec = 20
            value = Decimal(num) / denominator
        return _format_decimal(value)
    except (InvalidOperation, ZeroDivisionError):
        return f"{num}/{den}"


def pretty_fraction_text(expr: str) -> str:
    if not expr:
        return expr

    text = _RE_SPACE.sub("", expr)
    text = (
        text.replace("乘以", "×")
        .replace("乘", "×")
        .replace("*", "×")
        .replace("x", "×")
        .replace("X", "×")
        .replace("．", ".")
        .replace("。", ".")
        .replace("英吋", '"')
        .replace("公分", "cm")
    )

    def repl_mixed_cn(match: re.Match) -> str:
        whole, den, num = match.group(1), match.group(2), match.group(3)
        try:
            with localcontext() as ctx:
                ctx.prec = 20
                value = Decimal(whole) + (Decimal(num) / Decimal(den))
            return _format_decimal(value)
        except (InvalidOperation, ZeroDivisionError):
            return match.group(0)

    def repl_mixed_ascii(match: re.Match) -> str:
        whole, num, den = match.group(1), match.group(2), match.group(3)
        try:
            with localcontext() as ctx:
                ctx.prec = 20
                value = Decimal(whole) + (Decimal(num) / Decimal(den))
            return _format_decimal(value)
        except (InvalidOperation, ZeroDivisionError):
            return match.group(0)

    def repl_cn_fraction(match: re.Match) -> str:
        den, num = match.group(1), match.group(2)
        return _safe_fraction_to_decimal(num, den)

    def repl_ascii_fraction(match: re.Match) -> str:
        num, den = match.group(1), match.group(2)
        return _safe_fraction_to_decimal(num, den)

    text = _RE_MIXED_CN.sub(repl_mixed_cn, text)
    text = _RE_MIXED_ASCII.sub(repl_mixed_ascii, text)
    text = _RE_CN_FRACTION.sub(repl_cn_fraction, text)
    text = _RE_ASCII_FRACTION.sub(repl_ascii_fraction, text)
    return text