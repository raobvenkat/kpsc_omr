import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from openpyxl import Workbook
import db_credentials
import os
import tempfile
from datetime import datetime

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors

from pypdf import PdfReader, PdfWriter


class AllDiscrepancyGeneration:

    def __init__(self, root, user_id):
        self.root = root
        self.user_id = user_id

        self.columns = []
        self.rows = []

        self.root.title("All Discrepancy Generation & Export")
        self.root.geometry("1100x650")
        self.root.configure(bg="#f0f0f0")

        self.create_controls()

    # ====================================================
    # UI
    # ====================================================

    def create_controls(self):

        # Header Panel
        header_frame = ttk.LabelFrame(self.root, text="")
        header_frame.pack(fill="x", padx=10, pady=5)

        lbl_header = tk.Label(
            header_frame,
            text="All Discrepancy Generation & Export",
            font=("Segoe UI", 14, "bold")
        )
        lbl_header.pack(pady=10)

        # Filter Panel
        filter_frame = ttk.LabelFrame(self.root, text="")
        filter_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(
            filter_frame,
            text="Discrepancy For"
        ).grid(
            row=0,
            column=0,
            padx=10,
            pady=10,
            sticky="w"
        )

        self.discrepancy_var = tk.StringVar()

        self.cbo_discrepancy = ttk.Combobox(
            filter_frame,
            textvariable=self.discrepancy_var,
            width=40,
            state="readonly"
        )

        self.cbo_discrepancy["values"] = (
            "Counter Foil",
            "Nominal Roll 1 (Descriptive Test)",
            "Nominal Roll 2 (OMR Test)"
        )

        self.cbo_discrepancy.grid(
            row=0,
            column=1,
            padx=10,
            pady=10
        )

        btn_generate = ttk.Button(
            filter_frame,
            text="Generate",
            command=self.generate_discrepancy
        )

        btn_generate.grid(
            row=0,
            column=2,
            padx=10,
            pady=10
        )

        # Grid Frame
        grid_frame = ttk.LabelFrame(self.root, text="")
        grid_frame.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=5
        )

        self.tree = ttk.Treeview(grid_frame)

        vsb = ttk.Scrollbar(
            grid_frame,
            orient="vertical",
            command=self.tree.yview
        )

        hsb = ttk.Scrollbar(
            grid_frame,
            orient="horizontal",
            command=self.tree.xview
        )

        self.tree.configure(
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set
        )

        self.tree.pack(
            side="left",
            fill="both",
            expand=True
        )

        vsb.pack(
            side="right",
            fill="y"
        )

        hsb.pack(
            side="bottom",
            fill="x"
        )

        # Button Panel
        button_frame = ttk.LabelFrame(self.root, text="")
        button_frame.pack(
            fill="x",
            padx=10,
            pady=5
        )

        btn_export_excel = ttk.Button(
            button_frame,
            text="Export to Excel",
            command=self.export_to_excel
        )

        btn_export_excel.pack(
            side="left",
            padx=10,
            pady=10
        )

        btn_export_pdf = ttk.Button(
            button_frame,
            text="Export to PDF",
            command=self.export_to_pdf
        )

        btn_export_pdf.pack(
            side="left",
            padx=10,
            pady=10
        )

        btn_close = ttk.Button(
            button_frame,
            text="Close",
            command=self.close_screen
        )

        btn_close.pack(
            side="right",
            padx=10,
            pady=10
        )

    # ====================================================
    # GENERATE
    # ====================================================

    def generate_discrepancy(self):

        try:

            if not self.discrepancy_var.get():
                messagebox.showwarning(
                    "Validation",
                    "Please select Discrepancy For."
                )
                return

            discr_for = self.discrepancy_var.get()

            conn = db_credentials.get_sql_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                EXEC USP_GenerateDiscrepancy
                    @DiscrFor = ?,
                    @UserID = ?
                """,
                (
                    discr_for,
                    self.user_id
                )
            )

            self.tree.delete(*self.tree.get_children())

            self.columns = [
                column[0]
                for column in cursor.description
            ]

            self.tree["columns"] = self.columns
            self.tree["show"] = "headings"

            for col in self.columns:
                self.tree.heading(col, text=col)
                self.tree.column(
                    col,
                    width=150,
                    anchor="center"
                )

            self.rows = cursor.fetchall()

            for row in self.rows:
                self.tree.insert(
                    "",
                    "end",
                    values=list(row)
                )

            cursor.close()
            conn.close()

            messagebox.showinfo(
                "Success",
                "Discrepancy generated successfully."
            )

        except Exception as ex:

            messagebox.showerror(
                "Generate Error",
                str(ex)
            )

    # ====================================================
    # BIND GRID
    # ====================================================

    def bind_grid(self):

        self.tree.delete(
            *self.tree.get_children()
        )

        self.tree["columns"] = self.columns
        self.tree["show"] = "headings"

        for col in self.columns:

            self.tree.heading(
                col,
                text=col
            )

            self.tree.column(
                col,
                width=150,
                anchor="center"
            )

        for row in self.rows:

            self.tree.insert(
                "",
                "end",
                values=list(row)
            )

    # ====================================================
    # EXPORT EXCEL
    # ====================================================

    def export_to_excel(self):

        if len(self.rows) == 0:
            messagebox.showwarning(
                "Export",
                "No data available."
            )
            return

        file_name = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel File", "*.xlsx")]
        )

        if not file_name:
            return

        try:

            wb = Workbook()
            ws = wb.active
            ws.title = "Discrepancy Report"

            ws.append(self.columns)

            for row in self.rows:
                ws.append(list(row))

            wb.save(file_name)

            messagebox.showinfo(
                "Success",
                "Export completed successfully."
            )

        except Exception as ex:

            messagebox.showerror(
                "Export Error",
                str(ex)
            )

    # ====================================================
    # EXPORT PDF
    # ====================================================

    def export_to_pdf(self):

        if len(self.rows) == 0:
            messagebox.showwarning(
                "Export",
                "No data available."
            )
            return

        file_name = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF File", "*.pdf")]
        )

        if not file_name:
            return

        try:

            password = "KPSC" + datetime.now().strftime("%d%m%y")

            temp_pdf = tempfile.NamedTemporaryFile(
                delete=False,
                suffix=".pdf"
            )
            temp_pdf.close()

            doc = SimpleDocTemplate(temp_pdf.name)

            pdf_data = [self.columns]

            for row in self.rows:
                pdf_data.append(list(row))

            table = Table(pdf_data)

            table.setStyle(
                TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER')
                ])
            )

            doc.build([table])

            reader = PdfReader(temp_pdf.name)
            writer = PdfWriter()

            for page in reader.pages:
                writer.add_page(page)

            writer.encrypt(password)

            with open(file_name, "wb") as output_file:
                writer.write(output_file)

            if os.path.exists(temp_pdf.name):
                os.remove(temp_pdf.name)

            messagebox.showinfo(
                "Success",
                f"PDF exported successfully.\n\nPassword : {password}"
            )

        except Exception as ex:

            messagebox.showerror(
                "Export Error",
                str(ex)
            )

    # ====================================================
    # CLOSE
    # ====================================================

    def close_screen(self):
        self.root.destroy()