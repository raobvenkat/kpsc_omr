from __future__ import annotations

import os
import shutil
import threading
import pandas as pd
import tkinter as tk

from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox

import db_credentials


class DownloadCounterFoilsNominalRolls:

    def __init__(self, root, user_id):

        self.root = root
        self.user_id = user_id

        self.df = pd.DataFrame()
        self.csv_file = ""
        self.destination_folder = ""

        self.build_ui()

    # =====================================================
    # UI
    # =====================================================

    def build_ui(self):

        self.root.title(
            "Download Counter Foils & Nominal Rolls Copies"
        )

        self.root.configure(bg="white")

        header = tk.Label(
            self.root,
            text="Download Counter Foils & Nominal Rolls Copies",
            font=("Segoe UI", 16, "bold"),
            bg="white"
        )
        header.pack(pady=10)

        top_frame = tk.Frame(self.root, bg="white")
        top_frame.pack(fill="x", padx=10)

        # CSV Upload

        tk.Label(
            top_frame,
            text="CSV File To Upload",
            font=("Segoe UI", 10, "bold"),
            bg="white"
        ).grid(row=0, column=0, sticky="w", pady=5)

        tk.Button(
            top_frame,
            text="Upload CSV File",
            command=self.upload_csv,
            width=20
        ).grid(row=0, column=1, padx=5)

        # Destination Folder

        tk.Label(
            top_frame,
            text="Destination Folder",
            font=("Segoe UI", 10, "bold"),
            bg="white"
        ).grid(row=1, column=0, sticky="w", pady=5)

        tk.Button(
            top_frame,
            text="Select Folder",
            command=self.select_folder,
            width=20
        ).grid(row=1, column=1, padx=5)

        self.lbl_folder = tk.Label(
            top_frame,
            text="",
            anchor="w",
            bg="white",
            fg="blue"
        )

        self.lbl_folder.grid(
            row=1,
            column=2,
            sticky="w",
            padx=5
        )

        # Grid

        frame_grid = tk.Frame(self.root)
        frame_grid.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10
        )

        columns = (
            "SlNo",
            "RegNo",
            "CF Status",
            "NR Status"
        )

        self.grid = ttk.Treeview(
            frame_grid,
            columns=columns,
            show="headings"
        )

        vsb = ttk.Scrollbar(
            frame_grid,
            orient="vertical",
            command=self.grid.yview
        )

        self.grid.configure(
            yscrollcommand=vsb.set
        )

        self.grid.heading("SlNo", text="SlNo")
        self.grid.heading("RegNo", text="RegNo")
        self.grid.heading("CF Status", text="CF Status")
        self.grid.heading("NR Status", text="NR Status")

        self.grid.column("SlNo", width=100)
        self.grid.column("RegNo", width=200)
        self.grid.column("CF Status", width=250)
        self.grid.column("NR Status", width=250)

        self.grid.pack(
            side="left",
            fill="both",
            expand=True
        )

        vsb.pack(
            side="right",
            fill="y"
        )

        # Process Button

        self.btn_process = tk.Button(
            self.root,
            text="Process",
            font=("Segoe UI", 10, "bold"),
            bg="green",
            fg="white",
            width=20,
            command=self.start_process
        )

        self.btn_process.pack(pady=5)

        # Progress Bar

        self.progress = ttk.Progressbar(
            self.root,
            orient="horizontal",
            mode="determinate"
        )

        self.progress.pack(
            fill="x",
            padx=10,
            pady=5
        )

        self.lbl_progress = tk.Label(
            self.root,
            text="0 / 0",
            bg="white"
        )

        self.lbl_progress.pack(pady=5)

    # =====================================================
    # DATABASE
    # =====================================================

    def get_connection(self):

        try:
            return db_credentials.get_sql_connection()

        except Exception as ex:

            raise Exception(
                f"Database Connection Error : {str(ex)}"
            )

    # =====================================================
    # CSV
    # =====================================================

    def upload_csv(self):

        try:

            file_name = filedialog.askopenfilename(
                title="Select CSV File",
                filetypes=[
                    ("CSV Files", "*.csv")
                ]
            )

            if not file_name:
                return

            df = pd.read_csv(file_name)

            if "SlNo" not in df.columns:
                raise Exception(
                    "Column SlNo not found."
                )

            if "RegNo" not in df.columns:
                raise Exception(
                    "Column RegNo not found."
                )

            df["CF Status"] = ""
            df["NR Status"] = ""

            self.df = df

            self.load_grid()

            messagebox.showinfo(
                "Success",
                f"{len(df)} records loaded successfully."
            )

        except Exception as ex:

            messagebox.showerror(
                "CSV Upload Error",
                str(ex)
            )

    def load_grid(self):

        self.grid.delete(
            *self.grid.get_children()
        )

        for _, row in self.df.iterrows():

            self.grid.insert(
                "",
                "end",
                values=(
                    row["SlNo"],
                    row["RegNo"],
                    row["CF Status"],
                    row["NR Status"]
                )
            )

    # =====================================================
    # FOLDER
    # =====================================================

    def select_folder(self):

        folder = filedialog.askdirectory()

        if not folder:
            return

        self.destination_folder = folder

        self.lbl_folder.config(
            text=folder
        )

    # =====================================================
    # STORED PROCEDURE
    # =====================================================

    def execute_sp(
            self,
            proc_name,
            reg_no):

        conn = None

        try:

            conn = self.get_connection()

            cur = conn.cursor()

            cur.execute(
                f"EXEC {proc_name} ?, ?",
                reg_no,
                self.user_id
            )

            row = cur.fetchone()

            if row is None:
                return "No File"

            if row[0] is None:
                return "No File"

            filename = str(row[0]).strip()

            if filename == "":
                return "No File"

            return filename

        except Exception as ex:

            raise Exception(
                f"{proc_name} Error : {str(ex)}"
            )

        finally:

            if conn:
                try:
                    conn.close()
                except:
                    pass

    # =====================================================
    # FILE COPY
    # =====================================================

    def copy_file(
            self,
            source_file,
            destination_folder):

        try:

            if source_file is None:
                return "File Not Found"

            source_file = str(source_file).strip()

            if source_file.upper() == "NO FILE":
                return "File Not Found"

            if source_file == "":
                return "File Not Found"

            if not os.path.exists(source_file):
                return "File Not Found"

            os.makedirs(
                destination_folder,
                exist_ok=True
            )

            destination_file = os.path.join(
                destination_folder,
                os.path.basename(source_file)
            )

            shutil.copy2(
                source_file,
                destination_file
            )

            return "Copied File"

        except PermissionError:

            return "Permission Denied"

        except FileNotFoundError:

            return "File Not Found"

        except shutil.SameFileError:

            return "Already Exists"

        except Exception as ex:

            return f"Copy Failed : {str(ex)}"

    # =====================================================
    # PROCESS
    # =====================================================

    def start_process(self):

        if self.df.empty:

            messagebox.showwarning(
                "Warning",
                "Please upload CSV file."
            )
            return

        if not self.destination_folder:

            messagebox.showwarning(
                "Warning",
                "Please select destination folder."
            )
            return

        self.btn_process.config(
            state="disabled"
        )

        threading.Thread(
            target=self.process_records,
            daemon=True
        ).start()

    def process_records(self):

        try:

            total = len(self.df)

            self.progress["maximum"] = total
            self.progress["value"] = 0

            counterfoil_folder = os.path.join(
                self.destination_folder,
                "CounterFoil"
            )

            nominalroll_folder = os.path.join(
                self.destination_folder,
                "NominalRoll"
            )

            copied_count = 0

            for index, row in self.df.iterrows():

                reg_no = str(row["RegNo"]).strip()

                # Counter Foil

                try:

                    cf_file = self.execute_sp(
                        "USP_GetCounterFoilSheet",
                        reg_no
                    )

                    cf_status = self.copy_file(
                        cf_file,
                        counterfoil_folder
                    )

                except Exception as ex:

                    cf_status = str(ex)

                # Nominal Roll

                try:

                    nr_file = self.execute_sp(
                        "USP_GetNominalSheet",
                        reg_no
                    )

                    nr_status = self.copy_file(
                        nr_file,
                        nominalroll_folder
                    )

                except Exception as ex:

                    nr_status = str(ex)

                self.df.at[
                    index,
                    "CF Status"
                ] = cf_status

                self.df.at[
                    index,
                    "NR Status"
                ] = nr_status

                item = self.grid.get_children()[index]

                self.grid.item(
                    item,
                    values=(
                        row["SlNo"],
                        reg_no,
                        cf_status,
                        nr_status
                    )
                )

                if cf_status == "Copied File":
                    copied_count += 1

                if nr_status == "Copied File":
                    copied_count += 1

                current = index + 1

                self.progress["value"] = current

                self.lbl_progress.config(
                    text=f"{current} / {total}"
                )

                self.root.update_idletasks()

            self.btn_process.config(
                state="normal"
            )

            messagebox.showinfo(
                "Completed",
                f"""
Processing Completed.

Total Records : {total}

Files Copied : {copied_count}
"""
            )

        except Exception as ex:

            self.btn_process.config(
                state="normal"
            )

            messagebox.showerror(
                "Processing Error",
                str(ex)
            )


if __name__ == "__main__":

    root = tk.Tk()

    app = DownloadCounterFoilsNominalRolls(root,user_id=1)

    root.mainloop()