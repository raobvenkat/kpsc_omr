import os
import cv2
import numpy as np
import easyocr
import re
from core.nominal_roll import get_invigilator_signature_box
def read_printed_registration_number(crop_bgr, reader):
    """Read the printed registration number; return blank for empty fields."""
    if crop_bgr is None or crop_bgr.size == 0:
        return ""

    gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
    enlarged = cv2.resize(gray, None, fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
    _, thresholded = cv2.threshold(enlarged, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    candidates = []
    for source in (enlarged, thresholded):
        for _, text, confidence in reader.readtext(source, detail=1, allowlist="0123456789", paragraph=False):
            digits = "".join(ch for ch in text if ch.isdigit())
            if 6 <= len(digits) <= 12:
                candidates.append((float(confidence), digits))

    return max(candidates, key=lambda item: (item[0], len(item[1])), default=(0.0, ""))[1]

QCAB_X0 = 1180
QCAB_X1 = 1490


def read_qcab_serial_number(crop_bgr, reader):
    """Read the printed QCAB serial number; return blank for an empty field."""
    if crop_bgr is None or crop_bgr.size == 0:
        return ""

    gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
    enlarged = cv2.resize(gray, None, fx=3.0, fy=3.0,
                          interpolation=cv2.INTER_CUBIC)
    _, thresholded = cv2.threshold(
        enlarged, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    candidates = []
    for source in (enlarged, thresholded):
        for _, text, confidence in reader.readtext(
                source, detail=1, allowlist="0123456789", paragraph=False):
            digits = "".join(ch for ch in text if ch.isdigit())
            if 6 <= len(digits) <= 12:
                candidates.append((float(confidence), digits))

    return max(candidates, key=lambda item: (item[0], len(item[1])),
               default=(0.0, ""))[1]

def detect_left_border(img, expected_x=133):
    """
    Detects the leftmost table border line to align coordinates horizontally.
    """
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img.copy()
    
    # We look in Y: 300 to 1800, X: expected_x - 55 to expected_x + 55 (wider range)
    x0 = max(0, expected_x - 55)
    x1 = min(w, expected_x + 55)
    crop = gray[300:1800, x0:x1]
    
    # Threshold for dark lines
    _, thresh = cv2.threshold(crop, 120, 255, cv2.THRESH_BINARY_INV)
    col_sums = np.sum(thresh, axis=0)
    
    peak_local_x = np.argmax(col_sums)
    detected_x = x0 + peak_local_x
    return detected_x

def extract_blue_ink(crop_img):
    """
    Isolates blue/dark pen ink from red/pink background grid and watermarks.
    """
    if crop_img is None or crop_img.size == 0:
        return crop_img
        
    hsv = cv2.cvtColor(crop_img, cv2.COLOR_BGR2HSV)
    
    # Blue ink HSV range: H = 90 to 140, S = 40 to 255, V = 40 to 255
    lower_blue = np.array([90, 40, 40])
    upper_blue = np.array([140, 255, 255])
    blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)
    
    # Also include very dark pen strokes (black/dark gray pen)
    gray = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
    _, dark_mask = cv2.threshold(gray, 110, 255, cv2.THRESH_BINARY_INV)
    
    # Filter out red/pink grid lines by masking out red HSV range
    lower_red1 = np.array([0, 30, 40]); upper_red1 = np.array([15, 255, 255])
    lower_red2 = np.array([165, 30, 40]); upper_red2 = np.array([180, 255, 255])
    red_mask = cv2.bitwise_or(cv2.inRange(hsv, lower_red1, upper_red1),
                               cv2.inRange(hsv, lower_red2, upper_red2))
    
    # Combine blue ink and dark pen strokes, excluding red background elements
    ink_mask = cv2.bitwise_or(blue_mask, dark_mask)
    ink_mask[red_mask > 0] = 0
    
    # Create a clean white-background image with only the extracted ink
    clean_img = np.ones_like(crop_img) * 255
    clean_img[ink_mask > 0] = crop_img[ink_mask > 0]
    
    # Convert to grayscale and enhance contrast
    clean_gray = cv2.cvtColor(clean_img, cv2.COLOR_BGR2GRAY)
    return clean_gray

def check_signature_present(crop_img):
    """
    Checks for the presence of ink/signature inside the cropped signature box.
    """
    if crop_img is None or crop_img.size == 0:
        return False
    h_c, w_c = crop_img.shape[:2]
    # Crop inner 80% to avoid any border lines
    crop_inner = crop_img[int(h_c*0.1):int(h_c*0.9), int(w_c*0.1):int(w_c*0.9)]
        
    # Convert directly to grayscale to avoid erasing non-blue signatures
    gray = cv2.cvtColor(crop_inner, cv2.COLOR_BGR2GRAY) if len(crop_inner.shape) == 3 else crop_inner.copy()
    std_dev = np.std(gray)
    
    # Reject low-contrast empty signature boxes (scanner paper noise)
    if std_dev < 10.0:
        return False
        
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    
    h_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1)))
    v_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40)))
    clean_mask = cv2.bitwise_and(thresh, cv2.bitwise_not(cv2.bitwise_or(h_lines, v_lines)))
    
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(clean_mask, connectivity=8)
    if num_labels <= 1:
        return False
        
    areas = sorted(stats[1:, cv2.CC_STAT_AREA].tolist(), reverse=True)
    if not areas:
        return False
        
    # If the largest component is very large, it's a signature (cursive/continuous stroke)
    if areas[0] >= 80:
        return True
        
    # Otherwise, require at least 2 components of size >= 15
    large_components = sum(1 for a in areas if a >= 15)
    return large_components >= 2

