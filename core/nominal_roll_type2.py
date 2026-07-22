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

def read_qcab_serial_number(crop_bgr, reader):
    """Read the printed QCAB serial number; return blank for an empty field."""
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

def extract_qcab_number(img, box_a, box_b, reader):
    """
    Crops both Box A and Box B, runs OCR, and returns the best reading and chosen coordinates.
    """
    h, w = img.shape[:2]
    crop_a = img[box_a[0] : box_a[1], max(0, box_a[2]) : min(w, box_a[3])]
    crop_b = img[box_b[0] : box_b[1], max(0, box_b[2]) : min(w, box_b[3])]
    
    val_a = read_qcab_serial_number(crop_a, reader)
    val_b = read_qcab_serial_number(crop_b, reader)
    
    digits_a = "".join(c for c in val_a if c.isdigit())
    digits_b = "".join(c for c in val_b if c.isdigit())
    
    if 6 <= len(digits_a) <= 10:
        return val_a, box_a
    if 6 <= len(digits_b) <= 10:
        return val_b, box_b
        
    if len(digits_a) > len(digits_b):
        return val_a, box_a
    elif len(digits_b) > len(digits_a):
        return val_b, box_b
    else:
        return val_a, box_a

def detect_left_border(img, expected_x=133):
    """
    Detects the leftmost table border line to align coordinates horizontally.
    """
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img.copy()
    
    # Scan columns X=50 to X=250 with threshold 180 (to capture gray lines)
    _, thresh = cv2.threshold(gray[500:1800, 50:250], 180, 255, cv2.THRESH_BINARY_INV)
    col_sums = np.sum(thresh, axis=0)
    
    # Lock onto the very first significant peak from the left
    for x in range(10, len(col_sums)-10):
        val = col_sums[x]
        is_max = True
        for dx in range(-5, 6):
            if col_sums[x+dx] > val:
                is_max = False
                break
        if is_max and val > 20000:
            return 50 + x
            
    return expected_x

def detect_top_border(img):
    """
    Detects the top horizontal border of the table.
    """
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img.copy()
    
    # Scan rows Y=300 to 600, middle columns
    crop = gray[300:600, 300:1300]
    _, thresh = cv2.threshold(crop, 180, 255, cv2.THRESH_BINARY_INV)
    row_sums = np.sum(thresh, axis=1)
    
    peaks = []
    for y in range(len(row_sums)):
        val = row_sums[y]
        is_max = True
        for dx in range(-5, 6):
            if y+dx >= 0 and y+dx < len(row_sums):
                if row_sums[y+dx] > val:
                    is_max = False
                    break
        if is_max and val > 100 * 255:
            peaks.append((y, val))
            
    peaks_sorted = sorted(peaks, key=lambda item: item[1], reverse=True)
    if peaks_sorted:
        return 300 + peaks_sorted[0][0]
    return 350 # Default baseline

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

def check_invigilator_signature_present(img):
    """
    Detects the "Name of the Invigilator" entry cell on QCAB attendance sheets (Fit-to-Page version).
    """
    if img is None or img.size == 0:
        return False

    h, w = img.shape[:2]
    # Detect the table border to align horizontally
    anchor_x = detect_left_border(img, 133)
    
    # Calculate vertical shift
    detected_top = detect_top_border(img)
    y_shift = detected_top - 350
    if abs(y_shift) > 60:
        y_shift = 0
        
    x0 = anchor_x + 247
    x1 = anchor_x + 567
    y0 = 2060 + y_shift  # Shifted down to signature Box 2 directly
    y1 = 2130 + y_shift  
    
    crop = img[max(0, y0):min(h, y1), max(0, x0):min(w, x1)]
    return check_signature_present(crop)

def extract_header_codes(img, reader):
    """
    Extracts Subject Code, Centre Code, and Sub-Centre Code from the top header using EasyOCR.
    """
    if img is None or img.size == 0 or reader is None:
        return {"center_code": "", "subcenter_code": "", "subject_code": ""}
        
    h, w = img.shape[:2]
    header_crop = img[0:500, 0:w]
    
    results = reader.readtext(header_crop, detail=0)
    full_text = " ".join(results)
    
    center_code = ""
    subcenter_code = ""
    subject_code = ""
    
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

