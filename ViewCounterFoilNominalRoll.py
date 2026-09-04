from __future__ import annotations

import os
import tkinter as tk

from tkinter import ttk
from tkinter import messagebox

from PIL import Image
from PIL import ImageTk

import db_credentials


class ScrollableImageViewer(tk.Frame):

    def __init__(self, parent, show_record_details=False):

        super().__init__(parent)
        self.configure(width=400, height=400)
        self.pack_propagate(False)

        self.image_path = None
        self.original_image = None
        self.photo = None
        self.zoom = 100
        self.status_var = tk.StringVar(value="No image loaded")
        self.record_details_var = tk.StringVar()

        self.toolbar = tk.Frame(self)
        self.toolbar.pack(fill="x")

        if show_record_details:
            tk.Label(
                self.toolbar,
                textvariable=self.record_details_var,
                anchor="w"
            ).pack(side="left", padx=5)

        tk.Label(
            self.toolbar,
            text="Zoom %"
        ).pack(side="left", padx=5)

        tk.Label(
            self.toolbar,
            textvariable=self.status_var,
            anchor="w"
        ).pack(side="left", fill="x", expand=True, padx=5)

        self.zoom_var = tk.StringVar()
        self.zoom_combo = ttk.Combobox(
            self.toolbar,
            textvariable=self.zoom_var,
            values=[
                "50",
                "75",
                "100",
                "125",
                "150",
                "200",
                "300",
                "400"
            ],
            width=8,
            state="readonly"
        )

        self.zoom_combo.set("100")
        self.zoom_combo.pack(side="left")

        self.zoom_combo.bind(
            "<<ComboboxSelected>>",
            self.change_zoom
        )

        self.canvas = tk.Canvas(
            self,
            bg="white"
        )

        self.h_scroll = ttk.Scrollbar(
            self,
            orient="horizontal",
            command=self.canvas.xview
        )

        self.v_scroll = ttk.Scrollbar(
            self,
            orient="vertical",
            command=self.canvas.yview
        )

        self.canvas.configure(
            xscrollcommand=self.h_scroll.set,
            yscrollcommand=self.v_scroll.set
        )

        self.canvas.pack(
            side="left",
            fill="both",
            expand=True
        )

        self.v_scroll.pack(
            side="right",
            fill="y"
        )

        self.h_scroll.pack(
            side="bottom",
            fill="x"
        )

    def set_record_details(self, reg_no, subject_code):

        self.record_details_var.set(
            f"RegNo: {reg_no} / SubjectCode: {subject_code}"
        )

    def load_image(self, image_path):

        self.canvas.delete("all")
        self.original_image = None
        self.photo = None
        self.image_path = None

        if not image_path:
            self.status_var.set("No image path returned")
            messagebox.showerror(
                "Image Load Error",
                "The database did not return an image path.",
                parent=self.winfo_toplevel()
            )
            return

        if isinstance(image_path, bytes):
            image_path = image_path.decode("utf-8", errors="replace")

        image_path = os.path.normpath(
            str(image_path).strip().strip('"')
        )

        if not os.path.isfile(image_path):
            error_text = f"Image file not found:\n{image_path}"
            self.status_var.set(error_text)
            self.canvas.create_text(
                20,
                20,
                text=error_text,
                anchor="nw"
            )
            messagebox.showerror(
                "Image Load Error",
                error_text,
                parent=self.winfo_toplevel()
            )
            return

        try:
            with Image.open(image_path) as image:
                self.original_image = image.convert("RGB")
            self.image_path = image_path
            self.status_var.set(os.path.basename(image_path))
            self.display_image()
        except Exception as exc:
            error_text = f"Unable to load image:\n{exc}"
            self.status_var.set(error_text)
            self.canvas.create_text(
                20,
                20,
                text=error_text,
                anchor="nw"
            )
            messagebox.showerror(
                "Image Load Error",
                error_text,
                parent=self.winfo_toplevel()
            )

    def change_zoom(self, event=None):

        self.zoom = int(
            self.zoom_var.get()
        )

        self.display_image()

    def display_image(self):

        if self.original_image is None:
            return

        self.canvas.update_idletasks()

        scale = self.zoom / 100

        w = int(
            self.original_image.width * scale
        )

        h = int(
            self.original_image.height * scale
        )

        img = self.original_image.resize(
            (w, h)
        )

        self.photo = ImageTk.PhotoImage(
            img,
            master=self.canvas
        )

        self.canvas.delete("all")

        self.canvas.create_image(
            0,
            0,
            image=self.photo,
            anchor="nw"
        )

        self.canvas.configure(
            scrollregion=(0, 0, w, h)
        )