def find_invigilator_label_bottom(img, reader):
    """
    Scan the bottom 25 % of the page for the text "Name of the Invigilator"
    (or close variants) using EasyOCR.

    Returns the **bottom y-pixel** of that text block, or None if not found.
    The signature crop should start a few pixels below this value.
    """
    if img is None or img.size == 0 or reader is None:
        return None

    h, w = img.shape[:2]

    # Only search the bottom quarter of the page — faster and avoids false hits
    search_y0 = int(h * 0.72)
    footer_crop = img[search_y0:h, 0:w]

    try:
        results = reader.readtext(footer_crop, detail=1, paragraph=False)
    except Exception:
        return None

    keywords = ("name", "invigilator", "invigil")
    best_bottom = None

    for (bbox, text, conf) in results:
        if not text:
            continue
        text_lower = text.lower()
        if any(kw in text_lower for kw in keywords):
            # bbox is [[x0,y0],[x1,y0],[x1,y1],[x0,y1]] in the crop's space
            ys = [pt[1] for pt in bbox]
            label_bottom_in_crop = int(max(ys))
            label_bottom_abs = search_y0 + label_bottom_in_crop
            if best_bottom is None or label_bottom_abs > best_bottom:
                best_bottom = label_bottom_abs

    return best_bottom


def get_invigilator_sig_box_dynamic(img, reader):
    """
    Return (x0, y0, x1, y1) for the invigilator signature area on a
    normal Type-2 sheet.

    y0 is set just below the "Name of the Invigilator" label line.
    y1 extends to ~97 % of the image height to include the full signature.
    x0/x1 use the same horizontal extents as INVIGILATOR_BOX_TYPE2.

    Falls back to the static percentages if the label cannot be found.
    """
    h, w = img.shape[:2]

    label_bottom = find_invigilator_label_bottom(img, reader)

    if label_bottom is not None:
        # Add a small gap (5 px or 0.5 % of height) below the label baseline
        gap = max(5, int(h * 0.005))
        y0 = min(label_bottom + gap, int(h * 0.97))
        y1 = min(int(h * 0.975), h - 2)
    else:
        # Static fallback — same values as INVIGILATOR_BOX_TYPE2
        y0 = int(h * 0.915)
        y1 = int(h * 0.950)

    x0 = int(w * 0.040)   # slightly wider than the static box to not clip
    x1 = int(w * 0.450)

    return (max(0, x0), max(0, y0), min(w, x1), min(h, y1))


