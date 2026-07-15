import os
import shutil
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import pandas as pd

from tkcalendar import DateEntry

import db_credentials


class CopyDiscrepancySheets:

    def __init__(self, root, user_id):
        self.root = root
        self.user_id = user_id

        self.root.title("Copy the Discrepancy Sheets")
        self.root.geometry("1400x800")
        self.root.configure(bg="#14141c")

        self.selected_folder = ""
        self.grid_data = []

        self.create_ui()
        self.load_subjects()

    def create_ui(self):

        header = tk.Label(
            self.root,
            text="Copy the Discrepancy Sheets",
            font=("Segoe UI", 18, "bold"),
            bg="#14141c",
            fg="#00e676"
        )
        header.pack(fill="x", pady=10)

        # Folder Panel
        folder_frame = tk.Frame(self.root, bg="#14141c")
        folder_frame.pack(fill="x", padx=10, pady=5)

        tk.Button(
            folder_frame,
            text="Select Folder",
            command=self.select_folder,
            width=15
        ).pack(side="left")

        self.lbl_folder = tk.Label(
            folder_frame,
            text="No Folder Selected",
            bg="#14141c",
            fg="white",
            anchor="w"
        )
        self.lbl_folder.pack(side="left", padx=10, fill="x", expand=True)

        self.btn_process = tk.Button(
            folder_frame,
            text="Process",
            command=self.start_copy
        )
        self.btn_process.pack(side="right")

        # Filter Panel
        filter_frame = tk.LabelFrame(
            self.root,
            text="Filter",
            padx=10,
            pady=10
        )
        filter_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(filter_frame, text="From Date").grid(row=0, column=0, padx=5)

        self.from_date = DateEntry(
            filter_frame,
            width=12,
            date_pattern="yyyy-mm-dd"
        )
        self.from_date.grid(row=0, column=1, padx=5)

        tk.Label(filter_frame, text="To Date").grid(row=0, column=2, padx=5)

        self.to_date = DateEntry(
            filter_frame,
            width=12,
            date_pattern="yyyy-mm-dd"
        )
        self.to_date.grid(row=0, column=3, padx=5)

        tk.Label(filter_frame, text="Subject").grid(row=0, column=4, padx=5)

        self.cmb_subject = ttk.Combobox(
            filter_frame,
            state="readonly",
            width=25
        )
        self.cmb_subject.grid(row=0, column=5, padx=5)

        tk.Button(
            filter_frame,
            text="Load",
            command=self.load_grid
        ).grid(row=0, column=6, padx=10)

        # Grid Panel

        grid_frame = tk.Frame(self.root)
        grid_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.tree = ttk.Treeview(grid_frame)

        vs = ttk.Scrollbar(
            grid_frame,
            orient="vertical",
            command=self.tree.yview
        )

        hs = ttk.Scrollbar(
            grid_frame,
            orient="horizontal",
            command=self.tree.xview
        )

        self.tree.configure(
            yscrollcommand=vs.set,
            xscrollcommand=hs.set
        )

        self.tree.grid(row=0, column=0, sticky="nsew")
        vs.grid(row=0, column=1, sticky="ns")
        hs.grid(row=1, column=0, sticky="ew")

        grid_frame.rowconfigure(0, weight=1)
        grid_frame.columnconfigure(0, weight=1)

        # Result Panel

        result_frame = tk.LabelFrame(
            self.root,
            text="Result"
        )
        result_frame.pack(fill="x", padx=10, pady=10)

        self.progress = ttk.Progressbar(
            result_frame,
            orient="horizontal",
            mode="determinate"
        )
        self.progress.pack(fill="x", padx=10, pady=5)

        self.lbl_progress = tk.Label(
            result_frame,
            text="0 / 0",
            anchor="w"
        )
        self.lbl_progress.pack(fill="x", padx=10)

        self.lbl_result = tk.Label(
            result_frame,
            text="",
            anchor="w"
        )
        self.lbl_result.pack(fill="x", padx=10, pady=5)

        bottom = tk.Frame(self.root)
        bottom.pack(fill="x", padx=10, pady=10)

        tk.Button(
            bottom,
            text="Close",
            command=self.close_form
        ).pack(side="right")

    def select_folder(self):
        folder = filedialog.askdirectory()

        if folder:
            self.selected_folder = folder
            self.lbl_folder.config(text=folder)

    def load_subjects(self):

        try:
            conn = db_credentials.get_sql_connection()

            sql = """
            Select distinct
                subject_code SubjectCode
            from CounterFoilData
            order by subject_code
            """

            df = pd.read_sql(sql, conn)

            self.cmb_subject["values"] = df["SubjectCode"].tolist()

            conn.close()

        except Exception as ex:
            messagebox.showerror("Error", str(ex))

    def load_grid(self):

        try:

            subject = self.cmb_subject.get()

            if not subject:
                messagebox.showwarning(
                    "Warning",
                    "Select Subject"
                )
                return

            conn = db_credentials.get_sql_connection()

            query = """
            EXEC usp_LoadFilesExportGrid ?, ?, ?
            """

            df = pd.read_sql(
                query,
                conn,
                params=[
                    str(self.from_date.get_date()),
                    str(self.to_date.get_date()),
                    subject
                ]
            )

            conn.close()

            self.grid_data = df

            self.tree.delete(*self.tree.get_children())

            self.tree["columns"] = list(df.columns)
            self.tree["show"] = "headings"

            for col in df.columns:
                self.tree.heading(col, text=col)
                self.tree.column(col, width=140)

            for _, row in df.iterrows():
                self.tree.insert(
                    "",
                    "end",
                    values=list(row)
                )

            self.lbl_result.config(
                text=f"{len(df)} record(s) loaded."
            )

        except Exception as ex:
            messagebox.showerror("Error", str(ex))

    def start_copy(self):

        if len(self.grid_data) == 0:
            messagebox.showwarning(
                "Warning",
                "No data loaded."
            )
            return

        if not self.selected_folder:
            messagebox.showwarning(
                "Warning",
                "Select destination folder."
            )
            return

        threading.Thread(
            target=self.process_copy,
            daemon=True
        ).start()

    def process_copy(self):

        try:

            total = len(self.grid_data)

            copied = 0
            failed = 0

            self.progress["maximum"] = total

            for index, row in self.grid_data.iterrows():

                file_name = str(row["Filename"])

                try:

                    if os.path.exists(file_name):

                        destination = os.path.join(
                            self.selected_folder,
                            os.path.basename(file_name)
                        )

                        shutil.copy2(
                            file_name,
                            destination
                        )

                        copied += 1

                    else:
                        failed += 1

                except Exception:
                    failed += 1

                current = index + 1

                self.progress["value"] = current

                self.lbl_progress.config(
                    text=f"{current} / {total}"
                )

                self.root.update_idletasks()

            self.lbl_result.config(
                text=f"Total : {total}   Copied : {copied}   Failed : {failed}"
            )

            messagebox.showinfo(
                "Completed",
                f"{copied} files copied successfully."
            )

        except Exception as ex:
            messagebox.showerror(
                "Error",
                str(ex)
            )

    def close_form(self):
        self.root.destroy()
