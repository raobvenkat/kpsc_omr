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

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from core.nominal_roll_type1 import process_attendance_sheet1
from core.nominal_roll_type2 import process_attendance_sheet2

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
        self.root.geometry("1450x850")
        self.root.minsize(1100, 700)
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
        
        lbl_type = ttk.Label(top_frame, text="Sheet Type:", font=("Segoe UI", 11, "bold"), background="#2b2b36")
        lbl_type.pack(side="left", padx=(20, 5))
        
        self.type_combo = ttk.Combobox(top_frame, values=["Attendance Sheet 1 (OMR)", "Attendance Sheet 2 (QCAB)"], state="readonly", width=25, font=("Segoe UI", 10))
        self.type_combo.current(0)
        self.type_combo.pack(side="left", padx=10)
        self.type_combo.bind("<<ComboboxSelected>>", lambda e: self.on_sheet_type_changed())
        
        lbl_file = ttk.Label(top_frame, text="Select Image:", font=("Segoe UI", 11, "bold"), background="#2b2b36")
        lbl_file.pack(side="left", padx=(20, 5))
        
        browse_btn = ttk.Button(top_frame, text="Select Folder...", command=self.browse_folder, style="TButton")
        browse_btn.pack(side="left", padx=5)
        
        self.prev_btn = ttk.Button(top_frame, text="<- Prev", command=lambda: self.navigate_sheet(-1), style="TButton", width=8, state="disabled")
        self.prev_btn.pack(side="left", padx=2)
        
        self.file_combo = ttk.Combobox(top_frame, state="readonly", width=20, font=("Segoe UI", 10))
        self.file_combo.pack(side="left", padx=5)
        self.file_combo.bind("<<ComboboxSelected>>", lambda e: self.process_selected_sheet())
        
        self.next_btn = ttk.Button(top_frame, text="Next ->", command=lambda: self.navigate_sheet(1), style="TButton", width=8, state="disabled")
        self.next_btn.pack(side="left", padx=2)
        
        # Run Processing button removed as Next/Prev and selection handles processing automatically
        
        self.export_btn = ttk.Button(top_frame, text="Export to Excel", command=self.export_results_to_excel, style="TButton", width=16, state="disabled")
        self.export_btn.pack(side="right", padx=(5, 10))

        self.process_all_btn = ttk.Button(top_frame, text="Process All", command=self.process_all_sheets, style="TButton", width=12)
        self.process_all_btn.pack(side="right", padx=5)
        
        # 2. Main content split pane
        content_frame = tk.Frame(self.root, bg="#1c1c22")
        content_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        # Left Panel: Full Annotated Image
        self.left_frame = tk.LabelFrame(content_frame, text="Annotated Sheet Viewer", bg="#2b2b36", fg="#00e676", font=("Segoe UI", 10, "bold"), bd=1, width=650)
        self.left_frame.pack(fill="both", side="left", padx=(0, 10))
        self.left_frame.pack_propagate(False)

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
        
        # Right Panel: Table and crops
        right_frame = tk.Frame(content_frame, bg="#1c1c22")
        right_frame.pack(fill="both", side="right", expand=True, padx=(10, 0))
        
        # Table Frame
        table_frame = tk.LabelFrame(right_frame, text="Extracted Nominal Roll Table", bg="#2b2b36", fg="#00e676", font=("Segoe UI", 10, "bold"), bd=1)
        table_frame.pack(fill="x", expand=False, pady=(0, 10))
        
        # Scrollbars for Treeview
        tree_scroll_y = ttk.Scrollbar(table_frame, orient="vertical")
        tree_scroll_y.pack(side="right", fill="y")
        
        self.tree = ttk.Treeview(table_frame, columns=("row", "status", "sig", "reg_omr"), show="headings", yscrollcommand=tree_scroll_y.set, height=6)
        tree_scroll_y.config(command=self.tree.yview)
        
        self.tree.heading("row", text="Row")
        self.tree.heading("status", text="Status")
        self.tree.heading("sig", text="Signature")
        self.tree.heading("reg_omr", text="Registration/OMR No")
        
        self.tree.column("row", width=60, anchor="center")
        self.tree.column("status", width=120, anchor="center")
        self.tree.column("sig", width=120, anchor="center")
        self.tree.column("reg_omr", width=200, anchor="center")
        self.tree.pack(fill="x", expand=False, padx=5, pady=5)
        self.tree.bind("<<TreeviewSelect>>", self.on_row_selected)
        
        # Details / Crop Frame at Bottom Right
        details_frame = tk.LabelFrame(right_frame, text="Selected Row Visual Verification Snippets", bg="#2b2b36", fg="#00e676", font=("Segoe UI", 10, "bold"), bd=1, height=360)
        details_frame.pack(fill="both", expand=True)
        details_frame.pack_propagate(False)
        
        self.sig_preview_wrapper = tk.LabelFrame(details_frame, text="Signature Crop", bg="#2b2b36", fg="#ffffff", font=("Segoe UI", 8))
        self.sig_preview_wrapper.pack(side="left", fill="both", expand=True, padx=10, pady=5)
        self.sig_preview_lbl = tk.Label(self.sig_preview_wrapper, bg="#2b2b36")
        self.sig_preview_lbl.pack(fill="both", expand=True)
        
        self.reg_preview_wrapper = tk.LabelFrame(details_frame, text="Registration / OMR No Crop", bg="#2b2b36", fg="#ffffff", font=("Segoe UI", 8))
        self.reg_preview_wrapper.pack(side="left", fill="both", expand=True, padx=10, pady=5)
        self.reg_preview_lbl = tk.Label(self.reg_preview_wrapper, bg="#2b2b36")
        self.reg_preview_lbl.pack(fill="both", expand=True)

        # Correction Form Frame
        correction_frame = tk.LabelFrame(right_frame, text="Candidate Row Correction Form", bg="#2b2b36", fg="#00e676", font=("Segoe UI", 10, "bold"), bd=1, height=90)
        correction_frame.pack(fill="x", pady=(10, 0))
        correction_frame.pack_propagate(False)

        # Grid layout for correction widgets (1 row, 7 columns)
        for col_idx in range(7):
            correction_frame.columnconfigure(col_idx, weight=1)

        lbl_reg = ttk.Label(correction_frame, text="Reg/OMR No:", background="#2b2b36", font=("Segoe UI", 9, "bold"))
        lbl_reg.grid(row=0, column=0, sticky="w", padx=5, pady=15)
        self.edit_reg = ttk.Entry(correction_frame, font=("Segoe UI", 9), width=15)
        self.edit_reg.grid(row=0, column=1, sticky="ew", padx=5, pady=15)

        lbl_sig = ttk.Label(correction_frame, text="Signature:", background="#2b2b36", font=("Segoe UI", 9, "bold"))
        lbl_sig.grid(row=0, column=2, sticky="w", padx=5, pady=15)
        self.edit_sig = ttk.Combobox(correction_frame, values=["Yes", "No"], state="readonly", width=8, font=("Segoe UI", 9))
        self.edit_sig.grid(row=0, column=3, sticky="w", padx=5, pady=15)

        lbl_status = ttk.Label(correction_frame, text="Status:", background="#2b2b36", font=("Segoe UI", 9, "bold"))
        lbl_status.grid(row=0, column=4, sticky="w", padx=5, pady=15)
        self.edit_status = ttk.Combobox(correction_frame, values=["Present", "Absent", "Not Marked", "Double Marked"], state="readonly", width=12, font=("Segoe UI", 9))
        self.edit_status.grid(row=0, column=5, sticky="w", padx=5, pady=15)

        self.apply_btn = ttk.Button(correction_frame, text="Apply Correction", command=self.apply_corrections, style="TButton")
        self.apply_btn.grid(row=0, column=6, sticky="e", padx=10, pady=15)

    def on_annotated_image_mousewheel(self, event):
        if event.state & 0x0001:
            self.image_canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")
        else:
            self.image_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def on_sheet_type_changed(self):
        self.current_dir = None
        self.current_records = []
        self.current_img = None
        self.attendance_csv_records = {}
        self.file_combo["values"] = []
        self.file_combo.set("")
        self.image_canvas.delete("all")
        self.image_canvas.configure(scrollregion=(0, 0, 0, 0))
        self.sig_preview_lbl.config(image="")
        self.reg_preview_lbl.config(image="")
        for item in self.tree.get_children():
            self.tree.delete(item)
        if hasattr(self, "export_btn"):
            self.export_btn.config(state="disabled")
        if hasattr(self, "progress"):
            self.progress["value"] = 0
        self.prev_btn.config(state="disabled")
        self.next_btn.config(state="disabled")
        self.status_lbl.config(text="Select a folder to begin", foreground="#ffeb3b")

    def process_selected_sheet(self, force_reprocess=False):
        fname = self.file_combo.get()
        if not fname:
            messagebox.showwarning("Warning", "No image selected!")
            return
        if not self.current_dir:
            messagebox.showwarning("Warning", "Please select a folder first!")
            return
            
        img_path = os.path.join(self.current_dir, fname)
        self.status_lbl.config(text="Processing... Please wait", foreground="#ffeb3b")
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
                
            # Load from CSV database or process
            needs_reprocess = False
            if fname in self.attendance_csv_records and not force_reprocess:
                data = self.attendance_csv_records[fname]
                center_code = data.get("center_code", "")
                subcenter_code = data.get("subcenter_code", "")
                subject_code = data.get("subject_code", "")
                records = data.get("records", [])
                
                # Auto-reprocess if loaded CSV data is missing header codes or records
                if not center_code or not subcenter_code or not subject_code or not records:
                    needs_reprocess = True
                else:
                    # Also reprocess if OMR/Reg numbers are missing or incomplete (less than 6 digits)
                    for r in records:
                        if not r.get("reg_omr") or len(str(r.get("reg_omr")).strip()) < 6:
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
                
                self.attendance_csv_records[fname] = {
                    "center_code": center_code,
                    "subcenter_code": subcenter_code,
                    "subject_code": subject_code,
                    "records": records
                }
                
            self.current_records = records
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
                    # OMR No box
                    cv2.rectangle(annotated, (omr_x0 + shift, yc - 25), (omr_x1 + shift, yc + 25), (0, 255, 255), 2)
                else:
                    # Registration No box
                    cv2.rectangle(annotated, (reg_x0 + shift, yc - 25), (reg_x1 + shift, yc + 25), (255, 255, 0), 2)
                
            # Display full annotated image in scrollable viewer.
            color_cvt = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
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
                    r.get("reg_omr", "")
                ))
            
            # Auto-select row 1 in treeview
            if self.tree.get_children():
                self.tree.selection_set(self.tree.get_children()[0])
                
            self.status_lbl.config(text="Processing Completed Successfully", foreground="#00e676")
            
        except Exception as e:
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
            
            self.edit_reg.delete(0, tk.END)
            self.edit_reg.insert(0, record.get("reg_omr", ""))
            
            self.edit_sig.set("Yes" if record.get("signature_present") else "No")
            self.edit_status.set(record.get("status", "Not Marked"))
        
        if self.current_img is not None:
            yc = self.current_y_centers[row_num]
            shift = self.current_shift
            
            # Crop cells
            if self.is_type1:
                sig_crop = self.current_img[yc+25:yc+105, 330+shift : 810+shift]
                reg_crop = self.current_img[yc-25:yc+25, 1090+shift : 1250+shift] # OMR No crop for Sheet 1
            else:
                sig_crop = self.current_img[yc+40:yc+130, 380+shift : 850+shift]
                reg_crop = self.current_img[yc-25:yc+25, 760+shift : 950+shift] # Registration No crop for Sheet 2
                
            self.root.update_idletasks()

            def fit_preview(crop, label):
                max_w = max(label.winfo_width() - 12, 320)
                max_h = max(label.winfo_height() - 12, 160)
                if crop.size == 0:
                    return np.zeros((max_h, max_w, 3), dtype=np.uint8)

                h, w = crop.shape[:2]
                scale = min(max_w / w, max_h / h)
                new_w = max(1, int(w * scale))
                new_h = max(1, int(h * scale))
                return cv2.resize(crop, (new_w, new_h), interpolation=cv2.INTER_CUBIC)

            sig_resized = fit_preview(sig_crop, self.sig_preview_lbl)
            reg_resized = fit_preview(reg_crop, self.reg_preview_lbl)
            
            # Display Previews
            self.tk_sig = ImageTk.PhotoImage(image=Image.fromarray(cv2.cvtColor(sig_resized, cv2.COLOR_BGR2RGB)))
            self.sig_preview_lbl.config(image=self.tk_sig)
            
            self.tk_reg = ImageTk.PhotoImage(image=Image.fromarray(cv2.cvtColor(reg_resized, cv2.COLOR_BGR2RGB)))
            self.reg_preview_lbl.config(image=self.tk_reg)

    def apply_corrections(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "No row selected for correction!")
            return
            
        item = self.tree.item(selected[0])
        row_num = int(item["values"][0]) - 1 # 0-indexed
        
        reg_omr_val = self.edit_reg.get().strip()
        sig_val = self.edit_sig.get()
        status_val = self.edit_status.get()
        
        # Update memory
        record = self.current_records[row_num]
        record["reg_omr"] = reg_omr_val
        record["signature_present"] = (sig_val == "Yes")
        record["status"] = status_val
        
        # Update Treeview row
        self.tree.item(selected[0], values=(
            row_num + 1,
            status_val,
            sig_val,
            reg_omr_val
        ))
        
        self.status_lbl.config(text=f"Row {row_num + 1} updated successfully", foreground="#ffeb3b")
        
        # Save to database CSV
        fname = self.file_combo.get()
        if fname:
            self.attendance_csv_records[fname] = {
                "center_code": self.center_entry.get().strip(),
                "subcenter_code": self.subcenter_entry.get().strip(),
                "subject_code": self.subject_entry.get().strip(),
                "records": self.current_records
            }
            self.status_lbl.config(text="Correction saved in memory", foreground="#00e676")

    def browse_folder(self):
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.current_dir = dir_path
            if hasattr(self, "export_btn"):
                self.export_btn.config(state="disabled")
            if hasattr(self, "progress"):
                self.progress["value"] = 0
            self.load_attendance_csv()
            files = sorted([f for f in os.listdir(self.current_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
            self.file_combo["values"] = files
            if files:
                self.file_combo.current(0)
                self.process_selected_sheet()
            else:
                self.file_combo.set("")

    def process_all_sheets(self):
        files = list(self.file_combo["values"])
        if not files:
            messagebox.showwarning("Warning", "No images found to process!")
            return

        if hasattr(self, "export_btn"):
            self.export_btn.config(state="disabled")
        self.progress["value"] = 0
        self.progress["maximum"] = len(files)

        processed_count = 0
        for idx, fname in enumerate(files, 1):
            self.file_combo.current(idx - 1)
            self.status_lbl.config(
                text=f"Processing {idx}/{len(files)} - {fname}",
                foreground="#ffeb3b")
            self.root.update_idletasks()
            self.process_selected_sheet(force_reprocess=True)
            if fname in self.attendance_csv_records:
                processed_count += 1
            self.progress["value"] = idx
            self.root.update_idletasks()

        if processed_count > 0 and hasattr(self, "export_btn"):
            self.export_btn.config(state="normal")

        self.status_lbl.config(
            text=f"Processed {processed_count}/{len(files)} sheets",
            foreground="#00e676")
        messagebox.showinfo(
            "Success",
            "All sheets processed. Use Export to Excel to save the file.")

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
                            
                        if filename not in self.attendance_csv_records:
                            self.attendance_csv_records[filename] = {
                                "center_code": row.get("Center Code", ""),
                                "subcenter_code": row.get("Sub Center Code", ""),
                                "subject_code": row.get("Subject Code", ""),
                                "records": []
                            }
                        
                        reg_val = row.get("Registration No", "")
                        omr_val = row.get("OMR No", "")
                        reg_omr = reg_val if reg_val else omr_val
                            
                        self.attendance_csv_records[filename]["records"].append({
                            "row_number": int(row.get("Row Number", 1)),
                            "status": row.get("Status", "Not Marked"),
                            "signature_present": (row.get("Signature Present") == "Yes"),
                            "reg_omr": reg_omr
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
                "Row Number", "Status", "Signature Present", "Registration No", "OMR No"
            ])
            for filename in sorted(self.file_combo["values"]):
                if filename in self.attendance_csv_records:
                    data = self.attendance_csv_records[filename]
                    center_code = data.get("center_code", "")
                    subcenter_code = data.get("subcenter_code", "")
                    subject_code = data.get("subject_code", "")
                    for r in data.get("records", []):
                        reg_no = ""
                        omr_no = ""
                        if is_type1:
                            omr_no = r.get("reg_omr", "")
                        else:
                            reg_no = r.get("reg_omr", "")

                        writer.writerow([
                            filename,
                            center_code,
                            subcenter_code,
                            subject_code,
                            r["row_number"],
                            r["status"],
                            "Yes" if r["signature_present"] else "No",
                            reg_no,
                            omr_no
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
            self.status_lbl.config(
                text=f"Exported to: {os.path.basename(save_path)}",
                foreground="#00e676")
            messagebox.showinfo("Success", f"Results exported to:\n{save_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export results: {e}")

    def on_header_changed(self):
        fname = self.file_combo.get()
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
                fname = self.file_combo.get()
                if fname:
                    self.attendance_csv_records[fname] = {
                        "center_code": self.center_entry.get().strip(),
                        "subcenter_code": self.subcenter_entry.get().strip(),
                        "subject_code": self.subject_entry.get().strip(),
                        "records": self.current_records
                    }
            
            # Select the new sheet
            self.file_combo.current(new_idx)
            self.process_selected_sheet()

if __name__ == "__main__":
    root = tk.Tk()
    app = AttendanceViewerDemo(root)
    root.mainloop()