def check_invigilator_signature_present(img, reader=None):
    """
    Detect whether the invigilator has signed on a normal Type-2 sheet.

    When a reader is supplied the crop region is determined dynamically by
    locating the "Name of the Invigilator" label first.  Without a reader
    the static percentage fallback is used.
    """
    if img is None or img.size == 0:
        return False

    h, w = img.shape[:2]

    if reader is not None:
        x0, y0, x1, y1 = get_invigilator_sig_box_dynamic(img, reader)
    else:
        x0, y0, x1, y1 = get_invigilator_signature_box(2, w, h, "normal")

    crop = img[max(0, y0):min(h, y1), max(0, x0):min(w, x1)]
    return check_signature_present(crop)


    
def extract_header_codes(img, reader):
    """
    Extracts Subject Code, Centre Code, and Sub-Centre Code from the top header using EasyOCR.
    """
    if img is None or img.size == 0 or reader is None:
        return {"center_code": "", "subcenter_code": "", "subject_code": ""}
        
    h, w = img.shape[:2]
    # Crop the top 500 pixels (header area)
    header_crop = img[0:500, 0:w]
    
    # Run EasyOCR
    results = reader.readtext(header_crop, detail=0)
    full_text = " ".join(results)
    
    center_code = ""
    subcenter_code = ""
    subject_code = ""
    
    # Regex to find Center Code: look for "Center Code" followed by a number, possibly in parenthesis
    center_match = re.search(r"(?:Center|Centre)\s*Code.*?\(?(\d+)\)?", full_text, re.IGNORECASE)
    if center_match:
        center_code = center_match.group(1)
        
    subcenter_match = re.search(r"Sub\s*(?:Center|Centre)\s*Code.*?\(?(\d+)\)?", full_text, re.IGNORECASE)
    if subcenter_match:
        subcenter_code = subcenter_match.group(1)
        
    subject_match = re.search(r"Subject\s*Code.*?(\d+)", full_text, re.IGNORECASE)
    if subject_match:
        subject_code = subject_match.group(1)
        
    return {
        "center_code": center_code,
        "subcenter_code": subcenter_code,
        "subject_code": subject_code
    }

def process_attendance_sheet2(img_path, reader=None):
    """
    Processes Attendance Sheet 2 (QCAB-based) and returns a list of candidate records.

    Auto-detects whether the sheet is the standard A4-print layout or the
    fit-to-page layout and dispatches to the appropriate processor.
    The returned (records, header) structure is identical for both paths so
    all callers work without any changes.
    """
    img = cv2.imread(img_path)
    if img is None:
        raise ValueError(f"Failed to load image: {img_path}")

    # ── Auto-detect print type and dispatch ───────────────────────────────────
    subtype = detect_sheet_subtype(img)
    if subtype == "fitpage":
        return process_attendance_sheet2_fitpage(img_path, reader)

    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 1. Align horizontally using the leftmost border
    expected_border_x = 133
    detected_border = detect_left_border(img, expected_border_x)
    # If the detected border is too far off (e.g. more than 55px), fallback to expected
    if abs(detected_border - expected_border_x) > 55:
        shift = 0
    else:
        shift = detected_border - expected_border_x
        
    # 2. Set up row coordinates and offsets (6 candidate rows centers)
    y_centers = [580, 815, 1049, 1283, 1521, 1754]
    
    # Column coordinates (offsets relative to the leftmost border)
    # Present/Absent bubble offsets
    px_offset = 469
    ax_offset = 524
    bubble_r = 10

    # Candidate signature column
    sig_x0 = 380
    sig_x1 = 850
    
    # Registration No column (pre-printed)
    reg_x0 = 760
    reg_x1 = 950
    
    if reader is None:
        reader = easyocr.Reader(['en'], gpu=False)
        
    records = []
    
    for idx, yc in enumerate(y_centers):
        # A. Present/Absent bubble detection
        px = px_offset + shift
        ax = ax_offset + shift
        
        p_cell = gray[yc-bubble_r : yc+bubble_r, px-bubble_r : px+bubble_r]
        p_mean = np.mean(p_cell) if p_cell.size > 0 else 255
        
        a_cell = gray[yc-bubble_r : yc+bubble_r, ax-bubble_r : ax+bubble_r]
        a_mean = np.mean(a_cell) if a_cell.size > 0 else 255
        
        is_p_marked = p_mean < 135
        is_a_marked = a_mean < 135
  
        # B. Candidate Signature detection
        sig_crop = img[yc+40:yc+130, sig_x0+shift : sig_x1+shift]
        signature_present = check_signature_present(sig_crop)
        
        # Refined bubble classification logic
        if is_p_marked and is_a_marked:
            # If signature is present, it's very likely they are Present (A bubble is just signature bleed)
            if signature_present:
                status = "Present"
            else:
                # Pick the darker one if significant difference, otherwise double marked
                if p_mean < a_mean - 20:
                    status = "Present"
                elif a_mean < p_mean - 20:
                    status = "Absent"
                else:
                    status = "Double Marked"
        elif is_p_marked:
            status = "Present"
        elif is_a_marked:
            status = "Absent"
        else:
            status = "Not Marked"
            
        # C. Registration No OCR (yc-20 to yc+20) - pre-printed
        reg_crop = img[yc-15:yc+35, reg_x0+shift : reg_x1+shift]
        registration_no = read_printed_registration_number(reg_crop, reader)

        qcab_crop = img[yc-20:yc+30, QCAB_X0+shift : QCAB_X1+shift]
        qcab_serial_no = read_qcab_serial_number(qcab_crop, reader)
        
        records.append({
            "row_number": idx + 1,
            "status": status,
            "signature_present": signature_present,
            "registration_no": registration_no,
            "omr_no": "",
            "qcab_serial_no": qcab_serial_no
        })
        
    # Extract header codes
    header = extract_header_codes(img, reader)
    header["invigilator_signed"] = int(check_invigilator_signature_present(img, reader))
    header["sheet_subtype"] = "normal"
    return records, header


