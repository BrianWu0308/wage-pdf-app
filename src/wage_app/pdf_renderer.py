from __future__ import annotations

from decimal import Decimal, ROUND_CEILING
from pathlib import Path
import re
from typing import Dict, List, Sequence, Tuple

from fpdf import FPDF

from wage_app.models import PDFRecord
from wage_app.resources import get_font_path

MAX_ROWS_PER_PDF = 20
MAIN_FONT_NAME = "NotoSansTC"
FRACTION_FONT_NAME = "DejaVuSans"
MAIN_FONT_FILE = "NotoSansTC-Regular.ttf"
FRACTION_FONT_FILE = "DejaVuSans.ttf"

PER_COL_FONT_SIZE: Dict[str, int] = {
    "日期": 10,
    "訂單號碼": 10,
    "類別": 10,
    "顏色(組)": 9,
    "數量(片)": 10,
    "單價": 10,
    "重量(kg)": 10,
    "金額": 10,
    "備註": 9,
}
LINE_H = 7
HEADER_H = 10
COL_WIDTHS: List[int] = [24, 26, 18, 28, 18, 18, 18, 20, 20]
HEADERS = ["日期", "訂單號碼", "類別", "顏色(組)", "數量(片)", "單價", "重量(kg)", "金額", "備註"]
REPORT_TITLE_LEFT = "捷盛針織企業社"
REPORT_ADDR = "地址：新北市樹林區田尾街211-2號"
REPORT_TEL = "電話：8970-2937 / 8970-3534    傳真：8970-2936"
TAX_RATE = Decimal("0.05")

_CJK_RE = re.compile(r"[㐀-鿿豈-﫿]")
_SUP_TO_NORM = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")
_SUB_TO_NORM = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
_VULGAR_TO_PAIR: Dict[str, Tuple[int, int]] = {
    "½": (1, 2),
    "⅓": (1, 3),
    "⅔": (2, 3),
    "¼": (1, 4),
    "¾": (3, 4),
    "⅕": (1, 5),
    "⅖": (2, 5),
    "⅗": (3, 5),
    "⅘": (4, 5),
    "⅙": (1, 6),
    "⅚": (5, 6),
    "⅐": (1, 7),
    "⅛": (1, 8),
    "⅜": (3, 8),
    "⅝": (5, 8),
    "⅞": (7, 8),
    "⅑": (1, 9),
    "⅒": (1, 10),
}


class PDFGenerationError(Exception):
    pass


def ensure_fonts(pdf: FPDF) -> None:
    main_font = get_font_path(MAIN_FONT_FILE)
    frac_font = get_font_path(FRACTION_FONT_FILE)

    if not main_font.exists():
        raise PDFGenerationError(f"找不到字型檔：{main_font}")
    if not frac_font.exists():
        raise PDFGenerationError(f"找不到字型檔：{frac_font}")

    pdf.add_font(MAIN_FONT_NAME, fname=str(main_font))
    pdf.add_font(FRACTION_FONT_NAME, fname=str(frac_font))


def number_to_chinese(n: int | str) -> str:
    if int(n) == 0:
        return "零元整"

    digits = "零壹貳參肆伍陸柒捌玖"
    unit1 = ["", "拾", "佰", "仟"]
    unit2 = ["", "萬", "億", "兆", "京"]

    s = str(int(n))
    groups: List[str] = []
    while s:
        groups.insert(0, s[-4:].rjust(4, "0"))
        s = s[:-4]

    parts: List[str] = []
    for gi, group in enumerate(groups):
        seg = ""
        zero = False
        for i, ch in enumerate(group):
            d = int(ch)
            pos = 3 - i
            if d == 0:
                zero = True
            else:
                if zero and seg:
                    seg += "零"
                seg += digits[d] + (unit1[pos] if pos > 0 else "")
                zero = False
        if seg:
            seg += unit2[len(groups) - 1 - gi]
        parts.append(seg)

    return "".join(parts).rstrip("零") + " 元整"


def contains_cjk(s: str) -> bool:
    return bool(_CJK_RE.search(s or ""))


def to_ascii_fractions(s: str) -> str:
    if not s:
        return ""
    for ch, (num, den) in _VULGAR_TO_PAIR.items():
        s = s.replace(ch, f"{num}/{den}")
    s = s.translate(_SUP_TO_NORM).translate(_SUB_TO_NORM)
    s = s.replace("⁄", "/")
    s = s.replace("″", '"').replace("′", "'")
    return s


def _ceil_decimal_to_int(value: Decimal) -> int:
    return int(value.to_integral_value(rounding=ROUND_CEILING))


