from typing import Dict, Tuple

CUSTOMERS: Tuple[str, ...] = ("廣銘", "傑展", "儒鴻", "慧聚", "陞勇", "合一", "昌鴻", "其他")
ORDERNO_OPTIONS: Tuple[str, ...] = ("銷樣",)
CATEGORY_OPTIONS: Tuple[str, ...] = (
    "鍵盤",
    "領片",
    "袖口",
    "下擺",
    "門襟",
    "電腦領",
    "波浪領",
    "腰頭",
    "總針",
    "魚骨領",
    "雙面領",
    "其他",
)
REMARK_OPTIONS: Tuple[str, ...] = (
    "勾1次",
    "勾2次",
    "勾3次",
    "勾4次",
    "勾5次",
    "冷凍",
    "大尺寸",
    "立彬倒紗",
    "以下為冷凍",
    "其他",
)
MONTHS: Tuple[str, ...] = tuple(str(i) for i in range(1, 13))
DATES: Tuple[str, ...] = tuple(str(i) for i in range(1, 32))
COLOR_MODE_OPTIONS: Tuple[str, ...] = ("輸入數量", "輸入顏色")
PRICING_MODE_OPTIONS: Tuple[str, ...] = ("片數×單價", "重量×單價")
PRICING_MODE_COLUMN = "計價模式"

DATA_COLUMNS: Tuple[str, ...] = (
    "月份",
    "日期",
    "訂單號碼",
    "類別",
    "顏色(組)",
    "數量(片)",
    "單價(元)",
    "重量(kg)",
    "備註",
)
ROW_COLUMNS: Tuple[str, ...] = (PRICING_MODE_COLUMN,) + DATA_COLUMNS
DISPLAY_COLUMNS: Tuple[str, ...] = ("序號",) + ROW_COLUMNS

INPUT_WIDTHS: Dict[str, int] = {
    "月份": 6,
    "日期": 6,
    "訂單號碼": 12,
    "類別": 10,
    "顏色(組)": 16,
    "數量(片)": 8,
    "單價(元)": 8,
    "重量(kg)": 8,
    "備註": 16,
}

WINDOW_TITLE = "工繳明細自動產生器"
WINDOW_SIZE = "1500x900"
DEFAULT_FONT_FAMILY = "Microsoft JhengHei"
DEFAULT_FONT_SIZE = 16
TREEVIEW_ROW_HEIGHT = 40
TABLE_INDEX_COLUMN = "序號"
