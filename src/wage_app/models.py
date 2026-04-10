from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List

from wage_app.constants import ROW_COLUMNS


@dataclass(slots=True)
class TableRow:
    pricing_mode: str
    month: str
    date: str
    order_no: str
    category: str
    color: str
    quantity: str
    unit_price: str
    weight: str
    remark: str

    @classmethod
    def from_cleaned_dict(cls, data: Dict[str, str]) -> "TableRow":
        return cls(
            pricing_mode=data["計價模式"],
            month=data["月份"],
            date=data["日期"],
            order_no=data["訂單號碼"],
            category=data["類別"],
            color=data["顏色(組)"],
            quantity=data["數量(片)"],
            unit_price=data["單價(元)"],
            weight=data["重量(kg)"],
            remark=data["備註"],
        )

    def as_cleaned_dict(self) -> Dict[str, str]:
        return {
            "計價模式": self.pricing_mode,
            "月份": self.month,
            "日期": self.date,
            "訂單號碼": self.order_no,
            "類別": self.category,
            "顏色(組)": self.color,
            "數量(片)": self.quantity,
            "單價(元)": self.unit_price,
            "重量(kg)": self.weight,
            "備註": self.remark,
        }

    def as_display_values(self) -> List[str]:
        data = self.as_cleaned_dict()
        return [data[col] for col in ROW_COLUMNS]


@dataclass(slots=True)
class PDFRecord:
    pricing_mode: str
    month: str
    date: str
    order: str
    item_type: str
    color: str
    quantity: int | None
    unit_price: Decimal
    weight: Decimal | None
    remark: str