# ─────────────────────────────────────────────────────────────────────────────
# FIT-TO-PAGE SUPPORT
# The "fit-to-page" variant is a Type-2 sheet whose content has been scaled
# to fill the full printable area.  The visual structure is identical but all
# coordinates shrink proportionally.  Percentage-based coordinates are used so
# the logic works at any scanner resolution.
# ─────────────────────────────────────────────────────────────────────────────

# ── Percentage-based layout constants for the fit-to-page sheet ──────────────
# All values are fractions of image width (W) or height (H).
# Measured from the reference scan attached by the user.

FTP_LEFT_BORDER_PCT   = 0.040   # leftmost table border  (~4 % of W)

# Six candidate-row vertical centres as fraction of H
FTP_ROW_Y_PCTS = [0.250, 0.365, 0.470, 0.576, 0.681, 0.786]

# Present / Absent bubble centres (fraction of W)
FTP_P_BUBBLE_PCT  = 0.183
FTP_A_BUBBLE_PCT  = 0.213
FTP_BUBBLE_R_PCT  = 0.008   # sample radius

# Registration No box (fraction of W)
FTP_REG_X0_PCT  = 0.285
FTP_REG_X1_PCT  = 0.485

# QCAB Serial No box (fraction of W)
FTP_QCAB_X0_PCT = 0.620
FTP_QCAB_X1_PCT = 0.830

# Candidate Signature box — offsets relative to row centre (fraction of H)
FTP_SIG_X0_PCT      = 0.285
FTP_SIG_X1_PCT      = 0.485
FTP_SIG_DY_TOP_PCT  = 0.035   # sig box top  = yc + dy_top  * H
FTP_SIG_DY_BOT_PCT  = 0.085   # sig box bot  = yc + dy_bot  * H

# Invigilator signature box (fraction of W / H)
FTP_INV_X0_PCT = 0.030
FTP_INV_X1_PCT = 0.360
FTP_INV_Y0_PCT = 0.880
FTP_INV_Y1_PCT = 0.950


