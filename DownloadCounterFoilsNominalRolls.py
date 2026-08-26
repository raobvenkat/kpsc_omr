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

    def __init__(self, parent, user_id):

        self.parent = parent
        self.user_id = user_id

        self.csv_file = None
        self.destination_folder = None
        self.df = pd.DataFrame()

        self.build_ui()

    # =====================================================
    # UI
    # =====================================================

    def build_ui(self):

        self.parent.title(
            "Download Counter Foils & Nominal Rolls Copies"
        )

        header = tk.Label(
            self.parent,
            text="Download Counter Foils & Nominal Rolls Copies",
            font=("Segoe UI", 16, "bold")
        )
        header.pack(pady=10)

        # Download Type

        option_Type_frame = tk.LabelFrame(
            self.parent,
            text="Download Type",
            font=("Segoe UI", 10, "bold"),
            padx=10,
            pady=5
        )
        option_Type_frame.pack(
            fill="x",
            padx=10,
            pady=5
        )

        self.download_For = tk.StringVar()
        self.download_For.set("Discrepancy")
        self.download_For.trace_add(
            "write",
            self.toggle_csv_upload
        )

        tk.Radiobutton(
            option_Type_frame,
            text="Discrepancy",
            variable=self.download_For,
            value="Discrepancy"
        ).pack(side="left", padx=10)

        tk.Radiobutton(
            option_Type_frame,
            text="Final Data",
            variable=self.download_For,
            value="FinalData"
        ).pack(side="left", padx=10)

        top_frame = tk.Frame(self.parent)
        top_frame.pack(fill="x", padx=10)

        # CSV Upload

        tk.Label(
            top_frame,
            text="CSV File to Upload",
            font=("Segoe UI", 10, "bold")
        ).grid(row=0, column=0, sticky="w", padx=5, pady=5)

        self.upload_csv_btn = tk.Button(
            top_frame,
            text="Upload CSV File",
            command=self.upload_csv
        )
        self.upload_csv_btn.grid(
            row=0,
            column=1,
            padx=5,
            pady=5
        )

        self.lbl_csv = tk.Label(
            top_frame,
            text="No file selected"
        )
        self.lbl_csv.grid(
            row=0,
            column=2,
            sticky="w"
        )

        # Destination Folder

        tk.Label(
            top_frame,
            text="Destination Folder",
            font=("Segoe UI", 10, "bold")
        ).grid(row=1, column=0, sticky="w", padx=5)

        tk.Button(
            top_frame,
            text="Select Folder",
            command=self.select_folder
        ).grid(row=1, column=1, padx=5)

        self.lbl_folder = tk.Label(
            top_frame,
            text="No folder selected"
        )
        self.lbl_folder.grid(
            row=1,
            column=2,
            sticky="w"
        )

        # Download Options

        option_frame = tk.LabelFrame(
            self.parent,
            text="Download Options",
            font=("Segoe UI", 10, "bold"),
            padx=10,
            pady=5
        )
        option_frame.pack(
            fill="x",
            padx=10,
            pady=5
        )

        self.download_type = tk.StringVar()
        self.download_type.set("Both")

        tk.Radiobutton(
            option_frame,
            text="Both",
            variable=self.download_type,
            value="Both"
        ).pack(side="left", padx=10)

        tk.Radiobutton(
            option_frame,
            text="Counter Foil",
            variable=self.download_type,
            value="CounterFoil"
        ).pack(side="left", padx=10)

        tk.Radiobutton(
            option_frame,
            text="Nominal Roll",
            variable=self.download_type,
            value="NominalRoll"
        ).pack(side="left", padx=10)

        # Grid

        grid_frame = tk.Frame(self.parent)
        grid_frame.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10
        )

        columns = (
            "SlNo",
            "RegNo",
            "SubjectCode",
            "CF Status",
            "NR Status"
        )

        self.tree = ttk.Treeview(
            grid_frame,
            columns=columns,
            show="headings"
        )

        tree_style = ttk.Style()
        tree_style.configure(
            "Treeview.Heading",
            font=("Segoe UI", 10, "bold")
        )

        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(
                col,
                width=150,
                anchor="center"
            )

        yscroll = ttk.Scrollbar(
            grid_frame,
            orient="vertical",
            command=self.tree.yview
        )

        self.tree.configure(
            yscrollcommand=yscroll.set
        )

        self.tree.pack(
            side="left",
            fill="both",
            expand=True
        )

        yscroll.pack(
            side="right",
            fill="y"
        )

        # Process Button

        btn_frame = tk.Frame(self.parent)
        btn_frame.pack(fill="x")

        self.process_btn = tk.Button(
            btn_frame,
            text="Process",
            width=20,
            command=self.start_process
        )

        self.process_btn.pack(
            pady=10
        )

        # Progress

        self.progress = ttk.Progressbar(
            self.parent,
            orient="horizontal",
            mode="determinate",
            length=700
        )

        self.progress.pack(
            padx=10,
            fill="x"
        )

        self.progress_label = tk.Label(
            self.parent,
            text="0 / 0"
        )

        self.progress_label.pack(
            pady=5
        )

        self.toggle_csv_upload()

    def toggle_csv_upload(self, *_):

        self.upload_csv_btn.config(
            state=(
                "disabled"
                if self.download_For.get() == "FinalData"
                else "normal"
            )
        )
    #--------------------------
    def get_counterfoil_all(self):
        conn = db_credentials.get_sql_connection()

        try:
            cursor = conn.cursor()

            cursor.execute(
                "EXEC USP_GetCounterFoilSheetAll @UserID=?",
                (self.user_id,)
            )

            columns = [col[0] for col in cursor.description]

            return [
                dict(zip(columns, row))
                for row in cursor.fetchall()
            ]

        finally:
            conn.close()

    #-----------------------
    def process_finaldata_counterfoil(self):

        try:
            records = self.get_counterfoil_all()

            if not records:
                messagebox.showwarning(
                    "Warning",
                    "No records found."
                )
                self.process_btn.config(state="normal")
                return

            # Load records into dataframe and grid
            self.df = pd.DataFrame(records)

            self.df["CF Status"] = "Pending"
            self.df["NR Status"] = "N/A"

            self.load_grid()

            total = len(self.df)

            self.progress["maximum"] = total
            self.progress["value"] = 0

            for index, row in self.df.iterrows():

                reg_no = str(row["RegNo"])
                subject_code = str(row["SubjectCode"])
                source_file = str(row["ImgFileName"])

                try:

                    if (
                        not source_file
                        or source_file == "No File"
                        or not os.path.exists(source_file)
                    ):
                        cf_status = "File Not Found"

                    else:

                        # Create Subject Folder
                        subject_folder = os.path.join(
                            self.destination_folder,
                            subject_code
                        )

                        os.makedirs(
                            subject_folder,
                            exist_ok=True
                        )

                        # Preserve source extension
                        extension = os.path.splitext(
                            source_file
                        )[1]

                        destination_file = os.path.join(
                            subject_folder,
                            f"{reg_no}{extension}"
                        )

                        shutil.copy2(
                            source_file,
                            destination_file
                        )

                        cf_status = "Copied"

                except Exception as ex:
                    cf_status = f"Error : {str(ex)}"

                # Update DataFrame
                self.df.at[index, "CF Status"] = cf_status

                # Update Grid
                self.update_row(
                    index,
                    cf_status,
                    "N/A"
                )

                current = index + 1

                self.progress["value"] = current

                self.progress_label.config(
                    text=f"Processing {current} / {total}"
                )

                self.parent.update_idletasks()

            messagebox.showinfo(
                "Completed",
                f"{total} Counter Foil files processed successfully."
            )

        except Exception as ex:

            messagebox.showerror(
                "Error",
                str(ex)
            )

        finally:

            self.process_btn.config(
                state="normal"
            )
    #-------------Nominal Roll All
    def get_nominalroll_all(self):
        conn = db_credentials.get_sql_connection()

        try:
            cursor = conn.cursor()

            cursor.execute(
                "EXEC USP_GetNominalRoll2All @UserID=?",
                (self.user_id,)
            )

            columns = [col[0] for col in cursor.description]

            return [
                dict(zip(columns, row))
                for row in cursor.fetchall()
            ]

        finally:
            conn.close()
    #---------------------------
    def process_finaldata_nominalroll(self):

        try:

            if self.df.empty:
                messagebox.showwarning(
                    "Warning",
                    "No records found."
                )
                return

            total = len(self.df)

            self.progress["maximum"] = total
            self.progress["value"] = 0

            for index, row in self.df.iterrows():

                reg_no = str(row["RegNo"])

                subject_code = str(row["SubjectCode"])

                center_code = str(row["Center_Code"]).zfill(2)

                subcenter_code = str(
                    row["SubCenter_Code"]
                ).zfill(2)

                source_file = str(row["ImgFileName"])

                try:

                    if (
                        not source_file
                        or source_file == "No File"
                        or not os.path.exists(source_file)
                    ):

                        process_status = "File Not Found"

                    else:

                        folder_name = (
                            f"{subject_code}_"
                            f"{center_code}_"
                            f"{subcenter_code}"
                        )

                        target_folder = os.path.join(
                            self.destination_folder,
                            folder_name
                        )

                        os.makedirs(
                            target_folder,
                            exist_ok=True
                        )

                        extension = os.path.splitext(
                            source_file
                        )[1]

                        destination_file = os.path.join(
                            target_folder,
                            f"{reg_no}{extension}"
                        )

                        shutil.copy2(
                            source_file,
                            destination_file
                        )

                        process_status = "Copied"

                except Exception as ex:

                    process_status = (
                        f"Error : {str(ex)}"
                    )

                # Update DataFrame
                self.df.at[
                    index,
                    "NR Status"
                ] = process_status

                # Update Grid
                self.update_row(
                    index,
                    "N/A",
                    process_status
                )

                current = index + 1

                self.progress["value"] = current

                self.progress_label.config(
                    text=f"Processing {current} / {total}"
                )

                self.parent.update_idletasks()

            messagebox.showinfo(
                "Completed",
                f"{total} Nominal Roll files processed successfully."
            )

        except Exception as ex:

            messagebox.showerror(
                "Error",
                str(ex)
            )

        finally:

            self.process_btn.config(
                state="normal"
            )

    #--------------------------------



    # -- loading to grid if final data selected.
    def load_finaldata_grid(self):
        records = self.get_counterfoil_all()

        self.df = pd.DataFrame(records)

        if not self.df.empty:
            self.df["CF Status"] = "Pending"
            self.df["NR Status"] = "N/A"

        self.load_grid()

    def load_finaldata_nominalroll_grid(self):
        records = self.get_nominalroll_all()

        self.df = pd.DataFrame(records)

        if not self.df.empty:
            self.df["CF Status"] = "N/A"
            self.df["NR Status"] = "Pending"

        self.load_grid()
    #  ---------------------------------------------
    #       
    # =====================================================
    # Upload CSV
    # =====================================================

    def upload_csv(self):

        file_path = filedialog.askopenfilename(
            filetypes=[
                ("CSV Files", "*.csv")
            ]
        )

        if not file_path:
            return

        self.csv_file = file_path

        self.lbl_csv.config(
            text=os.path.basename(file_path)
        )

        try:

            self.df = pd.read_csv(file_path)

            self.df["CF Status"] = "Pending"
            self.df["NR Status"] = "Pending"

            self.load_grid()

        except Exception as e:

            messagebox.showerror(
                "CSV Error",
                str(e)
            )

    def load_grid(self):

        self.tree.delete(
            *self.tree.get_children()
        )

        for _, row in self.df.iterrows():

            self.tree.insert(
                "",
                "end",
                values=(
                    row["SlNo"],
                    row["RegNo"],
                    row["SubjectCode"],
                    row["CF Status"],
                    row["NR Status"]
                )
            )

    # =====================================================
    # Select Folder
    # =====================================================

    def select_folder(self):

        folder = filedialog.askdirectory()

        if folder:

            self.destination_folder = folder

            self.lbl_folder.config(
                text=folder
            )

    # =====================================================
    # Start Thread
    # =====================================================

    def start_process(self):


        if self.download_For.get() != "FinalData":
            if self.df.empty:
                messagebox.showwarning(
                    "Warning",
                    "Upload CSV file"
                )
                return
        
        if not self.destination_folder:
            messagebox.showwarning(
                "Warning",
                "Select destination folder"
            )
            return

        if (
            self.download_For.get() == "FinalData"
            and self.download_type.get() == "CounterFoil"
        ):
            self.load_finaldata_grid()

        elif (
            self.download_For.get() == "FinalData"
            and self.download_type.get() == "NominalRoll"
        ):
            self.load_finaldata_nominalroll_grid()

            if self.df.empty:
                messagebox.showwarning(
                    "Warning",
                    "No records found."
                )
                return

        self.process_btn.config(
            state="disabled"
        )

        if (
            self.download_For.get() == "FinalData"
            and self.download_type.get() == "CounterFoil"
        ):

            threading.Thread(
                target=self.process_finaldata_counterfoil,
                daemon=True
            ).start()

        elif (
            self.download_For.get() == "FinalData"
            and self.download_type.get() == "NominalRoll"
        ):

            threading.Thread(
                target=self.process_finaldata_nominalroll,
                daemon=True
            ).start()

        else:

            threading.Thread(
                target=self.process_records,
                daemon=True
            ).start()

    # =====================================================
    # Database
    # =====================================================

    def get_counterfoil_file(
            self,
            reg_no,
            subject):

        conn = db_credentials.get_sql_connection()

        try:

            cursor = conn.cursor()

            cursor.execute(
                """
                EXEC USP_GetCounterFoilSheet
                     @RegNo=?,
                     @Subject=?,
                     @UserID=?
                """,
                (
                    str(reg_no),
                    str(subject),
                    self.user_id
                )
            )

            row = cursor.fetchone()

            if row:
                return str(row[0])

            return None

        finally:

            conn.close()

    def get_nominalroll_file(
            self,
            reg_no,
            subject):

        conn = db_credentials.get_sql_connection()

        try:

            cursor = conn.cursor()

            cursor.execute(
                """
                EXEC USP_GetNominalSheet
                     @RegNo=?,
                     @Subject=?,
                     @UserID=?
                """,
                (
                    str(reg_no),
                    str(subject),
                    self.user_id
                )
            )

            row = cursor.fetchone()

            if row:
                return str(row[0])

            return None

        finally:

            conn.close()

    # =====================================================
    # Copy File
    # =====================================================

    def copy_file(
            self,
            source_file,
            parent_folder,
            subject_code,
            reg_no):

        if not source_file:
            return "File Not Found"

        if not os.path.exists(source_file):
            return "File Not Found"

        extension = os.path.splitext(
            source_file
        )[1]

        target_folder = os.path.join(
            self.destination_folder,
            parent_folder,
            str(subject_code)
        )

        os.makedirs(
            target_folder,
            exist_ok=True
        )

        destination_file = os.path.join(
            target_folder,
            f"{reg_no}{extension}"
        )

        shutil.copy2(
            source_file,
            destination_file
        )

        return "Copied"

    # =====================================================
    # Processing
    # =====================================================

    def process_records(self):

        total = len(self.df)

        self.progress["maximum"] = total

        process_type = self.download_type.get()
        process_for = self.download_For.get()
        for index in range(total):

            row = self.df.iloc[index]

            reg_no = str(row["RegNo"])
            subject = str(row["SubjectCode"])

            cf_status = "N/A"
            nr_status = "N/A"

            # ====================================
            # Counter Foil Processing
            # ====================================

            if process_type in ("Both", "CounterFoil"):

                try:

                    source_cf = self.get_counterfoil_file(
                        reg_no,
                        subject
                    )

                    cf_status = self.copy_file(
                        source_cf,
                        "CounterFoil",
                        subject,
                        reg_no
                    )

                except Exception as ex:

                    cf_status = f"Error" + str(ex)
            # ====================================
            # Nominal Roll Processing
            # ====================================

            if process_type in ("Both", "NominalRoll"):

                try:

                    source_nr = self.get_nominalroll_file(
                        reg_no,
                        subject
                    )

                    nr_status = self.copy_file(
                        source_nr,
                        "NominalRoll",
                        subject,
                        reg_no
                    )

                except Exception:

                    nr_status = "Error"

            self.df.at[index, "CF Status"] = cf_status
            self.df.at[index, "NR Status"] = nr_status

            self.update_row(
                index,
                cf_status,
                nr_status
            )

            current = index + 1

            self.progress["value"] = current

            self.progress_label.config(
                text=f"Processing {current} / {total}"
            )

            self.parent.update_idletasks()

        self.process_btn.config(
            state="normal"
        )

        messagebox.showinfo(
            "Completed",
            f"{process_type} download completed successfully."
        )
        
    # =====================================================
    # Update Grid Row
    # =====================================================

    def update_row(
            self,
            index,
            cf_status,
            nr_status):

        item = self.tree.get_children()[index]

        values = list(
            self.tree.item(
                item,
                "values"
            )
        )

        values[3] = cf_status
        values[4] = nr_status

        self.tree.item(
            item,
            values=values
        )

if __name__ == "__main__":

    root = tk.Tk()

    app = DownloadCounterFoilsNominalRolls(root,user_id=1)

    root.mainloop()