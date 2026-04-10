from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Dict, Optional, Tuple

from wage_app.constants import DATES, MONTHS, PRICING_MODE_OPTIONS, ROW_COLUMNS

ValidationResult = Tuple[bool, str, Optional[Dict[str, str]]]
MetadataValidationResult = Tuple[bool, str]


def _parse_decimal(value: str) -> Decimal:
    return Decimal(value)


def _normalize_decimal_text(value: str) -> str:
    decimal_value = Decimal(value)
    text = format(decimal_value.normalize(), "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def _normalize_int_text(value: str) -> str:
    return str(int(value))


def validate_row_input(raw: Dict[str, str], color_mode: str) -> ValidationResult:
    values = {col: (raw.get(col, "") or "").strip() for col in ROW_COLUMNS}

    if values["計價模式"] not in PRICING_MODE_OPTIONS:
        return False, "請選擇有效的【計價模式】。", None

    if values["月份"] not in MONTHS:
        return False, "請選擇有效的【月份】。", None

    if values["日期"] not in DATES:
        return False, "請選擇有效的【日期】。", None

    if not values["訂單號碼"]:
        return False, "請填寫【訂單號碼】。", None

    color_raw = values["顏色(組)"]
    if color_mode == "輸入數量":
        if color_raw == "":
            return False, "顏色輸入模式為【輸入數量】時，請輸入整數（例：3）。", None
        try:
            n = int(color_raw)
            if n < 0:
                raise ValueError
            values["顏色(組)"] = str(n)
        except ValueError:
            return False, "顏色輸入模式為【輸入數量】時，請輸入整數（例：3）。", None
    else:
        parts = [part for part in re.split(r"[,\s、]+", color_raw) if part]
        if not parts:
            return False, "請輸入至少一個顏色名稱（例：黑, 白, 紅）。", None
        values["顏色(組)"] = "、".join(parts)

    if not values["單價(元)"]:
        return False, "請填寫【單價(元)】。", None

    if values["數量(片)"]:
        try:
            quantity = int(values["數量(片)"])
            if quantity < 0:
                raise ValueError
            values["數量(片)"] = _normalize_int_text(values["數量(片)"])
        except ValueError:
            return False, "【數量(片)】需為非負整數。", None

    if values["單價(元)"]:
        try:
            price = _parse_decimal(values["單價(元)"])
            if price < 0:
                raise InvalidOperation
            values["單價(元)"] = _normalize_decimal_text(values["單價(元)"])
        except (InvalidOperation, ValueError):
            return False, "【單價(元)】需為非負數字。", None

    if values["重量(kg)"]:
        try:
            weight = _parse_decimal(values["重量(kg)"])
            if weight < 0:
                raise InvalidOperation
            values["重量(kg)"] = _normalize_decimal_text(values["重量(kg)"])
        except (InvalidOperation, ValueError):
            return False, "【重量(kg)】需為非負數字。", None

    if values["計價模式"] == "片數×單價" and not values["數量(片)"]:
        return False, "計價模式為【片數×單價】時，請填寫【數量(片)】。", None

    if values["計價模式"] == "重量×單價" and not values["重量(kg)"]:
        return False, "計價模式為【重量×單價】時，請填寫【重量(kg)】。", None

    return True, "", values


def validate_export_metadata(customer: str, year: str, month: str) -> MetadataValidationResult:
    customer = customer.strip()
    year = year.strip()
    month = month.strip()

    if not customer:
        return False, "請填寫【客戶名稱】。"
    if not year:
        return False, "請填寫【年份（民國）】。"
    if not year.isdigit():
        return False, "【年份（民國）】需為整數。"
    if int(year) <= 0:
        return False, "【年份（民國）】需大於 0。"
    if month not in MONTHS:
        return False, "請選擇有效的【標題月份】。"

    return True, ""
