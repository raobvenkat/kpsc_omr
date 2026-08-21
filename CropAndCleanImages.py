import os
import cv2
import shutil
import threading
import numpy as np
import tkinter as tk

from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox


class CropCleanApp:

    def __init__(self, root):

        self.root = root
        self.root.title("Crop & Clean the Image")
        self.root.geometry("850x350")
        self.root.resizable(False, False)

        self.folder_path = tk.StringVar()
        self.current_folder = tk.StringVar()
        self.current_file = tk.StringVar()

        self.create_ui()

    def create_ui(self):

        title = ttk.Label(
            self.root,
            text="Crop & Clean the Image",
            font=("Arial", 16, "bold")
        )
        title.pack(pady=10)

        frame = ttk.Frame(self.root, padding=10)
        frame.pack(fill="both", expand=True)

        top_frame = ttk.Frame(frame)
        top_frame.pack(fill="x")

        txt_folder = ttk.Entry(
            top_frame,
            textvariable=self.folder_path,
            width=90
        )
        txt_folder.pack(side="left", padx=5)

        btn_browse = ttk.Button(
            top_frame,
            text="Browse",
            command=self.select_folder
        )
        btn_browse.pack(side="left")

        ttk.Label(
            frame,
            text="Current Folder:"
        ).pack(anchor="w", pady=(20, 0))

        ttk.Label(
            frame,
            textvariable=self.current_folder,
            foreground="blue"
        ).pack(anchor="w")

        ttk.Label(
            frame,
            text="Current Image:"
        ).pack(anchor="w", pady=(15, 0))

        ttk.Label(
            frame,
            textvariable=self.current_file,
            foreground="green"
        ).pack(anchor="w")

        self.progress = ttk.Progressbar(
            frame,
            orient="horizontal",
            mode="determinate",
            length=750
        )

        self.progress.pack(pady=20)

        self.lbl_progress = ttk.Label(
            frame,
            text="0 / 0"
        )

        self.lbl_progress.pack()

        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=20)

        ttk.Button(
            button_frame,
            text="Process",
            width=15,
            command=self.start_process
        ).pack(side="left", padx=10)

        ttk.Button(
            button_frame,
            text="Close",
            width=15,
            command=self.root.destroy
        ).pack(side="left")

    def select_folder(self):

        folder = filedialog.askdirectory()

        if folder:
            self.folder_path.set(folder)
    def remove_scanner_drag_top(self, image):

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        row_mean = np.mean(gray, axis=1)

        crop_y = 0

        for y in range(min(image.shape[0] // 3, 1500)):

            if row_mean[y] > 220:

                consecutive = 0

                for yy in range(
                    y,
                    min(y + 40, len(row_mean))
                ):

                    if row_mean[yy] > 220:
                        consecutive += 1

                if consecutive > 25:
                    crop_y = y
                    break

        if crop_y > 0:
            return image[crop_y:, :], True

        return image, False



    def crop_document_contour(self, image):

        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY
        )

        blur = cv2.GaussianBlur(
                gray,
                (5, 5),
                0
            )

        thresh = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            35,
            15
        )

        contours, _ = cv2.findContours(
            thresh,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        if len(contours) == 0:
            return image, False

        page = max(
            contours,
            key=cv2.contourArea
        )

        x, y, w, h = cv2.boundingRect(
            page
        )

        margin = 10

        x = max(0, x - margin)
        y = max(0, y - margin)

        w = min(
            image.shape[1] - x,
            w + margin * 2
        )

        h = min(
            image.shape[0] - y,
            h + margin * 2
        )

        cropped = image[
            y:y+h,
            x:x+w
        ]

        changed = (
            x > 0 or
            y > 0 or
            w < image.shape[1] or
            h < image.shape[0]
        )

        return cropped, changed


    def deskew_image(self, image):

        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY
        )

        edges = cv2.Canny(
            gray,
            50,
            150
        )

        lines = cv2.HoughLinesP(
            edges,
            1,
            np.pi / 180,
            threshold=100,
            minLineLength=300,
            maxLineGap=20
        )

        if lines is None:
            return image, False

        angles = []

        for line in lines:

            x1, y1, x2, y2 = line[0]

            angle = np.degrees(
                np.arctan2(
                    y2 - y1,
                    x2 - x1
                )
            )

            if abs(angle) <= 15:
                angles.append(angle)

        if len(angles) == 0:
            return image, False

        angle = np.median(angles)

        if abs(angle) < 0.5:
            return image, False

        h, w = image.shape[:2]

        M = cv2.getRotationMatrix2D(
            (w // 2, h // 2),
            angle,
            1.0
        )

        rotated = cv2.warpAffine(
            image,
            M,
            (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE
        )

        return rotated, True


    def start_process(self):

        if not self.folder_path.get():

            messagebox.showerror(
                "Error",
                "Please select a folder."
            )
            return

        threading.Thread(
            target=self.process_folder,
            daemon=True
        ).start()

    # ----------------------------------
    # Remove Red Mark
    # ----------------------------------

    def remove_red_mark(self, image):

        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        lower_red1 = np.array([0, 70, 70])
        upper_red1 = np.array([10, 255, 255])

        lower_red2 = np.array([170, 70, 70])
        upper_red2 = np.array([180, 255, 255])

        mask1 = cv2.inRange(
            hsv,
            lower_red1,
            upper_red1
        )

        mask2 = cv2.inRange(
            hsv,
            lower_red2,
            upper_red2
        )

        red_mask = cv2.bitwise_or(
            mask1,
            mask2
        )

        h, w = image.shape[:2]

        roi = np.zeros_like(red_mask)

        roi[
            :int(h * 0.15),
            int(w * 0.85):
        ] = 255

        red_mask = cv2.bitwise_and(
            red_mask,
            roi
        )

        changed = np.count_nonzero(red_mask) > 0

        if changed:

            red_mask = cv2.dilate(
                red_mask,
                np.ones((5, 5), np.uint8),
                iterations=2
            )

            image = cv2.inpaint(
                image,
                red_mask,
                5,
                cv2.INPAINT_TELEA
            )

        return image, changed

    # ----------------------------------
    # Auto Crop Black Borders
    # ----------------------------------

    def crop_black_border(self, image):

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        row_mean = np.mean(gray, axis=1)
        col_mean = np.mean(gray, axis=0)

        threshold = 180

        top = 0
        for i in range(len(row_mean)):
            if row_mean[i] > threshold:
                top = i
                break

        bottom = len(row_mean) - 1
        for i in range(len(row_mean) - 1, -1, -1):
            if row_mean[i] > threshold:
                bottom = i
                break

        left = 0
        for i in range(len(col_mean)):
            if col_mean[i] > threshold:
                left = i
                break

        right = len(col_mean) - 1
        for i in range(len(col_mean) - 1, -1, -1):
            if col_mean[i] > threshold:
                right = i
                break

        margin = 5

        top = max(0, top - margin)
        left = max(0, left - margin)

        bottom = min(
            image.shape[0] - 1,
            bottom + margin
        )

        right = min(
            image.shape[1] - 1,
            right + margin
        )

        cropped = image[
            top:bottom + 1,
            left:right + 1
        ]

        changed = (
            top > 0 or
            left > 0 or
            right < image.shape[1] - 1 or
            bottom < image.shape[0] - 1
        )

        return cropped, changed

    # ----------------------------------
    # Process Single Image
    # ----------------------------------

    def process_image(self, image_path):

        image = cv2.imread(image_path)

        if image is None:
            raise Exception(
                f"Cannot read image: {image_path}"
            )

        image, scanner_changed = (
            self.remove_scanner_drag_top(image)
        )

        image, deskew_changed = (
            self.deskew_image(image)
        )

        image, border_changed = (
            self.crop_black_border(image)
        )

        image, red_changed = (
            self.remove_red_mark(image)
        )

        modified = any([
            scanner_changed,
            deskew_changed,
            border_changed,
            red_changed
        ])

        return image, modified

    # ----------------------------------
    # Get All Images Count
    # ----------------------------------

    def get_image_count(self, parent):

        extensions = (
            ".jpg",
            ".jpeg",
            ".png",
            ".bmp",
            ".tif",
            ".tiff"
        )

        total = 0

        for root, dirs, files in os.walk(parent):

            dirs[:] = [
                d for d in dirs
                if d not in (
                    "ProcessedImg",
                    "ProcessedError"
                )
            ]

            total += len([
                f for f in files
                if f.lower().endswith(extensions)
            ])

        return total

    # ----------------------------------
    # Main Processing
    # ----------------------------------

    def process_folder(self):

        source_root = self.folder_path.get()

        extensions = (
            ".jpg",
            ".jpeg",
            ".png",
            ".bmp",
            ".tif",
            ".tiff"
        )

        total_images = self.get_image_count(
            source_root
        )

        self.progress["maximum"] = total_images
        self.progress["value"] = 0

        processed = 0

        for folder, dirs, files in os.walk(source_root):

            dirs[:] = [
                d for d in dirs
                if d not in (
                    "ProcessedImg",
                    "ProcessedError"
                )
            ]

            image_files = [
                f for f in files
                if f.lower().endswith(extensions)
            ]

            if not image_files:
                continue

            processed_folder = os.path.join(
                folder,
                "ProcessedImg"
            )

            error_folder = os.path.join(
                folder,
                "ProcessedError"
            )

            os.makedirs(
                processed_folder,
                exist_ok=True
            )

            os.makedirs(
                error_folder,
                exist_ok=True
            )

            for file in image_files:

                input_file = os.path.join(
                    folder,
                    file
                )

                self.current_folder.set(folder)
                self.current_file.set(file)

                try:

                    processed_image, modified = (
                        self.process_image(
                            input_file
                        )
                    )

                    output_file = os.path.join(
                        processed_folder,
                        file
                    )

                    if modified:

                        saved = cv2.imwrite(
                            output_file,
                            processed_image
                        )

                        print(
                            f"File={file}"
                        )

                        print(
                            f"Modified={modified}"
                        )

                        print(
                            f"Saved={saved}"
                        )

                        if not saved:
                            raise Exception(
                                f"Unable to save {output_file}"
                            )

                    else:

                        shutil.copy2(
                            input_file,
                            output_file
                        )

                except Exception as ex:

                    print(
                        "Error:",
                        input_file,
                        str(ex)
                    )

                    shutil.copy2(
                        input_file,
                        os.path.join(
                            error_folder,
                            file
                        )
                    )

                processed += 1

                self.progress["value"] = processed

                self.lbl_progress.config(
                    text=f"{processed} / {total_images}"
                )

                self.root.update_idletasks()

        self.current_folder.set(
            "Completed"
        )

        self.current_file.set(
            f"Successfully processed {processed} images"
        )

        messagebox.showinfo(
            "Completed",
            f"Successfully processed {processed} images."
        )


# -----------------------------------------------------
# Application Start
# -----------------------------------------------------

if __name__ == "__main__":

    root = tk.Tk()

    app = CropCleanApp(root)

    root.mainloop()