def _wrap_lines(pdf: FPDF, text: str, max_w: float, padding: float = 1.5) -> List[str]:
    text = "" if text is None else str(text)
    if not text:
        return [""]

    lines: List[str] = []
    line = ""
    limit = max_w - padding

    for ch in text:
        if pdf.get_string_width(line + ch) <= limit:
            line += ch
        else:
            lines.append(line)
            line = ch
    lines.append(line)
    return lines


def _draw_wrapped_cell(
    pdf: FPDF,
    w: float,
    h: float,
    text: str,
    line_h: float,
    align: str = "C",
    font_size: int = 10,
    font_family: str = MAIN_FONT_NAME,
) -> None:
    x0, y0 = pdf.get_x(), pdf.get_y()
    pdf.cell(w, h, "", border=1)
    pdf.set_xy(x0, y0)
    pdf.set_font(font_family, size=font_size)

    lines = _wrap_lines(pdf, text or "", w)
    total_text_h = max(line_h * len(lines), line_h)
    y_text = y0 + max((h - total_text_h) / 2, 0)
    pdf.set_xy(x0, y_text)

    for i, line in enumerate(lines):
        pdf.multi_cell(w, line_h, line, border=0, align=align)
        if i < len(lines) - 1:
            pdf.set_x(x0)

    pdf.set_xy(x0 + w, y0)


def _fit_font_size(
    pdf: FPDF,
    text: str,
    max_w: float,
    font_family: str,
    base_size: float,
    min_size: float = 8.0,
) -> float:
    s = text or ""
    size = float(base_size)
    pdf.set_font(font_family, size=size)
    limit = max_w - 1.5

    while size > min_size and pdf.get_string_width(s) > limit:
        size -= 0.5
        pdf.set_font(font_family, size=size)

    return size


def _draw_fit_cell(
    pdf: FPDF,
    w: float,
    h: float,
    text: str,
    align: str = "C",
    base_size: int = 10,
    font_family: str = MAIN_FONT_NAME,
) -> None:
    x0, y0 = pdf.get_x(), pdf.get_y()
    pdf.cell(w, h, "", border=1)

    s = "" if text is None else str(text)
    size = _fit_font_size(pdf, s, w, font_family, base_size)
    pdf.set_font(font_family, size=size)
    limit = w - 1.5
    text_w = pdf.get_string_width(s)

    if text_w > limit:
        while s and pdf.get_string_width(s + "…") > limit:
            s = s[:-1]
        s = (s + "…") if s else s
        text_w = pdf.get_string_width(s)

    if align == "R":
        x = x0 + max(w - text_w - 1.0, 0)
    elif align == "C":
        x = x0 + max((w - text_w) / 2, 0)
    else:
        x = x0 + 1.0

    y = y0 + (h + size * 0.35) / 2.0
    pdf.text(x, y, s)
    pdf.set_xy(x0 + w, y0)


def _measure_row_height(pdf: FPDF, row: List[str]) -> float:
    max_lines = 1
    for i, header in enumerate(HEADERS):
        fs = PER_COL_FONT_SIZE.get(header, 10)
        cell_text = row[i] or ""
        if header == "類別":
            pdf.set_font(FRACTION_FONT_NAME if not contains_cjk(cell_text) else MAIN_FONT_NAME, size=fs)
            lines = 1
        else:
            pdf.set_font(MAIN_FONT_NAME, size=fs)
            lines = len(_wrap_lines(pdf, cell_text, COL_WIDTHS[i]))
        max_lines = max(max_lines, lines)
    return max(max_lines * LINE_H, HEADER_H)


