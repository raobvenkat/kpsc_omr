import os
import cv2
import shutil
import threading
import numpy as np

from tkinter import *
from tkinter import ttk, filedialog, messagebox

SUPPORTED_EXTENSIONS = (
    ".jpg", ".jpeg", ".png",
    ".bmp", ".tif", ".tiff"
)

DPI = 300
MM_TO_PX = DPI / 25.4

LEFT_MARGIN = int(5 * MM_TO_PX)
#TOP_MARGIN = int(2 * MM_TO_PX)
TOP_MARGIN = int(10 * MM_TO_PX)
RIGHT_MARGIN = int(5 * MM_TO_PX)
BOTTOM_MARGIN = int(10 * MM_TO_PX)


# ----- red tap mark removal
def remove_red_tape(img):

    hsv = cv2.cvtColor(
        img,
        cv2.COLOR_BGR2HSV
    )

    # Wider red/orange detection

    lower1 = np.array([0, 20, 80])
    upper1 = np.array([25, 255, 255])

    lower2 = np.array([160, 20, 80])
    upper2 = np.array([180, 255, 255])

    mask1 = cv2.inRange(
        hsv,
        lower1,
        upper1
    )

    mask2 = cv2.inRange(
        hsv,
        lower2,
        upper2
    )

    mask = cv2.bitwise_or(
        mask1,
        mask2
    )

    # Only check top-right region
    h, w = img.shape[:2]

    region = np.zeros(
        (h, w),
        dtype=np.uint8
    )

    region[
        0:int(h * 0.20),
        int(w * 0.80):w
    ] = 255

    mask = cv2.bitwise_and(
        mask,
        region
    )

    kernel = np.ones(
        (9, 9),
        np.uint8
    )

    mask = cv2.dilate(
        mask,
        kernel,
        iterations=3
    )

    result = img.copy()

    result[mask > 0] = (
        255,
        255,
        255
    )

    return result

# ------borders cleaning---------
def remove_scanner_borders(img):

    gray = cv2.cvtColor(
        img,
        cv2.COLOR_BGR2GRAY
    )

    # Anything darker than 80 becomes black
    _, thresh = cv2.threshold(
        gray,
        80,
        255,
        cv2.THRESH_BINARY
    )

    kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (7, 7)
    )

    thresh = cv2.morphologyEx(
        thresh,
        cv2.MORPH_CLOSE,
        kernel,
        iterations=2
    )

    result = img.copy()

    result[thresh == 0] = (255, 255, 255)

    return result