class ViewCounterFoilNominalRoll:

    def __init__(self, root, user_id):

        self.root = root
        self.user_id = user_id

        self.root.title(
            "View Counter Foil & Nominal Roll"
        )

        self.build_ui()

    # =====================================================
    # DATABASE
    # =====================================================

    def get_connection(self):

        return db_credentials.get_sql_connection()

    # =====================================================
    # UI
    # =====================================================

    def build_ui(self):

        header = tk.Label(
            self.root,
            text="View Counter Foil & Nominal Roll for the candidate",
            font=("Segoe UI", 16, "bold")
        )

        header.pack(pady=10)

        search_frame = tk.Frame(self.root)
        search_frame.pack(
            fill="x",
            padx=10,
            pady=5
        )

        tk.Label(
            search_frame,
            text="Subject Code"
        ).grid(
            row=0,
            column=0,
            padx=5,
            pady=5,
            sticky="w"
        )

        self.txt_subcode = tk.Entry(
            search_frame,
            width=20
        )

        self.txt_subcode.grid(
            row=0,
            column=1
        )

        tk.Label(
            search_frame,
            text="Reg. No."
        ).grid(
            row=0,
            column=2,
            padx=(20, 5)
        )

        self.txt_regno = tk.Entry(
            search_frame,
            width=25
        )

        self.txt_regno.grid(
            row=0,
            column=3
        )

        self.btn_find = tk.Button(
            search_frame,
            text="Find",
            width=12,
            command=self.find_images
        )

        self.btn_find.grid(
            row=0,
            column=4,
            padx=10
        )

        image_frame = tk.Frame(self.root)
        image_frame.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10
        )

        # Counter Foil

        cf_frame = tk.LabelFrame(
            image_frame,
            text="Counter Foil"
        )

        cf_frame.pack(
            side="left",
            fill="both",
            expand=True,
            padx=5
        )

        self.cf_viewer = ScrollableImageViewer(
            cf_frame,
            show_record_details=True
        )

        self.cf_viewer.pack(
            fill="both",
            expand=True
        )

        # Nominal Roll

        nr_frame = tk.LabelFrame(
            image_frame,
            text="Nominal Roll"
        )

        nr_frame.pack(
            side="left",
            fill="both",
            expand=True,
            padx=5
        )

        self.nr_viewer = ScrollableImageViewer(
            nr_frame
        )

        self.nr_viewer.pack(
            fill="both",
            expand=True
        )

        bottom = tk.Frame(self.root)
        bottom.pack(
            fill="x",
            pady=10
        )

        tk.Button(
            bottom,
            text="Close",
            width=15,
            command=self.root.destroy
        ).pack()

    # =====================================================
    # FIND
    # =====================================================

    def find_images(self):

        sub_code = self.txt_subcode.get().strip()
        reg_no = self.txt_regno.get().strip()

        if not sub_code:

            messagebox.showwarning(
                "Validation",
                "Enter Subject Code"
            )

            return

        if not reg_no:

            messagebox.showwarning(
                "Validation",
                "Enter Reg. No."
            )

            return

        try:

            conn = self.get_connection()

            cursor = conn.cursor()

            cursor.execute(
                """
                EXEC usp_getCFNRImages ?, ?, ?
                """,
                sub_code,
                reg_no,
                self.user_id
            )

            row = cursor.fetchone()

            conn.close()

            if row is None:

                messagebox.showinfo(
                    "Information",
                    "No File"
                )

                return

            cf_image = self._database_path(row[0])
            nr_image = self._database_path(row[1])

            self.cf_viewer.set_record_details(
                "" if row[3] is None else row[3],
                "" if row[2] is None else row[2]
            )

            # Counter Foil

            if cf_image and cf_image.upper() != "NO FILE":
                self.cf_viewer.load_image(
                    cf_image
                )
            else:
                self.cf_viewer.original_image = None
                self.cf_viewer.canvas.delete("all")

            # Nominal Roll

            if nr_image and nr_image.upper() != "NO FILE":
                self.nr_viewer.load_image(
                    nr_image
                )
            else:
                self.nr_viewer.original_image = None
                self.nr_viewer.canvas.delete("all")

        except Exception as ex:

            messagebox.showerror(
                "Error",
                str(ex)
            )

    @staticmethod
    def _database_path(value):

        if value is None:
            return ""

        if isinstance(value, bytes):
            value = os.fsdecode(value)

        return os.path.normpath(
            str(value).strip().strip('"')
        )

if __name__ == "__main__":

    root = tk.Tk()

    app = ViewCounterFoilNominalRoll(root, user_id=1)

    root.mainloop()