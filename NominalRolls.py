import os
import glob
import sys
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
import numpy as np
from PIL import Image, ImageTk
import easyocr
import audit

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from core.nominal_roll_type1 import process_attendance_sheet1
from core.nominal_roll_type2 import process_attendance_sheet2
from core.nominal_roll import get_invigilator_signature_box as invigilator_box_coords

# Initialize EasyOCR Reader globally once
_READER = None
def get_ocr_reader():
    global _READER
    if _READER is None:
        _READER = easyocr.Reader(['en'], gpu=False)
    return _READER

class AttendanceViewerDemo:
    def __init__(self, root):
        self.root = root
        self.root.title("Attendance Sheet Extraction Demo")

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        win_w = int(sw * 0.92)
        win_h = int(sh * 0.90)
        self.root.geometry(f"{win_w}x{win_h}+{(sw-win_w)//2}+{(sh-win_h)//2}")
        self.root.minsize(
            max(1024, int(sw * 0.65)),
            max(620, int(sh * 0.62)))
        self.root.configure(bg="#1c1c22") # Sleek premium dark background
        
        # Configure Styles
        self.style = ttk.Style()
        self.style.theme_use("clam")
        
        # Dark theme configuration
        self.style.configure(".", background="#1c1c22", foreground="#ffffff", fieldbackground="#2b2b36")
        self.style.configure("TLabel", background="#1c1c22", foreground="#ffffff", font=("Segoe UI", 10))
        self.style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground="#00e676", background="#1c1c22")
        self.style.configure("TButton", font=("Segoe UI", 10, "bold"), background="#00c853", foreground="#ffffff", borderwidth=0, focuscolor="none")
        self.style.map("TButton", background=[("active", "#00e676")])
        self.style.configure("TCombobox", background="#2b2b36", foreground="#ffffff", fieldbackground="#2b2b36")
        self.style.map("TCombobox", fieldbackground=[("readonly", "#2b2b36")], foreground=[("readonly", "#ffffff")])
        
        # Style Entry fields for clear contrast
        self.style.configure("TEntry", fieldbackground="#2b2b36", foreground="#ffffff", insertcolor="#ffffff")
        self.style.map("TEntry", fieldbackground=[("readonly", "#1c1c22")], foreground=[("readonly", "#888888")])
        self.style.configure("Thin.Horizontal.TProgressbar", troughcolor="#2b2b36", background="#00c853", thickness=8)
        
        # Treeview Styles
        self.style.configure("Treeview", background="#2b2b36", foreground="#ffffff", fieldbackground="#2b2b36", rowheight=25)
        self.style.map("Treeview", background=[("selected", "#00c853")], foreground=[("selected", "#ffffff")])
        self.style.configure("Treeview.Heading", background="#1c1c22", foreground="#00e676", font=("Segoe UI", 10, "bold"))
        
        # Configure Dropdown Listbox popup style globally
        self.root.option_add("*TCombobox*Listbox.background", "#2b2b36")
        self.root.option_add("*TCombobox*Listbox.foreground", "#ffffff")
        self.root.option_add("*TCombobox*Listbox.selectBackground", "#00c853")
        self.root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
        self.root.option_add("*TCombobox*Listbox.font", ("Segoe UI", 10))

        
        self.sheet1_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Attendance Sheet1")
        self.sheet2_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Attendance Sheet2")
        
        self.current_records = []
        self.current_img = None
        self.current_invigilator_signed = 0
        self.attendance_csv_records = {} # filename -> list of records
        self.current_dir = None
        
        self.build_ui()

    def build_ui(self):
        # Header row
        header = tk.Frame(self.root, bg="#2b2b36", height=46, bd=0)
        header.pack(fill="x", side="top", padx=0, pady=0)
        header.pack_propagate(False)

        tk.Label(header,
                 text="Nominal Roll Extraction Engine",
                 bg="#2b2b36", fg="#00e676",
                 font=("Segoe UI", 18, "bold"),
                 anchor="center").pack(fill="both", expand=True)

        tk.Frame(self.root, bg="#00c853", height=2).pack(fill="x", side="top")

        # 1. Top Panel (Control Panel)
        top_frame = tk.Frame(self.root, bg="#2b2b36", height=70, bd=0)
        top_frame.pack(fill="x", side="top", padx=0, pady=0)
        top_frame.pack_propagate(False)
        
        # 1.5 Header Info Panel
        self.header_frame = tk.Frame(self.root, bg="#2b2b36", height=45, bd=0)
        self.header_frame.pack(fill="x", side="top", padx=0, pady=(1, 0))
        self.header_frame.pack_propagate(False)
        
        lbl_center = ttk.Label(self.header_frame, text="Center Code:", font=("Segoe UI", 10, "bold"), background="#2b2b36")
        lbl_center.pack(side="left", padx=(20, 5))
        self.center_entry = ttk.Entry(self.header_frame, width=10, font=("Segoe UI", 10))
        self.center_entry.pack(side="left", padx=5)
        self.center_entry.bind("<KeyRelease>", lambda e: self.on_header_changed())
        
        lbl_subcenter = ttk.Label(self.header_frame, text="Sub Center Code:", font=("Segoe UI", 10, "bold"), background="#2b2b36")
        lbl_subcenter.pack(side="left", padx=(20, 5))
        self.subcenter_entry = ttk.Entry(self.header_frame, width=10, font=("Segoe UI", 10))
        self.subcenter_entry.pack(side="left", padx=5)
        self.subcenter_entry.bind("<KeyRelease>", lambda e: self.on_header_changed())
        
        lbl_subject = ttk.Label(self.header_frame, text="Subject Code:", font=("Segoe UI", 10, "bold"), background="#2b2b36")
        lbl_subject.pack(side="left", padx=(20, 5))
        self.subject_entry = ttk.Entry(self.header_frame, width=10, font=("Segoe UI", 10))
        self.subject_entry.pack(side="left", padx=5)
        self.subject_entry.bind("<KeyRelease>", lambda e: self.on_header_changed())

        self.status_lbl = ttk.Label(self.header_frame, text="Ready", font=("Segoe UI", 10, "italic"), background="#2b2b36", foreground="#ffeb3b")
        self.status_lbl.pack(side="left", padx=(24, 8))

        self.progress = ttk.Progressbar(
            self.header_frame, orient="horizontal", length=180,
            mode="determinate", style="Thin.Horizontal.TProgressbar")
        self.progress.pack(side="left", padx=4)

        self.invigilator_sig_lbl = ttk.Label(
            self.header_frame, text="Invigilator Signed: -",
            font=("Segoe UI", 10, "bold"), background="#2b2b36",
            foreground="#00e676")
        self.invigilator_sig_lbl.pack(side="left", padx=(18, 5))
        
        lbl_type = ttk.Label(top_frame, text="Sheet Type:", font=("Segoe UI", 11, "bold"), background="#2b2b36")
        lbl_type.pack(side="left", padx=(20, 5))
        
        self.type_combo = ttk.Combobox(top_frame, values=["Attendance Sheet 1 (OMR)", "Attendance Sheet 2 (QCAB)"], state="readonly", width=25, font=("Segoe UI", 10))
        self.type_combo.current(0)
        self.type_combo.pack(side="left", padx=10)
        self.type_combo.bind("<<ComboboxSelected>>", lambda e: self.on_sheet_type_changed())
        
        # lbl_file = ttk.Label(top_frame, text="Select Image:", font=("Segoe UI", 11, "bold"), background="#2b2b36")
        # lbl_file.pack(side="left", padx=(20, 5))
        
        browse_btn = ttk.Button(top_frame, text="Select Folder...", command=self.browse_folder, style="TButton")
        browse_btn.pack(side="left", padx=5)
        
        self.prev_btn = ttk.Button(top_frame, text="<- Prev", command=lambda: self.navigate_sheet(-1), style="TButton", width=8, state="disabled")
        self.prev_btn.pack(side="left", padx=2)
        
        self.file_combo = ttk.Combobox(top_frame, state="readonly", width=60, font=("Segoe UI", 10))
        self.file_combo.pack(side="left", padx=5)
        self.file_combo.bind("<<ComboboxSelected>>", lambda e: self.process_selected_sheet())
        
        self.next_btn = ttk.Button(top_frame, text="Next ->", command=lambda: self.navigate_sheet(1), style="TButton", width=8, state="disabled")
        self.next_btn.pack(side="left", padx=2)
        
        # Run Processing button removed as Next/Prev and selection handles processing automatically
        
        self.export_btn = ttk.Button(top_frame, text="Export to Excel", command=self.export_results_to_excel, style="TButton", width=16, state="disabled")
        self.export_btn.pack(side="right", padx=(5, 10))

        self.process_all_btn = ttk.Button(
            top_frame, text="Process All",
            command=self.process_all_sheets_to_mssql,
            style="TButton", width=12)
        self.process_all_btn.pack(side="right", padx=5)
        
        # 2. Main content split pane
        content_frame = tk.Frame(self.root, bg="#1c1c22")
        content_frame.pack(fill="both", expand=True, padx=15, pady=15)

        # Left column: annotated viewer (top) + process status grid (bottom)
        left_column = tk.Frame(content_frame, bg="#1c1c22", width=650)
        left_column.pack(fill="both", side="left", padx=(0, 10))
        left_column.pack_propagate(False)

        self.left_frame = tk.LabelFrame(
            left_column, text="Annotated Sheet Viewer",
            bg="#2b2b36", fg="#00e676",
            font=("Segoe UI", 10, "bold"), bd=1)
        self.left_frame.pack(fill="both", expand=True, padx=0, pady=(0, 8))

        self.image_canvas = tk.Canvas(self.left_frame, bg="#2b2b36", highlightthickness=0)
        self.image_scroll_y = ttk.Scrollbar(self.left_frame, orient="vertical", command=self.image_canvas.yview)
        self.image_scroll_x = ttk.Scrollbar(self.left_frame, orient="horizontal", command=self.image_canvas.xview)
        self.image_canvas.configure(
            yscrollcommand=self.image_scroll_y.set,
            xscrollcommand=self.image_scroll_x.set)
        self.image_scroll_y.pack(side="right", fill="y")
        self.image_scroll_x.pack(side="bottom", fill="x")
        self.image_canvas.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        self.image_canvas.bind("<MouseWheel>", self.on_annotated_image_mousewheel)

        self.build_status_panel(left_column)
        self._status_iids = {}
        self._status_state = {}
        
        # Right Panel: Table and crops
        right_frame = tk.Frame(content_frame, bg="#1c1c22")
        right_frame.pack(fill="both", side="right", expand=True, padx=(10, 0))
        
        # Table Frame
        table_frame = tk.LabelFrame(right_frame, text="Extracted Nominal Roll Table", bg="#2b2b36", fg="#00e676", font=("Segoe UI", 10, "bold"), bd=1)
        table_frame.pack(fill="x", expand=False, pady=(0, 10))
        
        # Scrollbars for Treeview
        tree_scroll_y = ttk.Scrollbar(table_frame, orient="vertical")
        tree_scroll_y.pack(side="right", fill="y")
        
        self.tree = ttk.Treeview(table_frame, columns=("row", "status", "sig", "inv_sig", "reg_no", "omr_no"), show="headings", yscrollcommand=tree_scroll_y.set, height=6)
        tree_scroll_y.config(command=self.tree.yview)
        
        self.tree.heading("row", text="Row")
        self.tree.heading("status", text="Status")
        self.tree.heading("sig", text="Std. Signature")
        self.tree.heading("inv_sig", text="Inv. Signature")
        self.tree.heading("reg_no", text="Registration No")
        self.tree.heading("omr_no", text="OMR No")
        
        self.tree.column("row", width=60, anchor="center")
        self.tree.column("status", width=120, anchor="center")
        self.tree.column("sig", width=120, anchor="center")
        self.tree.column("inv_sig", width=120, anchor="center")
        self.tree.column("reg_no", width=120, anchor="center")
        self.tree.column("omr_no", width=120, anchor="center")
        self.tree.pack(fill="x", expand=False, padx=5, pady=5)
        self.tree.bind("<<TreeviewSelect>>", self.on_row_selected)
        
        # Details / Crop Frame at Bottom Right
        details_frame = tk.LabelFrame(right_frame, text="Selected Row Visual Verification Snippets", bg="#2b2b36", fg="#00e676", font=("Segoe UI", 10, "bold"), bd=1, height=210)
        details_frame.pack(fill="x", expand=False)
        details_frame.pack_propagate(False)
        
        self.signature_preview_frame = tk.Frame(details_frame, bg="#2b2b36")
        self.signature_preview_frame.pack(side="left", fill="both", expand=True, padx=10, pady=5)

        self.sig_preview_wrapper = tk.LabelFrame(self.signature_preview_frame, text="Candidate Signature Crop", bg="#2b2b36", fg="#ffffff", font=("Segoe UI", 8))
        self.sig_preview_wrapper.pack(side="top", fill="both", expand=True, pady=(0, 3))
        self.sig_preview_lbl = tk.Label(self.sig_preview_wrapper, bg="#2b2b36")
        self.sig_preview_lbl.pack(fill="both", expand=True)

        self.inv_sig_preview_wrapper = tk.LabelFrame(self.signature_preview_frame, text="Invigilator Signature Crop", bg="#2b2b36", fg="#ffffff", font=("Segoe UI", 8))
        self.inv_sig_preview_wrapper.pack(side="top", fill="both", expand=True, pady=(3, 0))
        self.inv_sig_preview_lbl = tk.Label(self.inv_sig_preview_wrapper, bg="#2b2b36")
        self.inv_sig_preview_lbl.pack(fill="both", expand=True)
        
        self.reg_preview_wrapper = tk.LabelFrame(details_frame, text="Registration No Crop", bg="#2b2b36", fg="#ffffff", font=("Segoe UI", 8))
        self.reg_preview_wrapper.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        self.reg_preview_lbl = tk.Label(self.reg_preview_wrapper, bg="#2b2b36")
        self.reg_preview_lbl.pack(fill="both", expand=True)

        self.omr_preview_wrapper = tk.LabelFrame(details_frame, text="OMR No Crop", bg="#2b2b36", fg="#ffffff", font=("Segoe UI", 8))
        self.omr_preview_wrapper.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        self.omr_preview_lbl = tk.Label(self.omr_preview_wrapper, bg="#2b2b36")
        self.omr_preview_lbl.pack(fill="both", expand=True)

        # Correction Form Frame
        correction_frame = tk.LabelFrame(right_frame, text="Candidate Row Form", bg="#2b2b36", fg="#00e676", font=("Segoe UI", 10, "bold"), bd=1, height=90)
        correction_frame.pack(fill="x", pady=(10, 0))
        correction_frame.pack_propagate(False)

        # Grid layout for read-only row details
        for col_idx in range(10):
            correction_frame.columnconfigure(col_idx, weight=1)

        lbl_reg = ttk.Label(correction_frame, text="Reg No:", background="#2b2b36", font=("Segoe UI", 9, "bold"))
        lbl_reg.grid(row=0, column=0, sticky="w", padx=5, pady=15)
        self.edit_reg = ttk.Entry(correction_frame, font=("Segoe UI", 9), width=12)
        self.edit_reg.config(state="readonly")
        self.edit_reg.grid(row=0, column=1, sticky="ew", padx=5, pady=15)

        self.number_field_lbl = ttk.Label(correction_frame, text="OMR No:", background="#2b2b36", font=("Segoe UI", 9, "bold"))
        self.number_field_lbl.grid(row=0, column=2, sticky="w", padx=5, pady=15)
        self.edit_omr = ttk.Entry(correction_frame, font=("Segoe UI", 9), width=12)
        self.edit_omr.config(state="readonly")
        self.edit_omr.grid(row=0, column=3, sticky="ew", padx=5, pady=15)

        lbl_sig = ttk.Label(correction_frame, text="Std. Sign:", background="#2b2b36", font=("Segoe UI", 9, "bold"))
        lbl_sig.grid(row=0, column=4, sticky="w", padx=5, pady=15)
        self.edit_sig = ttk.Entry(correction_frame, font=("Segoe UI", 9), width=8, state="readonly")
        self.edit_sig.grid(row=0, column=5, sticky="w", padx=5, pady=15)

        lbl_inv_sig = ttk.Label(correction_frame, text="Inv. Sign:", background="#2b2b36", font=("Segoe UI", 9, "bold"))
        lbl_inv_sig.grid(row=0, column=6, sticky="w", padx=5, pady=15)
        self.edit_inv_sig = ttk.Entry(correction_frame, font=("Segoe UI", 9), width=8, state="readonly")
        self.edit_inv_sig.grid(row=0, column=7, sticky="w", padx=5, pady=15)

        lbl_status = ttk.Label(correction_frame, text="Status:", background="#2b2b36", font=("Segoe UI", 9, "bold"))
        lbl_status.grid(row=0, column=8, sticky="w", padx=5, pady=15)
        self.edit_status = ttk.Entry(correction_frame, font=("Segoe UI", 9), width=14, state="readonly")
        self.edit_status.grid(row=0, column=9, sticky="ew", padx=5, pady=15)

    def build_status_panel(self, parent):
        status_outer = tk.LabelFrame(
            parent, text="Sheet Process Status",
            bg="#2b2b36", fg="#00e676",
            font=("Segoe UI", 10, "bold"), bd=1, height=210)
        status_outer.pack(fill="x", side="bottom", padx=0, pady=0)
        status_outer.pack_propagate(False)

        status_hdr = tk.Frame(status_outer, bg="#2b2b36")
        status_hdr.pack(fill="x", padx=8, pady=(4, 2))

        tk.Label(
            status_hdr, text="Summary:",
            bg="#2b2b36", fg="#ffffff",
            font=("Segoe UI", 9, "bold"),
            anchor="w").pack(side="left")

        self.status_summary_lbl = tk.Label(
            status_hdr, text="",
            bg="#2b2b36", fg="#888899",
            font=("Segoe UI", 9),
            anchor="w")
        self.status_summary_lbl.pack(side="left", padx=(6, 0))

        grid_frame = tk.Frame(status_outer, bg="#2b2b36")
        grid_frame.pack(fill="both", expand=True, padx=8, pady=(0, 6))

        cols = ("img", "extracted", "saved_db")
        self.status_tree = ttk.Treeview(
            grid_frame, columns=cols, show="headings",
            height=6, selectmode="browse")

        self.status_tree.heading("img", text="Image")
        self.status_tree.heading("extracted", text="Extracted")
        self.status_tree.heading("saved_db", text="Saved to DB")
        self.status_tree.column("img", width=220, anchor="w", stretch=True)
        self.status_tree.column("extracted", width=95, anchor="center", stretch=True)
        self.status_tree.column("saved_db", width=95, anchor="center", stretch=True)

        self.status_tree.tag_configure("ok", background="#1b5e20", foreground="#a5d6a7")
        self.status_tree.tag_configure("warning", background="#4e2600", foreground="#ffcc80")
        self.status_tree.tag_configure("error", background="#4e0000", foreground="#ef9a9a")
        self.status_tree.tag_configure("imported", background="#0d2f5e", foreground="#90caf9")
        self.status_tree.tag_configure("pending", background="#2a2a3a", foreground="#888899")

        status_scroll = ttk.Scrollbar(grid_frame, orient="vertical", command=self.status_tree.yview)
        self.status_tree.configure(yscrollcommand=status_scroll.set)
        status_scroll.pack(side="right", fill="y")
        self.status_tree.pack(side="left", fill="both", expand=True)

    def _status_icon(self, status):
        return {"ok": "✔", "warning": "⚠", "error": "✘",
                "imported": "✔", "pending": "—"}.get(status, "—")

    def _ensure_status_row(self, filename):
        if not hasattr(self, "status_tree"):
            return
        if filename not in self._status_iids:
            iid = self.status_tree.insert(
                "", "end",
                values=(filename, "—", "—"),
                tags=("pending",))
            self._status_iids[filename] = iid

    def _extracted_status_from_attendance_data(self, data):
        if not data:
            return "error"
        if not data.get("center_code", "").strip():
            return "warning"
        if not data.get("subcenter_code", "").strip():
            return "warning"
        if not data.get("subject_code", "").strip():
            return "warning"
        records = data.get("records", [])
        if not records:
            return "warning"
        is_type1 = getattr(self, "is_type1", True)
        for record in records:
            reg_val = str(record.get("registration_no", "")).strip()
            omr_val = str(record.get("omr_no", "")).strip()
            if is_type1:
                if not reg_val or len(reg_val) < 6 or not omr_val or len(omr_val) < 6:
                    return "warning"
            else:
                qcab_val = str(record.get("qcab_serial_no", "")).strip()
                if not reg_val or len(reg_val) < 6 or (qcab_val and len(qcab_val) < 6):
                    return "warning"
            if record.get("status") in ("Double Marked", "Not Marked"):
                return "warning"
        return "ok"

    def set_sheet_status(self, filename, extracted=None, saved_db=None):
        if not hasattr(self, "status_tree"):
            return
        self._ensure_status_row(filename)
        iid = self._status_iids[filename]

        if filename not in self._status_state:
            self._status_state[filename] = {}
        if extracted:
            self._status_state[filename]["extracted"] = extracted
        if saved_db:
            self._status_state[filename]["saved_db"] = saved_db

        cur = self.status_tree.item(iid, "values")
        new_ext = (self._status_icon(extracted) + "  " + extracted.upper()
                   if extracted else cur[1])
        new_db = (self._status_icon(saved_db) + "  " + saved_db.upper()
                  if saved_db else cur[2])

        rank = {"error": 3, "warning": 2, "imported": 1, "ok": 1, "pending": 0}
        tag = max([extracted or "pending", saved_db or "pending"],
                  key=lambda s: rank.get(s, 0))
        if (saved_db or "pending") == "imported":
            tag = "imported"

        self.status_tree.item(iid, values=(filename, new_ext, new_db), tags=(tag,))
        self.status_tree.see(iid)
        self._refresh_status_summary()

    def _refresh_status_summary(self):
        if not hasattr(self, "status_summary_lbl"):
            return
        extracted = imported = errors = 0
        for state in self._status_state.values():
            ext = state.get("extracted")
            db = state.get("saved_db")
            if ext in ("ok", "warning"):
                extracted += 1
            if db == "imported":
                imported += 1
            if ext == "error" or db == "error":
                errors += 1
        if extracted or imported or errors:
            self.status_summary_lbl.config(
                text=(f"Extracted: {extracted}, "
                      f"Imported to DB: {imported}, "
                      f"Error Sheets: {errors}"))
        else:
            self.status_summary_lbl.config(text="")

    def _init_status_grid(self):
        if not hasattr(self, "status_tree"):
            return
        for iid in self.status_tree.get_children():
            self.status_tree.delete(iid)
        self._status_iids = {}
        self._status_state = {}
        for fp in self.file_combo["values"]:
            self._ensure_status_row(os.path.basename(fp))
        self._refresh_status_summary()

    def on_annotated_image_mousewheel(self, event):
        if event.state & 0x0001:
            self.image_canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")
        else:
            self.image_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def get_invigilator_signature_box(self, w, h, is_type1=None):
        if is_type1 is None:
            is_type1 = getattr(self, "is_type1", True)
        sheet_type = 1 if is_type1 else 2
        return invigilator_box_coords(sheet_type, w, h)

    def set_readonly_entry(self, entry, value):
        entry.config(state="normal")
        entry.delete(0, tk.END)
        entry.insert(0, value)
        entry.config(state="readonly")

    def normalize_image_path(self, path_value):
        if not path_value:
            return ""
        if os.path.isabs(path_value):
            return os.path.abspath(path_value)
        if self.current_dir:
            return os.path.abspath(os.path.join(self.current_dir, path_value))
        return os.path.abspath(path_value)

    def on_sheet_type_changed(self):
        is_type1 = "Sheet 1" in self.type_combo.get()
        number_title = "OMR No" if is_type1 else "QCAB Serial No"
        self.tree.heading("omr_no", text=number_title)
        self.omr_preview_wrapper.config(text=f"{number_title} Crop")
        self.number_field_lbl.config(text=f"{number_title}:")
        self.current_dir = None
        self.current_records = []
        self.current_img = None
        self.current_invigilator_signed = 0
        self.attendance_csv_records = {}
        self.file_combo["values"] = []
        self.file_combo.set("")
        self.image_canvas.delete("all")
        self.image_canvas.configure(scrollregion=(0, 0, 0, 0))
        self.sig_preview_lbl.config(image="")
        self.inv_sig_preview_lbl.config(image="")
        self.reg_preview_lbl.config(image="")
        self.omr_preview_lbl.config(image="")
        for item in self.tree.get_children():
            self.tree.delete(item)
        if hasattr(self, "export_btn"):
            self.export_btn.config(state="disabled")
        if hasattr(self, "progress"):
            self.progress["value"] = 0
        self.invigilator_sig_lbl.config(text="Invigilator Signed: -")
        self.prev_btn.config(state="disabled")
        self.next_btn.config(state="disabled")
        self.status_lbl.config(text="Select a folder to begin", foreground="#ffeb3b")
        if hasattr(self, "status_tree"):
            for iid in self.status_tree.get_children():
                self.status_tree.delete(iid)
            self._status_iids = {}
            self._status_state = {}
            self._refresh_status_summary()

    def process_selected_sheet(self, force_reprocess=False):
        img_path = self.normalize_image_path(self.file_combo.get())
        if not img_path:
            messagebox.showwarning("Warning", "No image selected!")
            return
        if not self.current_dir:
            messagebox.showwarning("Warning", "Please select a folder first!")
            return

        fname = img_path
        display_name = os.path.basename(img_path)
        self.status_lbl.config(text="Processing... Please wait", foreground="#ffeb3b")
        self.set_sheet_status(display_name, extracted="pending")
        self.root.update_idletasks()
        
        try:
            reader = get_ocr_reader()
            img = cv2.imread(img_path)
            self.current_img = img.copy()
            h, w = img.shape[:2]
            
            choice = self.type_combo.get()
            is_type1 = "Sheet 1" in choice
            
            # Setup visualization columns
            if is_type1:
                expected_border = 87
                from core.nominal_roll_type1 import detect_left_border
                detected_border = detect_left_border(img, expected_border)
                shift = detected_border - expected_border if abs(detected_border - expected_border) <= 55 else 0
                
                y_centers = [580, 815, 1049, 1283, 1521, 1754]
                px_offset, ax_offset = 423, 473
                sig_x0, sig_x1 = 330, 810
                reg_x0, reg_x1 = 830, 1030
                omr_x0, omr_x1 = 1090, 1250
            else:
                expected_border = 133
                from core.nominal_roll_type2 import detect_left_border as detect_left_border2
                detected_border = detect_left_border2(img, expected_border)
                shift = detected_border - expected_border if abs(detected_border - expected_border) <= 55 else 0
                
                y_centers = [580, 815, 1049, 1283, 1521, 1754]
                px_offset, ax_offset = 469, 524
                sig_x0, sig_x1 = 380, 850
                reg_x0, reg_x1 = 760, 950
                qcab_x0, qcab_x1 = 1180, 1490
                
            # Load from CSV database or process
            needs_reprocess = False
            if fname in self.attendance_csv_records and not force_reprocess:
                data = self.attendance_csv_records[fname]
                center_code = data.get("center_code", "")
                subcenter_code = data.get("subcenter_code", "")
                subject_code = data.get("subject_code", "")
                invigilator_signed = data.get("invigilator_signed", "")
                records = data.get("records", [])
                
                # Auto-reprocess if loaded CSV data is missing header codes or records
                if (not center_code or not subcenter_code or not subject_code
                        or not records or invigilator_signed == ""):
                    needs_reprocess = True
                else:
                    # Also reprocess if OMR/Reg numbers are missing or incomplete (less than 6 digits)
                    for r in records:
                        reg_val = str(r.get("registration_no", "")).strip()
                        omr_val = str(r.get("omr_no", "")).strip()
                        if is_type1:
                            if not reg_val or len(reg_val) < 6 or not omr_val or len(omr_val) < 6:
                                needs_reprocess = True
                                break
                        else:
                            qcab_val = str(r.get("qcab_serial_no", "")).strip()
                            if (not data.get("has_qcab_column", True)
                                    or not reg_val or len(reg_val) < 6
                                    or (qcab_val and len(qcab_val) < 6)):
                                needs_reprocess = True
                                break
            else:
                needs_reprocess = True

            if needs_reprocess or force_reprocess:
                self.status_lbl.config(text="Processing image (OCR)... Please wait", foreground="#ffeb3b")
                self.root.update_idletasks()
                
                if is_type1:
                    records, header = process_attendance_sheet1(img_path, reader)
                else:
                    records, header = process_attendance_sheet2(img_path, reader)
                    
                center_code = header.get("center_code", "")
                subcenter_code = header.get("subcenter_code", "")
                subject_code = header.get("subject_code", "")
                invigilator_signed = int(header.get("invigilator_signed", 0))
                
                self.attendance_csv_records[fname] = {
                    "center_code": center_code,
                    "subcenter_code": subcenter_code,
                    "subject_code": subject_code,
                    "invigilator_signed": invigilator_signed,
                    "has_qcab_column": True,
                    "records": records
                }
                
            self.current_records = records
            self.current_invigilator_signed = int(invigilator_signed or 0)
            self.current_y_centers = y_centers
            self.current_shift = shift
            self.is_type1 = is_type1
            
            # Populate header entries in GUI
            self.center_entry.delete(0, tk.END)
            self.center_entry.insert(0, center_code)
            self.subcenter_entry.delete(0, tk.END)
            self.subcenter_entry.insert(0, subcenter_code)
            self.subject_entry.delete(0, tk.END)
            self.subject_entry.insert(0, subject_code)
            self.invigilator_sig_lbl.config(
                text=f"Invigilator Signed: {self.current_invigilator_signed}")
            
            # Update navigation button states
            current_idx = self.file_combo.current()
            total_files = len(self.file_combo["values"])
            
            if current_idx <= 0:
                self.prev_btn.config(state="disabled")
            else:
                self.prev_btn.config(state="normal")
                
            if current_idx >= total_files - 1:
                self.next_btn.config(state="disabled")
            else:
                self.next_btn.config(state="normal")
            
            # Draw annotation on full image
            annotated = img.copy()
            
            # Draw leftmost border line
            cv2.line(annotated, (expected_border + shift, 0), (expected_border + shift, h), (0, 0, 255), 2)
            
            for idx, yc in enumerate(y_centers):
                # Row indicator
                cv2.putText(annotated, f"Row {idx+1}", (10, yc), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 230, 255), 2)
                
                # Present bubble (green)
                px = px_offset + shift
                cv2.circle(annotated, (px, yc), 12, (0, 255, 0), 2)
                
                # Absent bubble (red)
                ax = ax_offset + shift
                cv2.circle(annotated, (ax, yc), 12, (0, 255, 255), 2)
                
                # Signature box (magenta)
                if is_type1:
                    cv2.rectangle(annotated, (sig_x0 + shift, yc + 25), (sig_x1 + shift, yc + 105), (255, 0, 255), 2)
                else:
                    cv2.rectangle(annotated, (sig_x0 + shift, yc + 40), (sig_x1 + shift, yc + 130), (255, 0, 255), 2)
                
                # Reg/OMR box (cyan/yellow)
                if is_type1:
                    # Registration No box (yellow)
                    cv2.rectangle(annotated, (reg_x0 + shift, yc - 25), (reg_x1 + shift, yc + 25), (255, 255, 0), 2)
                    # OMR No box (cyan)
                    cv2.rectangle(annotated, (omr_x0 + shift, yc - 25), (omr_x1 + shift, yc + 25), (0, 255, 255), 2)
                else:
                    # Registration No and QCAB Serial No boxes
                    cv2.rectangle(annotated, (reg_x0 + shift, yc - 25), (reg_x1 + shift, yc + 25), (255, 255, 0), 2)
                    cv2.rectangle(annotated, (qcab_x0 + shift, yc - 20), (qcab_x1 + shift, yc + 30), (0, 255, 255), 2)

            inv_x0, inv_y0, inv_x1, inv_y1 = self.get_invigilator_signature_box(w, h)
            inv_color = (0, 255, 0) if self.current_invigilator_signed else (0, 0, 255)
            cv2.rectangle(annotated, (inv_x0, inv_y0), (inv_x1, inv_y1), inv_color, 3)
            cv2.putText(
                annotated,
                f"Invigilator Signed: {self.current_invigilator_signed}",
                (inv_x0, max(25, inv_y0 - 10)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, inv_color, 2)
                
            # Display a reduced annotated image in the scrollable viewer.
            self.root.update_idletasks()
            canvas_w = max(self.image_canvas.winfo_width() - 24, 480)
            canvas_h = max(self.image_canvas.winfo_height() - 24, 320)
            display_scale = min(
                0.55,
                max(0.22, min((canvas_w * 1.05) / w, (canvas_h * 1.25) / h))
            )
            display_w = max(1, int(w * display_scale))
            display_h = max(1, int(h * display_scale))
            annotated_view = cv2.resize(
                annotated, (display_w, display_h),
                interpolation=cv2.INTER_AREA)

            color_cvt = cv2.cvtColor(annotated_view, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(color_cvt)
            self.tk_img = ImageTk.PhotoImage(image=pil_img)
            self.image_canvas.delete("all")
            self.image_canvas.create_image(0, 0, anchor="nw", image=self.tk_img)
            self.image_canvas.configure(
                scrollregion=(0, 0, self.tk_img.width(), self.tk_img.height()))
            
            # Update Treeview
            for item in self.tree.get_children():
                self.tree.delete(item)
                
            for r in records:
                self.tree.insert("", "end", values=(
                    r["row_number"],
                    r["status"],
                    "Yes" if r["signature_present"] else "No",
                    "Yes" if self.current_invigilator_signed else "No",
                    r.get("registration_no", ""),
                    (r.get("omr_no", "") if is_type1
                     else r.get("qcab_serial_no", ""))
                ))
            
            # Auto-select row 1 in treeview
            if self.tree.get_children():
                self.tree.selection_set(self.tree.get_children()[0])

            extracted_status = self._extracted_status_from_attendance_data(
                self.attendance_csv_records.get(fname))
            self.set_sheet_status(display_name, extracted=extracted_status)
            self.status_lbl.config(text="Processing Completed Successfully", foreground="#00e676")
            audit.log("nominal_roll", "sheet_processed",
                      details={"file": display_name, "records": len(records)})
            
        except Exception as e:
            audit.log("nominal_roll", "sheet_processed", outcome="failed",
                      details={"file": display_name, "error": str(e)})
            self.set_sheet_status(display_name, extracted="error")
            self.status_lbl.config(text=f"Error: {str(e)}", foreground="#ff1744")
            messagebox.showerror("Error", f"An error occurred: {str(e)}")

    def on_row_selected(self, event):
        selected = self.tree.selection()
        if not selected:
            return
            
        item = self.tree.item(selected[0])
        values = item["values"]
        row_num = int(values[0]) - 1 # 0-indexed
        
        # Load into editing form
        if self.current_records and row_num < len(self.current_records):
            record = self.current_records[row_num]

            self.set_readonly_entry(self.edit_reg, record.get("registration_no", ""))
            number_value = (record.get("omr_no", "") if self.is_type1
                            else record.get("qcab_serial_no", ""))
            self.set_readonly_entry(self.edit_omr, number_value)
            self.set_readonly_entry(
                self.edit_sig,
                "Yes" if record.get("signature_present") else "No")
            self.set_readonly_entry(
                self.edit_inv_sig,
                "Yes" if self.current_invigilator_signed else "No")
            self.set_readonly_entry(
                self.edit_status,
                record.get("status", "Not Marked"))
        
        if self.current_img is not None:
            yc = self.current_y_centers[row_num]
            shift = self.current_shift
            
            # Crop cells
            if self.is_type1:
                sig_crop = self.current_img[yc+25:yc+105, 330+shift : 810+shift]
                reg_crop = self.current_img[yc-25:yc+25, 830+shift : 1030+shift]
                omr_crop = self.current_img[yc-25:yc+25, 1090+shift : 1250+shift]
            else:
                sig_crop = self.current_img[yc+40:yc+130, 380+shift : 850+shift]
                reg_crop = self.current_img[yc-25:yc+25, 760+shift : 950+shift]
                omr_crop = self.current_img[yc-20:yc+30, 1180+shift : 1490+shift]

            h_img, w_img = self.current_img.shape[:2]
            inv_x0, inv_y0, inv_x1, inv_y1 = self.get_invigilator_signature_box(w_img, h_img)
            inv_sig_crop = self.current_img[inv_y0:inv_y1, inv_x0:inv_x1]
                
            self.root.update_idletasks()

            def fit_preview(crop, label):
                max_w = max(label.winfo_width() - 12, 240)
                max_h = max(label.winfo_height() - 12, 70)
                if crop.size == 0:
                    return np.zeros((max_h, max_w, 3), dtype=np.uint8)

                h, w = crop.shape[:2]
                scale = min(max_w / w, max_h / h)
                new_w = max(1, int(w * scale))
                new_h = max(1, int(h * scale))
                return cv2.resize(crop, (new_w, new_h), interpolation=cv2.INTER_CUBIC)

            sig_resized = fit_preview(sig_crop, self.sig_preview_lbl)
            inv_sig_resized = fit_preview(inv_sig_crop, self.inv_sig_preview_lbl)
            reg_resized = fit_preview(reg_crop, self.reg_preview_lbl)
            omr_resized = fit_preview(omr_crop, self.omr_preview_lbl)
            
            # Display Previews
            self.tk_sig = ImageTk.PhotoImage(image=Image.fromarray(cv2.cvtColor(sig_resized, cv2.COLOR_BGR2RGB)))
            self.sig_preview_lbl.config(image=self.tk_sig)

            self.tk_inv_sig = ImageTk.PhotoImage(image=Image.fromarray(cv2.cvtColor(inv_sig_resized, cv2.COLOR_BGR2RGB)))
            self.inv_sig_preview_lbl.config(image=self.tk_inv_sig)
            
            self.tk_reg = ImageTk.PhotoImage(image=Image.fromarray(cv2.cvtColor(reg_resized, cv2.COLOR_BGR2RGB)))
            self.reg_preview_lbl.config(image=self.tk_reg)

            self.tk_omr = ImageTk.PhotoImage(image=Image.fromarray(cv2.cvtColor(omr_resized, cv2.COLOR_BGR2RGB)))
            self.omr_preview_lbl.config(image=self.tk_omr)

    def browse_folder(self):
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.current_dir = dir_path
            if hasattr(self, "export_btn"):
                self.export_btn.config(state="disabled")
            if hasattr(self, "progress"):
                self.progress["value"] = 0
            self.load_attendance_csv()
            files = sorted([
                os.path.abspath(os.path.join(self.current_dir, f))
                for f in os.listdir(self.current_dir)
                if f.lower().endswith(('.jpg', '.jpeg', '.png'))
            ])
            self.file_combo["values"] = files
            self._init_status_grid()
            if files:
                self.file_combo.current(0)
                self.process_selected_sheet()
            else:
                self.file_combo.set("")

    def get_sql_connection(self):
        from db_credentials import get_sql_connection
        return get_sql_connection()

    def check_table_exists(self, conn, table_name):
        cursor = conn.cursor()
        cursor.execute("""
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_NAME = ?
        """, (table_name,))
        return cursor.fetchone()[0] == 1

    def sheet_exists_in_db(self, cursor, table_name, filename):
        cursor.execute(
            f"SELECT COUNT(*) FROM {table_name} WHERE filename = ?",
            (filename,))
        return cursor.fetchone()[0] > 0

    def log_error_to_mssql(self, cursor, filename, sheet_type, error_message):
        cursor.execute("""
            EXEC sp_insert_attendance_error_log
                @source_module = ?,
                @sheet_type = ?,
                @filename = ?,
                @error_message = ?
        """, (
            "NominalRolls",
            sheet_type,
            filename,
            str(error_message)[:4000],
        ))

    def insert_attendance_rows_to_mssql(self, cursor, filename, data, is_type1):
        center_code = data.get("center_code", "")
        subcenter_code = data.get("subcenter_code", "")
        subject_code = data.get("subject_code", "")
        invigilator_signed = int(data.get("invigilator_signed") or 0)

        for record in data.get("records", []):
            row_number = int(record.get("row_number", 0))
            status = record.get("status", "Not Marked")
            signature_present = 1 if record.get("signature_present") else 0
            reg_val = record.get("registration_no", "")
            omr_val = record.get("omr_no", "")
            qcab_val = record.get("qcab_serial_no", "")

            if is_type1:
                cursor.execute("""
                    EXEC sp_insert_attendance_sheet_data_1
                        @filename = ?,
                        @center_code = ?,
                        @subcenter_code = ?,
                        @subject_code = ?,
                        @invigilator_signed = ?,
                        @row_number = ?,
                        @status = ?,
                        @signature_present = ?,
                        @omr_no = ?,
                        @registration_no = ?
                """, (
                    filename,
                    center_code,
                    subcenter_code,
                    subject_code,
                    invigilator_signed,
                    row_number,
                    status,
                    signature_present,
                    omr_val,
                    reg_val,
                ))
            else:
                cursor.execute("""
                    EXEC sp_insert_attendance_sheet_data2
                        @filename = ?,
                        @center_code = ?,
                        @subcenter_code = ?,
                        @subject_code = ?,
                        @invigilator_signed = ?,
                        @row_number = ?,
                        @status = ?,
                        @signature_present = ?,
                        @qcab_serial_no = ?,
                        @registration_no = ?
                """, (
                    filename,
                    center_code,
                    subcenter_code,
                    subject_code,
                    invigilator_signed,
                    row_number,
                    status,
                    signature_present,
                    qcab_val,
                    reg_val,
                ))

    def process_all_sheets_to_mssql(self):
        files = list(self.file_combo["values"])
        if not files:
            messagebox.showwarning("Warning", "No images found to process!")
            return

        if not self.current_dir or not os.path.exists(self.current_dir):
            messagebox.showerror("Error", "Invalid folder path!")
            return

        choice = self.type_combo.get()
        is_type1 = "Sheet 1" in choice
        table_name = "attendance_sheet_data_1" if is_type1 else "attendance_sheet_data2"
        sheet_type_label = "Nominal Roll 1 (OMR)" if is_type1 else "Nominal Roll 2 (QCAB)"

        try:
            conn = self.get_sql_connection()
            cursor = conn.cursor()

            # Auto-upgrade schema if table exists but doesn't have registration_no
            if self.check_table_exists(conn, "attendance_sheet_data_1"):
                cursor.execute("""
                SELECT COUNT(*) FROM sys.columns 
                WHERE object_id = OBJECT_ID(N'dbo.attendance_sheet_data_1') 
                  AND name = 'registration_no'
                """)
                if cursor.fetchone()[0] == 0:
                    try:
                        cursor.execute("ALTER TABLE dbo.attendance_sheet_data_1 ADD registration_no NVARCHAR(50) NULL")
                        conn.commit()
                        cursor.execute("""
                        CREATE OR ALTER PROCEDURE dbo.sp_insert_attendance_sheet_data_1
                            @filename           NVARCHAR(500),
                            @center_code        NVARCHAR(50) = NULL,
                            @subcenter_code     NVARCHAR(50) = NULL,
                            @subject_code       NVARCHAR(50) = NULL,
                            @invigilator_signed BIT = 0,
                            @row_number         INT,
                            @status             NVARCHAR(50) = NULL,
                            @signature_present  BIT = 0,
                            @omr_no             NVARCHAR(50) = NULL,
                            @registration_no    NVARCHAR(50) = NULL
                        AS
                        BEGIN
                            SET NOCOUNT ON;

                            IF EXISTS (
                                SELECT 1
                                FROM dbo.attendance_sheet_data_1
                                WHERE filename = @filename
                                  AND row_number = @row_number
                            )
                            BEGIN
                                RETURN;
                            END;

                            INSERT INTO dbo.attendance_sheet_data_1 (
                                filename,
                                center_code,
                                subcenter_code,
                                subject_code,
                                invigilator_signed,
                                row_number,
                                status,
                                signature_present,
                                omr_no,
                                registration_no
                            )
                            VALUES (
                                @filename,
                                @center_code,
                                @subcenter_code,
                                @subject_code,
                                @invigilator_signed,
                                @row_number,
                                @status,
                                @signature_present,
                                @omr_no,
                                @registration_no
                            );
                        END;
                        """)
                        conn.commit()
                    except Exception as ex:
                        print(f"Failed to auto-upgrade database schema: {ex}")
                        conn.rollback()

            if not self.check_table_exists(conn, table_name):
                messagebox.showerror(
                    "Error",
                    f"Table '{table_name}' does not exist. "
                    "Run sql/attendance_sheets_schema.sql in SSMS first.")
                conn.close()
                return

            if not is_type1 and not self.check_column_exists(
                    conn, "attendance_sheet_data2", "qcab_serial_no"):
                cursor.execute(
                    "ALTER TABLE dbo.attendance_sheet_data2 "
                    "ADD qcab_serial_no NVARCHAR(50) NULL")
                conn.commit()

            if not is_type1:
                cursor.execute("""
                    CREATE OR ALTER PROCEDURE dbo.sp_insert_attendance_sheet_data2
                        @filename NVARCHAR(500),
                        @center_code NVARCHAR(50) = NULL,
                        @subcenter_code NVARCHAR(50) = NULL,
                        @subject_code NVARCHAR(50) = NULL,
                        @invigilator_signed BIT = 0,
                        @row_number INT,
                        @status NVARCHAR(50) = NULL,
                        @signature_present BIT = 0,
                        @registration_no NVARCHAR(50) = NULL,
                        @qcab_serial_no NVARCHAR(50) = NULL
                    AS
                    BEGIN
                        SET NOCOUNT ON;
                        IF EXISTS (
                            SELECT 1 FROM dbo.attendance_sheet_data2
                            WHERE filename = @filename
                              AND row_number = @row_number
                        ) RETURN;
                        INSERT INTO dbo.attendance_sheet_data2 (
                            filename, center_code, subcenter_code, subject_code,
                            invigilator_signed, row_number, status,
                            signature_present, registration_no, qcab_serial_no
                        ) VALUES (
                            @filename, @center_code, @subcenter_code,
                            @subject_code, @invigilator_signed, @row_number,
                            @status, @signature_present, @registration_no,
                            @qcab_serial_no
                        );
                    END
                """)
                conn.commit()

            if not self.check_table_exists(conn, "error_log"):
                messagebox.showerror(
                    "Error",
                    "Table 'error_log' does not exist. "
                    "Run sql/attendance_sheets_schema.sql in SSMS first.")
                conn.close()
                return

            if hasattr(self, "export_btn"):
                self.export_btn.config(state="disabled")
            self.progress["value"] = 0
            self.progress["maximum"] = len(files)

            processed_count = 0
            saved_count = 0
            skipped_count = 0
            error_count = 0
            self._init_status_grid()

            for idx, fname in enumerate(files, 1):
                img_path = self.normalize_image_path(fname)
                display_name = os.path.basename(img_path)
                self.file_combo.current(idx - 1)
                self.set_sheet_status(display_name, extracted="pending", saved_db="pending")
                self.status_lbl.config(
                    text=f"Processing {idx}/{len(files)} - {display_name}",
                    foreground="#ffeb3b")
                self.root.update_idletasks()

                try:
                    self.process_selected_sheet(force_reprocess=True)
                    if img_path not in self.attendance_csv_records:
                        error_count += 1
                        self.set_sheet_status(
                            display_name, extracted="error", saved_db="error")
                        self.log_error_to_mssql(
                            cursor, img_path, sheet_type_label,
                            "Processing completed but no records were produced.")
                        continue

                    processed_count += 1
                    data = self.attendance_csv_records[img_path]
                    extracted_status = self._extracted_status_from_attendance_data(data)

                    if self.sheet_exists_in_db(cursor, table_name, img_path):
                        skipped_count += 1
                        self.set_sheet_status(
                            display_name,
                            extracted=extracted_status,
                            saved_db="imported")
                        continue

                    self.insert_attendance_rows_to_mssql(
                        cursor, img_path, data, is_type1)
                    saved_count += 1
                    self.set_sheet_status(
                        display_name,
                        extracted=extracted_status,
                        saved_db="imported")

                except Exception as e:
                    error_count += 1
                    self.set_sheet_status(
                        display_name, extracted="error", saved_db="error")
                    print(f"Error processing {display_name}: {e}")
                    try:
                        self.log_error_to_mssql(
                            cursor, img_path, sheet_type_label, str(e))
                    except Exception as log_err:
                        print(f"Failed to write error_log for {display_name}: {log_err}")

                self.progress["value"] = idx
                self.root.update_idletasks()

            conn.commit()
            conn.close()

            audit.log("nominal_roll", "bulk_database_import", details={
                "total": len(files), "processed": processed_count,
                "saved": saved_count, "skipped": skipped_count, "errors": error_count})

            self._refresh_status_summary()
            if processed_count > 0 and hasattr(self, "export_btn"):
                self.export_btn.config(state="normal")

            self.status_lbl.config(
                text=(
                    f"Processed {processed_count}/{len(files)} | "
                    f"Saved {saved_count} | Skipped {skipped_count} | Errors {error_count}"
                ),
                foreground="#00e676")
            messagebox.showinfo(
                "Success",
                f"Processed: {processed_count}/{len(files)}\n"
                f"Saved to DB: {saved_count}\n"
                f"Skipped (already in DB): {skipped_count}\n"
                f"Errors logged: {error_count}\n\n"
                "Use Export to Excel to save a CSV copy.")

        except Exception as e:
            audit.log("nominal_roll", "bulk_database_import", outcome="failed",
                      details={"error": str(e)})
            messagebox.showerror("Database Error", str(e))

    def load_attendance_csv(self):
        self.attendance_csv_records = {}
        csv_path = os.path.join(self.current_dir, "Attendance_Sheet_Results.csv")
        if os.path.exists(csv_path):
            import csv
            try:
                with open(csv_path, mode="r", newline="", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        filename = row.get("Filename")
                        if not filename:
                            continue
                        filename = self.normalize_image_path(filename)
                            
                        if filename not in self.attendance_csv_records:
                            self.attendance_csv_records[filename] = {
                                "center_code": row.get("Center Code", ""),
                                "subcenter_code": row.get("Sub Center Code", ""),
                                "subject_code": row.get("Subject Code", ""),
                                "invigilator_signed": row.get("Invigilator Signed", ""),
                                "has_qcab_column": "QCAB Serial No" in (reader.fieldnames or []),
                                "records": []
                            }
                        
                        reg_val = row.get("Registration No", "")
                        omr_val = row.get("OMR No", "")
                        qcab_val = row.get("QCAB Serial No", "")
                            
                        self.attendance_csv_records[filename]["records"].append({
                            "row_number": int(row.get("Row Number", 1)),
                            "status": row.get("Status", "Not Marked"),
                            "signature_present": (row.get("Signature Present") == "Yes"),
                            "registration_no": reg_val,
                            "omr_no": omr_val,
                            "qcab_serial_no": qcab_val
                        })
                        
                for fname in self.attendance_csv_records:
                    self.attendance_csv_records[fname]["records"].sort(key=lambda x: x["row_number"])
            except Exception as e:
                print(f"Error loading Attendance CSV: {e}")

    def write_attendance_csv(self, csv_path):
        import csv
        choice = self.type_combo.get()
        is_type1 = "Sheet 1" in choice

        with open(csv_path, mode="w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Filename", "Center Code", "Sub Center Code", "Subject Code",
                "Invigilator Signed", "Row Number", "Status",
                "Signature Present", "Registration No", "OMR No",
                "QCAB Serial No"
            ])
            for filename in sorted(self.file_combo["values"]):
                filename = self.normalize_image_path(filename)
                if filename in self.attendance_csv_records:
                    data = self.attendance_csv_records[filename]
                    center_code = data.get("center_code", "")
                    subcenter_code = data.get("subcenter_code", "")
                    subject_code = data.get("subject_code", "")
                    invigilator_signed = int(data.get("invigilator_signed") or 0)
                    for r in data.get("records", []):
                        reg_no = r.get("registration_no", "")
                        omr_no = r.get("omr_no", "")
                        qcab_no = r.get("qcab_serial_no", "")

                        writer.writerow([
                            filename,
                            center_code,
                            subcenter_code,
                            subject_code,
                            invigilator_signed,
                            r["row_number"],
                            r["status"],
                            "Yes" if r["signature_present"] else "No",
                            reg_no,
                            omr_no,
                            qcab_no
                        ])

    def export_results_to_excel(self):
        if not self.attendance_csv_records:
            messagebox.showwarning("Warning", "No processed data available to export!")
            return

        save_path = filedialog.asksaveasfilename(
            title="Export Attendance Sheet Results",
            initialdir=self.current_dir if hasattr(self, "current_dir") else os.getcwd(),
            initialfile="Attendance_Sheet_Results.csv",
            defaultextension=".csv",
            filetypes=[
                ("Excel CSV", "*.csv"),
                ("All Files", "*.*")
            ])
        if not save_path:
            return

        try:
            self.write_attendance_csv(save_path)
            audit.log("nominal_roll", "results_exported", details={
                "file": os.path.basename(save_path), "sheets": len(self.attendance_csv_records)})
            self.status_lbl.config(
                text=f"Exported to: {os.path.basename(save_path)}",
                foreground="#00e676")
            messagebox.showinfo("Success", f"Results exported to:\n{save_path}")
        except Exception as e:
            audit.log("nominal_roll", "results_exported", outcome="failed", details={"error": str(e)})
            messagebox.showerror("Error", f"Failed to export results: {e}")

    def on_header_changed(self):
        fname = self.normalize_image_path(self.file_combo.get())
        if fname and fname in self.attendance_csv_records:
            self.attendance_csv_records[fname]["center_code"] = self.center_entry.get().strip()
            self.attendance_csv_records[fname]["subcenter_code"] = self.subcenter_entry.get().strip()
            self.attendance_csv_records[fname]["subject_code"] = self.subject_entry.get().strip()

    def navigate_sheet(self, direction):
        if not self.file_combo["values"]:
            return
            
        current_idx = self.file_combo.current()
        new_idx = current_idx + direction
        
        if 0 <= new_idx < len(self.file_combo["values"]):
            # Auto-save changes of current sheet first
            if self.current_records:
                fname = self.normalize_image_path(self.file_combo.get())
                if fname:
                    self.attendance_csv_records[fname] = {
                        "center_code": self.center_entry.get().strip(),
                        "subcenter_code": self.subcenter_entry.get().strip(),
                        "subject_code": self.subject_entry.get().strip(),
                        "invigilator_signed": int(self.current_invigilator_signed),
                        "records": self.current_records
                    }
            
            # Select the new sheet
            self.file_combo.current(new_idx)
            self.process_selected_sheet()

if __name__ == "__main__":
    root = tk.Tk()
    app = AttendanceViewerDemo(root)
    root.mainloop()
