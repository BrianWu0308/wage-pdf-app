from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Sequence

from wage_app.constants import (
    CATEGORY_OPTIONS,
    COLOR_MODE_OPTIONS,
    CUSTOMERS,
    DATA_COLUMNS,
    DATES,
    DEFAULT_FONT_FAMILY,
    DEFAULT_FONT_SIZE,
    DISPLAY_COLUMNS,
    INPUT_WIDTHS,
    MONTHS,
    ORDERNO_OPTIONS,
    PRICING_MODE_OPTIONS,
    REMARK_OPTIONS,
    ROW_COLUMNS,
    TREEVIEW_ROW_HEIGHT,
    WINDOW_SIZE,
    WINDOW_TITLE,
)
from wage_app.export_service import build_default_pdf_name, export_table_rows_to_pdf
from wage_app.formatters import pretty_fraction_text
from wage_app.models import TableRow
from wage_app.validators import validate_export_metadata, validate_row_input


class WageApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry(WINDOW_SIZE)

        self.last_saved_dir = os.getcwd()
        self.inputs: Dict[str, tk.Widget] = {}
        self.color_mode = tk.StringVar(value=COLOR_MODE_OPTIONS[0])
        self.pricing_mode = tk.StringVar(value=PRICING_MODE_OPTIONS[0])
        self.last_used_pricing_mode = PRICING_MODE_OPTIONS[0]
        self.editing_item_id: str | None = None

        self._configure_styles()
        self._build_top()
        self._build_table()
        self._build_inputs()
        self._build_buttons()
        self._bind_shortcuts()

    def _configure_styles(self) -> None:
        default_font = (DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZE)
        self.root.option_add("*Font", default_font)

        style = ttk.Style()
        style.configure("Treeview.Heading", font=(DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZE))
        style.configure("Treeview", font=(DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZE), rowheight=TREEVIEW_ROW_HEIGHT)

    def _build_top(self) -> None:
        frame_top = tk.Frame(self.root)
        frame_top.pack(pady=5)

        tk.Label(frame_top, text="客戶名稱").grid(row=0, column=0, padx=4)
        tk.Label(frame_top, text="年份（民國）").grid(row=0, column=2, padx=4)
        tk.Label(frame_top, text="標題月份").grid(row=0, column=4, padx=4)

        self.customer_entry = ttk.Combobox(frame_top, width=18, state="normal", values=CUSTOMERS)
        self.year_entry = tk.Entry(frame_top, width=10)
        self.month_combobox = ttk.Combobox(frame_top, values=MONTHS, width=5, state="readonly")

        self.customer_entry.grid(row=0, column=1)
        self.year_entry.grid(row=0, column=3)
        self.month_combobox.grid(row=0, column=5)
        self.month_combobox.set("1")
        self.month_combobox.bind("<<ComboboxSelected>>", self._on_title_month_changed)

    def _build_table(self) -> None:
        table_frame = tk.Frame(self.root)
        table_frame.pack(padx=5, pady=5, fill="both", expand=True)

        self.table = ttk.Treeview(table_frame, columns=DISPLAY_COLUMNS, show="headings")
        y_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        x_scroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.table.xview)
        self.table.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        self.table.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")

        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        for col in DISPLAY_COLUMNS:
            self.table.heading(col, text=col)
            if col == "序號":
                self.table.column(col, width=70, anchor="center")
            elif col == "計價模式":
                self.table.column(col, width=0, stretch=False, anchor="center")
            else:
                self.table.column(col, width=130, anchor="center")

        def on_mousewheel(event):
            if event.num == 4:
                delta = 1
            elif event.num == 5:
                delta = -1
            else:
                delta = int(event.delta / 120)
            self.table.yview_scroll(-delta, "units")

        self.table.bind("<MouseWheel>", on_mousewheel)
        self.table.bind("<Button-4>", on_mousewheel)
        self.table.bind("<Button-5>", on_mousewheel)
        self.table.bind("<Shift-MouseWheel>", lambda e: self.table.xview_scroll(int(-e.delta / 120), "units"))
        self.table.bind("<Double-1>", lambda _e: self.load_selected_row_for_edit())

    def _build_inputs(self) -> None:
        frame_input = tk.Frame(self.root)
        frame_input.pack(pady=6)

        tk.Label(frame_input, text="計價模式").grid(row=0, column=0, padx=4, sticky="w")
        pricing_cb = ttk.Combobox(
            frame_input,
            textvariable=self.pricing_mode,
            values=PRICING_MODE_OPTIONS,
            width=12,
            state="readonly",
        )
        pricing_cb.grid(row=1, column=0, padx=4, sticky="w")

        tk.Label(frame_input, text="顏色輸入模式").grid(row=0, column=1, padx=4, sticky="w")
        color_mode_cb = ttk.Combobox(
            frame_input,
            textvariable=self.color_mode,
            values=COLOR_MODE_OPTIONS,
            width=10,
            state="readonly",
        )
        color_mode_cb.grid(row=1, column=1, padx=4, sticky="w")
        color_mode_cb.bind("<<ComboboxSelected>>", lambda _evt: self._refresh_color_hint())


        for i, col in enumerate(DATA_COLUMNS, start=2):
            tk.Label(frame_input, text=col).grid(row=0, column=i, padx=4, sticky="n", pady=(0, 2))
            width = INPUT_WIDTHS.get(col, 12)

            if col == "類別":
                cb = ttk.Combobox(frame_input, values=CATEGORY_OPTIONS, width=width, state="normal")
                cb.grid(row=1, column=i, padx=4, sticky="w")
                self.inputs[col] = cb

                def on_category_selected(_evt=None, this_cb=cb):
                    if this_cb.get() == "鍵盤":
                        this_cb.set("")
                        self.open_category_keypad(target_cb=this_cb)

                cb.bind("<<ComboboxSelected>>", on_category_selected)

            elif col == "月份":
                cb = ttk.Combobox(frame_input, values=MONTHS, width=width, state="readonly")
                cb.grid(row=1, column=i, padx=4, sticky="w")
                cb.set(self.month_combobox.get())
                self.inputs[col] = cb

            elif col == "日期":
                cb = ttk.Combobox(frame_input, values=DATES, width=width, state="normal")
                cb.grid(row=1, column=i, padx=4, sticky="w")
                self.inputs[col] = cb

            elif col == "訂單號碼":
                cb = ttk.Combobox(frame_input, width=width, state="normal", values=ORDERNO_OPTIONS)
                cb.grid(row=1, column=i, padx=4, sticky="w")
                self.inputs[col] = cb

            elif col == "顏色(組)":
                entry = tk.Entry(frame_input, width=width)
                entry.grid(row=1, column=i, padx=4, sticky="w")
                self.inputs[col] = entry

                self.color_hint = tk.Label(frame_input, fg="#666666")
                self.color_hint.grid(row=2, column=i, padx=4, pady=(2, 0), sticky="w")

            elif col == "備註":
                cb = ttk.Combobox(frame_input, width=width, state="normal", values=REMARK_OPTIONS)
                cb.grid(row=1, column=i, padx=4, sticky="w")
                self.inputs[col] = cb

            else:
                entry = tk.Entry(frame_input, width=width)
                entry.grid(row=1, column=i, padx=4, sticky="w")
                self.inputs[col] = entry

        self._refresh_color_hint()

    def _build_buttons(self) -> None:
        frame_button = tk.Frame(self.root)
        frame_button.pack(pady=8)

        self.save_row_button = tk.Button(frame_button, text="新增資料列", command=self.save_row)
        self.save_row_button.pack(side="left", padx=10)

        tk.Button(frame_button, text="載入選取列", command=self.load_selected_row_for_edit).pack(side="left", padx=10)

        self.cancel_edit_button = tk.Button(
            frame_button,
            text="取消編輯",
            command=self.cancel_edit,
            state="disabled",
        )
        self.cancel_edit_button.pack(side="left", padx=10)

        tk.Button(frame_button, text="刪除選取列", command=self.delete_row, bg="red", fg="white").pack(side="left", padx=10)
        tk.Button(frame_button, text="產生 PDF", command=self.export_pdf, bg="green", fg="white").pack(side="left", padx=10)

    def _bind_shortcuts(self) -> None:
        self.root.bind("<Return>", lambda event: self.save_row())
        self.root.bind("<Delete>", lambda event: self.delete_row())
        self.root.bind("<Escape>", lambda event: self.cancel_edit())

    def _refresh_color_hint(self) -> None:
        self.color_hint.config(text=f"（模式：{self.color_mode.get()}）")

    def _on_title_month_changed(self, _event=None) -> None:
        if self.editing_item_id is not None:
            return
        month_widget = self.inputs.get("月份")
        if isinstance(month_widget, ttk.Combobox):
            month_widget.set(self.month_combobox.get())

    def _get_widget_text(self, widget: tk.Widget) -> str:
        if isinstance(widget, ttk.Combobox):
            return widget.get().strip()
        return str(widget.get()).strip()

    def _collect_raw_inputs(self) -> Dict[str, str]:
        raw = {col: self._get_widget_text(self.inputs[col]) for col in DATA_COLUMNS}
        raw["計價模式"] = self.pricing_mode.get().strip()
        return raw

    def _focus_primary_input(self) -> None:
        target = self.inputs.get("日期") or self.inputs.get(DATA_COLUMNS[0])
        if target is not None:
            try:
                target.focus_set()
            except Exception:
                pass

    def _clear_inputs(self) -> None:
        for widget in self.inputs.values():
            if isinstance(widget, ttk.Combobox):
                widget.set("")
            else:
                try:
                    widget.delete(0, tk.END)
                except Exception:
                    pass

        self.pricing_mode.set(self.last_used_pricing_mode)

        month_widget = self.inputs.get("月份")
        if isinstance(month_widget, ttk.Combobox):
            month_widget.set(self.month_combobox.get())

        self._focus_primary_input()

    def _set_widget_text(self, widget: tk.Widget, text: str) -> None:
        value = "" if text is None else str(text)
        if isinstance(widget, ttk.Combobox):
            widget.set(value)
        else:
            try:
                widget.delete(0, tk.END)
                widget.insert(0, value)
            except Exception:
                pass

    def _renumber_rows(self) -> None:
        for i, iid in enumerate(self.table.get_children(), start=1):
            self.table.set(iid, "序號", str(i))

    def _get_selected_items(self) -> tuple[str, ...]:
        return tuple(self.table.selection())

    def _get_all_row_values(self) -> List[Sequence[object]]:
        return [self.table.item(row)["values"] for row in self.table.get_children()]

    def _set_editing_mode(self, item_id: str | None) -> None:
        self.editing_item_id = item_id
        is_editing = item_id is not None
        self.save_row_button.config(text="更新資料列" if is_editing else "新增資料列")
        self.cancel_edit_button.config(state="normal" if is_editing else "disabled")

    def open_category_keypad(self, target_cb: ttk.Combobox) -> None:
        top = tk.Toplevel(self.root)
        top.title("類別輸入鍵盤")
        top.grab_set()

        init_val = target_cb.get()
        expr_var = tk.StringVar(value="" if init_val == "鍵盤" else init_val)

        row0 = tk.Frame(top)
        row0.pack(padx=8, pady=6, fill="x")
        tk.Label(row0, text="輸入：").pack(side="left")
        entry = tk.Entry(row0, textvariable=expr_var, width=40)
        entry.pack(side="left", fill="x", expand=True)

        row1 = tk.Frame(top)
        row1.pack(padx=8, pady=(0, 8), fill="x")
        tk.Label(row1, text="預覽：").pack(side="left")
        preview = tk.Label(row1, text=pretty_fraction_text(expr_var.get()), fg="#444")
        preview.pack(side="left", fill="x", expand=True)

        expr_var.trace_add("write", lambda *_: preview.config(text=pretty_fraction_text(expr_var.get())))

        keys = [
            ["7", "8", "9", "乘", "英吋"],
            ["4", "5", "6", "分之", "公分"],
            ["1", "2", "3", "又", "小數點"],
            ["0", "←", "清除", "空白", "確定"],
        ]

        def put(token: str) -> None:
            if token == "小數點":
                token = "."
            if token == "乘":
                token = "×"
            if token == "英吋":
                token = '"'
            if token == "公分":
                token = "cm"
            if token == "空白":
                token = " "
            if token == "清除":
                expr_var.set("")
                return
            if token == "←":
                s = expr_var.get()
                expr_var.set(s[:-1] if s else s)
                return
            if token == "確定":
                nice = pretty_fraction_text(expr_var.get())
                target_cb.set(nice)
                top.destroy()
                return

            pos = entry.index(tk.INSERT)
            s = expr_var.get()
            expr_var.set(s[:pos] + token + s[pos:])
            entry.icursor(pos + len(token))
            entry.focus_set()

        grid = tk.Frame(top)
        grid.pack(padx=8, pady=8)
        for r, row in enumerate(keys):
            for c, label in enumerate(row):
                ttk.Button(grid, text=label, width=8, command=lambda t=label: put(t)).grid(row=r, column=c, padx=4, pady=4)

        entry.focus_set()

    def save_row(self) -> None:
        raw = self._collect_raw_inputs()
        ok, msg, cleaned = validate_row_input(raw, self.color_mode.get())
        if not ok or cleaned is None:
            messagebox.showwarning("格式錯誤", msg)
            return

        row = TableRow.from_cleaned_dict(cleaned)
        self.last_used_pricing_mode = row.pricing_mode
        display_values = row.as_display_values()

        if self.editing_item_id is None:
            next_idx = len(self.table.get_children()) + 1
            self.table.insert("", "end", values=[str(next_idx)] + display_values)
        else:
            self.table.item(self.editing_item_id, values=[self.table.set(self.editing_item_id, "序號")] + display_values)

        self.cancel_edit(clear_inputs=False)
        self._clear_inputs()

    def load_selected_row_for_edit(self) -> None:
        selected = self._get_selected_items()
        if not selected:
            messagebox.showwarning("未選取", "請先在表格選取要載入的一列")
            return
        if len(selected) > 1:
            messagebox.showwarning("一次僅支援一列", "請只選取一列再執行『載入選取列』")
            return

        iid = selected[0]
        values = self.table.item(iid)["values"]
        if not values:
            messagebox.showerror("資料錯誤", "選取列的資料格式不完整，無法載入。")
            return

        raw_values = values[1:]
        if len(raw_values) == len(ROW_COLUMNS):
            row_map = dict(zip(ROW_COLUMNS, raw_values))
        elif len(raw_values) == len(DATA_COLUMNS):
            row_map = {"計價模式": PRICING_MODE_OPTIONS[0], **dict(zip(DATA_COLUMNS, raw_values))}
        else:
            messagebox.showerror("資料錯誤", "選取列的資料格式不完整，無法載入。")
            return

        self.pricing_mode.set(str(row_map.get("計價模式") or PRICING_MODE_OPTIONS[0]))

        for col_name in DATA_COLUMNS:
            widget = self.inputs.get(col_name)
            if widget is not None:
                self._set_widget_text(widget, str(row_map.get(col_name, "")))

        self._set_editing_mode(iid)
        self._focus_primary_input()

    def cancel_edit(self, clear_inputs: bool = True) -> None:
        self._set_editing_mode(None)
        if clear_inputs:
            self._clear_inputs()

    def delete_row(self) -> None:
        selected = self._get_selected_items()
        if not selected:
            messagebox.showwarning("未選取", "請先選取要刪除的資料列")
            return

        lines: List[str] = []
        for iid in selected:
            vals = self.table.item(iid)["values"]
            row = {"序號": vals[0]}
            if len(vals[1:]) == len(ROW_COLUMNS):
                raw_map = dict(zip(ROW_COLUMNS, vals[1:]))
            else:
                raw_map = {"計價模式": PRICING_MODE_OPTIONS[0], **dict(zip(DATA_COLUMNS, vals[1:]))}
            row.update(raw_map)
            lines.append(
                f"#{row['序號']}  計價:{row.get('計價模式', '')}  月:{row.get('月份', '')} 日:{row.get('日期', '')}  "
                f"訂單:{row.get('訂單號碼', '')}  類別:{row.get('類別', '')}  "
                f"顏色:{row.get('顏色(組)', '')}  數量:{row.get('數量(片)', '')}  "
                f"單價:{row.get('單價(元)', '')}  重量:{row.get('重量(kg)', '')}  "
                f"備註:{row.get('備註', '')}"
            )

        preview_text = "\n".join(lines[:10]) + (f"\n...（共 {len(lines)} 筆）" if len(lines) > 10 else "")
        if not messagebox.askyesno("確認刪除", f"即將刪除以下 {len(selected)} 筆資料：\n\n{preview_text}\n\n是否確定刪除？"):
            return

        if self.editing_item_id in selected:
            self.cancel_edit()

        for iid in selected:
            self.table.delete(iid)

        self._renumber_rows()

    def export_pdf(self) -> None:
        customer = self.customer_entry.get().strip()
        year = self.year_entry.get().strip()
        month = self.month_combobox.get().strip()

        ok, msg = validate_export_metadata(customer, year, month)
        if not ok:
            messagebox.showwarning("匯出前檢查", msg)
            return

        row_items = self._get_all_row_values()
        if not row_items:
            messagebox.showwarning("沒有資料", "請先新增至少一筆資料再產生 PDF。")
            return

        default_name = build_default_pdf_name(customer, year, month)
        save_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            initialdir=self.last_saved_dir,
            initialfile=default_name,
            filetypes=[("PDF files", "*.pdf")],
        )
        if not save_path:
            return

        try:
            export_table_rows_to_pdf(
                save_path=save_path,
                customer=customer,
                year=year,
                month=month,
                table_rows=row_items,
            )
        except Exception as exc:
            messagebox.showerror("匯出失敗", str(exc))
            return

        self.last_saved_dir = os.path.dirname(save_path)
        messagebox.showinfo("成功", f"PDF 已輸出：\n{save_path}")
        try:
            os.startfile(save_path)
        except Exception:
            pass
