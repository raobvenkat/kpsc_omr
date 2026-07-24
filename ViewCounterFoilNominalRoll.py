from __future__ import annotations

import os
import tkinter as tk

from tkinter import ttk
from tkinter import messagebox

from PIL import Image
from PIL import ImageTk

import db_credentials


class ScrollableImageViewer(tk.Frame):

    def __init__(self, parent):

        super().__init__(parent)

        self.image_path = None
        self.original_image = None
        self.photo = None
        self.zoom = 100

        self.toolbar = tk.Frame(self)
        self.toolbar.pack(fill="x")

        tk.Label(
            self.toolbar,
            text="Zoom %"
        ).pack(side="left", padx=5)

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

    def load_image(self, image_path):

        self.canvas.delete("all")

        if not image_path:
            return

        self.image_path = image_path

        self.original_image = Image.open(
            image_path
        )

        self.display_image()

    def change_zoom(self, event=None):

        self.zoom = int(
            self.zoom_var.get()
        )

        self.display_image()

    def display_image(self):

        if self.original_image is None:
            return

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

        self.photo = ImageTk.PhotoImage(img)

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
            cf_frame
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

            cf_image = str(row[0]).strip()
            nr_image = str(row[1]).strip()

            # Counter Foil

            if (
                cf_image.upper() != "NO FILE"
                and
                os.path.exists(cf_image)
            ):
                self.cf_viewer.load_image(
                    cf_image
                )
            else:
                self.cf_viewer.canvas.delete("all")

            # Nominal Roll

            if (
                nr_image.upper() != "NO FILE"
                and
                os.path.exists(nr_image)
            ):
                self.nr_viewer.load_image(
                    nr_image
                )
            else:
                self.nr_viewer.canvas.delete("all")

        except Exception as ex:

            messagebox.showerror(
                "Error",
                str(ex)
            )

if __name__ == "__main__":

    root = tk.Tk()

    app = ViewCounterFoilsNominalRolls(root,user_id=1)

    root.mainloop()