def _draw_header(pdf: FPDF, customer: str, year: str, title_month: str) -> None:
    pdf.set_font(MAIN_FONT_NAME, size=20)
    pdf.cell(0, 16, REPORT_TITLE_LEFT, new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font(MAIN_FONT_NAME, size=10)
    pdf.cell(0, 6, REPORT_ADDR, new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.cell(0, 6, REPORT_TEL, new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(2)

    pdf.set_font(MAIN_FONT_NAME, size=16)
    pdf.cell(0, 14, f"{year}年{title_month}月份工繳請款明細表", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font(MAIN_FONT_NAME, size=12)
    pdf.cell(0, 10, f"客戶：{customer}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font(MAIN_FONT_NAME, size=10)
    for i, header in enumerate(HEADERS):
        pdf.cell(COL_WIDTHS[i], HEADER_H, header, border=1, align="C")
    pdf.ln()


def _render_one_pdf_page(
    pdf: FPDF,
    customer: str,
    year: str,
    title_month: str,
    rows: List[Dict[str, str]],
    overall_totals: Tuple[int, int, int] | None = None,
    is_last: bool = False,
) -> None:
    pdf.add_page()
    _draw_header(pdf, customer, year, title_month)

    for row_dict in rows:
        row = [
            row_dict["date_str"],
            row_dict["order"],
            row_dict["type"],
            row_dict["color"],
            row_dict["quantity"],
            row_dict["unit_price"],
            row_dict["weight"],
            row_dict["amount"],
            row_dict["remark"],
        ]
        row_h = _measure_row_height(pdf, row)

        bottom_limit = pdf.h - pdf.b_margin
        if pdf.get_y() + row_h > bottom_limit:
            pdf.add_page()
            _draw_header(pdf, customer, year, title_month)

        x0, y0 = pdf.get_x(), pdf.get_y()
        for i, text in enumerate(row):
            w = COL_WIDTHS[i]
            fs = PER_COL_FONT_SIZE.get(HEADERS[i], 10)

            if HEADERS[i] == "類別":
                if contains_cjk(text or ""):
                    safe_text = to_ascii_fractions(text or "")
                    _draw_fit_cell(pdf, w, row_h, safe_text, align="C", base_size=fs, font_family=MAIN_FONT_NAME)
                else:
                    _draw_fit_cell(pdf, w, row_h, text or "", align="C", base_size=fs, font_family=FRACTION_FONT_NAME)
            else:
                align = "R" if HEADERS[i] in ["數量(片)", "單價", "重量(kg)", "金額"] else "C"
                _draw_wrapped_cell(
                    pdf,
                    w,
                    row_h,
                    text or "",
                    LINE_H,
                    align=align,
                    font_size=fs,
                    font_family=MAIN_FONT_NAME,
                )
        pdf.set_xy(x0, y0 + row_h)

    if is_last and overall_totals is not None:
        subtotal, tax, total = overall_totals
        pdf.set_font(MAIN_FONT_NAME, size=12)
        pdf.multi_cell(0, 10, f"小計：{subtotal} 元\n稅(5%)：{tax} 元\n合計：{total} 元", align="R")
        pdf.set_x(10)
        pdf.multi_cell(190, 10, f"新臺幣：{number_to_chinese(total)}", align="R")


def normalize_records(records: Sequence[PDFRecord]) -> Tuple[List[Dict[str, str]], Tuple[int, int, int]]:
    enriched: List[Dict[str, str]] = []
    subtotal = 0

    for record in records:
        if record.pricing_mode == "重量×單價":
            if record.weight is None:
                raise PDFGenerationError(f"列資料缺少重量，無法以重量計價：{record}")
            base_value = record.weight
        else:
            if record.quantity is None:
                raise PDFGenerationError(f"列資料缺少數量，無法以片數計價：{record}")
            base_value = Decimal(record.quantity)

        amount = _ceil_decimal_to_int(base_value * record.unit_price)
        subtotal += amount

        quantity_text = "" if record.quantity is None else str(record.quantity)
        weight_text = "" if record.weight is None else f"{record.weight:.2f}"
        enriched.append(
            {
                "date_str": f"{record.month.strip()}/{record.date.strip()}",
                "order": record.order,
                "type": record.item_type,
                "color": record.color,
                "quantity": quantity_text,
                "unit_price": f"{record.unit_price:.2f}",
                "weight": weight_text,
                "amount": f"{amount}元",
                "remark": record.remark,
            }
        )

    tax = _ceil_decimal_to_int(Decimal(subtotal) * TAX_RATE)
    total = subtotal + tax
    return enriched, (subtotal, tax, total)


def render_pdf(output_path: str | Path, customer: str, year: str, month: str, records: Sequence[PDFRecord]) -> None:
    output_path = Path(output_path)

    if not customer or not year or not month:
        raise PDFGenerationError("customer / year / month 不可空白。")
    if not records:
        raise PDFGenerationError("沒有可輸出的資料。")

    normalized_rows, totals = normalize_records(records)
    chunks = [normalized_rows[i:i + MAX_ROWS_PER_PDF] for i in range(0, len(normalized_rows), MAX_ROWS_PER_PDF)]
    num_pages = max(1, len(chunks))

    pdf = FPDF(format="A4", unit="mm")
    pdf.set_auto_page_break(auto=False)
    ensure_fonts(pdf)

    for idx, rows_part in enumerate(chunks, start=1):
        _render_one_pdf_page(
            pdf=pdf,
            customer=customer,
            year=year,
            title_month=month,
            rows=rows_part,
            overall_totals=totals,
            is_last=(idx == num_pages),
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output_path))
