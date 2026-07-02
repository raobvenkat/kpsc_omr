# -*- coding: utf-8 -*-
"""
DiscrepancyReports.py
---------------------
Professional discrepancy review and correction hub for KPSC OMR.

Left panel  : 11 numbered report categories with live record counts.
Right panel : Grid of flagged records + per-record detail view showing
              cropped image regions, detected values, and editable fields
              so an operator can review and correct data in place.
"""
from __future__ import annotations

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, List, Dict, Any

try:
    from PIL import Image, ImageTk
    _PIL_OK = True
except ImportError:
    _PIL_OK = False

try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    BASE_DIR = os.getcwd()

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from db_credentials import get_sql_connection

# -----------------------------------------------------------------------------
# CONSTANTS
# -----------------------------------------------------------------------------

LOGGED_USER_ID = 1          # replaced at runtime when auth is wired in

# PIL crop boxes for counter-foil images (left = x0, upper = y0, right = x1, lower = y1)
# Coordinates assume full-resolution scan; thumbnail is shown separately.
CROP_SUBJECT  = (30,   35,  530, 130)
CROP_BOOKLET  = (930, 690, 1425, 890)
CROP_BARCODE  = (940,  40, 1570, 170)
CROP_CAND_SIG = ( 50, 380,  920, 510)
CROP_INV_SIG  = ( 50, 530,  920, 660)
CROP_REG_BOX  = (960, 330, 1520, 430)

# Colours
C_BG        = "#0f1218"
C_SIDEBAR   = "#101018"
C_CARD      = "#181c24"
C_CARD_HOV  = "#1e2330"
C_BORDER    = "#2b313d"
C_ACCENT    = "#2979ff"
C_GREEN     = "#00c853"
C_RED       = "#ff5252"
C_YELLOW    = "#ffeb3b"
C_TEXT      = "#e8eaf0"
C_MUTED     = "#8b93a7"
C_HEADER_BG = "#1976D2"
C_RESOLVED  = "#1b3a1b"

FONT_TITLE  = ("Segoe UI", 18, "bold")
FONT_HEAD   = ("Segoe UI", 12, "bold")
FONT_BODY   = ("Segoe UI", 10)
FONT_SMALL  = ("Segoe UI", 9)
FONT_MONO   = ("Consolas",  10)

# -----------------------------------------------------------------------------
# REPORT REGISTRY  — single source of truth
# -----------------------------------------------------------------------------

