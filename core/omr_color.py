"""
core/omr_color.py
-----------------
Processes COLOR OMR sheets (100005-100010 style).
Uses the proven bubble reading logic — DO NOT change the bubble algorithm.
Only addition: written register number via MNIST OCR.
"""

import os
import cv2
import numpy as np
from pyzbar.pyzbar import decode

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import get_omr_template

# Optional MNIST ONNX model for written digit OCR
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
# SIGNATURE DETECTION  (color: blue ink + dark, exclude red)
# ──────────────────────────────────────────────────────────

def check_ink_present(crop_img, ratio_threshold=0.002):
    if crop_img is None or crop_img.size == 0:
        return False, 0.0
    h_c, w_c = crop_img.shape[:2]
    # Crop inner 80% to avoid borders
    crop_inner = crop_img[int(h_c*0.1):int(h_c*0.9), int(w_c*0.1):int(w_c*0.9)]
    
    # Red mask to ignore the printed red text
    import numpy as np
    import cv2
    hsv = cv2.cvtColor(crop_inner, cv2.COLOR_BGR2HSV)
    lower_red1 = np.array([0, 30, 40]);  upper_red1 = np.array([15, 255, 255])
    lower_red2 = np.array([165, 30, 40]); upper_red2 = np.array([180, 255, 255])
    red_mask = cv2.bitwise_or(cv2.inRange(hsv, lower_red1, upper_red1),
                               cv2.inRange(hsv, lower_red2, upper_red2))
    
    gray = cv2.cvtColor(crop_inner, cv2.COLOR_BGR2GRAY)
    gray_norm = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)
    _, binary = cv2.threshold(gray_norm, 180, 255, cv2.THRESH_BINARY_INV)
    
    # Ignore red text from the binary mask
    binary = cv2.bitwise_and(binary, cv2.bitwise_not(red_mask))
    
    ratio = np.sum(binary > 0) / binary.size
    return bool(ratio > ratio_threshold), float(ratio)




# ──────────────────────────────────────────────────────────
# GRID ALIGNMENT  (color: HSV red contour → grayscale fallback)
# ──────────────────────────────────────────────────────────