def detect_sheet_subtype(img, dpi=200):
    """Return 'fitpage' or 'normal' for a Type-2 Nominal Roll sheet.

    Rule (as specified)
    ───────────────────
    Find the bottom-most full-width horizontal table line.
    Measure the gap between that line and the bottom edge of the image.

        gap > 3 cm  →  fit-to-page   (content scaled down, large white margin)
        gap ≤ 3 cm  →  normal A4     (content fills the page to the bottom)

    The 3 cm threshold is converted to pixels using the supplied DPI.
    Common scanner DPIs: 150, 200 (default), 300.  The function is robust
    across all three because it uses the actual image height to normalise.
    """
    if img is None or img.size == 0:
        return "normal"

    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img.copy()

    # ── 3 cm threshold in pixels ─────────────────────────────────────────────
    # 1 inch = 2.54 cm  →  3 cm = 3/2.54 inches
    # Fallback: if DPI is unknown, estimate it from image height assuming A4
    # (A4 height = 29.7 cm).  This gives a reasonable estimate even without
    # knowing the actual DPI.
    if dpi is None or dpi <= 0:
        dpi = int(h / (29.7 / 2.54))   # pixels per inch from A4 height

    threshold_px = int((3.0 / 2.54) * dpi)   # 3 cm → pixels

    # ── Find the bottom-most wide horizontal line ─────────────────────────────
    # Search only in the lower 40 % of the image to avoid false hits from
    # the candidate-row grid lines in the middle of the sheet.
    search_y0 = int(h * 0.60)
    roi = gray[search_y0:h, 0:w]

    _, thresh = cv2.threshold(roi, 120, 255, cv2.THRESH_BINARY_INV)

    # A genuine table border spans at least 50 % of the page width.
    min_line_px = int(w * 0.50)

    # Horizontal projection: count dark pixels per row
    row_sums = np.sum(thresh, axis=1) / 255.0

    # Collect rows that qualify as a horizontal line
    line_rows = [y for y, s in enumerate(row_sums) if s >= min_line_px]

    if not line_rows:
        # No wide horizontal line found — cannot measure; assume normal
        return "normal"

    # Bottom-most qualifying line (in the ROI's coordinate space)
    bottom_line_y_roi = max(line_rows)
    bottom_line_y_abs = search_y0 + bottom_line_y_roi

    gap_px = h - bottom_line_y_abs   # pixels from that line to the image bottom

    return "fitpage" if gap_px > threshold_px else "normal"