REPORTS: List[Dict[str, Any]] = [
    {
        "id": 1,
        "name": "Subject Code & Booklet Serial No",
        "proc": "dbo.Disc_SubjectCodeBookletNo",
        "update_proc": "dbo.Disc_Update_SubjectBooklet",
        "source": "counter_foil",
        "cols": [
            ("ID","ID",50), ("FileName","File",220), ("Barcode","Barcode",120),
            ("Subject_Code","Subject Code",110), ("Booklet_Sl_No","Booklet Serial No",130),
            ("IsResolved","Resolved",70),
        ],
        "edit_fields": [
            ("Subject_Code",      "Subject Code",       "subject"),
            ("Booklet_Sl_No",     "Booklet Serial No",  "booklet"),
        ],
        "crops": {
            "subject": CROP_SUBJECT,
            "booklet": CROP_BOOKLET,
        },
    },
    {
        "id": 2,
        "name": "Barcode Discrepancy",
        "proc": "dbo.Disc_BarcodeDiscrepancy",
        "update_proc": "dbo.Disc_Update_Barcode",
        "source": "counter_foil",
        "cols": [
            ("ID","ID",50), ("FileName","File",220), ("Detected_Barcode","Detected Barcode",160),
            ("Bubble_RegNo","Bubble RegNo",120), ("Final_RegNo","Final RegNo",120),
            ("IsResolved","Resolved",70),
        ],
        "edit_fields": [
            ("Detected_Barcode", "Barcode", "barcode"),
        ],
        "crops": {
            "barcode": CROP_BARCODE,
        },
    },
    {
        "id": 3,
        "name": "Written RegNo Discrepancy",
        "proc": "dbo.Disc_WrittenRegNoDiscrepancy",
        "update_proc": "dbo.Disc_Update_RegNo",
        "source": "counter_foil",
        "cols": [
            ("ID","ID",50), ("FileName","File",220), ("Barcode","Barcode",120),
            ("Handwritten_RegNo","Handwritten RegNo",140), ("Bubble_RegNo","Bubble RegNo",120),
            ("Final_RegNo","Final RegNo",120), ("IsResolved","Resolved",70),
        ],
        "edit_fields": [
            ("Handwritten_RegNo", "Handwritten RegNo", "reg_box"),
            ("Bubble_RegNo",      "Bubble RegNo",      "reg_box"),
            ("Final_RegNo",       "Final RegNo",       None),
        ],
        "crops": {
            "reg_box": CROP_REG_BOX,
        },
    },
    {
        "id": 4,
        "name": "OMR RegNo Discrepancy",
        "proc": "dbo.Disc_OMRRegNoDiscrepancy",
        "update_proc": "dbo.Disc_Update_RegNo",
        "source": "counter_foil",
        "cols": [
            ("ID","ID",50), ("FileName","File",220), ("Barcode","Barcode",120),
            ("Bubble_RegNo","Bubble RegNo",130), ("Handwritten_RegNo","Handwritten RegNo",140),
            ("Final_RegNo","Final RegNo",120), ("Discrepancy_Detail","Detail",200),
            ("IsResolved","Resolved",70),
        ],
        "edit_fields": [
            ("Bubble_RegNo",      "Bubble RegNo",      "reg_box"),
            ("Handwritten_RegNo", "Handwritten RegNo", "reg_box"),
            ("Final_RegNo",       "Final RegNo",       None),
        ],
        "crops": {
            "reg_box": CROP_REG_BOX,
        },
    },
    {
        "id": 5,
        "name": "Whitener Used in Bubbles",
        "proc": "dbo.Disc_WhitenerUsed",
        "update_proc": "dbo.Disc_Update_BubbleIssue",
        "source": "counter_foil",
        "cols": [
            ("ID","ID",50), ("FileName","File",220), ("Barcode","Barcode",120),
            ("Bubble_RegNo","Bubble RegNo",130), ("Final_RegNo","Final RegNo",120),
            ("Whitener_Detected","Whitener",80), ("IsResolved","Resolved",70),
        ],
        "edit_fields": [
            ("Final_RegNo", "Final RegNo (corrected)", None),
        ],
        "crops": {
            "reg_box": CROP_REG_BOX,
        },
    },
    {
        "id": 6,
        "name": "Bubbles Marked <35% Threshold",
        "proc": "dbo.Disc_BubbleThreshold",
        "update_proc": "dbo.Disc_Update_BubbleIssue",
        "source": "counter_foil",
        "cols": [
            ("ID","ID",50), ("FileName","File",220), ("Barcode","Barcode",120),
            ("Bubble_RegNo","Bubble RegNo",130), ("OMR_Threshold","Threshold",90),
            ("Final_RegNo","Final RegNo",120), ("IsResolved","Resolved",70),
        ],
        "edit_fields": [
            ("Final_RegNo", "Final RegNo (corrected)", None),
        ],
        "crops": {
            "reg_box": CROP_REG_BOX,
        },
    },
    {
        "id": 7,
        "name": "Candidate Signature Discrepancy",
        "proc": "dbo.Disc_CandidateSignature",
        "update_proc": "dbo.Disc_Update_CounterFoilSignature",
        "source": "counter_foil",
        "cols": [
            ("ID","ID",50), ("FileName","File",220), ("Barcode","Barcode",120),
            ("Final_RegNo","Final RegNo",130), ("Candidate_Signed","Cand. Signed",100),
            ("IsResolved","Resolved",70),
        ],
        "edit_fields": [
            ("Candidate_Signed",   "Candidate Signed",   "cand_sig"),
            ("Invigilator_Signed", "Invigilator Signed", "inv_sig"),
        ],
        "crops": {
            "cand_sig": CROP_CAND_SIG,
            "inv_sig":  CROP_INV_SIG,
        },
    },
    {
        "id": 8,
        "name": "Invigilator Signature Discrepancy",
        "proc": "dbo.Disc_InvigilatorSignature",
        "update_proc": "dbo.Disc_Update_CounterFoilSignature",
        "source": "counter_foil",
        "cols": [
            ("ID","ID",50), ("FileName","File",220), ("Barcode","Barcode",120),
            ("Final_RegNo","Final RegNo",130), ("Invigilator_Signed","Invgl. Signed",110),
            ("IsResolved","Resolved",70),
        ],
        "edit_fields": [
            ("Candidate_Signed",   "Candidate Signed",   "cand_sig"),
            ("Invigilator_Signed", "Invigilator Signed", "inv_sig"),
        ],
        "crops": {
            "cand_sig": CROP_CAND_SIG,
            "inv_sig":  CROP_INV_SIG,
        },
    },
    {
        "id": 9,
        "name": "Non-Standard OMR Sheet",
        "proc": "dbo.Disc_NonStandardOMR",
        "update_proc": "dbo.Disc_Update_NonStandardOMR",
        "source": "counter_foil",
        "cols": [
            ("ID","ID",50), ("FileName","File",220), ("Barcode","Barcode",120),
            ("Final_RegNo","Final RegNo",130), ("Is_BW","B&W",60),
            ("Is_Non_Standard","Non-Std",75), ("IsResolved","Resolved",70),
        ],
        "edit_fields": [
            ("Is_Non_Standard", "Non-Standard Flag (0/1)", None),
        ],
        "crops": {},
    },
    {
        "id": 10,
        "name": "Candidate Not Signed - Nominal Roll",
        "proc": "dbo.Disc_NominalRollCandidateSignature",
        "update_proc": "dbo.Disc_Update_NominalRollRow",
        "source": "nominal_roll",
        "cols": [
            ("ID","ID",50), ("Sheet_Type","Type",60), ("FileName","File",200),
            ("Row_Number","Row",50), ("Registration_No","Reg No",120),
            ("OMR_No","OMR/QCAB No",120), ("Status","Status",80),
            ("Signature_Present","Sig Present",90), ("IsResolved","Resolved",70),
        ],
        "edit_fields": [
            ("Registration_No",  "Registration No",   None),
            ("Signature_Present","Signature Present (0/1)", None),
        ],
        "crops": {},
    },
    {
        "id": 11,
        "name": "Invigilator Not Signed - Nominal Roll",
        "proc": "dbo.Disc_NominalRollInvigilatorSignature",
        "update_proc": "dbo.Disc_Update_NominalRollRow",
        "source": "nominal_roll",
        "cols": [
            ("ID","ID",50), ("Sheet_Type","Type",60), ("FileName","File",200),
            ("Invigilator_Signed","Invgl. Signed",100),
            ("Center_Code","Center",90), ("Subject_Code","Subject",90),
            ("IsResolved","Resolved",70),
        ],
        "edit_fields": [
            ("Invigilator_Signed", "Invigilator Signed (0/1)", None),
        ],
        "crops": {},
    },
]

REPORT_BY_ID = {r["id"]: r for r in REPORTS}


# -----------------------------------------------------------------------------
# HELPERS
# -----------------------------------------------------------------------------

def _conn():
    return get_sql_connection()


def _fetch(proc: str) -> tuple[list, list]:
    """Execute a stored procedure and return (columns, rows)."""
    conn = _conn()
    cur  = conn.cursor()
    cur.execute(f"EXEC {proc}")
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    conn.close()
    return cols, rows