def find_handwritten_box(img, tpl, scale):
    h, w = img.shape[:2]
    right_half = img[:, w // 2:]
    hsv = cv2.cvtColor(right_half, cv2.COLOR_BGR2HSV)
    red_mask = cv2.bitwise_or(
        cv2.inRange(hsv, np.array([0, 25, 40]),   np.array([15, 255, 255])),
        cv2.inRange(hsv, np.array([165, 25, 40]), np.array([180, 255, 255]))
    )
    box_conf = tpl["handwritten_box_contour"]
    w_min = int(box_conf["w_min"] * scale * 0.8)
    w_max = int(box_conf["w_max"] * scale * 1.4)
    h_min = int(box_conf["h_min"] * scale * 0.8)
    h_max = int(box_conf["h_max"] * scale * 1.25)

    def _pick(mask):
        contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        candidates = []
        for c in contours:
            rx, ry, rw, rh = cv2.boundingRect(c)
            if w_min <= rw <= w_max and h_min <= rh <= h_max and ry < int(320 * scale):
                candidates.append((w // 2 + rx, ry, rw, rh))
        if not candidates:
            return None
        candidates.sort(key=lambda x: x[1])
        bx, by, bw, bh = candidates[0]
        if bw > box_conf["w_max"] * scale * 1.05:
            label_w = bw - int(630 * scale)
            bx += label_w; bw -= label_w
        return bx, by, bw, bh

    result = _pick(red_mask)
    if result:
        return result
    # Grayscale fallback
    gray_half = cv2.cvtColor(right_half, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray_half, 180, 255, cv2.THRESH_BINARY_INV)
    return _pick(thresh)


def find_header_origin(img, tpl, scale):
    h, w = img.shape[:2]
    right_half = img[:, w // 2:]
    hsv = cv2.cvtColor(right_half, cv2.COLOR_BGR2HSV)
    red_mask = cv2.bitwise_or(
        cv2.inRange(hsv, np.array([0, 25, 40]),   np.array([15, 255, 255])),
        cv2.inRange(hsv, np.array([165, 25, 40]), np.array([180, 255, 255]))
    )
    h_conf = tpl["header_contour"]
    w_min = int(h_conf["w_min"] * scale * 0.8)
    h_min = int(h_conf["h_min"] * scale * 0.8)

    def _pick(mask):
        contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        candidates = []
        for c in contours:
            rx, ry, rw, rh = cv2.boundingRect(c)
            if rw > w_min and rh > h_min and ry < int(250 * scale):
                candidates.append((w // 2 + rx, ry, rw, rh))
        if not candidates:
            return None
        candidates.sort(key=lambda x: (x[1], x[0]))
        return candidates[0]

    result = _pick(red_mask)
    if result:
        return result
    gray_half = cv2.cvtColor(right_half, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray_half, 180, 255, cv2.THRESH_BINARY_INV)
    candidates = []
    contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    for c in contours:
        rx, ry, rw, rh = cv2.boundingRect(c)
        if rw > w_min and rh > h_min and rw < w * 0.9 and rh < h * 0.5:
            candidates.append((w // 2 + rx, ry, rw, rh))
    if candidates:
        candidates.sort(key=lambda x: (x[1], x[0]))
        return candidates[0]
    return None


def _get_dynamic_spacing(w):
    col_spacing = 60.5 + 0.03095 * (w - 1620)
    row_spacing = 29.0 + 0.01390 * (w - 1620)
    return col_spacing, row_spacing


def _align_grid_snapping(img, tpl, scale, bx, by, bw, bh):
    """Snaps grid to detected bubble centroids using QCA offset logic."""
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    qca_y = None
    for c in contours:
        rx, ry, rw, rh = cv2.boundingRect(c)
        if rw > 400 * scale and rh > 60 * scale and ry > 500 * scale and rx > 400 * scale:
            qca_y = ry
            break

    b_conf = tpl["bubble_grid"]
    col_spacing = b_conf["col_spacing"] * scale
    col_start = b_conf["col_start_offset"] * scale
    row_start = b_conf["row_start_offset"] * scale
    dx, dy = tpl["grid_offset_from_box"]
    est_grid_x = bx + int(dx * scale)
    est_grid_y = by + int(dy * scale)

    if qca_y is None:
        row_spacing = b_conf["row_spacing"] * scale
        return est_grid_x, est_grid_y, col_spacing, row_spacing, col_start, row_start, "no_qca_fallback"

    x_start = est_grid_x - int(30 * scale)
    x_end   = est_grid_x + int(420 * scale)
    min_dim = int(8 * scale)
    max_dim = int(35 * scale)

    centroids = []
    for c in contours:
        x, y, rw, rh = cv2.boundingRect(c)
        if x_start <= x <= x_end:
            if 0.7 <= rw / float(rh) <= 1.4 and min_dim <= rw <= max_dim and min_dim <= rh <= max_dim:
                M = cv2.moments(c)
                if M["m00"] != 0:
                    centroids.append((int(M["m10"]/M["m00"]), int(M["m01"]/M["m00"])))

    centroids.sort(key=lambda c: c[1])
    rows = []
    current_row = []
    for cx, cy in centroids:
        if not current_row:
            current_row.append((cx, cy))
        else:
            if cy - current_row[0][1] <= 15 * scale:
                current_row.append((cx, cy))
            else:
                if len(current_row) >= 5:
                    rows.append({'cy': np.median([c[1] for c in current_row]), 'centroids': current_row})
                current_row = [(cx, cy)]
    if len(current_row) >= 5:
        rows.append({'cy': np.median([c[1] for c in current_row]), 'centroids': current_row})

    best_seq = []
    for i in range(len(rows)):
        seq = [rows[i]]
        for j in range(i+1, len(rows)):
            diff = rows[j]['cy'] - seq[-1]['cy']
            if 22 * scale <= diff <= 38 * scale:
                seq.append(rows[j])
            elif diff > 38 * scale:
                break
        if len(seq) > len(best_seq):
            best_seq = seq

    if len(best_seq) < 10:
        row_spacing = b_conf["row_spacing"] * scale
        return est_grid_x, est_grid_y, col_spacing, row_spacing, col_start, row_start, "no_seq_fallback"

    row_spacing = float(np.median(np.diff([r['cy'] for r in best_seq])))
    target_y = qca_y - 322 * scale
    bubbles_y = min(best_seq, key=lambda r: abs(r['cy'] - target_y))['cy']
    grid_y = bubbles_y - row_start

    T = []
    for i in range(b_conf["cols"]):
        for j in range(b_conf["rows"]):
            T.append([col_start + i * col_spacing, j * row_spacing])
    T = np.array(T)
    C = np.array([c for r in best_seq for c in r['centroids']])

    match_thresh2 = (8 * scale) ** 2
    best_x = est_grid_x
    max_score = -1

    for tx in range(-45, 46):
        P = T + [est_grid_x + tx, bubbles_y - row_start]
        dist2 = np.sum((P[:, np.newaxis, :] - C[np.newaxis, :, :]) ** 2, axis=2)
        score = int(np.sum(np.min(dist2, axis=1) < match_thresh2))
        if score > max_score:
            max_score = score
            best_x = est_grid_x + tx

    return best_x, grid_y, col_spacing, row_spacing, col_start, row_start, f"snapped_{max_score}"


# ──────────────────────────────────────────────────────────
# BUBBLE READING  — PROVEN WORKING LOGIC, do not change
# ──────────────────────────────────────────────────────────

def read_bubbles(img, tpl, scale):
    """
    Reads OMR bubbles. Returns (bubble_regno, debug_img, align_method).
    - Filled column  ->  digit "0"-"9"
    - Empty column   ->  space " "
    THIS IS THE PROVEN WORKING ALGORITHM. Do not modify.
    """
    box = find_handwritten_box(img, tpl, scale)
    if box:
        bx, by, bw, bh = box
        grid_x, grid_y, col_spacing, row_spacing, col_start, row_start, method = \
            _align_grid_snapping(img, tpl, scale, bx, by, bw, bh)
        align_method = method
    else:
        origin = find_header_origin(img, tpl, scale)
        if origin:
            ox, oy, ow, oh = origin
            bx = ox + int(105 * scale); by = oy + int(142 * scale)
            bw = int(630 * scale);      bh = int(90 * scale)
            grid_x, grid_y, col_spacing, row_spacing, col_start, row_start, method = \
                _align_grid_snapping(img, tpl, scale, bx, by, bw, bh)
            align_method = "header_" + method
        else:
            dx, dy = tpl["grid_hardcoded_fallback"]
            grid_x, grid_y = int(dx * scale), int(dy * scale)
            col_spacing, row_spacing = _get_dynamic_spacing(img.shape[1])
            b_conf = tpl["bubble_grid"]
            col_start = b_conf["col_start_offset"] * (col_spacing / b_conf["col_spacing"])
            row_start = b_conf["row_start_offset"] * (row_spacing / b_conf["row_spacing"])
            align_method = "hardcoded_fallback"

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    b_conf = tpl["bubble_grid"]
    r = int(max(3, b_conf["sample_radius"] * scale))
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
                cv2.circle(img_draw, (cx, cy), int(10*scale), (0,255,0) if is_filled else (0,0,255), -1)
            else:
                cv2.circle(img_draw, (cx, cy), int(6*scale), (255,0,0), 1)

    bubble_regno = "".join(detected_digits)
    h_d, w_d = img_draw.shape[:2]
    debug = img_draw[max(0, int(grid_y-80*scale)):min(h_d, int(grid_y+320*scale)),
                     max(0, int(grid_x-20*scale)):min(w_d, int(grid_x+580*scale))]
    return bubble_regno, debug, align_method


# ──────────────────────────────────────────────────────────
# WRITTEN REGNO OCR  (MNIST per digit cell)
# ──────────────────────────────────────────────────────────

def _ocr_cell(cell_img, trim_ratio=0.10):
    """
    Predicts a single handwritten digit from a cell image on a color OMR.
    Filters out red printed borders before running MNIST preprocessing.
    """
    if cell_img.size == 0:
        return " "

    # 1. Convert to grayscale
    if len(cell_img.shape) == 3:
        gray = cv2.cvtColor(cell_img, cv2.COLOR_BGR2GRAY)
    else:
        gray = cell_img.copy()

    # 2. Trim outer border pixels
    h, w = gray.shape[:2]
    margin_y = max(1, int(h * trim_ratio))
    margin_x = max(1, int(w * trim_ratio))
    gray_trimmed = gray[margin_y:-margin_y, margin_x:-margin_x]
    h_t, w_t = gray_trimmed.shape

    # For color sheets, mask out red pixels
    hsv_crop = cv2.cvtColor(cell_img[margin_y:-margin_y, margin_x:-margin_x], cv2.COLOR_BGR2HSV)
    lower_red1 = np.array([0, 30, 40])
    upper_red1 = np.array([15, 255, 255])
    lower_red2 = np.array([165, 30, 40])
    upper_red2 = np.array([180, 255, 255])
    red_mask = cv2.bitwise_or(
        cv2.inRange(hsv_crop, lower_red1, upper_red1),
        cv2.inRange(hsv_crop, lower_red2, upper_red2)
    )
    gray_trimmed = gray_trimmed.copy()
    gray_trimmed[red_mask > 0] = 255

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


def _detect_bubbles_centroids_color(img, scale):
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

def _align_grid_decoupled_color(img, tpl, scale, barcode_rect):
    h, w, _ = img.shape
    barcode_left = w//2 + barcode_rect.left
    est_grid_x = int(barcode_left - 66 * scale)
    est_grid_y = int(barcode_rect.top + 293 * scale)
    
    detected_centroids = _detect_bubbles_centroids_color(img, scale)
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

def read_written_regno(img, tpl, scale):
    """Reads the 9 handwritten digit cells and returns a 9-char string (spaces for blank cells)."""
    h, w = img.shape[:2]
    right_half = img[:, w//2:]
    decoded = decode(right_half)
    if not decoded:
        return " " * 9
        
    barcode_rect = decoded[0].rect
    alignment_scale = 1.15 if w > 1800 else 0.97
    grid_x, grid_y = _align_grid_decoupled_color(img, tpl, alignment_scale, barcode_rect)
    
    b_conf = tpl["bubble_grid"]
    col_spacing = b_conf["col_spacing"] * scale
    
    box_cy = grid_y - int(26 * scale)
    box_h = int(45 * scale)
    box_w = int(col_spacing * 0.85)
    
    col_start = b_conf["col_start_offset"] * scale
    
    digits = []
    for i in range(9):
        cx = int(grid_x + col_start + i * col_spacing)
        x1 = int(cx - box_w // 2)
        x2 = int(cx + box_w // 2)
        y1 = int(box_cy - box_h // 2)
        y2 = int(box_cy + box_h // 2)
        
        cell = img[max(0, y1):min(img.shape[0], y2), max(0, x1):min(img.shape[1], x2)]
        digits.append(_ocr_cell(cell) if cell.size > 0 else " ")
    return "".join(digits)


# ──────────────────────────────────────────────────────────
# MAIN PROCESSOR
# ──────────────────────────────────────────────────────────

def process_color_omr_sheet(img_path, output_dir, file_prefix):
    img = cv2.imread(img_path)
    if img is None:
        raise FileNotFoundError(f"Cannot load: {img_path}")
    h, w = img.shape[:2]
    tpl = get_omr_template(w)
    scale = w / tpl["target_width"]

    def sc(t): return int(t[0]*scale), int(t[1]*scale), int(t[2]*scale), int(t[3]*scale)
    def crop(t): y0,y1,x0,x1=sc(t); return img[y0:y1, x0:x1]

    barcode_crop  = crop(tpl["barcode"])
    reg_box_crop  = crop(tpl["reg_boxes"])
    qca_crop      = crop(tpl["qca"])
    cand_sig_save = crop(tpl["cand_sig_save"])
    inv_sig_save  = crop(tpl["inv_sig_save"])

    decoded = decode(barcode_crop)
    barcode_val = decoded[0].data.decode("utf-8") if decoded else "Not Detected"

    cand_signed, cand_ratio = check_ink_present(crop(tpl["cand_sig_detect"]), tpl["signature_ink_threshold"])
    inv_signed,  inv_ratio  = check_ink_present(crop(tpl["inv_sig_detect"]),  tpl["signature_ink_threshold"])

    bubble_regno, debug_img, align_method = read_bubbles(img, tpl, scale)
    written_regno = read_written_regno(img, tpl, scale)

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