def process_attendance_sheet2_unified(img_path, reader=None, force_layout=None):
    """
    Unified, template-free Attendance Sheet 2 reader.
    Locates "Registration No." labels dynamically to align rows,
    and falls back to robust relative alignment parameters.
    """
    img = cv2.imread(img_path)
    if img is None:
        raise ValueError(f"Failed to load image: {img_path}")
        
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    if reader is None:
        reader = easyocr.Reader(['en'], gpu=False)
        
    # 1. Align horizontally using the leftmost border line
    expected_border_x = 133
    detected_border = detect_left_border(img, expected_border_x)
    if abs(detected_border - expected_border_x) > 55:
        shift = 0
    else:
        shift = detected_border - expected_border_x
        
    # 2. Align vertically using the top border
    detected_top = detect_top_border(img)
    
    # 3. Dynamic printed label detection: run OCR on the vertical corridor where "Registration No." column resides.
    # The printed text always starts between X = 600 and X = 1000.
    ocr_x0, ocr_x1 = 600, min(1000, w)
    ocr_y0, ocr_y1 = 320, min(2000, h)
    label_crop = img[ocr_y0:ocr_y1, ocr_x0:ocr_x1]
    ocr_results = reader.readtext(label_crop, detail=1, paragraph=False, low_text=0.3)
    
    reg_labels = []
    for bbox, text, conf in ocr_results:
        y_center = ocr_y0 + int((bbox[0][1] + bbox[2][1]) / 2)
        x_left   = ocr_x0 + int(bbox[0][0])
        
        txt_lower = text.lower()
        if re.search(r"reg", txt_lower):
            reg_labels.append((y_center, x_left))
            
    # Sort and filter: real row labels appear below column header (Y > 430) and right of photo (X > 380)
    reg_labels = sorted(reg_labels, key=lambda item: item[0])
    reg_labels = [lbl for lbl in reg_labels if lbl[0] > 430 and lbl[1] > 380]
    
    # 4. Classify layout type (Normal vs Fit-to-Page)
    is_normal = False
    if force_layout == "normal":
        is_normal = True
    elif force_layout == "fit_to_page":
        is_normal = False
    else:
        # Auto detect using row spacing
        if len(reg_labels) >= 2:
            dy = reg_labels[1][0] - reg_labels[0][0]
            is_normal = dy >= 230
        else:
            is_normal = detected_top > 400
            
    # 5. Row height spacing (dy)
    if len(reg_labels) >= 2:
        diffs = [reg_labels[i+1][0] - reg_labels[i][0] for i in range(len(reg_labels)-1)]
        valid_diffs = [d for d in diffs if 200 <= d <= 260]
        spacing = np.mean(valid_diffs) if valid_diffs else (242.5 if is_normal else 222.0)
    else:
        spacing = 242.5 if is_normal else 222.0
        
    # Reconstruct missing candidate row center coordinates
    final_rows = []
    if len(reg_labels) > 0:
        first_y, first_x = reg_labels[0]
        row1_y_approx = 561 if is_normal else 547
        y_shift = detected_top - (454 if is_normal else 350)
        row_index_of_first = round((first_y - (row1_y_approx + y_shift)) / spacing)
        row_index_of_first = max(0, min(5, row_index_of_first))
        
        for i in range(6):
            offset_multiplier = i - row_index_of_first
            ry = int(first_y + offset_multiplier * spacing)
            closest = min(reg_labels, key=lambda item: abs(item[0] - ry))
            if abs(closest[0] - ry) < 30:
                final_rows.append(closest)
            else:
                final_rows.append((ry, first_x))
    else:
        # Fallback to pure relative templates if zero labels detected
        y_shift = detected_top - (454 if is_normal else 350)
        if abs(y_shift) > 60:
            y_shift = 0
            
        if is_normal:
            y_centers_base = [561, 803, 1046, 1288, 1531, 1773]
            rx_left = 800 + shift
        else:
            y_centers_base = [547, 769, 991, 1213, 1435, 1657]
            rx_left = 785 + shift
            
        for yc in y_centers_base:
            final_rows.append((yc + y_shift, rx_left))
            
    # 6. Extract candidate data for each row
    records = []
    for idx, (ry, rx_left) in enumerate(final_rows[:6]):
        if not is_normal:
            # Fit-to-Page relative coordinates
            reg_coords = [ry, ry + 50, rx_left - 55, rx_left + 175]
            box_a = [ry - 5, ry + 45, rx_left + 349, rx_left + 659]
            box_b = [ry + 75, ry + 155, rx_left + 349, rx_left + 659]
            sig_coords = [ry + 75, ry + 155, rx_left - 391, rx_left + 79]
            p_y, p_x = ry + 35, rx_left - 289
            a_y, a_x = ry + 35, rx_left - 234
        else:
            # Normal relative coordinates
            reg_coords = [ry - 10, ry + 55, rx_left - 55, rx_left + 205]
            box_a = [ry - 5, ry + 45, rx_left + 525, rx_left + 865]
            box_b = [ry + 85, ry + 155, rx_left + 525, rx_left + 865]
            sig_coords = [ry + 72, ry + 147, rx_left - 395, rx_left + 75]
            p_y, p_x = ry + 40, rx_left - 320
            a_y, a_x = ry + 40, rx_left - 265
            
        # A. OCR Registration number
        reg_crop = img[reg_coords[0] : reg_coords[1], max(0, reg_coords[2]) : min(w, reg_coords[3])]
        registration_no = read_printed_registration_number(reg_crop, reader)
        
        # B. Double-box detection for QCAB booklet
        qcab_serial_no, chosen_coords = extract_qcab_number(img, box_a, box_b, reader)
        
        # C. Candidate Signature presence
        sig_crop = img[sig_coords[0] : sig_coords[1], max(0, sig_coords[2]) : min(w, sig_coords[3])]
        signature_present = check_signature_present(sig_crop)
        
        # D. Bubble Present/Absent detection
        bubble_r = 14
        p_cell = gray[max(0, p_y-bubble_r) : min(h, p_y+bubble_r), max(0, p_x-bubble_r) : min(w, p_x+bubble_r)]
        p_mean = np.mean(p_cell) if p_cell.size > 0 else 255
        
        a_cell = gray[max(0, a_y-bubble_r) : min(h, a_y+bubble_r), max(0, a_x-bubble_r) : min(w, a_x+bubble_r)]
        a_mean = np.mean(a_cell) if a_cell.size > 0 else 255
        
        is_p_marked = p_mean < 160
        is_a_marked = a_mean < 160
        
        if is_p_marked and is_a_marked:
            if signature_present:
                status = "Present"
            else:
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
            
        records.append({
            "row_number": idx + 1,
            "status": status,
            "signature_present": signature_present,
            "registration_no": registration_no,
            "omr_no": "",
            "qcab_serial_no": qcab_serial_no,
            "coords": {
                "reg": reg_coords,
                "qcab": chosen_coords, 
                "sig": sig_coords,
                "bubble_p": [p_y, p_x],
                "bubble_a": [a_y, a_x],
                "is_normal": is_normal
            }
        })
        
    # E. Invigilator Signature
    header = extract_header_codes(img, reader)
    
    anchor_x = detect_left_border(img, 133)
    y_shift = detected_top - (454 if is_normal else 350)
    if abs(y_shift) > 60:
        y_shift = 0
        
    if not is_normal:
        inv_coords = [2020 + y_shift, 2090 + y_shift, anchor_x + 247, anchor_x + 567]  
    else:
        inv_coords = [2110 + y_shift, 2170 + y_shift, anchor_x + 142, anchor_x + 566]  
        
    inv_crop = img[inv_coords[0] : inv_coords[1], max(0, inv_coords[2]) : min(w, inv_coords[3])]
    header["invigilator_signed"] = int(check_signature_present(inv_crop))
    
    if len(records) > 0:
        records[0]["coords"]["inv"] = inv_coords
        
    return records, header

def process_attendance_sheet2(img_path, reader=None):
    """Fallback entry point delegating to the unified dynamic processor."""
    return process_attendance_sheet2_unified(img_path, reader, force_layout="fit_to_page")

def process_attendance_sheet2_normal(img_path, reader=None):
    """Fallback entry point delegating to the unified dynamic processor."""
    return process_attendance_sheet2_unified(img_path, reader, force_layout="normal")

def process_attendance_sheet2_relative(img_path, reader=None):
    """Auto-detect entry point delegating to the unified dynamic processor."""
    return process_attendance_sheet2_unified(img_path, reader, force_layout=None)