def _pil_crop(filepath: str, box: tuple, display_size: tuple) -> Optional[ImageTk.PhotoImage]:
    """Open image, crop box, resize to display_size, return PhotoImage."""
    if not _PIL_OK or not filepath or not os.path.isfile(filepath):
        return None
    try:
        img = Image.open(filepath)
        if box:
            # Scale crop box to actual image size if needed
            iw, ih = img.size
            # Reference size assumed 1654×1080; scale proportionally
            sx = iw / 1654.0
            sy = ih / 1080.0
            x0 = int(box[0] * sx); y0 = int(box[1] * sy)
            x1 = int(box[2] * sx); y1 = int(box[3] * sy)
            x0 = max(0, x0); y0 = max(0, y0)
            x1 = min(iw, x1); y1 = min(ih, y1)
            if x1 > x0 and y1 > y0:
                img = img.crop((x0, y0, x1, y1))
        img.thumbnail(display_size, Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None


def _pil_thumbnail(filepath: str, display_size: tuple) -> Optional[ImageTk.PhotoImage]:
    """Return a thumbnail PhotoImage of the full image."""
    if not _PIL_OK or not filepath or not os.path.isfile(filepath):
        return None
    try:
        img = Image.open(filepath)
        img.thumbnail(display_size, Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None


def _count_report(proc: str) -> int:
    try:
        _, rows = _fetch(proc)
        return len(rows)
    except Exception:
        return -1


def _styled_entry(parent, width=22, **kw) -> tk.Entry:
    e = tk.Entry(
        parent, width=width,
        bg="#1e2330", fg=C_TEXT,
        insertbackground=C_TEXT,
        relief="flat",
        font=FONT_MONO,
        highlightthickness=1,
        highlightbackground=C_BORDER,
        highlightcolor=C_ACCENT,
        **kw
    )
    return e


def _styled_label(parent, text, bold=False, muted=False, **kw) -> tk.Label:
    fg   = C_MUTED if muted else C_TEXT
    font = ("Segoe UI", 10, "bold") if bold else FONT_BODY
    return tk.Label(parent, text=text, bg=C_CARD, fg=fg, font=font, anchor="w", **kw)


def _img_label(parent, text="", **kw) -> tk.Label:
    return tk.Label(
        parent, text=text,
        bg="#0d1017", fg=C_MUTED,
        font=FONT_SMALL,
        relief="flat",
        **kw
    )


# -----------------------------------------------------------------------------
# SIDEBAR — list of 11 report categories
# -----------------------------------------------------------------------------

class ReportSidebar(tk.Frame):
    """Left panel: numbered list of report categories with record counts."""

    def __init__(self, parent, on_select, **kw):
        super().__init__(parent, bg=C_SIDEBAR, **kw)
        self.on_select   = on_select
        self._items      = {}     # report_id -> {"frame", "count_lbl"}
        self._active_id  = None
        self._build()

    def _build(self):
        # Header
        tk.Label(
            self, text="Discrepancy Reports",
            bg=C_SIDEBAR, fg=C_TEXT,
            font=("Segoe UI", 13, "bold"),
            pady=14, padx=16, anchor="w"
        ).pack(fill="x")
        tk.Frame(self, bg=C_BORDER, height=1).pack(fill="x")

        # Scrollable container
        canvas = tk.Canvas(self, bg=C_SIDEBAR, highlightthickness=0)
        sb     = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self._list_frame = tk.Frame(canvas, bg=C_SIDEBAR)
        canvas_win = canvas.create_window((0, 0), window=self._list_frame, anchor="nw")

        def _on_frame_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
        def _on_canvas_configure(e):
            canvas.itemconfig(canvas_win, width=e.width)

        self._list_frame.bind("<Configure>", _on_frame_configure)
        canvas.bind("<Configure>", _on_canvas_configure)
        canvas.bind("<MouseWheel>",
                    lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        self._list_frame.bind("<MouseWheel>",
                    lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        for rpt in REPORTS:
            self._add_item(rpt)

    def _add_item(self, rpt: dict):
        rid   = rpt["id"]
        frame = tk.Frame(self._list_frame, bg=C_SIDEBAR, cursor="hand2")
        frame.pack(fill="x", padx=0, pady=0)

        # Left accent bar (hidden by default)
        accent = tk.Frame(frame, bg=C_SIDEBAR, width=4)
        accent.pack(side="left", fill="y")

        # Content
        body = tk.Frame(frame, bg=C_SIDEBAR, padx=10, pady=10)
        body.pack(side="left", fill="both", expand=True)

        # Number badge + name
        top_row = tk.Frame(body, bg=C_SIDEBAR)
        top_row.pack(fill="x")

        badge = tk.Label(
            top_row,
            text=f" {rid:02d} ",
            bg=C_BORDER, fg=C_MUTED,
            font=("Segoe UI", 8, "bold"),
            padx=3, pady=1
        )
        badge.pack(side="left", padx=(0, 6))

        name_lbl = tk.Label(
            top_row, text=rpt["name"],
            bg=C_SIDEBAR, fg=C_TEXT,
            font=("Segoe UI", 10),
            anchor="w", wraplength=210, justify="left"
        )
        name_lbl.pack(side="left", fill="x", expand=True)

        # Count row
        count_lbl = tk.Label(
            body, text="— records",
            bg=C_SIDEBAR, fg=C_MUTED,
            font=FONT_SMALL, anchor="w"
        )
        count_lbl.pack(fill="x")

        separator = tk.Frame(self._list_frame, bg=C_BORDER, height=1)
        separator.pack(fill="x")

        self._items[rid] = {
            "frame":     frame,
            "accent":    accent,
            "name_lbl":  name_lbl,
            "badge":     badge,
            "count_lbl": count_lbl,
            "body":      body,
        }

        # Bind all sub-widgets
        for w in (frame, body, top_row, badge, name_lbl, count_lbl, accent, separator):
            w.bind("<Button-1>", lambda e, r=rid: self._click(r))
            w.bind("<Enter>",    lambda e, r=rid: self._hover(r, True))
            w.bind("<Leave>",    lambda e, r=rid: self._hover(r, False))

    def _click(self, rid: int):
        self.select(rid)
        self.on_select(rid)

    def _hover(self, rid: int, on: bool):
        if rid == self._active_id:
            return
        bg = C_CARD_HOV if on else C_SIDEBAR
        item = self._items[rid]
        for w in (item["frame"], item["body"]):
            w.configure(bg=bg)
        for w in (item["name_lbl"], item["count_lbl"], item["badge"]):
            w.configure(bg=bg)

    def select(self, rid: int):
        # Deactivate previous
        if self._active_id and self._active_id in self._items:
            prev = self._items[self._active_id]
            prev["accent"].configure(bg=C_SIDEBAR)
            prev["frame"].configure(bg=C_SIDEBAR)
            prev["body"].configure(bg=C_SIDEBAR)
            prev["name_lbl"].configure(bg=C_SIDEBAR, fg=C_TEXT, font=("Segoe UI", 10))
            prev["count_lbl"].configure(bg=C_SIDEBAR)
            prev["badge"].configure(bg=C_BORDER, fg=C_MUTED)

        self._active_id = rid
        item = self._items[rid]
        item["accent"].configure(bg=C_ACCENT)
        item["frame"].configure(bg="#141a28")
        item["body"].configure(bg="#141a28")
        item["name_lbl"].configure(bg="#141a28", fg="#ffffff", font=("Segoe UI", 10, "bold"))
        item["count_lbl"].configure(bg="#141a28")
        item["badge"].configure(bg=C_ACCENT, fg="#ffffff")

    def set_count(self, rid: int, count: int):
        if rid not in self._items:
            return
        lbl = self._items[rid]["count_lbl"]
        if count < 0:
            lbl.configure(text="error loading", fg=C_RED)
        elif count == 0:
            lbl.configure(text="no open items", fg=C_GREEN)
        else:
            lbl.configure(text=f"{count} open item{'s' if count != 1 else ''}", fg=C_YELLOW)


# -----------------------------------------------------------------------------
# DETAIL PANEL — shows cropped images + editable fields for one record
# -----------------------------------------------------------------------------

class DetailPanel(tk.Frame):
    """
    Right-side detail view.
    Rendered fresh each time a row is selected.
    """

    def __init__(self, parent, on_save, on_reset, **kw):
        super().__init__(parent, bg=C_CARD, **kw)
        self.on_save  = on_save
        self.on_reset = on_reset
        self._photo_refs: list = []   # keep PhotoImage references alive
        self._entries: dict   = {}    # field_key -> tk.Entry
        self._row_data: dict  = {}
        self._report: dict    = {}
        self._build_empty()

    # ------------------------------------------------------------------
    def _build_empty(self):
        tk.Label(
            self,
            text="Select a record from the grid to review and correct it.",
            bg=C_CARD, fg=C_MUTED,
            font=("Segoe UI", 11),
        ).place(relx=0.5, rely=0.5, anchor="center")

    # ------------------------------------------------------------------
    def clear(self):
        for w in self.winfo_children():
            w.destroy()
        self._photo_refs.clear()
        self._entries.clear()
        self._row_data  = {}
        self._report    = {}

    # ------------------------------------------------------------------
    def load(self, report: dict, col_names: list, row_values: list):
        self.clear()
        self._report   = report
        self._row_data = dict(zip(col_names, row_values))

        # -- Scrollable container ---------------------------------------
        outer = tk.Frame(self, bg=C_CARD)
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(outer, bg=C_CARD, highlightthickness=0)
        vsb    = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(canvas, bg=C_CARD)
        win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_inner_conf(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
        def _on_canvas_conf(e):
            canvas.itemconfig(win_id, width=e.width)
        inner.bind("<Configure>", _on_inner_conf)
        canvas.bind("<Configure>", _on_canvas_conf)
        for w in (canvas, inner):
            w.bind("<MouseWheel>",
                   lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        self._render_detail(inner, report, col_names, row_values)

    # ------------------------------------------------------------------
    def _render_detail(self, parent, report: dict, col_names: list, row_values: list):
        rd   = self._row_data
        rid  = rd.get("ID", "")
        fname = str(rd.get("FileName", ""))
        pad  = dict(padx=16, pady=6)

        # -- Header bar ------------------------------------------------
        hdr = tk.Frame(parent, bg=C_HEADER_BG)
        hdr.pack(fill="x")
        tk.Label(
            hdr,
            text=f"  {report['id']:02d}  {report['name']}",
            bg=C_HEADER_BG, fg="white",
            font=("Segoe UI", 13, "bold"),
            pady=10
        ).pack(side="left")
        tk.Label(
            hdr, text=f"Record ID: {rid}",
            bg=C_HEADER_BG, fg="#bbdefb",
            font=FONT_SMALL, padx=16
        ).pack(side="right")

        # -- Resolved banner -------------------------------------------
        if str(rd.get("IsResolved", "0")) in ("1", "True"):
            tk.Frame(parent, bg="#2e7d32", height=28).pack(fill="x")
            tk.Label(
                parent,
                text="  [OK]  This record has been resolved and updated.",
                bg="#2e7d32", fg="#c8e6c9",
                font=("Segoe UI", 9, "bold"),
                pady=4
            ).pack(fill="x")

        # -- File name info row -----------------------------------------
        info_row = tk.Frame(parent, bg=C_CARD)
        info_row.pack(fill="x", padx=16, pady=(10, 0))
        tk.Label(info_row, text="File:", bg=C_CARD, fg=C_MUTED,
                 font=FONT_SMALL).pack(side="left")
        tk.Label(info_row,
                 text=os.path.basename(fname) if fname else "—",
                 bg=C_CARD, fg=C_TEXT, font=FONT_SMALL).pack(side="left", padx=(4, 0))
        # Full path tooltip-style
        tk.Label(info_row, text=fname, bg=C_CARD, fg="#445566",
                 font=("Segoe UI", 8), wraplength=500, justify="left"
                 ).pack(side="left", padx=(10, 0))

        tk.Frame(parent, bg=C_BORDER, height=1).pack(fill="x", padx=16, pady=6)

        # -- Main body: LEFT crops  /  RIGHT edit fields ----------------
        body = tk.Frame(parent, bg=C_CARD)
        body.pack(fill="both", expand=True, padx=0, pady=0)

        crops_cfg = report.get("crops", {})
        if crops_cfg and _PIL_OK and fname and os.path.isfile(fname):
            left  = tk.Frame(body, bg=C_CARD)
            right = tk.Frame(body, bg=C_CARD)
            left.pack(side="left", fill="both", expand=True, padx=(16, 8), pady=8)
            right.pack(side="right", fill="both", expand=True, padx=(8, 16), pady=8)
            self._render_crops(left, fname, crops_cfg)
            self._render_full_thumb(left, fname)
        else:
            right = tk.Frame(body, bg=C_CARD)
            right.pack(fill="both", expand=True, padx=16, pady=8)

        self._render_detected_values(right, report, rd)
        self._render_edit_fields(right, report, rd)
        self._render_action_buttons(parent)

    # ------------------------------------------------------------------
    def _render_crops(self, parent, fname: str, crops_cfg: dict):
        """Show each named crop region with its label."""
        CROP_LABELS = {
            "subject":  "Subject Code Region",
            "booklet":  "Booklet Serial No Region",
            "barcode":  "Barcode Region",
            "reg_box":  "Handwritten Register No Region",
            "cand_sig": "Candidate Signature Region",
            "inv_sig":  "Invigilator Signature Region",
        }
        CROP_SIZE = {
            "subject":  (340, 90),
            "booklet":  (340, 110),
            "barcode":  (340, 80),
            "reg_box":  (340, 80),
            "cand_sig": (340, 110),
            "inv_sig":  (340, 110),
        }

        tk.Label(parent, text="Scanned Regions",
                 bg=C_CARD, fg=C_MUTED, font=("Segoe UI", 9, "bold"),
                 anchor="w").pack(fill="x", pady=(0, 4))

        for key, box in crops_cfg.items():
            section = tk.Frame(parent, bg="#0d1017",
                                highlightthickness=1, highlightbackground=C_BORDER)
            section.pack(fill="x", pady=4)

            tk.Label(section, text=CROP_LABELS.get(key, key),
                     bg="#0d1017", fg=C_MUTED,
                     font=("Segoe UI", 8, "bold"),
                     anchor="w", padx=6, pady=4
                     ).pack(fill="x")

            size   = CROP_SIZE.get(key, (340, 100))
            photo  = _pil_crop(fname, box, size)
            if photo:
                self._photo_refs.append(photo)
                img_lbl = tk.Label(section, image=photo, bg="#0d1017",
                                   relief="flat")
                img_lbl.pack(padx=4, pady=(0, 6))
            else:
                tk.Label(section,
                         text="Image not available",
                         bg="#0d1017", fg="#445566",
                         font=FONT_SMALL, pady=12
                         ).pack()

    # ------------------------------------------------------------------
    def _render_full_thumb(self, parent, fname: str):
        """Show a full-sheet thumbnail below the crops."""
        tk.Frame(parent, bg=C_BORDER, height=1).pack(fill="x", pady=(10, 6))
        tk.Label(parent, text="Full Sheet Thumbnail",
                 bg=C_CARD, fg=C_MUTED, font=("Segoe UI", 9, "bold"),
                 anchor="w").pack(fill="x", pady=(0, 4))

        thumb_frame = tk.Frame(parent, bg="#0d1017",
                               highlightthickness=1, highlightbackground=C_BORDER)
        thumb_frame.pack(fill="x", pady=2)

        photo = _pil_thumbnail(fname, (340, 440))
        if photo:
            self._photo_refs.append(photo)
            tk.Label(thumb_frame, image=photo, bg="#0d1017").pack(padx=4, pady=4)
        else:
            tk.Label(thumb_frame, text="Thumbnail unavailable",
                     bg="#0d1017", fg="#445566",
                     font=FONT_SMALL, pady=20).pack()

    # ------------------------------------------------------------------
    def _render_detected_values(self, parent, report: dict, rd: dict):
        """Show all column values as read-only detected data."""
        section = tk.LabelFrame(
            parent, text="  Detected Values  ",
            bg=C_CARD, fg=C_MUTED,
            font=("Segoe UI", 9, "bold"),
            bd=1, relief="groove",
            labelanchor="n"
        )
        section.pack(fill="x", pady=(0, 10))

        for db_col, display_name, _width in report["cols"]:
            val = rd.get(db_col, "")
            row = tk.Frame(section, bg=C_CARD)
            row.pack(fill="x", padx=10, pady=3)
            tk.Label(row, text=f"{display_name}:",
                     bg=C_CARD, fg=C_MUTED,
                     font=("Segoe UI", 9), width=22, anchor="w"
                     ).pack(side="left")

            # Highlight flags
            val_str = str(val) if val is not None else "—"
            fg = C_TEXT
            if db_col in ("IsResolved",) and val_str in ("1", "True"):
                fg = C_GREEN
            elif db_col in ("Whitener_Detected", "Is_Non_Standard") and val_str in ("1", "True"):
                fg = C_RED
            elif db_col in ("Candidate_Signed", "Invigilator_Signed",
                            "Signature_Present") and val_str in ("False", "0"):
                fg = C_RED
            elif db_col == "OMR_Threshold":
                try:
                    if float(val_str) < 0.35:
                        fg = C_RED
                except Exception:
                    pass

            tk.Label(row, text=val_str,
                     bg=C_CARD, fg=fg,
                     font=FONT_MONO, anchor="w"
                     ).pack(side="left", fill="x", expand=True)

    # ------------------------------------------------------------------
    def _render_edit_fields(self, parent, report: dict, rd: dict):
        """Editable fields — pre-filled with current (or edited) value."""
        section = tk.LabelFrame(
            parent, text="  Correct Values  ",
            bg=C_CARD, fg=C_ACCENT,
            font=("Segoe UI", 9, "bold"),
            bd=1, relief="groove",
            labelanchor="n"
        )
        section.pack(fill="x", pady=(0, 6))

        self._entries.clear()

        for db_col, display_name, _crop_key in report["edit_fields"]:
            # Use edited value if available, otherwise detected value
            edited_key = f"Edited_{db_col}"
            current_val = rd.get(edited_key) or rd.get(db_col, "")
            if current_val is None:
                current_val = ""

            row = tk.Frame(section, bg=C_CARD)
            row.pack(fill="x", padx=10, pady=5)

            tk.Label(row, text=f"{display_name}:",
                     bg=C_CARD, fg=C_TEXT,
                     font=("Segoe UI", 10, "bold"), width=26, anchor="w"
                     ).pack(side="left")

            entry = _styled_entry(row, width=28)
            entry.pack(side="left", fill="x", expand=True, ipady=4)
            entry.insert(0, str(current_val))
            self._entries[db_col] = entry

        # Instructions
        tk.Label(
            section,
            text="Edit the fields above, then click  Update Record  to save.",
            bg=C_CARD, fg=C_MUTED,
            font=("Segoe UI", 8), pady=4
        ).pack(fill="x", padx=10)

    # ------------------------------------------------------------------
    def _render_action_buttons(self, parent):
        bar = tk.Frame(parent, bg="#0d1017")
        bar.pack(fill="x", side="bottom", pady=0)
        tk.Frame(bar, bg=C_BORDER, height=1).pack(fill="x")

        btn_row = tk.Frame(bar, bg="#0d1017")
        btn_row.pack(fill="x", padx=16, pady=12)

        self._msg_lbl = tk.Label(
            btn_row, text="",
            bg="#0d1017", fg=C_GREEN,
            font=("Segoe UI", 9), anchor="w"
        )
        self._msg_lbl.pack(side="left", fill="x", expand=True)

        tk.Button(
            btn_row, text="Reset Fields",
            command=self._do_reset,
            bg="#2b313d", fg=C_TEXT,
            activebackground="#3a4050", activeforeground=C_TEXT,
            relief="flat", font=("Segoe UI", 10, "bold"),
            padx=14, pady=7, cursor="hand2"
        ).pack(side="right", padx=(6, 0))

        tk.Button(
            btn_row, text="  Update Record  ",
            command=self._do_save,
            bg=C_GREEN, fg="#ffffff",
            activebackground="#00e676", activeforeground="#ffffff",
            relief="flat", font=("Segoe UI", 10, "bold"),
            padx=14, pady=7, cursor="hand2"
        ).pack(side="right")

    # ------------------------------------------------------------------
    def _do_save(self):
        values = {k: e.get().strip() for k, e in self._entries.items()}
        self.on_save(self._report, self._row_data, values, self._msg_lbl)

    def _do_reset(self):
        self.on_reset(self._report, self._row_data, self._entries)

    def set_message(self, text: str, success: bool = True):
        if hasattr(self, "_msg_lbl"):
            self._msg_lbl.configure(
                text=text,
                fg=C_GREEN if success else C_RED
            )


# -----------------------------------------------------------------------------
# GRID PANEL — Treeview list of flagged records for the active report
# -----------------------------------------------------------------------------

class GridPanel(tk.Frame):
    """
    Top-right: filterable Treeview that lists all records for the chosen report.
    """

    def __init__(self, parent, on_row_select, **kw):
        super().__init__(parent, bg=C_BG, **kw)
        self.on_row_select = on_row_select
        self._col_names: list = []
        self._all_rows:  list = []
        self._row_map:   dict = {}   # iid -> row_values list
        self._build()

    # ------------------------------------------------------------------
    def _build(self):
        # -- Toolbar ---------------------------------------------------
        toolbar = tk.Frame(self, bg=C_BG)
        toolbar.pack(fill="x", padx=10, pady=(8, 4))

        tk.Label(toolbar, text="Filter:", bg=C_BG, fg=C_MUTED,
                 font=FONT_BODY).pack(side="left")
        self._filter_var = tk.StringVar()
        self._filter_var.trace_add("write", lambda *_: self._apply_filter())
        filter_entry = tk.Entry(
            toolbar, textvariable=self._filter_var, width=28,
            bg="#1e2330", fg=C_TEXT, insertbackground=C_TEXT,
            relief="flat", font=FONT_MONO,
            highlightthickness=1, highlightbackground=C_BORDER,
            highlightcolor=C_ACCENT
        )
        filter_entry.pack(side="left", padx=(4, 12), ipady=4)

        self._count_lbl = tk.Label(
            toolbar, text="0 records",
            bg=C_BG, fg=C_MUTED, font=FONT_SMALL
        )
        self._count_lbl.pack(side="left")

        tk.Button(
            toolbar, text="Refresh",
            bg="#24242f", fg=C_TEXT,
            activebackground="#32324a", activeforeground=C_TEXT,
            relief="flat", font=("Segoe UI", 9, "bold"),
            padx=10, pady=4, cursor="hand2",
            command=self._refresh_requested
        ).pack(side="right")

        self._refresh_cmd = None

        # -- Treeview --------------------------------------------------
        tree_frame = tk.Frame(self, bg=C_BG)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 4))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Disc.Treeview",
                        background="#181c24",
                        foreground=C_TEXT,
                        fieldbackground="#181c24",
                        rowheight=26,
                        bordercolor=C_BORDER,
                        font=("Segoe UI", 9))
        style.configure("Disc.Treeview.Heading",
                        background="#101018",
                        foreground="#a0c4ff",
                        font=("Segoe UI", 9, "bold"),
                        relief="flat")
        style.map("Disc.Treeview",
                  background=[("selected", "#1a3a6a")],
                  foreground=[("selected", "#ffffff")])
        style.map("Disc.Treeview.Heading",
                  background=[("active", "#1e2330")])

        self._tree = ttk.Treeview(
            tree_frame, style="Disc.Treeview",
            show="headings", selectmode="browse"
        )
        vsb = ttk.Scrollbar(tree_frame, orient="vertical",
                             command=self._tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal",
                             command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set,
                              xscrollcommand=hsb.set)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self._tree.pack(fill="both", expand=True)

        self._tree.bind("<<TreeviewSelect>>", self._on_select)
        self._tree.bind("<MouseWheel>",
                        lambda e: self._tree.yview_scroll(
                            int(-1*(e.delta/120)), "units"))

        # Row tags
        self._tree.tag_configure("resolved",
                                  background="#1b2e1b", foreground="#4caf50")
        self._tree.tag_configure("odd",  background="#181c24")
        self._tree.tag_configure("even", background="#141820")
        self._tree.tag_configure("flag", background="#2e1515", foreground="#ff8a80")

    # ------------------------------------------------------------------
    def set_refresh_command(self, cmd):
        self._refresh_cmd = cmd

    def _refresh_requested(self):
        if self._refresh_cmd:
            self._refresh_cmd()

    # ------------------------------------------------------------------
    def load(self, report: dict, col_names: list, rows: list):
        self._col_names = col_names
        self._all_rows  = [list(r) for r in rows]
        self._row_map   = {}
        self._filter_var.set("")

        # Configure columns
        self._tree.configure(columns=col_names)
        for db_col, display_name, width in report["cols"]:
            if db_col in col_names:
                self._tree.heading(db_col, text=display_name,
                                   anchor="w")
                self._tree.column(db_col, width=width, minwidth=40,
                                  stretch=False, anchor="w")

        self._populate(self._all_rows)

    # ------------------------------------------------------------------
    def _populate(self, rows: list):
        self._tree.delete(*self._tree.get_children())
        self._row_map.clear()

        for idx, row in enumerate(rows):
            rd  = dict(zip(self._col_names, row))
            iid = str(idx)

            resolved = str(rd.get("IsResolved", "0")) in ("1", "True")
            tag = "resolved" if resolved else ("even" if idx % 2 == 0 else "odd")

            # Flag rows with obvious problems in red
            if not resolved:
                for warn_key in ("Candidate_Signed", "Invigilator_Signed",
                                 "Signature_Present", "Whitener_Detected"):
                    if str(rd.get(warn_key, "")).strip() in ("False", "0"):
                        tag = "flag"
                        break

            values = [str(v) if v is not None else "" for v in row]
            self._tree.insert("", "end", iid=iid, values=values, tags=(tag,))
            self._row_map[iid] = row

        total = len(rows)
        self._count_lbl.configure(
            text=f"{total} record{'s' if total != 1 else ''}",
            fg=C_YELLOW if total > 0 else C_GREEN
        )

    # ------------------------------------------------------------------
    def _apply_filter(self):
        term = self._filter_var.get().lower().strip()
        if not term:
            self._populate(self._all_rows)
            return
        filtered = [
            row for row in self._all_rows
            if any(term in str(v).lower() for v in row)
        ]
        self._populate(filtered)

    # ------------------------------------------------------------------
    def _on_select(self, _event):
        sel = self._tree.selection()
        if not sel:
            return
        iid = sel[0]
        row = self._row_map.get(iid)
        if row is not None:
            self.on_row_select(self._col_names, row)

    # ------------------------------------------------------------------
    def clear(self):
        self._tree.configure(columns=[])
        self._tree.delete(*self._tree.get_children())
        self._count_lbl.configure(text="0 records")


# -----------------------------------------------------------------------------
# UPDATE DISPATCHER — translates edit-field values into the correct SP call
# -----------------------------------------------------------------------------

def _dispatch_update(report: dict, row_data: dict, values: dict,
                     user_id: int = LOGGED_USER_ID) -> str:
    """
    Call the correct update stored procedure for the given report.
    Returns a success message string.
    Raises on error.
    """
    rid  = int(row_data.get("ID", 0))
    proc = report["update_proc"]
    conn = _conn()
    cur  = conn.cursor()

    try:
        if report["id"] == 1:
            cur.execute(
                f"EXEC {proc} ?,?,?,?",
                rid,
                values.get("Subject_Code", ""),
                values.get("Booklet_Sl_No", ""),
                user_id
            )

        elif report["id"] == 2:
            cur.execute(
                f"EXEC {proc} ?,?,?",
                rid,
                values.get("Detected_Barcode", ""),
                user_id
            )

        elif report["id"] in (3, 4):
            cur.execute(
                f"EXEC {proc} ?,?,?,?,?",
                rid,
                values.get("Bubble_RegNo", ""),
                values.get("Handwritten_RegNo", ""),
                values.get("Final_RegNo", ""),
                user_id
            )

        elif report["id"] in (5, 6):
            cur.execute(
                f"EXEC {proc} ?,?,?",
                rid,
                values.get("Final_RegNo", ""),
                user_id
            )

        elif report["id"] in (7, 8):
            cur.execute(
                f"EXEC {proc} ?,?,?,?",
                rid,
                values.get("Candidate_Signed",   ""),
                values.get("Invigilator_Signed",  ""),
                user_id
            )

        elif report["id"] == 9:
            flag_val = values.get("Is_Non_Standard", "0")
            flag_bit = 1 if str(flag_val).strip() in ("1", "True", "true") else 0
            cur.execute(
                f"EXEC {proc} ?,?,?",
                rid,
                flag_bit,
                user_id
            )

        elif report["id"] in (10, 11):
            sheet_type = str(row_data.get("Sheet_Type", "Type1"))
            reg_no  = values.get("Registration_No", "")
            qcab    = values.get("OMR_No", "")      # re-used key in type2

            if report["id"] == 10:
                sig_raw = values.get("Signature_Present", "0")
                sig_bit = 1 if str(sig_raw).strip() in ("1", "True", "true") else 0
                invgl_bit = None
            else:
                sig_bit   = None
                invgl_raw = values.get("Invigilator_Signed", "0")
                invgl_bit = 1 if str(invgl_raw).strip() in ("1", "True", "true") else 0

            cur.execute(
                f"EXEC {proc} ?,?,?,?,?,?,?",
                rid,
                sheet_type,
                reg_no or None,
                qcab   or None,
                sig_bit,
                invgl_bit,
                user_id
            )

        conn.commit()
        return f"Record ID {rid} updated successfully."

    finally:
        conn.close()


# -----------------------------------------------------------------------------
# MAIN WINDOW CLASS
# -----------------------------------------------------------------------------

class DiscrepancyReports:
    """
    Full discrepancy review hub.
    Layout:
        +-------------+--------------------------------------------------+
        |             |  GRID (top ~40%)                                 |
        |  SIDEBAR    +--------------------------------------------------+
        |  (11 items) |  DETAIL PANEL (bottom ~60%)                      |
        +-------------+--------------------------------------------------+
    """

    def __init__(self, root: tk.Misc):
        self.root = root if isinstance(root, tk.Tk) else root
        self.root.title("Discrepancy Review & Correction")
        self.root.configure(bg=C_BG)

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w  = min(1720, max(1280, int(sw * 0.92)))
        h  = min(960,  max(700,  int(sh * 0.88)))
        self.root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        self.root.minsize(1100, 650)

        self._active_report: Optional[dict] = None
        self._col_names:     list           = []
        self._rows:          list           = []

        self._build_ui()
        self._load_all_counts()

        # Auto-select first report
        self.root.after(200, lambda: self._select_report(1))

    # ------------------------------------------------------------------
    # UI BUILD
    # ------------------------------------------------------------------

    def _build_ui(self):
        # -- Top header bar ---------------------------------------------
        header = tk.Frame(self.root, bg=C_HEADER_BG, pady=0)
        header.pack(fill="x")

        tk.Label(
            header,
            text="  KPSC OMR — Discrepancy Review & Correction",
            bg=C_HEADER_BG, fg="white",
            font=("Segoe UI", 15, "bold"),
            pady=12
        ).pack(side="left")

        # Status label (top-right)
        self._status_lbl = tk.Label(
            header, text="",
            bg=C_HEADER_BG, fg="#bbdefb",
            font=("Segoe UI", 9), padx=16
        )
        self._status_lbl.pack(side="right")

        tk.Button(
            header, text="Close",
            command=self.root.destroy,
            bg="#b71c1c", fg="white",
            activebackground="#d32f2f", activeforeground="white",
            relief="flat", font=("Segoe UI", 10, "bold"),
            padx=14, pady=8, cursor="hand2"
        ).pack(side="right", padx=(0, 8))

        # -- Body: sidebar + main ---------------------------------------
        body = tk.Frame(self.root, bg=C_BG)
        body.pack(fill="both", expand=True)

        # Sidebar (fixed 260 px)
        self._sidebar = ReportSidebar(
            body,
            on_select=self._select_report,
            width=260
        )
        self._sidebar.pack(side="left", fill="y")
        self._sidebar.pack_propagate(False)

        tk.Frame(body, bg=C_BORDER, width=1).pack(side="left", fill="y")

        # Main area
        main = tk.Frame(body, bg=C_BG)
        main.pack(side="left", fill="both", expand=True)

        # Paned window: grid top / detail bottom
        self._paned = tk.PanedWindow(
            main,
            orient=tk.VERTICAL,
            bg=C_BORDER,
            sashwidth=6,
            sashrelief="flat",
            handlesize=0
        )
        self._paned.pack(fill="both", expand=True)

        # Grid panel (top pane)
        self._grid_panel = GridPanel(
            self._paned,
            on_row_select=self._on_row_selected
        )
        self._grid_panel.set_refresh_command(self._refresh_current)
        self._paned.add(self._grid_panel, stretch="always", minsize=180)

        # Detail panel (bottom pane)
        self._detail_panel = DetailPanel(
            self._paned,
            on_save=self._on_save,
            on_reset=self._on_reset
        )
        self._paned.add(self._detail_panel, stretch="always", minsize=260)

        # Set initial sash position after layout
        self.root.after(100, self._set_sash)

    def _set_sash(self):
        try:
            h = self._paned.winfo_height()
            self._paned.sash_place(0, 0, max(180, int(h * 0.38)))
        except Exception:
            pass

    # ------------------------------------------------------------------
    # COUNT LOADING (background thread to avoid blocking startup)
    # ------------------------------------------------------------------

    def _load_all_counts(self):
        import threading

        def _worker():
            for rpt in REPORTS:
                count = _count_report(rpt["proc"])
                self.root.after(0, lambda r=rpt["id"], c=count:
                                self._sidebar.set_count(r, c))

        threading.Thread(target=_worker, daemon=True,
                         name="disc-count-loader").start()

    # ------------------------------------------------------------------
    # REPORT SELECTION
    # ------------------------------------------------------------------

    def _select_report(self, report_id: int):
        rpt = REPORT_BY_ID.get(report_id)
        if not rpt:
            return
        self._active_report = rpt
        self._sidebar.select(report_id)
        self._grid_panel.clear()
        self._detail_panel.clear()
        self._detail_panel._build_empty()
        self._set_status(f"Loading {rpt['name']}…", colour="#ffeb3b")
        self.root.after(20, lambda: self._load_report(rpt))

    def _load_report(self, rpt: dict):
        try:
            col_names, rows = _fetch(rpt["proc"])
            self._col_names = col_names
            self._rows      = [list(r) for r in rows]
            self._grid_panel.load(rpt, col_names, self._rows)
            count = len(self._rows)
            self._sidebar.set_count(rpt["id"], count)
            msg = (f"{count} open item{'s' if count != 1 else ''}"
                   if count > 0 else "No open discrepancies")
            self._set_status(msg, colour=C_YELLOW if count > 0 else C_GREEN)
        except Exception as exc:
            self._set_status(f"Error: {exc}", colour=C_RED)
            messagebox.showerror("Load Error", str(exc), parent=self.root)

    def _refresh_current(self):
        if self._active_report:
            self._select_report(self._active_report["id"])

    # ------------------------------------------------------------------
    # ROW SELECTION → populate detail panel
    # ------------------------------------------------------------------

    def _on_row_selected(self, col_names: list, row_values: list):
        if not self._active_report:
            return
        self._detail_panel.load(self._active_report, col_names, row_values)

    # ------------------------------------------------------------------
    # SAVE
    # ------------------------------------------------------------------

    def _on_save(self, report: dict, row_data: dict,
                 values: dict, msg_lbl: tk.Label):
        try:
            msg = _dispatch_update(report, row_data, values, LOGGED_USER_ID)
            msg_lbl.configure(text=f"[OK]  {msg}", fg=C_GREEN)
            self._set_status(msg, colour=C_GREEN)
            # Refresh grid + counts after a short delay
            self.root.after(600, self._refresh_current)
            self.root.after(700, self._load_all_counts)
        except Exception as exc:
            msg_lbl.configure(text=f"[X]  {exc}", fg=C_RED)
            self._set_status(f"Update failed: {exc}", colour=C_RED)
            self._log_error(report["name"], str(exc))

    # ------------------------------------------------------------------
    # RESET — restore entry fields to original detected values
    # ------------------------------------------------------------------

    def _on_reset(self, report: dict, row_data: dict, entries: dict):
        for db_col, _label, _crop_key in report["edit_fields"]:
            entry = entries.get(db_col)
            if entry is None:
                continue
            edited_key  = f"Edited_{db_col}"
            restore_val = row_data.get(edited_key) or row_data.get(db_col, "")
            if restore_val is None:
                restore_val = ""
            entry.delete(0, "end")
            entry.insert(0, str(restore_val))

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    def _set_status(self, text: str, colour: str = C_MUTED):
        if self.root.winfo_exists():
            self._status_lbl.configure(text=text, fg=colour)

    def _log_error(self, screen: str, msg: str):
        try:
            conn = _conn()
            cur  = conn.cursor()
            cur.execute(
                "INSERT INTO dbo.ErrorLog(ErrorScreen,ErrorModule,ErrorText,ErrorTime) "
                "VALUES (?,?,?,GETDATE())",
                "DiscrepancyReports", screen, msg
            )
            conn.commit()
            conn.close()
        except Exception:
            pass


# -----------------------------------------------------------------------------
# STANDALONE ENTRY POINT
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    root = tk.Tk()
    try:
        ttk.Style().theme_use("clam")
    except tk.TclError:
        pass
    app = DiscrepancyReports(root)
    root.mainloop()
