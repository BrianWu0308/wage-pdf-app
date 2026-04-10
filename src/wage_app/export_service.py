from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable, Sequence

from wage_app.constants import DATA_COLUMNS, PRICING_MODE_OPTIONS, ROW_COLUMNS
from wage_app.models import PDFRecord
from wage_app.pdf_renderer import render_pdf


def sanitize_filename_part(text: str) -> str:
    invalid_chars = '<>:"/\\|?*'
    sanitized = ''.join('_' if ch in invalid_chars else ch for ch in text.strip())
    return sanitized or '未命名'


def build_default_pdf_name(customer: str, year: str, month: str) -> str:
    safe_customer = sanitize_filename_part(customer)
    safe_year = sanitize_filename_part(year)
    safe_month = sanitize_filename_part(month)
    return f"{safe_year}年{safe_month}月份_{safe_customer}_工繳明細.pdf"


def _coerce_optional_decimal(value: object) -> Decimal | None:
    text = str(value or '').strip()
    if not text:
        return None
    return Decimal(text)


def _coerce_optional_int(value: object) -> int | None:
    text = str(value or '').strip()
    if not text:
        return None
    return int(text)


def table_rows_to_records(table_rows: Iterable[Sequence[object]]) -> list[PDFRecord]:
    records: list[PDFRecord] = []

    for row in table_rows:
        values = list(row)
        if len(values) == len(ROW_COLUMNS) + 1:
            values = values[1:]
            row_map = dict(zip(ROW_COLUMNS, values))
        elif len(values) == len(DATA_COLUMNS) + 1:
            # 舊格式：沒有存計價模式時，預設為片數×單價
            values = values[1:]
            row_map = {"計價模式": PRICING_MODE_OPTIONS[0], **dict(zip(DATA_COLUMNS, values))}
        elif len(values) == len(DATA_COLUMNS):
            row_map = {"計價模式": PRICING_MODE_OPTIONS[0], **dict(zip(DATA_COLUMNS, values))}
        else:
            raise ValueError(f"表格列格式不正確：{row}")

        try:
            price_text = str(row_map["單價(元)"] or "0").strip() or '0'
            record = PDFRecord(
                pricing_mode=str(row_map.get("計價模式") or PRICING_MODE_OPTIONS[0]),
                month=str(row_map["月份"]),
                date=str(row_map["日期"]),
                order=str(row_map["訂單號碼"]),
                item_type=str(row_map["類別"]),
                color=str(row_map["顏色(組)"]),
                quantity=_coerce_optional_int(row_map["數量(片)"]),
                unit_price=Decimal(price_text),
                weight=_coerce_optional_decimal(row_map["重量(kg)"]),
                remark=str(row_map["備註"]),
            )
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise ValueError(f"有資料無法解析：{row}") from exc

        records.append(record)

    return records


def export_table_rows_to_pdf(
    save_path: str | Path,
    customer: str,
    year: str,
    month: str,
    table_rows: Iterable[Sequence[object]],
) -> None:
    records = table_rows_to_records(table_rows)
    if not records:
        raise ValueError("沒有可輸出的資料。")
    render_pdf(Path(save_path), customer, year, month, records)
