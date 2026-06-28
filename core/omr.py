"""
core/omr.py
-----------
Production-ready OMR sheet processing module.

Features:
- Dynamic scaling: works for any image resolution, not hardcoded
- Dual-mode alignment:
    * Color OMRs: uses RED contour detection (handwritten box or header)
    * B&W OMRs: falls back to grayscale contour detection
- Bubble reading:
    * Single-mark   -> digit string e.g. "2004321 "
    * No mark       -> space  " "
    * Double-mark   -> "#"
- Signature detection: detects blue ink, dark ink; excludes red borders
"""

import os
import cv2
import numpy as np
from pyzbar.pyzbar import decode

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import get_omr_template


# ─────────────────────────────────────────────
# SIGNATURE DETECTION
# ─────────────────────────────────────────────

def check_ink_present(crop_img, ratio_threshold=0.002):
    """
    Detects handwriting (ink) in a cropped image region.

    Works for both color and B&W scans:
    - Color: looks for blue ink and dark non-red pixels
    - B&W: dark pixels that are not part of the printed border

    Returns:
        (bool: ink detected, float: ink ratio)
    """
    if crop_img is None or crop_img.size == 0:
        return False, 0.0

    gray = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)

    # Determine if this is B&W or color by checking saturation
    hsv = cv2.cvtColor(crop_img, cv2.COLOR_BGR2HSV)
    avg_saturation = np.mean(hsv[:, :, 1])
    is_bw = avg_saturation < 15  # Very low saturation => B&W scan

    if is_bw:
        # B&W: just look for dark pixels (pencil/pen both show as dark gray)
        # Use a slightly higher threshold to capture pencil marks
        _, dark_mask = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY_INV)

        # Remove thin horizontal/vertical lines (border artifacts)
        # Erode horizontally and vertically to find box borders
        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 1))
        v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 30))
        h_lines = cv2.morphologyEx(dark_mask, cv2.MORPH_OPEN, h_kernel)
        v_lines = cv2.morphologyEx(dark_mask, cv2.MORPH_OPEN, v_kernel)
        border_mask = cv2.bitwise_or(h_lines, v_lines)

        # Ink = dark pixels that are NOT border lines
        ink_mask = cv2.bitwise_and(dark_mask, cv2.bitwise_not(border_mask))

        # Remove small isolated noise
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        ink_mask = cv2.morphologyEx(ink_mask, cv2.MORPH_OPEN, kernel)
    else:
        # Color: look for blue ink + dark non-red pixels

        # Mask for blue ink (pen ink): H=90-140, S>30, V>20
        lower_blue = np.array([90, 30, 20])
        upper_blue = np.array([140, 255, 255])
        blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)

        # Mask for dark/black ink: very dark pixels
        _, dark_mask = cv2.threshold(gray, 80, 255, cv2.THRESH_BINARY_INV)

        # Red mask (to exclude printed borders/text): H=0-15 or H=165-180, S>40
        lower_red1 = np.array([0, 40, 40])
        upper_red1 = np.array([15, 255, 255])
        lower_red2 = np.array([165, 40, 40])
        upper_red2 = np.array([180, 255, 255])
        red_mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        red_mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        red_mask = cv2.bitwise_or(red_mask1, red_mask2)

        # Dark ink = dark pixels that are NOT red
        dark_ink_mask = cv2.bitwise_and(dark_mask, cv2.bitwise_not(red_mask))

        # Combine blue ink + dark non-red ink
        ink_mask = cv2.bitwise_or(blue_mask, dark_ink_mask)

        # Remove small noise
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        ink_mask = cv2.morphologyEx(ink_mask, cv2.MORPH_OPEN, kernel)

    total_pixels = ink_mask.size
    ink_pixels = np.sum(ink_mask > 0)
    ratio = ink_pixels / total_pixels if total_pixels > 0 else 0.0
    return bool(ratio > ratio_threshold), float(ratio)


# ─────────────────────────────────────────────
# GRID ALIGNMENT
# ─────────────────────────────────────────────

