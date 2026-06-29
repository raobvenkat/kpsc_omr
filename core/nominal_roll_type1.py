import os
import cv2
import numpy as np
import onnxruntime as ort
import easyocr
import re
from core.nominal_roll import get_invigilator_signature_box

# Load ONNX MNIST Model
_MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "core", "mnist-8.onnx")
if os.path.exists(_MODEL_PATH):
    sess = ort.InferenceSession(_MODEL_PATH)
    input_name = sess.get_inputs()[0].name
else:
    sess = None
    input_name = None

def detect_left_border(img, expected_x=87):
    """
    Detects the leftmost table border line to align coordinates horizontally.
    """
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img.copy()
    
    x0 = max(0, expected_x - 55)
    x1 = min(w, expected_x + 55)
    crop = gray[300:1800, x0:x1]
    
    _, thresh = cv2.threshold(crop, 120, 255, cv2.THRESH_BINARY_INV)
    col_sums = np.sum(thresh, axis=0)
    
    peak_local_x = np.argmax(col_sums)
    detected_x = x0 + peak_local_x
    return detected_x

def extract_blue_ink(crop_img):
    """
    Isolates blue/dark pen ink from red/pink/gray watermarks.
    """
    if crop_img is None or crop_img.size == 0:
        return crop_img
        
    hsv = cv2.cvtColor(crop_img, cv2.COLOR_BGR2HSV)
    
    lower_blue = np.array([90, 40, 40])
    upper_blue = np.array([140, 255, 255])
    blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)
    
    gray = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
    _, dark_mask = cv2.threshold(gray, 110, 255, cv2.THRESH_BINARY_INV)
    
    lower_red1 = np.array([0, 30, 40]); upper_red1 = np.array([15, 255, 255])
    lower_red2 = np.array([165, 30, 40]); upper_red2 = np.array([180, 255, 255])
    red_mask = cv2.bitwise_or(cv2.inRange(hsv, lower_red1, upper_red1),
                               cv2.inRange(hsv, lower_red2, upper_red2))
    
    ink_mask = cv2.bitwise_or(blue_mask, dark_mask)
    ink_mask[red_mask > 0] = 0
    
    clean_img = np.ones_like(crop_img) * 255
    clean_img[ink_mask > 0] = crop_img[ink_mask > 0]
    
    clean_gray = cv2.cvtColor(clean_img, cv2.COLOR_BGR2GRAY)
    return clean_gray

