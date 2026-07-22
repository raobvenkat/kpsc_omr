import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd
import db_credentials


class ImportMasterData:

    def __init__(self, root, user_id):

        self.root = root
        self.user_id = user_id
        self.csv_file = ""

        self.root.title("IMPORT MASTER DATA")
        self.root.geometry("900x250")
        self.root.resizable(False, False)
        self.root.configure(bg="#14141c")

        self.build_ui()

    def build_ui(self):

        title_lbl = tk.Label(
            self.root,
            text="IMPORT MASTER DATA",
            font=("Segoe UI", 18, "bold"),
            fg="#00e676",
            bg="#14141c"
        )
        title_lbl.pack(pady=15)

        browse_frame = tk.Frame(self.root, bg="#14141c")
        browse_frame.pack(pady=10, fill="x", padx=20)

        btn_browse = tk.Button(
            browse_frame,
            text="Select CSV File",
            width=18,
            command=self.select_csv_file
        )
        btn_browse.pack(side="left")

        self.lbl_file = tk.Label(
            browse_frame,
            text="No file selected",
            width=90,
            anchor="w",
            relief="sunken",
            bg="white"
        )
        self.lbl_file.pack(side="left", padx=10, fill="x", expand=True)

        button_frame = tk.Frame(self.root, bg="#14141c")
        button_frame.pack(pady=25)

        self.btn_import = tk.Button(
            button_frame,
            text="Import",
            width=15,
            state="disabled",
            bg="#00c853",
            fg="white",
            command=self.import_data
        )
        self.btn_import.grid(row=0, column=0, padx=10)

        btn_close = tk.Button(
            button_frame,
            text="Close",
            width=15,
            bg="#d32f2f",
            fg="white",
            command=self.root.destroy
        )
        btn_close.grid(row=0, column=1, padx=10)

    def select_csv_file(self):

        filename = filedialog.askopenfilename(
            title="Select CSV File",
            filetypes=[("CSV Files", "*.csv")]
        )

        if filename:
            self.csv_file = filename
            self.lbl_file.config(text=filename)
            self.btn_import.config(state="normal")


    # if table is not there then it has to create it
    def create_master_table_if_not_exists(self, cursor):

        cursor.execute("""
        IF NOT EXISTS (
            SELECT *
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = 'MASERDATA'
        )
        BEGIN

            CREATE TABLE dbo.MASERDATA
            (
                SlNo            INT IDENTITY(1,1) NOT NULL,
                Registration_Number VARCHAR(20)   NOT NULL,
                CentreCode      VARCHAR(10)        NOT NULL,
                SubCentreCode   VARCHAR(10)        NOT NULL,
                SubjectCode     VARCHAR(10)        NOT NULL,
                AddedBy         INT                NULL,
                AddedDate       DATETIME           NULL,
                CONSTRAINT [PK_MASERDATA] PRIMARY KEY CLUSTERED (SlNo ASC)
            ) ON [PRIMARY]

        END
        """)
    def import_data(self):

        if not self.csv_file:
            messagebox.showwarning(
                "Warning",
                "Please select CSV file."
            )
            return

        try:

            df = pd.read_csv(self.csv_file)

            conn = db_credentials.get_sql_connection()
            cursor = conn.cursor()
            
            # Create table if not exists
            self.create_master_table_if_not_exists(cursor)
            conn.commit()

            #if messagebox.askyesno(
            #    "Confirm Import",
            #    "Delete existing records from MASERDATA and import new records?"
            #):

            #    cursor.execute("DELETE FROM MASERDATA")
            #    conn.commit()

            #else:
            #    return

            insert_sql = """
            INSERT INTO MASERDATA
            (
                Registration_Number,
                CentreCode,
                SubCentreCode,
                SubjectCode,
                AddedBy,
                AddedDate
            )
            VALUES
            (
                ?,?,?,?,?,
                GETDATE()
            )
            """

            record_count = 0

            for _, row in df.iterrows():

                cursor.execute(
                    insert_sql,
                    str(row.get("Registration Number", "")),
                    str(row.get("Centre Code", "")),
                    str(row.get("Sub Centre Code", "")),
                    str(row.get("Subject Code", "")),
                    self.user_id
                )

                record_count += 1

            conn.commit()
            cursor.close()
            conn.close()

            messagebox.showinfo(
                "Import Successful",
                f"{record_count} record(s) imported successfully."
            )

        except Exception as ex:

            try:
                conn.rollback()
            except:
                pass

            messagebox.showerror(
                "Import Failed",
                str(ex)
            )


if __name__ == "__main__":

    root = tk.Tk()

    # Test UserID
    ImportMasterData(root, 1)

    root.mainloop()