def _find_red_contour(right_half_img, w_min, h_min, w_max=None, h_max=None, y_min=None, y_max=None):
    """
    Internal helper: finds a contour matching size constraints in the right half of the image.
    First tries red (HSV) detection; falls back to grayscale for B&W scans.
    Returns (rel_x, rel_y, rw, rh) in right_half coordinates, or None.
    """
    hsv = cv2.cvtColor(right_half_img, cv2.COLOR_BGR2HSV)

    lower_red1 = np.array([0, 50, 50])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 50, 50])
    upper_red2 = np.array([180, 255, 255])
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    red_mask = cv2.bitwise_or(mask1, mask2)

    for use_gray in [False, True]:
        if use_gray:
            gray = cv2.cvtColor(right_half_img, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)
            contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        else:
            contours, _ = cv2.findContours(red_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        for c in contours:
            rx, ry, rw, rh = cv2.boundingRect(c)
            if rw < w_min:
                continue
            if w_max is not None and rw > w_max:
                continue
            if rh < h_min:
                continue
            if h_max is not None and rh > h_max:
                continue
            if y_min is not None and ry < y_min:
                continue
            if y_max is not None and ry > y_max:
                continue
            return rx, ry, rw, rh

    return None


def find_header_origin(img, tpl, scale_x, scale_y):
    """
    Locates the large red header box as a fallback grid origin reference.
    Works for both color (red contour) and B&W scans (grayscale fallback).

    Returns (abs_x, abs_y, rw, rh) or None.
    """
    h, w = img.shape[:2]
    right_half = img[:, w // 2:]

    h_conf = tpl["header_contour"]
    w_min = int(h_conf["w_min"] * scale_x * 0.85)
    h_min = int(h_conf["h_min"] * scale_y * 0.85)

    result = _find_red_contour(right_half, w_min=w_min, h_min=h_min)
    if result:
        rx, ry, rw, rh = result
        return (w // 2 + rx, ry, rw, rh)
    return None


def find_handwritten_box(img, tpl, scale_x, scale_y):
    """
    Locates the red border around the handwritten register number digit boxes.
    Works for both color and B&W scans.

    Returns (abs_x, abs_y, rw, rh) or None.
    """
    h, w = img.shape[:2]
    right_half = img[:, w // 2:]

    box_conf = tpl["handwritten_box_contour"]
    w_min = int(box_conf["w_min"] * scale_x * 0.85)
    w_max = int(box_conf["w_max"] * scale_x * 1.15)
    h_min = int(box_conf["h_min"] * scale_y * 0.85)
    h_max = int(box_conf["h_max"] * scale_y * 1.15)
    y_min = int(box_conf["y_min"] * scale_y * 0.85)
    y_max = int(box_conf["y_max"] * scale_y * 1.15)

    result = _find_red_contour(
        right_half,
        w_min=w_min, w_max=w_max,
        h_min=h_min, h_max=h_max,
        y_min=y_min, y_max=y_max
    )
    if result:
        rx, ry, rw, rh = result
        return (w // 2 + rx, ry, rw, rh)
    return None


# ─────────────────────────────────────────────
# BUBBLE READING
# ─────────────────────────────────────────────

def read_bubbles(img, tpl, scale_x, scale_y):
    """
    Reads the OMR bubble grid and returns the register number as a string.

    Rules:
    - Single bubble filled  -> digit character e.g. "3"
    - No bubble filled      -> space " "
    - Multiple bubbles filled -> "#" (double marking)

    Uses dynamic calibration:
    - Background value per column is the mean of the 4 brightest (unfilled) rows
    - A bubble is filled if its value is MORE than `double_mark_gap` darker than background
    - The threshold is relative, not a fixed global value => works for both color & B&W

    Returns:
        (bubble_regno_str, debug_grid_img, align_method_str)
    """
    # ── Step 1: Determine grid origin ──────────────────────────────────────────
    box = find_handwritten_box(img, tpl, scale_x, scale_y)
    if box:
        bx, by, bw, bh = box
        dx, dy = tpl["grid_offset_from_box"]
        grid_x = bx + int(dx * scale_x)
        grid_y = by + int(dy * scale_y)
        align_method = "boxes_contour"
    else:
        origin = find_header_origin(img, tpl, scale_x, scale_y)
        if origin:
            ox, oy, _, _ = origin
            dx, dy = tpl["grid_offset_from_header"]
            grid_x = ox + int(dx * scale_x)
            grid_y = oy + int(dy * scale_y)
            align_method = "header_origin"
        else:
            dx, dy = tpl["grid_hardcoded_fallback"]
            grid_x = int(dx * scale_x)
            grid_y = int(dy * scale_y)
            align_method = "hardcoded_fallback"

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    b_conf = tpl["bubble_grid"]
    cols = b_conf["cols"]
    rows = b_conf["rows"]
    r = int(max(3, b_conf["sample_radius"] * min(scale_x, scale_y)))

    col_xs = [
        int(grid_x + b_conf["col_start_offset"] * scale_x + i * b_conf["col_spacing"] * scale_x)
        for i in range(cols)
    ]
    row_ys = [
        int(grid_y + b_conf["row_start_offset"] * scale_y + j * b_conf["row_spacing"] * scale_y)
        for j in range(rows)
    ]

    img_draw = img.copy()
    detected_digits = []

    # ── Step 2: Read each column ────────────────────────────────────────────────
    # Dynamic threshold: background = mean of top 4 brightest values in column
    # A bubble is considered filled if: background - bubble_val > GAP_THRESHOLD
    GAP_THRESHOLD = 45  # Works for both color and B&W

    for i, cx in enumerate(col_xs):
        col_vals = []

        for j, cy in enumerate(row_ys):
            y1 = max(0, cy - r)
            y2 = min(gray.shape[0], cy + r)
            x1 = max(0, cx - r)
            x2 = min(gray.shape[1], cx + r)
            cell = gray[y1:y2, x1:x2]
            avg = float(np.mean(cell)) if cell.size > 0 else 255.0
            col_vals.append(avg)

        # Background = mean of 4 brightest (empty) values
        sorted_vals = sorted(col_vals, reverse=True)
        bg_val = float(np.mean(sorted_vals[:4]))

        filled_rows = [
            j for j, val in enumerate(col_vals)
            if bg_val - val > GAP_THRESHOLD
        ]

        if len(filled_rows) == 0:
            digit = " "
        elif len(filled_rows) == 1:
            digit = str(filled_rows[0])
        else:
            digit = "#"

        detected_digits.append(digit)

        # ── Draw debug overlay ─────────────────────────────────────────────
        for j, cy in enumerate(row_ys):
            if j in filled_rows:
                if len(filled_rows) > 1:
                    color = (0, 165, 255)  # Orange for double mark
                else:
                    color = (0, 255, 0)    # Green for single fill
                cv2.circle(img_draw, (cx, cy), int(10 * min(scale_x, scale_y)), color, -1)
            else:
                cv2.circle(img_draw, (cx, cy), int(6 * min(scale_x, scale_y)), (255, 0, 0), 1)

    bubble_regno = "".join(detected_digits)

    # ── Step 3: Crop debug image ────────────────────────────────────────────────
    h_d, w_d = img_draw.shape[:2]
    y_start = max(0, int(grid_y - 80 * scale_y))
    y_end   = min(h_d, int(grid_y + 320 * scale_y))
    x_start = max(0, int(grid_x - 20 * scale_x))
    x_end   = min(w_d, int(grid_x + 580 * scale_x))
    crop_debug = img_draw[y_start:y_end, x_start:x_end]

    return bubble_regno, crop_debug, align_method


# ─────────────────────────────────────────────
# MAIN SHEET PROCESSOR
# ─────────────────────────────────────────────

def process_omr_sheet(img_path, output_dir, file_prefix):
    """
    Processes a single OMR sheet image (color or B&W) and extracts all fields.

    Handles any image resolution dynamically via template scaling.

    Args:
        img_path (str): Full path to the OMR image file.
        output_dir (str): Directory to save cropped images.
        file_prefix (str): Prefix for saved image filenames.

    Returns:
        dict with all extracted fields and paths to saved crops.

    Raises:
        FileNotFoundError: if the image cannot be loaded.
    """
    img = cv2.imread(img_path)
    if img is None:
        raise FileNotFoundError(f"Could not load OMR image: {img_path}")

    h, w = img.shape[:2]

    # ── 1. Select template based on image width ─────────────────────────────────
    tpl = get_omr_template(w)

    # ── 2. Calculate scale factors ──────────────────────────────────────────────
    # template target_width is the canonical reference width
    scale_x = w / tpl["target_width"]
    # Use a standard aspect ratio for Y scaling
    # Standard template target height = 1080, Blind/Disabled = 784
    h_target = 1080 if tpl["name"] == "standard" else 784
    scale_y = h / h_target

    # ── 3. Scale all crop coordinates ──────────────────────────────────────────
    def sc(coords):
        """Scale (y0, y1, x0, x1) by scale_y and scale_x."""
        y0, y1, x0, x1 = coords
        return (
            int(y0 * scale_y), int(y1 * scale_y),
            int(x0 * scale_x), int(x1 * scale_x)
        )

    c_sig_d = sc(tpl["cand_sig_detect"])
    c_sig_s = sc(tpl["cand_sig_save"])
    i_sig_d = sc(tpl["inv_sig_detect"])
    i_sig_s = sc(tpl["inv_sig_save"])
    b_coords = sc(tpl["barcode"])
    r_coords = sc(tpl["reg_boxes"])
    q_coords = sc(tpl["qca"])

    # ── 4. Crop regions ────────────────────────────────────────────────────────
    def crop(coords):
        y0, y1, x0, x1 = coords
        return img[y0:y1, x0:x1]

    cand_sig_detect = crop(c_sig_d)
    cand_sig_save   = crop(c_sig_s)
    inv_sig_detect  = crop(i_sig_d)
    inv_sig_save    = crop(i_sig_s)
    barcode_crop    = crop(b_coords)
    reg_boxes_crop  = crop(r_coords)
    qca_crop        = crop(q_coords)

    # ── 5. Decode barcode ──────────────────────────────────────────────────────
    decoded = decode(barcode_crop)
    barcode_val = "Not Detected"
    if decoded:
        barcode_val = decoded[0].data.decode("utf-8")

    # ── 6. Check signatures ────────────────────────────────────────────────────
    cand_signed, cand_ratio = check_ink_present(
        cand_sig_detect, ratio_threshold=tpl["signature_ink_threshold"]
    )
    inv_signed, inv_ratio = check_ink_present(
        inv_sig_detect, ratio_threshold=tpl["signature_ink_threshold"]
    )

    # ── 7. Read bubbles ────────────────────────────────────────────────────────
    bubble_regno, debug_grid_img, align_method = read_bubbles(img, tpl, scale_x, scale_y)

    # ── 8. Define output paths ─────────────────────────────────────────────────
    os.makedirs(output_dir, exist_ok=True)

    paths = {
        "cand_sig":   os.path.join(output_dir, f"{file_prefix}_omr_cand_sig.png"),
        "inv_sig":    os.path.join(output_dir, f"{file_prefix}_omr_inv_sig.png"),
        "barcode":    os.path.join(output_dir, f"{file_prefix}_omr_barcode.png"),
        "reg_boxes":  os.path.join(output_dir, f"{file_prefix}_omr_reg_boxes.png"),
        "qca":        os.path.join(output_dir, f"{file_prefix}_omr_qca.png"),
        "debug_grid": os.path.join(output_dir, f"{file_prefix}_omr_debug_grid.png"),
    }

    # ── 9. Save crops ──────────────────────────────────────────────────────────
    cv2.imwrite(paths["cand_sig"],   cand_sig_save)
    cv2.imwrite(paths["inv_sig"],    inv_sig_save)
    cv2.imwrite(paths["barcode"],    barcode_crop)
    cv2.imwrite(paths["reg_boxes"],  reg_boxes_crop)
    cv2.imwrite(paths["qca"],        qca_crop)
    if debug_grid_img is not None and debug_grid_img.size > 0:
        cv2.imwrite(paths["debug_grid"], debug_grid_img)

    # ── 10. Return results ─────────────────────────────────────────────────────
    return {
        "filename":               os.path.basename(img_path),
        "bubble_register_number": bubble_regno,
        "barcode":                barcode_val,
        "candidate_signed":       cand_signed,
        "candidate_ink_ratio":    round(cand_ratio, 6),
        "invigilator_signed":     inv_signed,
        "invigilator_ink_ratio":  round(inv_ratio, 6),
        "omr_cand_sig_image":     os.path.relpath(paths["cand_sig"]),
        "omr_inv_sig_image":      os.path.relpath(paths["inv_sig"]),
        "omr_barcode_image":      os.path.relpath(paths["barcode"]),
        "omr_reg_boxes_image":    os.path.relpath(paths["reg_boxes"]),
        "omr_qca_image":          os.path.relpath(paths["qca"]),
        "omr_debug_grid_image":   os.path.relpath(paths["debug_grid"]),
        "align_method":           align_method,
        "template_used":          tpl["name"],
        "image_size":             f"{w}x{h}",
        "scale":                  f"{scale_x:.3f}x{scale_y:.3f}",
    }
