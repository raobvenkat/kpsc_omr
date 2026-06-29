import os
import cv2
import numpy as np
import easyocr
import re
from core.nominal_roll import get_invigilator_signature_box
from core.nominal_roll_type1 import read_registration_number

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

def check_invigilator_signature_present(img):
    """
    Detects the "Name of the Invigilator" entry cell on QCAB attendance sheets.
    """
    if img is None or img.size == 0:
        return False

    h, w = img.shape[:2]
    x0, y0, x1, y1 = get_invigilator_signature_box(2, w, h)
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
    """
    img = cv2.imread(img_path)
    if img is None:
        raise ValueError(f"Failed to load image: {img_path}")
        
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
        reg_crop = img[yc-5:yc+45, reg_x0+shift : reg_x1+shift]
        registration_no = read_registration_number(reg_crop, reader)

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
    header["invigilator_signed"] = int(check_invigilator_signature_present(img))
    return records, header