#-----------------
def deskew_image(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    coords = np.column_stack(np.where(gray < 200))

    if len(coords) < 100:
        return img

    angle = cv2.minAreaRect(coords)[-1]

    if angle < -45:
        angle = 90 + angle

    if angle > 15:
        angle = 15

    if angle < -15:
        angle = -15

    #h, w = img.shape[:2]
    # Force-clean top-right corner area

    h, w = img.shape[:2]

    img[
        0:int(h * 0.08),
        int(w * 0.95):w
    ] = (255, 255, 255)
    
    M = cv2.getRotationMatrix2D(
        (w // 2, h // 2),
        angle,
        1.0
    )

    return cv2.warpAffine(
        img,
        M,
        (w, h),
        borderValue=(255, 255, 255)
    )


def detect_form_border(img):

    gray = cv2.cvtColor(
        img,
        cv2.COLOR_BGR2GRAY
    )

    _, bw = cv2.threshold(
        gray,
        220,
        255,
        cv2.THRESH_BINARY_INV
    )

    h, w = bw.shape

    vertical_sum = np.sum(
        bw > 0,
        axis=0
    )

    horizontal_sum = np.sum(
        bw > 0,
        axis=1
    )

    # LEFT BORDER
    search_left = int(w * 0.25)

    left_candidates = np.where(
        vertical_sum[:search_left]
        > vertical_sum.max() * 0.35
    )[0]

    if len(left_candidates) == 0:
        raise Exception("Left border not found")

    left_x = left_candidates[0]

    # RIGHT BORDER
    search_right = int(w * 0.75)

    right_candidates = np.where(
        vertical_sum[search_right:]
        > vertical_sum.max() * 0.35
    )[0]

    if len(right_candidates) == 0:
        raise Exception("Right border not found")

    right_x = (
        right_candidates[-1]
        + search_right
    )

    # TOP BORDER
    top_candidates = np.where(
        horizontal_sum[:int(h * 0.25)]
        > horizontal_sum.max() * 0.35
    )[0]

    if len(top_candidates) == 0:
        raise Exception("Top border not found")

    #top_y = top_candidates[0]
    top_y = max(
    0,
    top_candidates[0] - 20
    )


    # BOTTOM BORDER
    bottom_start = int(h * 0.60)

    bottom_candidates = np.where(
        horizontal_sum[bottom_start:]
        > horizontal_sum.max() * 0.35
    )[0]

    if len(bottom_candidates) == 0:
        raise Exception("Bottom border not found")

    bottom_y = (
        bottom_candidates[-1]
        + bottom_start
    )

    return (
        left_x,
        top_y,
        right_x,
        bottom_y
    )

def validate_sheet_coverage(img):

    gray = cv2.cvtColor(
        img,
        cv2.COLOR_BGR2GRAY
    )

    _, bw = cv2.threshold(
        gray,
        245,
        255,
        cv2.THRESH_BINARY_INV
    )

    contours, _ = cv2.findContours(
        bw,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    if not contours:
        return False

    largest = max(
        contours,
        key=cv2.contourArea
    )

    x, y, w, h = cv2.boundingRect(
        largest
    )

    img_h, img_w = img.shape[:2]

    width_ratio = w / img_w
    height_ratio = h / img_h

    # Relaxed checks

    if width_ratio < 0.70:
        return False

    if height_ratio < 0.55:
        return False

    # Reject only if sheet is very low
    if y > img_h * 0.25:
        return False

    return True

def crop_sheet(img):

    original = img.copy()

    try:

        # -------------------------
        # DESKEW
        # -------------------------

        img = deskew_image(img)

        # -------------------------
        # REMOVE SCANNER BORDERS
        # -------------------------

        img = remove_scanner_borders(img)

        # -------------------------
        # REMOVE RED STICKER
        # -------------------------

        img = remove_red_tape(img)

        # -------------------------
        # VALIDATE SHEET POSITION
        # -------------------------

        gray = cv2.cvtColor(
            img,
            cv2.COLOR_BGR2GRAY
        )

        _, bw = cv2.threshold(
            gray,
            245,
            255,
            cv2.THRESH_BINARY_INV
        )

        contours, _ = cv2.findContours(
            bw,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        if not contours:
            raise Exception(
                "No sheet detected"
            )

        largest = max(
            contours,
            key=cv2.contourArea
        )

        x, y, w, h = cv2.boundingRect(
            largest
        )

        img_h, img_w = img.shape[:2]

        width_ratio = w / img_w
        height_ratio = h / img_h

        # Reject only badly scanned sheets

        if width_ratio < 0.55:
            raise Exception(
                "Sheet width too small"
            )

        if height_ratio < 0.40:
            raise Exception(
                "Sheet height too small"
            )

        # Reject huge blank scanner area above sheet
        if y > img_h * 0.35:
            raise Exception(
                "Large blank area above sheet"
            )

        # -------------------------
        # DETECT FORM BORDER
        # -------------------------

        left, top, right, bottom = \
            detect_form_border(img)

        crop_left = max(
            0,
            left - LEFT_MARGIN
        )

        crop_top = max(
            0,
            top - max(TOP_MARGIN, 40)
        )

        crop_right = min(
            img.shape[1],
            right + RIGHT_MARGIN
        )

        crop_bottom = min(
            img.shape[0],
            bottom + BOTTOM_MARGIN
        )

        # -------------------------
        # PARTIAL CROP CHECK
        # -------------------------

        crop_width = (
            crop_right - crop_left
        )

        crop_height = (
            crop_bottom - crop_top
        )
        width_ratio = crop_width / img.shape[1]

        if width_ratio < 0.85:
            raise Exception(
                "Internal divider detected"
            )

        if crop_width < img.shape[1] * 0.60:
            raise Exception(
                "Partial crop width"
            )

        if crop_height < img.shape[0] * 0.50:
            raise Exception(
                "Partial crop height"
            )
        # Subject code protection

        if crop_top > 50:

            raise Exception(
                "Top portion removed"
            )
        # -------------------------
        # KEEP ONLY CROP AREA
        # -------------------------

        result = np.full_like(
            img,
            255
        )

        result[
            crop_top:crop_bottom,
            crop_left:crop_right
        ] = img[
            crop_top:crop_bottom,
            crop_left:crop_right
        ]

        cropped = result[
            crop_top:crop_bottom,
            crop_left:crop_right
        ]

        # -------------------------
        # REMOVE TOP DOTTED LINE
        # -------------------------

        dot_height = min(
            int(10 * MM_TO_PX),
            cropped.shape[0]
        )

        cropped[
            0:dot_height,
            :
        ] = 255

        return cropped, "cropped"

    except Exception as ex:

        raise Exception(str(ex))


class CropApplication:

    def __init__(self, root):

        self.root = root

        root.title(
            "Clean & Crop the Images"
        )

        root.geometry("750x280")

        self.folder_path = StringVar()

        Label(
            root,
            text="Source Folder"
        ).pack(pady=10)

        frame = Frame(root)

        frame.pack(fill=X, padx=10)

        Entry(
            frame,
            textvariable=self.folder_path
        ).pack(
            side=LEFT,
            fill=X,
            expand=True
        )

        Button(
            frame,
            text="Browse",
            command=self.select_folder
        ).pack(side=LEFT, padx=5)

        btn_frame = Frame(root)

        btn_frame.pack(pady=15)

        Button(
            btn_frame,
            text="Preview Crop",
            width=15,
            command=self.preview_crop
        ).pack(side=LEFT, padx=5)

        Button(
            btn_frame,
            text="Process",
            width=15,
            command=self.start_process
        ).pack(side=LEFT, padx=5)

        Button(
            btn_frame,
            text="Close",
            width=15,
            command=root.destroy
        ).pack(side=LEFT, padx=5)

        self.progress = ttk.Progressbar(
            root,
            length=650
        )

        self.progress.pack(pady=10)

        self.status = Label(
            root,
            text="Ready"
        )

        self.status.pack()

    def select_folder(self):

        folder = filedialog.askdirectory()

        if folder:
            self.folder_path.set(folder)

    def preview_crop(self):

        folder = self.folder_path.get()

        if not folder:
            return

        for root_dir, _, files in os.walk(folder):

            for file in files:

                if file.lower().endswith(
                    SUPPORTED_EXTENSIONS
                ):

                    path = os.path.join(
                        root_dir,
                        file
                    )

                    img = cv2.imread(path)

                    if img is None:
                        continue

                    try:

                        left, top, right, bottom = \
                            detect_form_border(img)

                        preview = img.copy()

                        cv2.rectangle(
                            preview,
                            (left, top),
                            (right, bottom),
                            (0, 255, 255),
                            3
                        )

                        cv2.imshow(
                            "Crop Preview",
                            preview
                        )

                        cv2.waitKey(0)
                        cv2.destroyAllWindows()

                    except Exception as ex:

                        messagebox.showerror(
                            "Preview Error",
                            str(ex)
                        )

                    return

    def start_process(self):

        threading.Thread(
            target=self.process_folder,
            daemon=True
        ).start()

    def process_folder(self):

        folder = self.folder_path.get()

        if not folder:
            return

        processed_dir = os.path.join(
            folder,
            "Processed"
        )

        error_dir = os.path.join(
            folder,
            "ProcessedError"
        )

        os.makedirs(
            processed_dir,
            exist_ok=True
        )

        os.makedirs(
            error_dir,
            exist_ok=True
        )

        files = []

        for root_dir, _, names in os.walk(folder):

            if root_dir.startswith(processed_dir):
                continue

            if root_dir.startswith(error_dir):
                continue

            for f in names:

                if f.lower().endswith(
                    SUPPORTED_EXTENSIONS
                ):
                    files.append(
                        os.path.join(root_dir, f)
                    )

        total = len(files)

        processed = 0
        fallback = 0
        errors = 0

        self.progress["maximum"] = total

        processed = 0
        fallback = 0
        errors = 0

        log_file = os.path.join(
            folder,
            "ProcessingErrors.txt"
        )

        for i, file in enumerate(files, start=1):

            try:

                img = cv2.imread(file)

                if img is None:

                    shutil.copy2(
                        file,
                        os.path.join(
                            error_dir,
                            os.path.basename(file)
                        )
                    )

                    with open(
                        log_file,
                        "a",
                        encoding="utf-8"
                    ) as f:

                        f.write(
                            f"{file} : Cannot read image\n"
                        )

                    errors += 1

                    continue

                result_img, status = crop_sheet(img)

                output_file = os.path.join(
                    processed_dir,
                    os.path.basename(file)
                )

                cv2.imwrite(
                    output_file,
                    result_img
                )

                if status == "cropped":
                    processed += 1
                else:
                    fallback += 1

            except Exception as ex:

                try:

                    shutil.copy2(
                        file,
                        os.path.join(
                            error_dir,
                            os.path.basename(file)
                        )
                    )

                except:
                    pass

                with open(
                    log_file,
                    "a",
                    encoding="utf-8"
                ) as f:

                    f.write(
                        f"{file} : {str(ex)}\n"
                    )

                errors += 1

            self.progress["value"] = i

            self.status.config(
                text=f"Processing {i}/{total}"
            )

            self.root.update_idletasks()

        messagebox.showinfo(
            "Completed",
            f"Processed : {processed}\n"
            f"Fallback : {fallback}\n"
            f"Errors : {errors}"
        )


if __name__ == "__main__":

    root = Tk()

    CropApplication(root)

    root.mainloop()