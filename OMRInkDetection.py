import os
import cv2
import numpy as np
import tkinter as tk

from tkinter import ttk
from tkinter import filedialog

import db_credentials

from ink_detection import classify_ink_type


class OMRInkDetection:

    PAGE_SIZE = 100

    def __init__(self, root, user_id):

        self.root = root
        self.user_id = user_id

        self.root.title(
            "Pencil & Blue ink detection for OMR Bubble"
        )

        try:
            self.root.state("zoomed")
        except:
            self.root.geometry("1600x900")

        self.selected_folder = tk.StringVar()
        self.message_var = tk.StringVar()

        self.create_controls()

    # --------------------------------------------------
    # UI
    # --------------------------------------------------

    def create_controls(self):

        header = tk.Label(
            self.root,
            text="Pencil & Blue ink detection for OMR Bubble",
            font=("Segoe UI", 18, "bold"),
            bg="#0D47A1",
            fg="white",
            pady=10
        )

        header.pack(fill="x")

        control_frame = ttk.LabelFrame(
            self.root,
            text="Control Panel"
        )

        control_frame.pack(
            fill="x",
            padx=5,
            pady=5
        )

        ttk.Button(
            control_frame,
            text="Select Folder",
            command=self.select_folder
        ).grid(
            row=0,
            column=0,
            padx=5,
            pady=5
        )

        ttk.Label(
            control_frame,
            textvariable=self.selected_folder,
            width=100
        ).grid(
            row=0,
            column=1,
            padx=5,
            pady=5,
            sticky="w"
        )

        ttk.Button(
            control_frame,
            text="Process",
            command=self.process_folder
        ).grid(
            row=0,
            column=2,
            padx=5
        )

        # ------------------------------------
        # Result Panel
        # ------------------------------------

        result_frame = ttk.LabelFrame(
            self.root,
            text="Result Panel"
        )

        result_frame.pack(
            fill="both",
            expand=True,
            padx=5,
            pady=5
        )

        columns = (
            "ID",
            "FileName",
            "InkType",
            "CreatedDate",
            "UserID"
        )

        self.grid = ttk.Treeview(
            result_frame,
            columns=columns,
            show="headings"
        )

        for col in columns:

            self.grid.heading(
                col,
                text=col
            )

            self.grid.column(
                col,
                width=200,
                anchor="center"
            )

        self.grid.pack(
            fill="both",
            expand=True,
            padx=5,
            pady=5
        )

        self.progress = ttk.Progressbar(
            result_frame,
            mode="determinate"
        )

        self.progress.pack(
            fill="x",
            padx=5,
            pady=5
        )

        ttk.Label(
            result_frame,
            textvariable=self.message_var,
            font=("Segoe UI", 12, "bold")
        ).pack(
            fill="x",
            padx=5,
            pady=5
        )

    # --------------------------------------------------
    # Folder Selection
    # --------------------------------------------------

    def select_folder(self):

        folder = filedialog.askdirectory()

        if folder:
            self.selected_folder.set(folder)

    # --------------------------------------------------
    # Bubble Detection
    # --------------------------------------------------

    def detect_sheet_ink(self, image_path):

        image = cv2.imread(image_path)

        if image is None:
            return "Unknown"

        h, w = image.shape[:2]

        x1 = int(w * 0.60)
        x2 = int(w * 0.96)

        y1 = int(h * 0.34)
        y2 = int(h * 0.74)

        bubble_block = image[
            y1:y2,
            x1:x2
        ]

        rows = 10
        cols = 9

        block_h, block_w = bubble_block.shape[:2]

        cell_h = block_h / rows
        cell_w = block_w / cols

        detected_types = []

        for col in range(cols):

            best_score = 0
            best_crop = None

            for row in range(rows):

                sx1 = int(col * cell_w)
                sx2 = int((col + 1) * cell_w)

                sy1 = int(row * cell_h)
                sy2 = int((row + 1) * cell_h)

                cell = bubble_block[
                    sy1:sy2,
                    sx1:sx2
                ]

                gray = cv2.cvtColor(
                    cell,
                    cv2.COLOR_BGR2GRAY
                )

                dark_pixels = np.sum(
                    gray < 160
                )

                if dark_pixels > best_score:

                    best_score = dark_pixels
                    best_crop = cell

            if best_score > 80:

                ink_type = classify_ink_type(
                    best_crop
                )

                detected_types.append(
                    ink_type
                )

        if not detected_types:
            return "Empty"

        unique_types = set(
            detected_types
        )

        if len(unique_types) == 1:
            return list(unique_types)[0]

        if "Blue Pen" in unique_types:
            return "Mixed"

        if "Pencil" in unique_types:
            return "Mixed"

        return detected_types[0]

    # --------------------------------------------------
    # Database
    # --------------------------------------------------

    def save_result(
        self,
        filename,
        ink_type
    ):

        conn = db_credentials.get_sql_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO OMRInkDetection
            (
                FileName,
                InkType,
                CreatedDate,
                AddUserID
            )
            VALUES
            (
                ?,
                ?,
                GETDATE(),
                ?
            )
            """,
            (
                filename,
                ink_type,
                self.user_id
            )
        )

        conn.commit()

        cursor.execute(
            "SELECT @@IDENTITY"
        )

        record_id = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        return record_id

    # --------------------------------------------------
    # Processing
    # --------------------------------------------------

    def process_folder(self):

        folder = self.selected_folder.get()

        if not folder:

            self.message_var.set(
                "Please select folder."
            )

            return

        files = []

        for file in os.listdir(folder):

            if file.lower().endswith(
                (
                    ".jpg",
                    ".jpeg",
                    ".png",
                    ".bmp",
                    ".tif",
                    ".tiff"
                )
            ):
                files.append(
                    os.path.join(folder, file)
                )

        if not files:

            self.message_var.set(
                "No image files found."
            )

            return

        self.grid.delete(
            *self.grid.get_children()
        )

        self.progress["maximum"] = len(files)
        self.progress["value"] = 0

        processed = 0

        for filepath in files:

            try:

                filename = os.path.basename(
                    filepath
                )

                ink_type = self.detect_sheet_ink(
                    filepath
                )

                rec_id = self.save_result(
                    filename,
                    ink_type
                )

                self.grid.insert(
                    "",
                    "end",
                    values=
                    (
                        rec_id,
                        filename,
                        ink_type,
                        "",
                        self.user_id
                    )
                )

                processed += 1

                self.progress["value"] = processed

                self.root.update_idletasks()

            except Exception as ex:

                print(
                    filename,
                    ex
                )

        self.message_var.set(
            f"{processed} files processed and imported successfully."
        )