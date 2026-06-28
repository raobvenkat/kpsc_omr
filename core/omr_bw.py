"""
core/omr_bw.py
--------------
Processes B&W scanned sheets (100001-100004 style).
SAME proven bubble algorithm as omr_color.py.
Only difference: signature detection uses dark pixel + border removal (no HSV).
"""

import os
import cv2
import numpy as np
from pyzbar.pyzbar import decode

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import get_omr_template

_MODEL_PATH = os.path.join(os.path.dirname(__file__), "mnist-8.onnx")
_ort_session = None
_onnx_available = False
try:
    import onnxruntime as ort
    _onnx_available = True
except ImportError:
    pass

def _get_ort_session():
    global _ort_session
    if _ort_session is None and _onnx_available:
        _ort_session = ort.InferenceSession(_MODEL_PATH)
    return _ort_session


# ──────────────────────────────────────────────────────────
# SIGNATURE DETECTION  (B&W: dark pixels minus box borders)
# ──────────────────────────────────────────────────────────

def check_ink_present_bw(crop_img, ratio_threshold=0.001):
    """
    Detects pen or pencil handwriting in a B&W scan.
    Removes box border lines morphologically before checking for ink.
    Lower threshold (0.001) catches faint pencil marks.
    """
    if crop_img is None or crop_img.size == 0:
        return False, 0.0
    gray = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY) if len(crop_img.shape) == 3 else crop_img.copy()
    gray_norm = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)
    _, dark_mask = cv2.threshold(gray_norm, 200, 255, cv2.THRESH_BINARY_INV)
    # Remove long horizontal/vertical border lines
    h_lines = cv2.morphologyEx(dark_mask, cv2.MORPH_OPEN,
                                cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1)))
    v_lines = cv2.morphologyEx(dark_mask, cv2.MORPH_OPEN,
                                cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40)))
    ink_mask = cv2.bitwise_and(dark_mask, cv2.bitwise_not(cv2.bitwise_or(h_lines, v_lines)))
    ink_mask = cv2.morphologyEx(ink_mask, cv2.MORPH_OPEN,
                                 cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2)))
    ratio = np.sum(ink_mask > 0) / ink_mask.size
    return bool(ratio > ratio_threshold), float(ratio)


# ──────────────────────────────────────────────────────────
# GRID ALIGNMENT  (B&W: grayscale only, no HSV)
# ──────────────────────────────────────────────────────────