def _detect_fitpage_row_centers(img):
    """
    Try to detect the actual six candidate-row vertical centres from the
    horizontal grid lines of the fit-to-page sheet.

    Falls back to the percentage-based defaults if detection fails.
    """
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img.copy()

    # Look for horizontal lines in the table body region (15 % … 90 % of H)
    y0_scan = int(h * 0.15)
    y1_scan = int(h * 0.90)
    x0_scan = int(w * 0.03)
    x1_scan = int(w * 0.97)

    strip = gray[y0_scan:y1_scan, x0_scan:x1_scan]
    _, thresh = cv2.threshold(strip, 120, 255, cv2.THRESH_BINARY_INV)

    # Horizontal projection — rows with many dark pixels are table lines
    row_sums = np.sum(thresh, axis=1) / 255.0
    min_line_px = (x1_scan - x0_scan) * 0.40   # line must span ≥ 40 % of width

    # Collect y-positions of dark horizontal lines
    line_ys = []
    in_line = False
    group = []
    for y_local, s in enumerate(row_sums):
        if s >= min_line_px:
            group.append(y_local)
            in_line = True
        else:
            if in_line and group:
                line_ys.append(int(np.mean(group)) + y0_scan)
                group = []
                in_line = False
    if in_line and group:
        line_ys.append(int(np.mean(group)) + y0_scan)

    # We expect 7+ horizontal lines bounding the 6 candidate rows
    if len(line_ys) >= 7:
        # Take the first 7 and compute row centres
        row_centers = [(line_ys[i] + line_ys[i + 1]) // 2 for i in range(6)]
        return row_centers

    # Fallback: percentage defaults
    return [int(p * h) for p in FTP_ROW_Y_PCTS]


def _check_invigilator_fitpage(img):
    """Detect invigilator signature in the fit-to-page footer."""
    if img is None or img.size == 0:
        return False
    h, w = img.shape[:2]
    x0 = int(w * FTP_INV_X0_PCT)
    x1 = int(w * FTP_INV_X1_PCT)
    y0 = int(h * FTP_INV_Y0_PCT)
    y1 = int(h * FTP_INV_Y1_PCT)
    crop = img[max(0, y0):min(h, y1), max(0, x0):min(w, x1)]
    return check_signature_present(crop)


def process_attendance_sheet2_fitpage(img_path, reader=None):
    """
    Process a fit-to-page Nominal Roll Type-2 sheet.

    All coordinates are percentage-based so the function is resolution-
    independent.  The same helper functions used by the normal Type-2
    processor (check_signature_present, read_printed_registration_number,
    read_qcab_serial_number, extract_header_codes) are reused unchanged.

    Returns (records, header) with the same structure as
    process_attendance_sheet2() so callers need no special-casing.
    """
    img = cv2.imread(img_path)
    if img is None:
        raise ValueError(f"Failed to load image: {img_path}")

    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    if reader is None:
        reader = easyocr.Reader(['en'], gpu=False)

    # ── Row centres (dynamic detection with percentage fallback) ─────────────
    y_centers = _detect_fitpage_row_centers(img)

    # ── Pre-compute pixel coordinates from percentages ───────────────────────
    p_x   = int(w * FTP_P_BUBBLE_PCT)
    a_x   = int(w * FTP_A_BUBBLE_PCT)
    bub_r = max(6, int(min(w, h) * FTP_BUBBLE_R_PCT))

    reg_x0  = int(w * FTP_REG_X0_PCT)
    reg_x1  = int(w * FTP_REG_X1_PCT)
    qcab_x0 = int(w * FTP_QCAB_X0_PCT)
    qcab_x1 = int(w * FTP_QCAB_X1_PCT)
    sig_x0  = int(w * FTP_SIG_X0_PCT)
    sig_x1  = int(w * FTP_SIG_X1_PCT)

    records = []

    for idx, yc in enumerate(y_centers):
        # A. Present / Absent bubbles ─────────────────────────────────────────
        p_cell = gray[max(0, yc - bub_r): yc + bub_r,
                      max(0, p_x - bub_r): p_x + bub_r]
        a_cell = gray[max(0, yc - bub_r): yc + bub_r,
                      max(0, a_x - bub_r): a_x + bub_r]

        p_mean = float(np.mean(p_cell)) if p_cell.size > 0 else 255.0
        a_mean = float(np.mean(a_cell)) if a_cell.size > 0 else 255.0

        is_p_marked = p_mean < 135
        is_a_marked = a_mean < 135

        # B. Candidate signature ──────────────────────────────────────────────
        sig_dy_top = int(h * FTP_SIG_DY_TOP_PCT)
        sig_dy_bot = int(h * FTP_SIG_DY_BOT_PCT)
        sig_crop = img[max(0, yc + sig_dy_top): min(h, yc + sig_dy_bot),
                       max(0, sig_x0): min(w, sig_x1)]
        signature_present = check_signature_present(sig_crop)

        # C. Status from bubbles + signature ──────────────────────────────────
        if is_p_marked and is_a_marked:
            if signature_present:
                status = "Present"
            elif p_mean < a_mean - 20:
                status = "Present"
            elif a_mean < p_mean - 20:
                status = "Absent"
            else:
                status = "Double Marked"
        elif is_p_marked:
            status = "Present"
        elif is_a_marked:
            status = "Absent"
        else:
            status = "Not Marked"

        # D. Registration No ──────────────────────────────────────────────────
        row_half = max(20, int(h * 0.028))
        reg_crop = img[max(0, yc - row_half): min(h, yc + row_half),
                       max(0, reg_x0): min(w, reg_x1)]
        registration_no = read_printed_registration_number(reg_crop, reader)

        # E. QCAB Serial No ───────────────────────────────────────────────────
        qcab_crop = img[max(0, yc - row_half): min(h, yc + row_half),
                        max(0, qcab_x0): min(w, qcab_x1)]
        qcab_serial_no = read_qcab_serial_number(qcab_crop, reader)

        records.append({
            "row_number":        idx + 1,
            "status":            status,
            "signature_present": signature_present,
            "registration_no":   registration_no,
            "omr_no":            "",
            "qcab_serial_no":    qcab_serial_no,
        })

    # ── Header codes + invigilator ────────────────────────────────────────────
    header = extract_header_codes(img, reader)
    header["invigilator_signed"] = int(_check_invigilator_fitpage(img))
    # Tag so NominalRolls.py knows which layout to use for annotations
    header["sheet_subtype"] = "fitpage"
    return records, header