def preprocess_cell_digit(cell_bgr):
    """
    Crops the inner region of a grid cell to remove borders, extracts ink,
    and returns a centered 28x28 normalized MNIST digit image if a digit is present.
    """
    if cell_bgr is None or cell_bgr.size == 0:
        return None
    h_c, w_c = cell_bgr.shape[:2]
    # Crop inner 70% to avoid vertical and horizontal box lines
    y0, y1 = int(h_c * 0.15), int(h_c * 0.85)
    x0, x1 = int(w_c * 0.15), int(w_c * 0.85)
    inner = cell_bgr[y0:y1, x0:x1]
    
    # Isolate ink (blue/dark)
    gray_ink = extract_blue_ink(inner)
    
    # Threshold (since background and removed elements are pure white 255)
    _, thresh = cv2.threshold(gray_ink, 200, 255, cv2.THRESH_BINARY_INV)
    
    # Find bounding box of all non-zero pixels (the digit)
    coords = cv2.findNonZero(thresh)
    if coords is None:
        return None
        
    x, y, w, h = cv2.boundingRect(coords)
    # Filter out tiny noise (like small dust/specks)
    if w * h < 10 or w < 2 or h < 3:
        return None
        
    digit_crop = thresh[y:y+h, x:x+w]
    
    # Resize to fit in 20x20
    if h > w:
        new_h = 20
        new_w = max(1, int(w * (20.0 / h)))
    else:
        new_w = 20
        new_h = max(1, int(h * (20.0 / w)))
        
    digit_resized = cv2.resize(digit_crop, (new_w, new_h), interpolation=cv2.INTER_AREA)
    
    # Create 28x28 canvas and center the digit
    canvas = np.zeros((28, 28), dtype=np.float32)
    dy = (28 - new_h) // 2
    dx = (28 - new_w) // 2
    canvas[dy:dy+new_h, dx:dx+new_w] = digit_resized.astype(np.float32) / 255.0
    return canvas

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
    if std_dev < 14.0:
        return False
        
    # Fixed threshold to avoid noise amplification
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
    Detects the bottom-left "Sign of the Invigilator" signature using the same
    ink/component logic as candidate signature detection.
    """
    if img is None or img.size == 0:
        return False

    h, w = img.shape[:2]
    x0, y0, x1, y1 = get_invigilator_signature_box(1, w, h)
    crop = img[max(0, y0):min(h, y1), max(0, x0):min(w, x1)]
    return check_signature_present(crop)

def clean_and_segment_digits(crop_bgr):
    """
    Uses morphology and connected components to isolate handwritten digits in a single open box,
    returning a list of normalized 28x28 digit image inputs for the MNIST model.
    """
    if crop_bgr is None or crop_bgr.size == 0:
        return []
        
    h_c, w_c = crop_bgr.shape[:2]
    # Crop inner 90% horizontally and 80% vertically to avoid outer borders
    crop_inner = crop_bgr[int(h_c*0.1):int(h_c*0.9), int(w_c*0.05):int(w_c*0.95)]
    h_t, w_t = crop_inner.shape[:2]
    
    # Isolate ink
    gray_ink = extract_blue_ink(crop_inner)
    
    # Fixed threshold to avoid noise amplification
    _, thresh = cv2.threshold(gray_ink, 200, 255, cv2.THRESH_BINARY_INV)
    
    # Remove horizontal/vertical lines (in case of residue lines)
    h_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1)))
    v_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 25)))
    clean_mask = cv2.bitwise_and(thresh, cv2.bitwise_not(cv2.bitwise_or(h_lines, v_lines)))
    
    # Find components
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(clean_mask, connectivity=8)
    if num_labels <= 1:
        return []
        
    # Gather digit candidates
    candidates = []
    for idx in range(1, num_labels):
        x, y, w, h = stats[idx, cv2.CC_STAT_LEFT], stats[idx, cv2.CC_STAT_TOP], stats[idx, cv2.CC_STAT_WIDTH], stats[idx, cv2.CC_STAT_HEIGHT]
        area = stats[idx, cv2.CC_STAT_AREA]
        
        # Filter noise and large borders
        if area < 6 or w > w_t * 0.7 or h > h_t * 0.9:
            continue
            
        # Filter thin vertical lines
        if w <= 3 or (h > 15 and h / w > 3.5):
            continue
            
        # Filter components touching top/bottom borders
        touches_top_bottom = (y <= 2) or (y + h >= h_t - 2)
        if touches_top_bottom and w < 10:
            continue
            
        candidates.append((x, y, w, h, idx))
        
    # Sort candidates left-to-right
    candidates = sorted(candidates, key=lambda c: c[0])
    
    digit_inputs = []
    for x, y, w, h, idx in candidates:
        digit_mask = (labels == idx).astype(np.uint8) * 255
        digit_crop = digit_mask[y:y+h, x:x+w]
        
        # Resize and pad to 28x28
        if h > w:
            new_h = 20
            new_w = max(1, int(w * (20.0 / h)))
        else:
            new_w = 20
            new_h = max(1, int(h * (20.0 / w)))
            
        digit_resized = cv2.resize(digit_crop, (new_w, new_h), interpolation=cv2.INTER_AREA)
        canvas = np.zeros((28, 28), dtype=np.float32)
        dy = (28 - new_h) // 2
        dx = (28 - new_w) // 2
        canvas[dy:dy+new_h, dx:dx+new_w] = digit_resized.astype(np.float32) / 255.0
        digit_inputs.append(canvas)
        
    return digit_inputs

def read_handwritten_field(crop_bgr):
    """
    Recognizes digits in an open handwritten field (like Registration No) using contour segmentation.
    """
    if sess is None or crop_bgr is None or crop_bgr.size == 0:
        return ""
    digit_inputs = clean_and_segment_digits(crop_bgr)
    if not digit_inputs:
        return ""
        
    digits = []
    for canvas in digit_inputs:
        outputs = sess.run(None, {input_name: canvas.reshape(1, 1, 28, 28)})
        pred = np.argmax(outputs[0])
        digits.append(str(pred))
    return "".join(digits)

def read_handwritten_field_grid(crop_bgr):
    """
    Recognizes digits in a boxed handwritten field (like QP Serial No) by splitting the crop
    horizontally into 7 equal cells and running the MNIST classifier on each.
    """
    if sess is None or crop_bgr is None or crop_bgr.size == 0:
        return ""
        
    h, w = crop_bgr.shape[:2]
    num_cells = 7
    cell_w = w / num_cells
    
    digits = []
    for i in range(num_cells):
        x0 = int(i * cell_w)
        x1 = int((i + 1) * cell_w)
        cell_img = crop_bgr[0:h, x0:x1]
        
        canvas = preprocess_cell_digit(cell_img)
        if canvas is not None:
            outputs = sess.run(None, {input_name: canvas.reshape(1, 1, 28, 28)})
            pred = np.argmax(outputs[0])
            digits.append(str(pred))
            
    return "".join(digits)


def read_handwritten_reg_no_9(crop_bgr):
    """
    Recognizes digits in the 9-digit Registration No box by splitting the crop
    horizontally into 9 equal cells and using the OMR_Sheets.py cell processing logic.
    """
    if sess is None or crop_bgr is None or crop_bgr.size == 0:
        return ""
        
    h, w = crop_bgr.shape[:2]
    num_cells = 9
    cell_w = w / num_cells
    trim_ratio = 0.10
    
    digits = []
    for i in range(num_cells):
        x0 = int(i * cell_w)
        x1 = int((i + 1) * cell_w)
        cell_bgr = crop_bgr[0:h, x0:x1]
        if cell_bgr.size == 0:
            digits.append(" ")
            continue
            
        gray = cv2.cvtColor(cell_bgr, cv2.COLOR_BGR2GRAY)
        hc, wc = gray.shape[:2]
        
        # Blue ink filter / fallback from OMR_Sheets.py
        hsv_crop = cv2.cvtColor(cell_bgr, cv2.COLOR_BGR2HSV)
        lower_blue = np.array([90, 40, 40])
        upper_blue = np.array([140, 255, 255])
        blue_mask = cv2.inRange(hsv_crop, lower_blue, upper_blue)
        if np.sum(blue_mask > 0) > 15:
            gray_clean = np.ones_like(gray) * 255
            gray_clean[blue_mask > 0] = gray[blue_mask > 0]
        else:
            gray_clean = gray.copy()
            
        margin_y = max(1, int(hc * trim_ratio))
        margin_x = max(1, int(wc * trim_ratio))
        gray_trimmed = gray_clean[margin_y:-margin_y, margin_x:-margin_x]
        h_t, w_t = gray_trimmed.shape
        
        min_val, max_val, _, _ = cv2.minMaxLoc(gray_trimmed)
        contrast = max_val - min_val
        if contrast < 40:
            digits.append(" ")
            continue
            
        gray_norm = cv2.normalize(gray_trimmed, None, 0, 255, cv2.NORM_MINMAX)
        _, binary_inv = cv2.threshold(gray_norm, 160, 255, cv2.THRESH_BINARY_INV)
        
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary_inv, connectivity=8)
        if num_labels <= 1:
            digits.append(" ")
            continue
            
        erase_mask = np.zeros_like(binary_inv)
        for idx in range(1, num_labels):
            cx_comp = stats[idx, cv2.CC_STAT_LEFT]
            cy_comp = stats[idx, cv2.CC_STAT_TOP]
            w_comp = stats[idx, cv2.CC_STAT_WIDTH]
            h_comp = stats[idx, cv2.CC_STAT_HEIGHT]
            touches = (cx_comp <= 1) or (cy_comp <= 1) or (cx_comp + w_comp >= w_t - 1) or (cy_comp + h_comp >= h_t - 1)
            if touches:
                erase_mask[labels == idx] = 255
                
        binary_clean = binary_inv.copy()
        binary_clean[erase_mask > 0] = 0
        
        num_labels2, labels2, stats2, _ = cv2.connectedComponentsWithStats(binary_clean, connectivity=8)
        if num_labels2 <= 1:
            digits.append(" ")
            continue
            
        largest_label = 1 + np.argmax(stats2[1:, cv2.CC_STAT_AREA])
        largest_area = stats2[largest_label, cv2.CC_STAT_AREA]
        if largest_area < 8:
            digits.append(" ")
            continue
            
        cell_mask = (labels2 == largest_label).astype(np.uint8) * 255
        y_indices, x_indices = np.where(cell_mask > 0)
        if len(y_indices) == 0 or len(x_indices) == 0:
            digits.append(" ")
            continue
            
        y_min_idx, y_max_idx = np.min(y_indices), np.max(y_indices)
        x_min_idx, x_max_idx = np.min(x_indices), np.max(x_indices)
        
        digit_crop = cell_mask[y_min_idx:y_max_idx+1, x_min_idx:x_max_idx+1]
        h_c, w_c = digit_crop.shape
        if h_c == 0 or w_c == 0:
            digits.append(" ")
            continue
            
        if h_c > w_c:
            new_h = 20
            new_w = max(1, int(w_c * (20.0 / h_c)))
        else:
            new_w = 20
            new_h = max(1, int(h_c * (20.0 / w_c)))
            
        digit_resized = cv2.resize(digit_crop, (new_w, new_h), interpolation=cv2.INTER_AREA)
        canvas = np.zeros((28, 28), dtype=np.float32)
        dy = (28 - new_h) // 2
        dx = (28 - new_w) // 2
        canvas[dy:dy+new_h, dx:dx+new_w] = digit_resized.astype(np.float32) / 255.0
        
        outputs = sess.run(None, {input_name: canvas.reshape(1, 1, 28, 28)})
        predicted_digit = int(np.argmax(outputs[0]))
        digits.append(str(predicted_digit))
        
    return "".join(digits).strip()


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

def process_attendance_sheet1(img_path, reader=None):
    """
    Processes Attendance Sheet 1 (OMR-based) and returns a list of candidate records.
    """
    img = cv2.imread(img_path)
    if img is None:
        raise ValueError(f"Failed to load image: {img_path}")
        
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 1. Align horizontally using the leftmost border
    expected_border_x = 87
    detected_border = detect_left_border(img, expected_border_x)
    if abs(detected_border - expected_border_x) > 55:
        shift = 0
    else:
        shift = detected_border - expected_border_x
        
    # 2. Set up row coordinates (6 candidate rows centers)
    y_centers = [580, 815, 1049, 1283, 1521, 1754]
    
    # Offsets relative to leftmost border
    px_offset = 423
    ax_offset = 473
    bubble_r = 10  # Increased radius to evaluate the full bubble circle
    
    sig_x0, sig_x1 = 330, 810
    omr_x0, omr_x1 = 1090, 1250

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
        
        # Check signature presence (bottom half of the row cell)
        sig_crop = img[yc+25:yc+105, sig_x0+shift : sig_x1+shift]
        signature_present = check_signature_present(sig_crop)

        # Refined bubble logic
        is_p_marked = p_mean < 135
        is_a_marked = a_mean < 135
        
        if is_p_marked and is_a_marked:
            if signature_present:
                status = "Present"
            else:
                if p_mean < a_mean - 15:
                    status = "Present"
                elif a_mean < p_mean - 15:
                    status = "Absent"
                else:
                    status = "Double Marked"
        elif is_p_marked:
            status = "Present"
        elif is_a_marked:
            status = "Absent"
        else:
            status = "Not Marked"
            
        # B. OMR Number OCR (Printed)
        omr_crop = img[yc-20:yc+20, omr_x0+shift : omr_x1+shift]
        omr_no = ""
        if omr_crop.size > 0:
            # Upscale 2x with cubic interpolation for 100% accuracy on printed text
            omr_crop_large = cv2.resize(omr_crop, (0,0), fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
            omr_txt = reader.readtext(omr_crop_large, detail=0, allowlist="0123456789")
            if omr_txt:
                joined = "".join(omr_txt).strip()
                digits = "".join(c for c in joined if c.isdigit())
                if len(digits) >= 6:
                    omr_no = digits

        # C. Registration Number OCR (using same logic as OMR no)
        reg_x0, reg_x1 = 830, 1030
        reg_crop = img[yc-20:yc+20, reg_x0+shift : reg_x1+shift]
        reg_no = ""
        if reg_crop.size > 0:
            reg_crop_large = cv2.resize(reg_crop, (0,0), fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
            reg_txt = reader.readtext(reg_crop_large, detail=0, allowlist="0123456789")
            if reg_txt:
                joined = "".join(reg_txt).strip()
                digits = "".join(c for c in joined if c.isdigit())
                if len(digits) >= 6:
                    reg_no = digits
            
            if not reg_no or len(reg_no) < 6:
                handwritten = read_handwritten_reg_no_9(reg_crop)
                if len(handwritten) >= 6:
                    reg_no = handwritten
                
        records.append({
            "row_number": idx + 1,
            "status": status,
            "signature_present": signature_present,
            "registration_no": reg_no,
            "omr_no": omr_no
        })
        
    # Extract header codes
    header = extract_header_codes(img, reader)
    header["invigilator_signed"] = int(check_invigilator_signature_present(img))
    return records, header