def find_handwritten_box_bw(img, tpl, scale_x, scale_y):
    h, w = img.shape[:2]
    right_half = img[:, w // 2:]
    gray_half = cv2.cvtColor(right_half, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray_half, 180, 255, cv2.THRESH_BINARY_INV)

    box_conf = tpl["handwritten_box_contour"]
    w_min = int(box_conf["w_min"] * scale_x * 0.8)
    w_max = int(box_conf["w_max"] * scale_x * 1.4)
    h_min = int(box_conf["h_min"] * scale_y * 0.8)
    h_max = int(box_conf["h_max"] * scale_y * 1.25)

    contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    candidates = []
    for c in contours:
        rx, ry, rw, rh = cv2.boundingRect(c)
        if w_min <= rw <= w_max and h_min <= rh <= h_max and ry < int(500 * scale_y):
            candidates.append((w // 2 + rx, ry, rw, rh))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[1])
    bx, by, bw, bh = candidates[0]
    if bw > box_conf["w_max"] * scale_x * 1.05:
        label_w = bw - int(630 * scale_x)
        bx += label_w; bw -= label_w
    return bx, by, bw, bh


def find_header_origin_bw(img, tpl, scale_x, scale_y):
    import cv2
    h, w = img.shape[:2]
    right_half = img[:, w // 2:]
    gray_half = cv2.cvtColor(right_half, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray_half, 180, 255, cv2.THRESH_BINARY_INV)

    contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    for c in contours:
        rx, ry, rw, rh = cv2.boundingRect(c)
        if rw > 400 * scale_x and 60 * scale_y < rh < 150 * scale_y and ry < 300 * scale_y:
            return w // 2 + rx, ry, rw, rh
    return None


def _get_dynamic_spacing(w):
    col_spacing = 60.5 + 0.03095 * (w - 1620)
    row_spacing = 29.0 + 0.01390 * (w - 1620)
    return col_spacing, row_spacing


def _snap_grid_bw(img, b_conf, grid_x_guess, grid_y_guess, scale_x, scale_y):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    x_start = grid_x_guess - int(30 * scale_x)
    x_end   = grid_x_guess + int(420 * scale_x)
    min_dim = int(8 * scale_x)
    max_dim = int(35 * scale_x)
    
    centroids = []
    for c in contours:
        x, y, rw, rh = cv2.boundingRect(c)
        if x_start <= x <= x_end:
            if 0.7 <= rw / float(rh) <= 1.4 and min_dim <= rw <= max_dim and min_dim <= rh <= max_dim:
                M = cv2.moments(c)
                if M['m00'] != 0:
                    centroids.append((int(M['m10']/M['m00']), int(M['m01']/M['m00'])))
                    
    col_spacing = b_conf['col_spacing'] * scale_x
    row_spacing = b_conf['row_spacing'] * scale_y
    col_start = b_conf['col_start_offset'] * scale_x
    row_start = b_conf['row_start_offset'] * scale_y
    
    if not centroids:
        return grid_x_guess, grid_y_guess, row_spacing
        
    C = np.array(centroids, dtype=np.float32)
    T = np.array([[col_start + i*col_spacing, row_start + j*row_spacing]
                  for i in range(b_conf["cols"]) for j in range(b_conf["rows"])], dtype=np.float32)

    match_thresh2 = (8 * scale_x) ** 2
    penalty_dist2 = (15 * scale_x) ** 2
    best_tx, best_ty, max_score, best_avg = 0, 0, -1, 999999

    shifts_y, shifts_x = np.meshgrid(np.arange(-35, 35), np.arange(-35, 35), indexing='ij')
    for tx, ty in np.stack([shifts_x, shifts_y], axis=-1).reshape(-1, 2):
        P = T + [grid_x_guess + tx, grid_y_guess + ty]
        dist2 = np.sum((P[:, np.newaxis, :] - C[np.newaxis, :, :]) ** 2, axis=2)
        min_d2 = np.min(dist2, axis=1)
        score = int(np.sum(min_d2 < match_thresh2))
        avg_d2 = float(np.mean(np.where(min_d2 < match_thresh2, min_d2, penalty_dist2)))
        if score > max_score or (score == max_score and avg_d2 < best_avg):
            max_score, best_avg, best_tx, best_ty = score, avg_d2, tx, ty

    return grid_x_guess + best_tx, grid_y_guess + best_ty, row_spacing



# ──────────────────────────────────────────────────────────
# BUBBLE READING  — SAME PROVEN LOGIC AS omr_color.py
# ──────────────────────────────────────────────────────────

def read_bubbles_bw(img, tpl, scale_x, scale_y):
    """
    Reads OMR bubbles from a B&W scan.
    KEY: uses scale_y for col/row spacing (B&W scans scale differently in x vs y).
    - Filled column  ->  digit "0"-"9"
    - Empty column   ->  space " "
    """
    box = find_handwritten_box_bw(img, tpl, scale_x, scale_y)
    if box:
        bx, by, bw, bh = box
        dx, dy = tpl["grid_offset_from_box"]
        grid_x = bx + int(dx * scale_x)
        grid_y = by + int(dy * scale_y)
        align_method = "boxes_contour"
    else:
        origin = find_header_origin_bw(img, tpl, scale_x, scale_y)
        if origin:
            ox, oy, ow, oh = origin
            grid_x = int(tpl["grid_hardcoded_fallback"][0] * scale_x)
            grid_y = oy + oh + int(160 * scale_y)
            align_method = "dont_tamper_origin"
        else:
            fx, fy = tpl["grid_hardcoded_fallback"]
            grid_x = int(fx * scale_x)
            grid_y = int(fy * scale_y)
            align_method = "hardcoded_fallback"

    grid_x, grid_y, _ = _snap_grid_bw(img, tpl["bubble_grid"], grid_x, grid_y, scale_x, scale_y)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    b_conf = tpl["bubble_grid"]
    # CRITICAL: use scale_y for spacing (not scale_x) - proven by measurement
    col_spacing = b_conf["col_spacing"] * scale_y
    row_spacing = b_conf["row_spacing"] * scale_y
    col_start   = b_conf["col_start_offset"] * scale_y
    row_start   = b_conf["row_start_offset"] * scale_y
    r = int(max(3, b_conf["sample_radius"] * scale_y))

    img_draw = img.copy()
    detected_digits = []

    for i in range(b_conf["cols"]):
        cx = int(grid_x + col_start + i * col_spacing)
        col_vals = []
        for j in range(b_conf["rows"]):
            cy = int(grid_y + row_start + j * row_spacing)
            cell = gray[max(0, cy-r):min(gray.shape[0], cy+r),
                        max(0, cx-r):min(gray.shape[1], cx+r)]
            avg = float(np.mean(cell)) if cell.size > 0 else 255.0
            col_vals.append((j, avg))

        col_vals_sorted = sorted(col_vals, key=lambda x: x[1])
        min_idx, min_val = col_vals_sorted[0]
        avg_unmarked = float(np.mean([v for _, v in col_vals_sorted[2:]])) if len(col_vals_sorted) > 2 else 255.0
        contrast = col_vals_sorted[1][1] - col_vals_sorted[0][1]

        is_filled = (avg_unmarked - min_val > 25) and (contrast > 12)
        detected_digits.append(str(min_idx) if is_filled else " ")

        for j, _ in col_vals:
            cy = int(grid_y + row_start + j * row_spacing)
            if j == min_idx:
                cv2.circle(img_draw, (cx, cy), int(10*scale_y), (0,255,0) if is_filled else (0,0,255), -1)
            else:
                cv2.circle(img_draw, (cx, cy), int(6*scale_y), (255,0,0), 1)

    bubble_regno = "".join(detected_digits)
    h_d, w_d = img_draw.shape[:2]
    debug = img_draw[max(0, int(grid_y-80*scale_y)):min(h_d, int(grid_y+320*scale_y)),
                     max(0, int(grid_x-20*scale_x)):min(w_d, int(grid_x+580*scale_x))]
    return bubble_regno, debug, align_method


# ──────────────────────────────────────────────────────────
# WRITTEN REGNO OCR  (MNIST per digit cell)
# ──────────────────────────────────────────────────────────

def _ocr_cell_bw(cell_img, trim_ratio=0.10):
    """
    Predicts a single handwritten/pencil digit from a B&W scanned cell.
    Uses proper MNIST preprocessing (center of mass/bounding box in 20x20).
    """
    if cell_img.size == 0:
        return " "

    # 1. Convert to grayscale
    if len(cell_img.shape) == 3:
        gray = cv2.cvtColor(cell_img, cv2.COLOR_BGR2GRAY)
    else:
        gray = cell_img.copy()

    # Check for blue ink
    if len(cell_img.shape) == 3:
        hsv = cv2.cvtColor(cell_img, cv2.COLOR_BGR2HSV)
        lower_blue = np.array([90, 40, 40])
        upper_blue = np.array([140, 255, 255])
        blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)
        if np.sum(blue_mask > 0) > 15:
            gray_clean = np.ones_like(gray) * 255
            gray_clean[blue_mask > 0] = gray[blue_mask > 0]
        else:
            gray_clean = gray.copy()
    else:
        gray_clean = gray.copy()

    # 2. Trim outer border pixels
    h, w = gray_clean.shape[:2]
    margin_y = max(1, int(h * trim_ratio))
    margin_x = max(1, int(w * trim_ratio))
    gray_trimmed = gray_clean[margin_y:-margin_y, margin_x:-margin_x]
    h_t, w_t = gray_trimmed.shape

    # 3. Blank cell detection (low contrast check before normalization)
    min_val, max_val, _, _ = cv2.minMaxLoc(gray_trimmed)
    contrast = max_val - min_val
    if contrast < 40:
        return " "

    # 4. Normalize and binarize
    gray_norm = cv2.normalize(gray_trimmed, None, 0, 255, cv2.NORM_MINMAX)
    _, binary_inv = cv2.threshold(gray_norm, 160, 255, cv2.THRESH_BINARY_INV)

    # 5. Keep only the largest connected component (the digit stroke)
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary_inv, connectivity=8)
    if num_labels <= 1:
        return " "
        
    # Topological border erasure
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
        return " "

    largest_label = 1 + np.argmax(stats2[1:, cv2.CC_STAT_AREA])
    largest_area = stats2[largest_label, cv2.CC_STAT_AREA]
    if largest_area < 8:
        return " "
        
    cell_mask = (labels2 == largest_label).astype(np.uint8) * 255

    # 6. Bounding box crop for MNIST centering
    y_indices, x_indices = np.where(cell_mask > 0)
    if len(y_indices) == 0 or len(x_indices) == 0:
        return " "

    y_min, y_max = np.min(y_indices), np.max(y_indices)
    x_min, x_max = np.min(x_indices), np.max(x_indices)

    digit_crop = cell_mask[y_min:y_max+1, x_min:x_max+1]
    h_c, w_c = digit_crop.shape
    if h_c == 0 or w_c == 0:
        return " "

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

    session = _get_ort_session()
    if session is None:
        return "?"

    outputs = session.run(None, {"Input3": canvas.reshape(1, 1, 28, 28)})
    return str(int(np.argmax(outputs[0])))


def _detect_bubbles_centroids_bw(img, scale):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    detected_centroids = []
    min_dim = int(8 * scale)
    max_dim = int(24 * scale)
    
    for c in contours:
        x, y, rw, rh = cv2.boundingRect(c)
        aspect_ratio = rw / float(rh)
        if 0.7 <= aspect_ratio <= 1.4 and min_dim <= rw <= max_dim and min_dim <= rh <= max_dim:
            M = cv2.moments(c)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                detected_centroids.append((cx, cy))
    return detected_centroids

def _align_grid_decoupled_bw(img, tpl, scale, barcode_rect):
    h, w, _ = img.shape
    barcode_left = w//2 + barcode_rect.left
    est_grid_x = int(barcode_left - 66 * scale)
    est_grid_y = int(barcode_rect.top + 293 * scale)
    
    detected_centroids = _detect_bubbles_centroids_bw(img, scale)
    if not detected_centroids:
        return est_grid_x, est_grid_y
        
    b_conf = tpl["bubble_grid"]
    col_spacing = b_conf["col_spacing"] * scale
    col_start = b_conf["col_start_offset"] * scale
    
    best_tx = 0
    max_score_x = -1
    best_avg_dist_x = 999999
    
    for tx in range(-50, 50):
        score = 0
        dist_sum = 0
        for i in range(b_conf["cols"]):
            cx_tpl = est_grid_x + col_start + i * col_spacing + tx
            dists = [abs(c[0] - cx_tpl) for c in detected_centroids]
            min_dist = min(dists) if dists else 999
            if min_dist < 6 * scale:
                score += 1
                dist_sum += min_dist
        if score > max_score_x or (score == max_score_x and dist_sum < best_avg_dist_x):
            max_score_x = score
            best_avg_dist_x = dist_sum
            best_tx = tx
            
    aligned_grid_x = est_grid_x + best_tx
    
    best_ty = 0
    max_score_y = -1
    best_avg_dist_y = 999999
    
    match_thresh2 = (8 * scale) ** 2
    penalty_dist2 = (15 * scale) ** 2
    
    template_points = []
    for i in range(b_conf["cols"]):
        cx = col_start + i * col_spacing
        for j in range(b_conf["rows"]):
            cy = b_conf["row_start_offset"] * scale + j * b_conf["row_spacing"] * scale
            template_points.append([cx, cy])
    T = np.array(template_points, dtype=np.float32)
    C = np.array(detected_centroids, dtype=np.float32)
    
    for ty in range(-80, 80):
        P = T + [aligned_grid_x, est_grid_y + ty]
        diff = P[:, np.newaxis, :] - C[np.newaxis, :, :]
        dist2 = np.sum(diff**2, axis=2)
        min_dist2 = np.min(dist2, axis=1)
        
        score = np.sum(min_dist2 < match_thresh2)
        effective_dist2 = np.where(min_dist2 < match_thresh2, min_dist2, penalty_dist2)
        avg_dist2 = np.mean(effective_dist2)
        
        if score > max_score_y or (score == max_score_y and avg_dist2 < best_avg_dist_y):
            max_score_y = score
            best_avg_dist_y = avg_dist2
            best_ty = ty
            
    aligned_grid_y = est_grid_y + best_ty
    return aligned_grid_x, aligned_grid_y

def read_written_regno_bw(img, tpl, scale_x, scale_y):
    """Reads 9 handwritten digit cells by extracting directly above the bubble grid."""
    h, w = img.shape[:2]
    right_half = img[:, w//2:]
    decoded = decode(right_half)
    if not decoded:
        return " " * 9
        
    barcode_rect = decoded[0].rect
    scale = 1.15 if w > 1800 else 0.97
    grid_x, grid_y = _align_grid_decoupled_bw(img, tpl, scale, barcode_rect)
    
    b_conf = tpl["bubble_grid"]
    col_spacing = b_conf["col_spacing"] * scale_x
    
    box_cy = grid_y - int(26 * scale_y)
    box_h = int(45 * scale_y)
    box_w = int(col_spacing * 0.85)
    
    col_start = b_conf["col_start_offset"] * scale_x
    
    digits = []
    for i in range(9):
        cx = int(grid_x + col_start + i * col_spacing)
        x1 = int(cx - box_w // 2)
        x2 = int(cx + box_w // 2)
        y1 = int(box_cy - box_h // 2)
        y2 = int(box_cy + box_h // 2)
        
        cell = img[max(0, y1):min(img.shape[0], y2), max(0, x1):min(img.shape[1], x2)]
        digits.append(_ocr_cell_bw(cell) if cell.size > 0 else " ")
        
    return "".join(digits)


# ──────────────────────────────────────────────────────────
# MAIN PROCESSOR
# ──────────────────────────────────────────────────────────

def process_bw_omr_sheet(img_path, output_dir, file_prefix):
    img = cv2.imread(img_path)
    if img is None:
        raise FileNotFoundError(f"Cannot load: {img_path}")
    h, w = img.shape[:2]
    tpl = get_omr_template(w)
    # B&W scans: use SEPARATE x and y scales (image may be squeezed/stretched differently)
    scale_x = w / tpl["target_width"]
    h_target = 1080 if tpl["name"] == "standard" else 784
    scale_y = h / h_target

    def sc(t): return int(t[0]*scale_y), int(t[1]*scale_y), int(t[2]*scale_x), int(t[3]*scale_x)
    def crop(t): y0,y1,x0,x1=sc(t); return img[y0:y1, x0:x1]

    barcode_crop  = crop(tpl["barcode"])
    reg_box_crop  = crop(tpl["reg_boxes"])
    qca_crop      = crop(tpl["qca"])
    cand_sig_save = crop(tpl["cand_sig_save"])
    inv_sig_save  = crop(tpl["inv_sig_save"])

    decoded = decode(barcode_crop)
    barcode_val = decoded[0].data.decode("utf-8") if decoded else "Not Detected"

    cand_signed, cand_ratio = check_ink_present_bw(crop(tpl["cand_sig_detect"]), ratio_threshold=0.001)
    inv_signed,  inv_ratio  = check_ink_present_bw(crop(tpl["inv_sig_detect"]),  ratio_threshold=0.001)

    bubble_regno, debug_img, align_method = read_bubbles_bw(img, tpl, scale_x, scale_y)
    written_regno = read_written_regno_bw(img, tpl, scale_x, scale_y)

    os.makedirs(output_dir, exist_ok=True)
    paths = {k: os.path.join(output_dir, f"{file_prefix}_{k}.png")
             for k in ["cand_sig","inv_sig","barcode","reg_boxes","qca","debug_grid"]}
    cv2.imwrite(paths["cand_sig"],   cand_sig_save)
    cv2.imwrite(paths["inv_sig"],    inv_sig_save)
    cv2.imwrite(paths["barcode"],    barcode_crop)
    cv2.imwrite(paths["reg_boxes"],  reg_box_crop)
    cv2.imwrite(paths["qca"],        qca_crop)
    if debug_img is not None and debug_img.size > 0:
        cv2.imwrite(paths["debug_grid"], debug_img)

    return {
        "filename": os.path.basename(img_path),
        "written_register_number": written_regno,
        "bubble_register_number":  bubble_regno,
        "barcode":                 barcode_val,
        "candidate_signed":        cand_signed,
        "candidate_ink_ratio":     round(cand_ratio, 6),
        "invigilator_signed":      inv_signed,
        "invigilator_ink_ratio":   round(inv_ratio, 6),
        "align_method":            align_method,
        "template_used":           tpl["name"],
        **{f"{k}_image": v for k, v in paths.items()}
    }
