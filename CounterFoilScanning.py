# Generated from: NewOMRExtract.ipynb
# Converted at: 2026-06-28T08:23:47.242Z
# Next step (optional): refactor into modules & generate tests with RunCell
# Quick start: pip install runcell

import os
import glob
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
try:
    import cv2
except Exception as e:
    raise ImportError(
        "OpenCV (cv2) is required but could not be imported.\n"
        "Install it via: pip install opencv-python or pip install opencv-python-headless\n"
        f"Original error: {e}"
    )
import numpy as np
from PIL import Image, ImageTk
from pyzbar.pyzbar import decode
import onnxruntime as ort
import easyocr
import torch
import audit

#import pytesseract
#pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Add parent directory to system path
# Added on 25/06/2026 by Venkat Rao
_READER = None
def get_ocr_reader():
    global _READER
    if _READER is None:
        use_gpu = torch.cuda.is_available()
        _READER = easyocr.Reader(['en'], gpu=use_gpu)
    return _READER

print("CUDA available:", torch.cuda.is_available())


if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))
else:
    print("Using CPU")

try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    BASE_DIR = os.getcwd()

#sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
from config import get_omr_template
from core.omr_color import read_bubbles as read_bubbles_color, read_written_regno as read_written_regno_color, find_handwritten_box as find_handwritten_box_color, check_ink_present as check_ink_present_color
from core.omr_bw import check_ink_present_bw, find_handwritten_box_bw

# Global model session cache
_MNIST_SESSION = None
#_MNIST_MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "core", "mnist-8.onnx")
_MNIST_MODEL_PATH = os.path.join(BASE_DIR, "core", "mnist-8.onnx")
def get_mnist_session():
    global _MNIST_SESSION
    if _MNIST_SESSION is None:
        if os.path.exists(_MNIST_MODEL_PATH):
            _MNIST_SESSION = ort.InferenceSession(_MNIST_MODEL_PATH)
        else:
            raise FileNotFoundError(f"ONNX Model not found at: {_MNIST_MODEL_PATH}")
    return _MNIST_SESSION

# ──────────────────────────────────────────────────────────
# SIGNATURE DETECTION
# ──────────────────────────────────────────────────────────
def check_ink_present_unified(crop_img, is_bw):
    if crop_img is None or crop_img.size == 0:
        return False, 0.0
    
    if not is_bw:
        hsv = cv2.cvtColor(crop_img, cv2.COLOR_BGR2HSV)
        lower_red1 = np.array([0, 30, 40]);  upper_red1 = np.array([15, 255, 255])
        lower_red2 = np.array([165, 30, 40]); upper_red2 = np.array([180, 255, 255])
        red_mask = cv2.bitwise_or(cv2.inRange(hsv, lower_red1, upper_red1),
                                   cv2.inRange(hsv, lower_red2, upper_red2))
        
        h_c, w_c = crop_img.shape[:2]
        crop_inner = crop_img[int(h_c*0.05):int(h_c*0.95), int(w_c*0.05):int(w_c*0.95)]
        red_mask_inner = red_mask[int(h_c*0.05):int(h_c*0.95), int(w_c*0.05):int(w_c*0.95)]
        
        gray = cv2.cvtColor(crop_inner, cv2.COLOR_BGR2GRAY)
        gray_norm = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)
        _, dark_mask = cv2.threshold(gray_norm, 180, 255, cv2.THRESH_BINARY_INV)
        dark_mask = cv2.bitwise_and(dark_mask, cv2.bitwise_not(red_mask_inner))
    else:
        h_c, w_c = crop_img.shape[:2]
        crop_inner = crop_img[int(h_c*0.05):int(h_c*0.95), int(w_c*0.05):int(w_c*0.95)]
        gray = cv2.cvtColor(crop_inner, cv2.COLOR_BGR2GRAY) if len(crop_inner.shape) == 3 else crop_inner.copy()
        gray_norm = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)
        _, dark_mask = cv2.threshold(gray_norm, 200, 255, cv2.THRESH_BINARY_INV)
        
    h_lines = cv2.morphologyEx(dark_mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1)))
    v_lines = cv2.morphologyEx(dark_mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40)))
    ink_mask = cv2.bitwise_and(dark_mask, cv2.bitwise_not(cv2.bitwise_or(h_lines, v_lines)))
    ink_mask = cv2.morphologyEx(ink_mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2)))
    
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(ink_mask, connectivity=8)
    if num_labels <= 1:
        return False, 0.0
        
    areas = sorted(stats[1:, cv2.CC_STAT_AREA].tolist(), reverse=True)
    large_components = sum(1 for a in areas if a >= 30)
    # ✅ FIX: Calculate ink density
    ink_density = np.sum(ink_mask > 0) / float(ink_mask.size)
    is_signed = large_components >= 2 and ink_density > 0.003
    ratio = float(areas[0]) / ink_mask.size if areas else 0.0
    return bool(is_signed), ratio

def align_grid_perfect(img, tpl, scale_x, scale_y, box, is_bw):
    bx, by, bw, bh = box
    est_grid_x = bx + int(19 * scale_x)
    est_grid_y = by + int(208 * scale_y)
    
    detected_centroids = detect_bubbles_centroids(img, scale_x)
    
    b_conf = tpl["bubble_grid"]
    col_spacing = b_conf["col_spacing"] * scale_x
    col_start = b_conf["col_start_offset"] * scale_x
    row_spacing = b_conf["row_spacing"] * scale_y
    row_start = b_conf["row_start_offset"] * scale_y
    
    best_tx = 0
    max_score_x = -1
    best_avg_dist_x = 999999
    
    for tx in range(-15, 15):
        score = 0
        dist_sum = 0
        for i in range(b_conf["cols"]):
            cx_tpl = est_grid_x + col_start + i * col_spacing + tx
            dists = [abs(c[0] - cx_tpl) for c in detected_centroids]
            min_dist = min(dists) if dists else 999
            if min_dist < 6 * scale_x:
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
    
    match_thresh2 = (8 * scale_y) ** 2
    penalty_dist2 = (15 * scale_y) ** 2
    
    template_points = []
    for i in range(b_conf["cols"]):
        cx = col_start + i * col_spacing
        for j in range(b_conf["rows"]):
            cy = row_start + j * row_spacing
            template_points.append([cx, cy])
    T = np.array(template_points, dtype=np.float32)
    C = np.array(detected_centroids, dtype=np.float32) if detected_centroids else np.empty((0, 2), dtype=np.float32)
    
    if len(C) > 0:
        for ty in range(-15, 15):
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
    else:
        best_ty = 0
        
    aligned_grid_y = est_grid_y + best_ty
    return aligned_grid_x, aligned_grid_y

def read_bubbles_custom(img, tpl, scale_x, scale_y, is_bw):
    if is_bw:
        box = find_handwritten_box_bw(img, tpl, scale_x, scale_y)
        grid_x, grid_y = align_grid_perfect(img, tpl, scale_x, scale_y, box, is_bw)
        align_method = "perfect_snapped_bw"
    else:
        box = find_handwritten_box_color(img, tpl, scale_x)
        bx, by, bw, bh = box
        grid_x = bx + int(19 * scale_x)
        grid_y = by + int(208 * scale_y)
        align_method = "box_direct_color"
        
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    b_conf = tpl["bubble_grid"]
    col_spacing = b_conf["col_spacing"] * scale_x
    row_spacing = b_conf["row_spacing"] * scale_y
    col_start = b_conf["col_start_offset"] * scale_x
    row_start = b_conf["row_start_offset"] * scale_y
    
    img_draw = img.copy()
    detected_digits = []
    bubble_Th_status = 0
    
    for i in range(b_conf["cols"]):
        cx = int(grid_x + col_start + i * col_spacing)
        col_vals = []
        for j in range(b_conf["rows"]):
            cy = int(grid_y + row_start + j * row_spacing)
            r = int(max(3, b_conf["sample_radius"] * scale_x))
            y_min_idx = max(0, cy - r)
            y_max_idx = min(gray.shape[0], cy + r)
            x_min_idx = max(0, cx - r)
            x_max_idx = min(gray.shape[1], cx + r)
            cell = gray[y_min_idx:y_max_idx, x_min_idx:x_max_idx]
            avg = np.mean(cell) if cell.size > 0 else 255
            col_vals.append((j, avg))
            
        col_vals_sorted = sorted(col_vals, key=lambda x: x[1])
        min_idx, min_val = col_vals_sorted[0]
        unmarked_vals = [x[1] for x in col_vals_sorted[2:]]
        avg_unmarked = np.mean(unmarked_vals) if unmarked_vals else 255
        contrast = col_vals_sorted[1][1] - col_vals_sorted[0][1]
        fill_percent = 0.0
        if avg_unmarked > 0:
            fill_percent = 100.0 * (avg_unmarked - min_val) / avg_unmarked
        
        is_filled = (avg_unmarked - min_val > 25) and (contrast > 12)
        if is_filled and fill_percent < 35.0:
            bubble_Th_status = 1
        
        if is_filled:
            detected_digits.append(str(min_idx))
        else:
            detected_digits.append(" ")
            
        for j in range(b_conf["rows"]):
            cy = int(grid_y + row_start + j * row_spacing)
            if j == min_idx:
                color = (0, 255, 0) if is_filled else (0, 0, 255)
                cv2.circle(img_draw, (cx, cy), int(10 * scale_x), color, -1)
            else:
                cv2.circle(img_draw, (cx, cy), int(6 * scale_x), (255, 0, 0), 1)
                
    bubble_regno = "".join(detected_digits)
    h_d, w_d, _ = img_draw.shape
    y_start_crop = max(0, int(grid_y - 80 * scale_y))
    y_end_crop = min(h_d, int(grid_y + 320 * scale_y))
    x_start_crop = max(0, int(grid_x - 20 * scale_x))
    x_end_crop = min(w_d, int(grid_x + 580 * scale_x))
    crop_debug = img_draw[y_start_crop:y_end_crop, x_start_crop:x_end_crop]
    
    return bubble_regno, crop_debug, grid_x, grid_y, align_method, bubble_Th_status

# ──────────────────────────────────────────────────────────
# DECOUPLED ALIGNMENT & BUBBLE READING (B&W PADDED FILES)
# ──────────────────────────────────────────────────────────
def detect_bubbles_centroids(img, scale):
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

def align_grid_decoupled(img, tpl, scale_x, scale_y, barcode_rect):
    h, w, _ = img.shape
    barcode_left = w//2 + barcode_rect.left
    est_grid_x = int(barcode_left - 66 * scale_x)
    est_grid_y = int(barcode_rect.top + 293 * scale_y)
    
    detected_centroids = detect_bubbles_centroids(img, scale_x)
    if not detected_centroids:
        return est_grid_x, est_grid_y, 0
        
    b_conf = tpl["bubble_grid"]
    col_spacing = b_conf["col_spacing"] * scale_x
    col_start = b_conf["col_start_offset"] * scale_x
    row_spacing = b_conf["row_spacing"] * scale_y
    row_start = b_conf["row_start_offset"] * scale_y
    
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
            if min_dist < 6 * scale_x:
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
    
    match_thresh2 = (8 * scale_y) ** 2
    penalty_dist2 = (15 * scale_y) ** 2
    
    template_points = []
    for i in range(b_conf["cols"]):
        cx = col_start + i * col_spacing
        for j in range(b_conf["rows"]):
            cy = row_start + j * row_spacing
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
    return aligned_grid_x, aligned_grid_y, max_score_y

def read_bubbles_decoupled(img, tpl, scale_x, scale_y, barcode_rect):
    grid_x, grid_y, score = align_grid_decoupled(img, tpl, scale_x, scale_y, barcode_rect)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w, _ = img.shape
    
    b_conf = tpl["bubble_grid"]
    col_spacing = b_conf["col_spacing"] * scale_x
    row_spacing = b_conf["row_spacing"] * scale_y
    col_start = b_conf["col_start_offset"] * scale_x
    row_start = b_conf["row_start_offset"] * scale_y
    
    img_draw = img.copy()
    detected_digits = []
    
    for i in range(b_conf["cols"]):
        cx = int(grid_x + col_start + i * col_spacing)
        col_vals = []
        for j in range(b_conf["rows"]):
            cy = int(grid_y + row_start + j * row_spacing)
            r = int(max(3, b_conf["sample_radius"] * scale_x))
            y_min_idx = max(0, cy - r)
            y_max_idx = min(gray.shape[0], cy + r)
            x_min_idx = max(0, cx - r)
            x_max_idx = min(gray.shape[1], cx + r)
            cell = gray[y_min_idx:y_max_idx, x_min_idx:x_max_idx]
            avg = np.mean(cell) if cell.size > 0 else 255
            col_vals.append((j, avg))
            
        col_vals_sorted = sorted(col_vals, key=lambda x: x[1])
        min_idx, min_val = col_vals_sorted[0]
        unmarked_vals = [x[1] for x in col_vals_sorted[2:]]
        avg_unmarked = np.mean(unmarked_vals) if unmarked_vals else 255
        contrast = col_vals_sorted[1][1] - col_vals_sorted[0][1]
        
        is_filled = (avg_unmarked - min_val > 25) and (contrast > 12)
        
        if is_filled:
            detected_digits.append(str(min_idx))
        else:
            detected_digits.append(" ")
            
        for j in range(b_conf["rows"]):
            cy = int(grid_y + row_start + j * row_spacing)
            if j == min_idx:
                color = (0, 255, 0) if is_filled else (0, 0, 255)
                cv2.circle(img_draw, (cx, cy), int(10 * scale_x), color, -1)
            else:
                cv2.circle(img_draw, (cx, cy), int(6 * scale_x), (255, 0, 0), 1)
                
    bubble_regno = "".join(detected_digits)
    h_d, w_d, _ = img_draw.shape
    y_start_crop = max(0, int(grid_y - 80 * scale_y))
    y_end_crop = min(h_d, int(grid_y + 320 * scale_y))
    x_start_crop = max(0, int(grid_x - 20 * scale_x))
    x_end_crop = min(w_d, int(grid_x + 580 * scale_x))
    crop_debug = img_draw[y_start_crop:y_end_crop, x_start_crop:x_end_crop]
    
    return bubble_regno, crop_debug, grid_x, grid_y, f"decoupled_snapped_{score}"

# ──────────────────────────────────────────────────────────
# WRITTEN REGNO OCR WITH BORDER MASKING (FOR B&W FILES)
# ──────────────────────────────────────────────────────────
def read_handwritten_regno(img, tpl, scale_x, scale_y, grid_x, grid_y, is_bw):
    sess = get_mnist_session()
    input_name = sess.get_inputs()[0].name
    h, w, _ = img.shape
    b_conf = tpl["bubble_grid"]
    
    col_spacing = b_conf["col_spacing"] * scale_x
    col_start = b_conf["col_start_offset"] * scale_x
    
    box_cy = grid_y - int(26 * scale_y)
    box_h = int(45 * scale_y)
    box_w = int(col_spacing * 0.85)
    trim_ratio = 0.10

    digits = []
    for i in range(b_conf["cols"]):
        cx = int(grid_x + col_start + i * col_spacing)
        x1 = cx - box_w // 2
        x2 = cx + box_w // 2
        y1 = box_cy - box_h // 2
        y2 = box_cy + box_h // 2

        cell_bgr = img[max(0, y1):min(h, y2), max(0, x1):min(w, x2)]
        if cell_bgr.size == 0:
            digits.append(' ')
            continue

        gray = cv2.cvtColor(cell_bgr, cv2.COLOR_BGR2GRAY)
        hc, wc = gray.shape[:2]
        
        # Color masking
        if not is_bw:
            hsv_crop = cv2.cvtColor(cell_bgr, cv2.COLOR_BGR2HSV)
            lower_red1 = np.array([0, 30, 40]); upper_red1 = np.array([15, 255, 255])
            lower_red2 = np.array([165, 30, 40]); upper_red2 = np.array([180, 255, 255])
            red_mask = cv2.bitwise_or(cv2.inRange(hsv_crop, lower_red1, upper_red1),
                                       cv2.inRange(hsv_crop, lower_red2, upper_red2))
            gray_clean = gray.copy()
            gray_clean[red_mask > 0] = 255
        else:
            # Blue ink filter for B&W
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

    return "".join(digits)

def determine_final_regno(bubble_regno, handwritten_regno):
    bubble_stripped = bubble_regno.strip()
    hw_stripped = handwritten_regno.strip()
    
    if not bubble_stripped and not hw_stripped:
        return '', False, 'Both empty'
    if not bubble_stripped:
        return hw_stripped, False, 'Handwritten only'
    if not hw_stripped:
        return bubble_stripped, False, 'Bubble only'
    
    bubble_digits = ''.join(bubble_regno).replace(' ', '')
    hw_digits = hw_stripped.replace(' ', '')
    
    if bubble_digits == hw_digits:
        return bubble_stripped, False, 'Match'
    else:
        return bubble_stripped, True, f'MISMATCH: Bubble={bubble_stripped} HW={hw_stripped}'

def detect_whitener_applied(img, grid_x, grid_y, tpl, scale_x, scale_y,
                            hw_x0, hw_y0, hw_x1, hw_y1):
    """
    Detect correction-fluid (whitener) patches on the bubble grid and
    handwritten registration regions. Whitener appears as very bright,
    low-saturation blobs that are locally brighter than surrounding paper.
    """
    h, w = img.shape[:2]
    b_conf = tpl["bubble_grid"]
    col_start = b_conf["col_start_offset"] * scale_x
    row_start = b_conf["row_start_offset"] * scale_y
    col_spacing = b_conf["col_spacing"] * scale_x
    row_spacing = b_conf["row_spacing"] * scale_y

    regions = []
    bg_y0 = max(0, int(grid_y + row_start - 15))
    bg_y1 = min(h, int(grid_y + row_start + 9 * row_spacing + 15))
    bg_x0 = max(0, int(grid_x + col_start - 15))
    bg_x1 = min(w, int(grid_x + col_start + 8 * col_spacing + 15))
    if bg_y1 > bg_y0 and bg_x1 > bg_x0:
        regions.append(img[bg_y0:bg_y1, bg_x0:bg_x1])

    hy0, hy1 = max(0, hw_y0), min(h, hw_y1)
    hx0, hx1 = max(0, hw_x0), min(w, hw_x1)
    if hy1 > hy0 and hx1 > hx0:
        regions.append(img[hy0:hy1, hx0:hx1])

    min_blob_area = max(60, int(40 * scale_x * scale_y))

    for region in regions:
        if region.size == 0:
            continue
        hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
        gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        sat = hsv[:, :, 1]
        val = hsv[:, :, 2]

        local_mean = cv2.GaussianBlur(gray, (31, 31), 0)
        whitener_mask = (
            (val >= 248) &
            (sat <= 25) &
            (gray.astype(np.int16) > local_mean.astype(np.int16) + 8)
        ).astype(np.uint8) * 255

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        whitener_mask = cv2.morphologyEx(whitener_mask, cv2.MORPH_OPEN, kernel)

        n_labels, _, stats, _ = cv2.connectedComponentsWithStats(
            whitener_mask, connectivity=8)
        for i in range(1, n_labels):
            if stats[i, cv2.CC_STAT_AREA] >= min_blob_area:
                return True

    return False

# ──────────────────────────────────────────────────────────
# MAIN PROCESSING WRAPPER
# ──────────────────────────────────────────────────────────
def analyze_sheet_color_mode(img):
    """
    Detect whether the scanned sheet contains the original red/magenta print.

    The original colour OMR sheets use red/magenta template ink. If that ink is
    present across the page, isblack must be 0. Black-and-white scans and any
    scan without red/magenta template ink must return isblack as 1.
    """
    empty_result = {
        "is_bw": True,
        "isblack": 1,
        "avg_sat": 0.0,
        "color_pixel_ratio": 0.0,
        "strong_color_ratio": 0.0,
    }
    if img is None or img.size == 0:
        return empty_result.copy()

    if len(img.shape) < 3 or img.shape[2] == 1:
        return empty_result.copy()

    h, w = img.shape[:2]
    max_side = 1200
    sample = img
    if max(h, w) > max_side:
        scale = max_side / float(max(h, w))
        sample = cv2.resize(
            img, (int(w * scale), int(h * scale)),
            interpolation=cv2.INTER_AREA)

    hsv = cv2.cvtColor(sample, cv2.COLOR_BGR2HSV)
    hue = hsv[:, :, 0]
    sat = hsv[:, :, 1].astype(np.float32)
    val = hsv[:, :, 2].astype(np.float32)

    valid = (val > 35) & (val < 250)
    valid_count = int(np.count_nonzero(valid))
    if valid_count == 0:
        return empty_result.copy()

    red_hue = (hue <= 14) | (hue >= 166)
    magenta_hue = (hue >= 135) & (hue <= 174)
    red_magenta_pixels = (
        valid &
        (sat > 45) &
        (val > 80) &
        (red_hue | magenta_hue)
    )
    strong_red_magenta_pixels = (
        valid &
        (sat > 65) &
        (val > 100) &
        (red_hue | magenta_hue)
    )

    red_magenta_mask = red_magenta_pixels.astype(np.uint8)
    red_magenta_ratio = (
        np.count_nonzero(red_magenta_mask) / float(red_magenta_mask.size)
    )
    strong_red_magenta_ratio = (
        np.count_nonzero(strong_red_magenta_pixels) /
        float(red_magenta_mask.size)
    )

    n_labels, _, stats, _ = cv2.connectedComponentsWithStats(
        red_magenta_mask, connectivity=8)
    largest_component_ratio = 0.0
    if n_labels > 1:
        largest_component_ratio = (
            np.max(stats[1:, cv2.CC_STAT_AREA]) / float(red_magenta_mask.size)
        )

    avg_sat = float(np.mean(sat[valid]))

    has_red_magenta_template = (
        red_magenta_ratio >= 0.01 or
        (
            red_magenta_ratio >= 0.004 and
            largest_component_ratio >= 0.002
        ) or
        strong_red_magenta_ratio >= 0.006
    )

    return {
        "is_bw": not has_red_magenta_template,
        "isblack": 0 if has_red_magenta_template else 1,
        "avg_sat": round(avg_sat, 2),
        "color_pixel_ratio": round(float(red_magenta_ratio), 5),
        "strong_color_ratio": round(float(strong_red_magenta_ratio), 5),
    }

def process_single_sheet_for_demo(img_path):
    img = cv2.imread(img_path)
    if img is None:
        return None
        
    h, w, _ = img.shape
    tpl = get_omr_template(w)
    
    color_mode = analyze_sheet_color_mode(img)
    avg_sat = color_mode["avg_sat"]
    is_bw = bool(color_mode["is_bw"])
    isblack = int(color_mode["isblack"])
    
    h_target = 1080 if tpl["name"] == "standard" else 784
    scale_y = h / h_target
    
    right_half = img[:, w//2:]
    decoded = decode(right_half)
    barcode_val = decoded[0].data.decode('utf-8') if decoded else "Not Detected"
    
    is_padded_bw = w > 1800
    if is_padded_bw:
        scale_y = h / 1080.0
        scale_x = scale_y
    else:
        scale_x = w / tpl["target_width"]
        scale_y = scale_x
        
    # 1. Alignment & Bubble Reading
    bubble_regno, debug_grid_img, grid_x, grid_y, align_method, bubble_Th_status = read_bubbles_custom(img, tpl, scale_x, scale_y, is_bw)
            
    # 2. Handwritten Digit OCR
    handwritten_regno = read_handwritten_regno(img, tpl, scale_x, scale_y, grid_x, grid_y, is_bw)
        
    # 3. Signature crops and status (x_start shifted to 130 to avoid border and printed label noise)
    cand_sig_y_start = max(0, int(grid_y + 2 * scale_y))
    cand_sig_y_end = min(h, int(grid_y + 92 * scale_y))
    cand_sig_x_start = max(0, int(130 * scale_x))
    cand_sig_x_end = min(w, int(900 * scale_x))
    
    cand_sig_crop = img[cand_sig_y_start:cand_sig_y_end, cand_sig_x_start:cand_sig_x_end]
    cand_signed, cand_ratio = check_ink_present_unified(cand_sig_crop, is_bw)
    
    inv_sig_y_start = max(0, int(grid_y + 152 * scale_y))
    inv_sig_y_end = min(h, int(grid_y + 252 * scale_y))
    inv_sig_x_start = max(0, int(130 * scale_x))
    inv_sig_x_end = min(w, int(900 * scale_x))
    
    inv_sig_crop = img[inv_sig_y_start:inv_sig_y_end, inv_sig_x_start:inv_sig_x_end]
    inv_signed, inv_ratio = check_ink_present_unified(inv_sig_crop, is_bw)
    
    # 4. Handwritten Box Crop for display
    col_spacing = tpl["bubble_grid"]["col_spacing"] * scale_x
    col_start = tpl["bubble_grid"]["col_start_offset"] * scale_x
    box_cy = grid_y - int(38 * scale_y)
    box_h = int(45 * scale_y)
    box_w = int(col_spacing * 0.85)
    
    # Crop full 9 digit cells bounding region
    hw_x0 = int(grid_x + col_start - box_w//2 - 10)
    hw_x1 = int(grid_x + col_start + 8 * col_spacing + box_w//2 + 10)
    hw_y0 = int(box_cy - box_h//2 - 5)
    hw_y1 = int(box_cy + box_h//2 + 5)
    reg_box_crop = img[max(0, hw_y0):min(h, hw_y1), max(0, hw_x0):min(w, hw_x1)]

    subject_code, subject_crop = VisualOMRViewerDemo.extract_subject_code(None, img, scale_x, scale_y)
    booklet_sl_no, omr_threshold, booklet_crop = VisualOMRViewerDemo.extract_booklet_number(None, img, scale_x, scale_y)

    # Whitener flag: True when OMR bubble threshold is below 10%, indicating
    # correction fluid (whitener) may have been applied on the bubble region.
    whitenerflag = omr_threshold < 10

    final_regno, has_disc, disc_detail = determine_final_regno(bubble_regno, handwritten_regno)
    
    # 5. Create Full Annotated Image for Left Panel
    full_annotated = img.copy()
    
    # Draw barcode rect (in right half, so shift coordinates)
    if decoded:
        br = decoded[0].rect
        cv2.rectangle(full_annotated, (w//2 + br.left, br.top), (w//2 + br.left + br.width, br.top + br.height), (0, 165, 255), 3)
        cv2.putText(full_annotated, "Barcode", (w//2 + br.left, max(25, br.top - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
        
    # Draw Bubble Grid
    bg_x0 = int(grid_x + col_start - 10)
    bg_x1 = int(grid_x + col_start + 8 * col_spacing + 10)
    row_spacing = tpl["bubble_grid"]["row_spacing"] * scale_y
    row_start = tpl["bubble_grid"]["row_start_offset"] * scale_y
    bg_y0 = int(grid_y + row_start - 10)
    bg_y1 = int(grid_y + row_start + 9 * row_spacing + 10)
    cv2.rectangle(full_annotated, (bg_x0, bg_y0), (bg_x1, bg_y1), (0, 255, 0), 3)
    cv2.putText(full_annotated, "Bubble Grid", (bg_x0, max(25, bg_y0 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    # Draw Handwritten registration box
    cv2.rectangle(full_annotated, (hw_x0, hw_y0), (hw_x1, hw_y1), (255, 0, 0), 3)
    cv2.putText(full_annotated, "Handwritten RegNo", (hw_x0, max(25, hw_y0 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
    
    # Draw Candidate Signature
    cv2.rectangle(full_annotated, (cand_sig_x_start, cand_sig_y_start), (cand_sig_x_end, cand_sig_y_end), (255, 0, 255), 3)
    cv2.putText(full_annotated, "Candidate Sig", (cand_sig_x_start, max(25, cand_sig_y_start - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
    
    # Draw Invigilator Signature
    cv2.rectangle(full_annotated, (inv_sig_x_start, inv_sig_y_start), (inv_sig_x_end, inv_sig_y_end), (0, 255, 255), 3)
    cv2.putText(full_annotated, "Invigilator Sig", (inv_sig_x_start, max(25, inv_sig_y_start - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    
    image_path = os.path.abspath(img_path)

    return {
        "filename": image_path,
        "image_name": os.path.basename(img_path),
        "image_path": image_path,
        "resolution": f"{w}x{h}",
        "avg_sat": round(avg_sat, 2),
        "is_bw": is_bw,
        "isblack": isblack,
        "color_pixel_ratio": color_mode["color_pixel_ratio"],
        "strong_color_ratio": color_mode["strong_color_ratio"],
        "is_padded_bw": is_padded_bw,
        "barcode": barcode_val,
        "bubble_regno": bubble_regno,
        "handwritten_regno": handwritten_regno,
        "final_regno": final_regno,
        "bubble_Th_status": bubble_Th_status,
        
        "subject_code": subject_code,
        "booklet_number": booklet_sl_no,        # kept as "booklet_number" for UI compat
        "BookletSlNo": booklet_sl_no,           # canonical field name
        "omr_threshold": omr_threshold,         # OCR confidence score for booklet number
        "subject_crop": subject_crop,
        "booklet_crop": booklet_crop,

        "has_disc": has_disc,
        "disc_detail": disc_detail,
        "whitenerflag": whitenerflag,
        "cand_signed": cand_signed,
        "cand_ratio": cand_ratio,
        "inv_signed": inv_signed,
        "inv_ratio": inv_ratio,
        "debug_grid_img": debug_grid_img,
        "reg_box_crop": reg_box_crop,
        "cand_sig_crop": cand_sig_crop,
        "inv_sig_crop": inv_sig_crop,
        "full_annotated_img": full_annotated
    }

# ──────────────────────────────────────────────────────────
# TKINTER DUST-FREE visual EXTRACTOR APP
# ──────────────────────────────────────────────────────────
class VisualOMRViewerDemo:
    def __init__(self, root):
        self.root = root
        self.root.title("OMR ICR OCR Extraction Engine")

        # Responsive: fill 92% of screen, centered
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        win_w = int(sw * 0.92)
        win_h = int(sh * 0.90)
        self.root.geometry(f"{win_w}x{win_h}+{(sw-win_w)//2}+{(sh-win_h)//2}")
        self.root.minsize(1024, 600)
        self.root.configure(bg="#1a1a22")

        # Scale factor relative to 1920-wide display
        sf = max(0.8, min(1.5, sw / 1920))
        self._fs = lambda n: max(7, int(n * sf))   # font size
        self._px = lambda n: max(2, int(n * sf))   # pixel gap

        # Colour palette
        self._BG      = "#1a1a22"
        self._PANEL   = "#24242f"
        self._ACCENT  = "#00c853"
        self._ACCH    = "#00e676"
        self._FG      = "#e8e8ee"
        self._FGD     = "#888899"
        self._ENTRY   = "#2a2a38"

        self._setup_styles()

        self.omr_dir             = None
        self.last_loaded_filename = None
        self.last_loaded_folder  = None
        self.image_paths         = []
        self.filenames           = []
        self.current_omr_res     = None

        self.build_ui()
    def _setup_styles(self):
        fs = self._fs; px = self._px
        BG = self._BG; P = self._PANEL; AC = self._ACCENT
        FG = self._FG; FGD = self._FGD; EN = self._ENTRY

        s = ttk.Style()
        s.theme_use("clam")
        self.style = s

        s.configure(".", background=BG, foreground=FG,
                    fieldbackground=EN, font=("Segoe UI", fs(9)))
        s.configure("TLabel",  background=BG,  foreground=FG,  font=("Segoe UI", fs(9)))
        s.configure("Pan.TLabel", background=P, foreground=FG,  font=("Segoe UI", fs(9)))
        s.configure("Dim.TLabel", background=P, foreground=FGD, font=("Segoe UI", fs(8)))
        s.configure("Title.TLabel", background=P, foreground=AC,
                    font=("Segoe UI", fs(11), "bold"))
        s.configure("TButton", background=AC, foreground="#fff",
                    font=("Segoe UI", fs(9), "bold"),
                    borderwidth=0, focuscolor="none",
                    padding=(px(8), px(4)))
        s.configure("Large.TButton", background=AC, foreground="#fff",
                    font=("Segoe UI", fs(14), "bold"),
                    borderwidth=0, focuscolor="none",
                    padding=(px(10), px(8)))
        s.map("TButton", background=[("active", self._ACCH), ("disabled", "#44445a")])
        s.map("Large.TButton", background=[("active", self._ACCH), ("disabled", "#44445a")])
        s.configure("TEntry", fieldbackground=EN, foreground=FG,
                    insertcolor=FG, font=("Consolas", fs(9)))
        s.map("TEntry",
              fieldbackground=[("readonly", "#1e1e2a")],
              foreground=[("readonly", FGD)])
        s.configure("TCombobox", fieldbackground=EN, background=EN, foreground=FG)
        s.map("TCombobox",
              fieldbackground=[("readonly", EN)],
              foreground=[("readonly", FG)])
        s.configure("Thin.Horizontal.TProgressbar",
                    troughcolor=P, background=AC, thickness=px(8))

        self.root.option_add("*TCombobox*Listbox.background", EN)
        self.root.option_add("*TCombobox*Listbox.foreground", FG)
        self.root.option_add("*TCombobox*Listbox.selectBackground", AC)
        self.root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
        self.root.option_add("*TCombobox*Listbox.font", ("Segoe UI", fs(9)))
            
    # ── helpers ────────────────────────────────────────────────────────────
    def _sep(self, parent, pady=2):
        tk.Frame(parent, bg="#33334a", height=1).pack(
            fill="x", padx=self._px(6), pady=pady)

    def _field(self, parent, label, font_name="Consolas",
               font_size=10, label_font_size=None, bold=False, readonly=False):
        px = self._px
        label_font = self._fs(label_font_size if label_font_size is not None else 9)
        tk.Label(parent, text=label,
                 bg=self._PANEL, fg=self._FG,
                 font=("Segoe UI", label_font, "bold"),
                 anchor="w").pack(fill="x", padx=px(8), pady=(px(3), px(2)))
        e = ttk.Entry(parent,
                      font=(font_name, self._fs(font_size),
                            "bold" if bold else "normal"))
        if readonly:
            e.config(state="readonly")
        e.pack(fill="x", padx=px(8), pady=(1, px(8)))
        return e

    def build_ui(self):
        px = self._px; fs = self._fs
        BG = self._BG; P = self._PANEL; AC = self._ACCENT; FG = self._FG; FGD = self._FGD

        # ── HEADER ROW ─────────────────────────────────────────────────────
        header = tk.Frame(self.root, bg=P, height=px(46))
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        tk.Label(header,
                 text="Counter Foil Extraction Engine",
                 bg=P, fg=AC,
                 font=("Segoe UI", fs(18), "bold"),
                 anchor="center").pack(fill="both", expand=True)

        # thin accent underline
        tk.Frame(self.root, bg=AC, height=2).pack(fill="x", side="top")

        # ── CONTROLS ROW ───────────────────────────────────────────────────
        top = tk.Frame(self.root, bg="#1e1e2a", height=px(42))
        top.pack(fill="x", side="top")
        top.pack_propagate(False)

        # Left side: image navigation + folder + status + progress
        ttk.Label(top, text="Image:", style="Pan.TLabel",
                  font=("Segoe UI", fs(16), "bold")).pack(
                      side="left", padx=(px(10), px(3)))

        self.prev_btn = ttk.Button(top, text="◀", width=4,
            command=lambda: self.navigate_sheet(-1), state="disabled",
            style="Large.TButton")
        self.prev_btn.pack(side="left", padx=px(2))

        self.file_combo = ttk.Combobox(top, values=[], state="readonly",
                                       width=52, font=("Segoe UI", fs(14)))
        self.file_combo.pack(side="left", padx=px(3))
        self.file_combo.bind("<<ComboboxSelected>>",
                             lambda e: self.process_selected_sheet())

        self.next_btn = ttk.Button(top, text="▶", width=4,
            command=lambda: self.navigate_sheet(1), state="disabled",
            style="Large.TButton")
        self.next_btn.pack(side="left", padx=px(2))

        ttk.Button(top, text="📂 Select Folder",
                   command=self.browse_folder,
                   style="Large.TButton").pack(side="left", padx=px(6))

        self.status_lbl = ttk.Label(top, text="Ready",
            style="Pan.TLabel",
            font=("Segoe UI", fs(9), "italic"),
            foreground="#ffeb3b")
        self.status_lbl.pack(side="left", padx=px(8))

        self.progress = ttk.Progressbar(
            top, orient="horizontal", length=px(150), mode="determinate",
            style="Thin.Horizontal.TProgressbar")
        self.progress.pack(side="left", padx=px(4))

        # Right side: Process All + Export buttons
        self.export_btn = ttk.Button(top, text="Export to Excel",
            command=self.export_results_to_excel, width=16,
            style="Large.TButton",
            state="disabled")
        self.export_btn.pack(side="right", padx=(px(2), px(12)))
        self.All_btn = ttk.Button(top, text="⚙  Process All",
            command=self.process_all_sheets_to_mssql, width=14,
            style="Large.TButton")
        self.All_btn.pack(side="right", padx=px(2))

        # thin separator below controls
        tk.Frame(self.root, bg="#33334a", height=1).pack(fill="x", side="top")

        # ── MAIN 3-COLUMN GRID ─────────────────────────────────────────────
        content = tk.Frame(self.root, bg=BG)
        content.pack(fill="both", expand=True,
                     padx=px(5), pady=px(4))
        content.columnconfigure(0, weight=48)
        content.columnconfigure(1, weight=38)
        content.columnconfigure(2, weight=14)
        content.rowconfigure(0, weight=1)

        # COL 0 — Original sheet
        col0 = tk.LabelFrame(content, text=" Original Scanned Sheet ",
            bg=P, fg=AC,
            font=("Segoe UI", fs(8), "bold"), bd=1, relief="solid")
        col0.grid(row=0, column=0, sticky="nsew", padx=(0, px(4)))
        col0.columnconfigure(0, weight=1)
        col0.rowconfigure(1, weight=1)

        self.full_omr_zoom_frame = tk.Frame(col0, bg=P)
        self.full_omr_zoom_frame.grid(row=0, column=0, sticky="ew",
                                      padx=px(3), pady=(px(3), px(2)))
        ttk.Button(self.full_omr_zoom_frame, text="−", width=3,
                   command=lambda: self.adjust_original_zoom(-0.25)).pack(side="left")
        self.full_omr_zoom_lbl = ttk.Label(self.full_omr_zoom_frame, text="100%", width=7)
        self.full_omr_zoom_lbl.pack(side="left", padx=px(4))
        ttk.Button(self.full_omr_zoom_frame, text="+", width=3,
                   command=lambda: self.adjust_original_zoom(0.25)).pack(side="left")

        self.full_omr_zoom = 1.0
        self._full_omr_cv_img = None
        self._full_omr_photo = None

        self.full_omr_canvas = tk.Canvas(col0, bg=P,
                                         highlightthickness=0, bd=0)
        self.full_omr_canvas.grid(row=1, column=0, sticky="nsew",
                                   padx=px(3), pady=(0, px(3)))

        self.full_omr_xscroll = ttk.Scrollbar(col0, orient="horizontal",
                                              command=self.full_omr_canvas.xview)
        self.full_omr_yscroll = ttk.Scrollbar(col0, orient="vertical",
                                              command=self.full_omr_canvas.yview)
        self.full_omr_xscroll.grid(row=2, column=0, sticky="ew")
        self.full_omr_yscroll.grid(row=1, column=1, sticky="ns")
        self.full_omr_canvas.configure(xscrollcommand=self.full_omr_xscroll.set,
                                       yscrollcommand=self.full_omr_yscroll.set)

        self.full_omr_canvas_frame = tk.Frame(self.full_omr_canvas, bg=P)
        self._full_omr_window = self.full_omr_canvas.create_window(
            (0, 0), window=self.full_omr_canvas_frame, anchor="nw")
        self.full_omr_img_lbl = tk.Label(self.full_omr_canvas_frame, bg=P,
                                         text="No image loaded", fg=FGD)
        self.full_omr_img_lbl.pack(fill="both", expand=True)
        self.full_omr_canvas.bind("<Configure>",
            lambda e: self._refresh_full_omr_image())
        self.full_omr_canvas.bind_all("<MouseWheel>",
            lambda e: self.full_omr_canvas.yview_scroll(
                int(-1*(e.delta/120)), "units"))

        self.build_status_panel(col0)

        # COL 1 — Centre crops
        col1 = tk.Frame(content, bg=BG)
        col1.grid(row=0, column=1, sticky="nsew", padx=(0, px(4)))
        col1.rowconfigure(0, weight=5)
        col1.rowconfigure(1, weight=2)
        col1.rowconfigure(2, weight=2)
        col1.columnconfigure(0, weight=1)

        self.grid_labelframe = tk.LabelFrame(col1,
            text=" Bubble Grid Extraction Map ",
            bg=P, fg=AC,
            font=("Segoe UI", fs(8), "bold"), bd=1, relief="solid")
        self.grid_labelframe.grid(row=0, column=0,
                                  sticky="nsew", pady=(0, px(3)))
        self.grid_canvas_lbl = tk.Label(self.grid_labelframe, bg=P)
        self.grid_canvas_lbl.pack(fill="both", expand=True,
                                  padx=px(3), pady=px(3))

        self.hw_labelframe = tk.LabelFrame(col1,
            text=" Handwritten Box (MNIST) ",
            bg=P, fg=AC,
            font=("Segoe UI", fs(8), "bold"), bd=1, relief="solid")
        self.hw_labelframe.grid(row=1, column=0,
                                sticky="nsew", pady=(0, px(3)))
        self.hw_crop_lbl = tk.Label(self.hw_labelframe, bg=P)
        self.hw_crop_lbl.pack(fill="both", expand=True,
                              padx=px(3), pady=px(3))

        sig_lf = tk.LabelFrame(col1,
            text=" Signature Regions ",
            bg=P, fg=AC,
            font=("Segoe UI", fs(8), "bold"), bd=1, relief="solid")
        sig_lf.grid(row=2, column=0, sticky="nsew")
        sig_lf.columnconfigure(0, weight=1)
        sig_lf.columnconfigure(1, weight=1)
        sig_lf.rowconfigure(0, weight=1)

        cand_wrap = tk.LabelFrame(sig_lf, text=" Candidate ",
            bg=P, fg=FGD, font=("Segoe UI", fs(7)), bd=1)
        cand_wrap.grid(row=0, column=0, sticky="nsew",
                       padx=(px(3), px(2)), pady=px(3))
        self.cand_sig_lbl = tk.Label(cand_wrap, bg=P)
        self.cand_sig_lbl.pack(fill="both", expand=True)

        inv_wrap = tk.LabelFrame(sig_lf, text=" Invigilator ",
            bg=P, fg=FGD, font=("Segoe UI", fs(7)), bd=1)
        inv_wrap.grid(row=0, column=1, sticky="nsew",
                      padx=(px(2), px(3)), pady=px(3))
        self.inv_sig_lbl = tk.Label(inv_wrap, bg=P)
        self.inv_sig_lbl.pack(fill="both", expand=True)

        # COL 2 — Results
        col2_outer = tk.LabelFrame(content,
            text=" Extraction & Processing Results ",
            bg=P, fg=AC,
            font=("Segoe UI", fs(8), "bold"), bd=1, relief="solid")
        col2_outer.grid(row=0, column=2, sticky="nsew")
        col2_outer.columnconfigure(0, weight=1)
        col2_outer.rowconfigure(0, weight=1)

        self.right_frame = tk.Frame(col2_outer, bg=P)
        self.right_frame.grid(row=0, column=0, sticky="nsew",
                              padx=px(4), pady=px(4))

        self.build_results_panel()

    def build_status_panel(self, parent):
        """Build the status grid beneath the original scanned sheet panel."""
        px = self._px; fs = self._fs
        P = self._PANEL; FG = self._FG; FGD = self._FGD; AC = self._ACCENT

        status_frame = tk.LabelFrame(parent, text=" Sheet Process Status ",
            bg=P, fg=AC,
            font=("Segoe UI", fs(8), "bold"), bd=1, relief="solid")
        status_frame.grid(row=3, column=0, sticky="nsew",
                          padx=px(3), pady=(px(4), px(3)))
        status_frame.columnconfigure(0, weight=1)
        status_frame.rowconfigure(1, weight=1)

        status_hdr = tk.Frame(status_frame, bg=P)
        status_hdr.grid(row=0, column=0, sticky="ew",
                        padx=px(6), pady=(px(4), px(2)))

        tk.Label(status_hdr, text="Sheet Process Status:",
                 bg=P, fg=FG,
                 font=("Segoe UI", fs(8), "bold"),
                 anchor="w").pack(side="left")

        self.status_summary_lbl = tk.Label(
            status_hdr, text="",
            bg=P, fg=FGD,
            font=("Segoe UI", fs(8)),
            anchor="w")
        self.status_summary_lbl.pack(side="left", padx=px(6))

        grid_frame = tk.Frame(status_frame, bg=P)
        grid_frame.grid(row=1, column=0, sticky="nsew",
                        padx=px(6), pady=(0, px(6)))

        cols = ("img", "extracted", "saved_db")
        self.status_tree = ttk.Treeview(
            grid_frame, columns=cols, show="headings",
            height=8, selectmode="browse")

        self.status_tree.heading("img",       text="Image")
        self.status_tree.heading("extracted", text="Extracted")
        self.status_tree.heading("saved_db",  text="Saved to DB")
        self.status_tree.column("img",       width=px(130), anchor="w",   stretch=True)
        self.status_tree.column("extracted", width=px(90),  anchor="center", stretch=True)
        self.status_tree.column("saved_db",  width=px(90),  anchor="center", stretch=True)

        self.status_tree.tag_configure("ok",       background="#1b5e20", foreground="#a5d6a7")
        self.status_tree.tag_configure("warning",  background="#4e2600", foreground="#ffcc80")
        self.status_tree.tag_configure("error",    background="#4e0000", foreground="#ef9a9a")
        self.status_tree.tag_configure("imported", background="#0d2f5e", foreground="#90caf9")
        self.status_tree.tag_configure("pending",  background="#2a2a3a", foreground="#888899")

        self.style.configure("Treeview",
            background="#1e1e2a", foreground=self._FG,
            fieldbackground="#1e1e2a",
            rowheight=px(22),
            font=("Segoe UI", fs(8)))
        self.style.configure("Treeview.Heading",
            background=self._PANEL, foreground=self._ACCENT,
            font=("Segoe UI", fs(8), "bold"), relief="flat")
        self.style.map("Treeview",
            background=[("selected", "#2a4a7f")],
            foreground=[("selected", "#ffffff")])

        vsb = ttk.Scrollbar(grid_frame, orient="vertical",
                            command=self.status_tree.yview)
        self.status_tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.status_tree.pack(side="left", fill="both", expand=True)

        self._status_iids = {}
        self._status_state = {}
        
    def _validate_subject_code(self, event=None):
        value = self.edit_subject.get()
        digits = "".join(ch for ch in value if ch.isdigit())
        digits = digits[:3]
        if value != digits:
            self.edit_subject.delete(0, tk.END)
            self.edit_subject.insert(0, digits)

    def build_results_panel(self):
        """Populate the scrollable right panel with all result fields."""
        px = self._px; fs = self._fs
        P = self._PANEL; FG = self._FG; FGD = self._FGD

        # Metadata
        self.meta_lbl = tk.Label(self.right_frame,
            text="File: —\nResolution: —\nType: —",
            justify="left", anchor="w",
            bg=P, fg=FGD, font=("Segoe UI", fs(12)))
        self.meta_lbl.pack(fill="x", padx=px(8), pady=(px(4), px(2)))

        self._sep(self.right_frame)

        # Subject Code
        self.edit_subject = self._field(
            self.right_frame, "Subject Code", font_size=14, bold=True)
        self.edit_subject.configure(width=3)
        self.edit_subject.bind("<KeyRelease>", self._validate_subject_code)
        self.edit_subject.bind("<<Paste>>", self._validate_subject_code)

        # Booklet Serial No
        self.edit_booklet = self._field(
            self.right_frame, "Booklet Serial No  (BookletSlNo)",
            font_size=14, label_font_size=14, bold=True)

        tk.Label(self.right_frame, text="OCR Confidence:",
                 bg=P, fg=FGD, font=("Segoe UI", fs(12)),
                 anchor="w").pack(fill="x", padx=px(8))
        self.edit_booklet_threshold = ttk.Entry(
            self.right_frame, font=("Consolas", fs(14)))
        self.edit_booklet_threshold.config(state="readonly")
        self.edit_booklet_threshold.pack(fill="x", padx=px(8), pady=(1, px(3)))

        self._sep(self.right_frame)

        # Barcode — inline label + entry
        bc_row = tk.Frame(self.right_frame, bg=P)
        bc_row.pack(fill="x", padx=px(8), pady=(px(3), px(1)))
        tk.Label(bc_row, text="Decoded Barcode:",
                 bg=P, fg=FG,
                 font=("Segoe UI", fs(14), "bold")).pack(side="left")
        self.edit_barcode = ttk.Entry(
            bc_row, font=("Consolas", fs(14), "bold"))
        self.edit_barcode.pack(side="right", fill="x",
                               expand=True, padx=(px(6), 0))

        self._sep(self.right_frame)

        # OMR Bubble reading
        self.edit_bubble = self._field(
            self.right_frame, "OMR Bubble Reading",
            font_size=14, label_font_size=14, bold=True)

        # Handwritten OCR
        self.edit_hw = self._field(
            self.right_frame, "Handwritten OCR Reading",
            font_size=14, label_font_size=14, bold=True)

        # Resolved Register No
        self.edit_final = self._field(
            self.right_frame, "Resolved Register No  (SOP Output)",
            font_size=14, label_font_size=14, bold=True)

        self.edit_bubble.bind("<KeyRelease>",
                              self.recalculate_discrepancy_and_final)
        self.edit_hw.bind("<KeyRelease>",
                          self.recalculate_discrepancy_and_final)

        # Discrepancy banner
        self.disc_frame = tk.Frame(self.right_frame, bg=P,
                                   bd=1, relief="solid")
        self.disc_frame.pack(fill="x", padx=px(8), pady=px(4))
        self.disc_lbl = tk.Label(self.disc_frame,
            text="DISCREPANCY STATUS: OK",
            bg="#2e7d32", fg="#ffffff",
            font=("Segoe UI", fs(12), "bold"), height=2)
        self.disc_lbl.pack(fill="x")

        self._sep(self.right_frame)

        # Signatures — side by side on one row
        sig_row = tk.Frame(self.right_frame, bg=P)
        sig_row.pack(fill="x", padx=px(8), pady=px(3))

        tk.Label(sig_row, text="Candidate Signed:",
                 bg=P, fg=FG,
                 font=("Segoe UI", fs(14), "bold")).grid(
                     row=0, column=0, sticky="w", pady=px(2))
        self.edit_cand_sig = ttk.Combobox(
            sig_row, values=["YES", "NO"],
            state="readonly", width=7,
            font=("Segoe UI", fs(14)))
        self.edit_cand_sig.grid(row=0, column=1,
                                sticky="w", padx=(px(4), px(14)))

        tk.Label(sig_row, text="Invigilator Signed:",
                 bg=P, fg=FG,
                 font=("Segoe UI", fs(14), "bold")).grid(
                     row=0, column=2, sticky="w")
        self.edit_inv_sig = ttk.Combobox(
            sig_row, values=["YES", "NO"],
            state="readonly", width=7,
            font=("Segoe UI", fs(14)))
        self.edit_inv_sig.grid(row=0, column=3,
                               sticky="w", padx=(px(4), 0))

        # Save button (hidden)
        self.save_btn = ttk.Button(self.right_frame,
            text="💾  Save Corrections",
            command=self.save_corrections)
        self.save_btn.pack(fill="x", padx=px(8), pady=px(6))
        self.save_btn.pack_forget()

        self._sep(self.right_frame)

    # ── Status grid helpers ────────────────────────────────────────────────
    def _status_icon(self, status):
        return {"ok": "✔", "warning": "⚠", "error": "✘",
                "imported": "✔", "pending": "—"}.get(status, "—")

    def _ensure_status_row(self, filename):
        """Insert a pending row for filename if it doesn't exist yet."""
        if filename not in self._status_iids:
            iid = self.status_tree.insert(
                "", "end",
                values=(filename, "—", "—"),
                tags=("pending",))
            self._status_iids[filename] = iid

    def _extracted_status_from_result(self, res):
        """Map processing result to extracted-column status."""
        if not res:
            return "error"
        barcode_ok = bool(res["barcode"] and res["barcode"] != "Not Detected")
        regno_ok = bool(res["final_regno"].strip())
        _, has_disc, _ = determine_final_regno(
            res["bubble_regno"], res["handwritten_regno"])
        if not barcode_ok or not regno_ok or has_disc:
            return "warning"
        return "ok"

    def set_sheet_status(self, filename, extracted=None, saved_db=None):
        """
        Update the status grid row for `filename`.
        extracted / saved_db each accept: None (no change), "ok", "warning", "error", "pending"
        """
        if not hasattr(self, 'status_tree'):
            return
        self._ensure_status_row(filename)
        iid = self._status_iids[filename]

        if filename not in self._status_state:
            self._status_state[filename] = {}
        if extracted:
            self._status_state[filename]["extracted"] = extracted
        if saved_db:
            self._status_state[filename]["saved_db"] = saved_db

        cur = self.status_tree.item(iid, "values")
        new_ext = (self._status_icon(extracted) + "  " + extracted.upper()
                   if extracted else cur[1])
        new_db  = (self._status_icon(saved_db)  + "  " + saved_db.upper()
                   if saved_db  else cur[2])

        # Overall row tag = worst of the two
        rank = {"error": 3, "warning": 2, "imported": 1, "ok": 1, "pending": 0}
        tag = max([extracted or "pending", saved_db or "pending"],
                  key=lambda s: rank.get(s, 0))
        if (saved_db or "pending") == "imported":
            tag = "imported"

        self.status_tree.item(iid, values=(filename, new_ext, new_db), tags=(tag,))
        # Scroll to keep updated row visible
        self.status_tree.see(iid)

    def _refresh_status_summary(self):
        """Update summary counts beside the Sheet Process Status heading."""
        if not hasattr(self, 'status_summary_lbl'):
            return
        extracted = imported = errors = 0
        for state in self._status_state.values():
            ext = state.get("extracted")
            db = state.get("saved_db")
            if ext in ("ok", "warning"):
                extracted += 1
            if db == "imported":
                imported += 1
            if ext == "error" or db == "error":
                errors += 1
        if extracted or imported or errors:
            self.status_summary_lbl.config(
                text=(f"Extracted: {extracted}, "
                      f"Imported to DB: {imported}, "
                      f"Error Sheets: {errors}"))
        else:
            self.status_summary_lbl.config(text="")

    def _init_status_grid(self):
        """Populate grid with all known filenames as pending rows."""
        if not hasattr(self, 'status_tree'):
            return
        # Clear existing rows
        for iid in self.status_tree.get_children():
            self.status_tree.delete(iid)
        self._status_iids = {}
        self._status_state = {}
        for fp in self.filenames:
            self._ensure_status_row(os.path.basename(fp))
        self._refresh_status_summary()

    def browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.omr_dir)
        if not folder:
            return

        raw_paths = (
            glob.glob(os.path.join(folder, "*.jpg")) +
            glob.glob(os.path.join(folder, "*.png")) +
            glob.glob(os.path.join(folder, "*.jpeg")) +
            glob.glob(os.path.join(folder, "*.JPG")) +
            glob.glob(os.path.join(folder, "*.PNG")) +
            glob.glob(os.path.join(folder, "*.JPEG"))
        )
        seen = set()
        image_paths = []
        for p in raw_paths:
            norm = os.path.normcase(os.path.abspath(p))
            if norm not in seen:
                seen.add(norm)
                image_paths.append(p)
        image_paths.sort()

        if not image_paths:
            messagebox.showwarning("No Images Found",
                f"No image files (.jpg, .jpeg, .png) found in:\n{folder}")
            return

        self.omr_dir = folder
        self.image_paths = image_paths
        # Store full paths in combo; display full path to user
        self.filenames = [os.path.abspath(p) for p in self.image_paths]

        self.load_omr_csv()

        self.file_combo.config(values=self.filenames)
        self.file_combo.current(0)
        self.progress["value"] = 0
        if hasattr(self, "export_btn"):
            self.export_btn.config(state="disabled")
        self._init_status_grid()   # reset grid for the new folder
        self.status_lbl.config(text="Ready", foreground="#00e676")
        self.process_selected_sheet()

    def process_selected_sheet(self):
        img_path = self.file_combo.get()
        if not img_path:
            messagebox.showwarning("Warning", "Please select an OMR sheet first!")
            return

        # filename (basename) is used as the CSV record key
        filename = os.path.basename(img_path)

        # Auto-save previous sheet silently
        if (hasattr(self, 'last_loaded_filename') and self.last_loaded_filename
                and self.last_loaded_filename != filename):
            if (hasattr(self, 'last_loaded_folder')
                    and self.last_loaded_folder == self.omr_dir):
                if self.current_omr_res:
                    self.save_corrections(
                        filename_to_save=self.last_loaded_filename,
                        show_msg=False)

        if not os.path.exists(img_path):
            messagebox.showerror("Error", f"Image file not found:\n{img_path}")
            return
            
        try:
            self.status_lbl.config(text="Processing...", foreground="#ffeb3b")
            self.set_sheet_status(filename, extracted="pending")
            self.root.update_idletasks()
            
            # Run processing
            res = process_single_sheet_for_demo(img_path)
            if res is None:
                self.status_lbl.config(text="Processing failed", foreground="#ff3d00")
                self.set_sheet_status(filename, extracted="error")
                messagebox.showerror("Error", "Processing failed!")
                return
                
            self.current_omr_res = res
            
            # Update navigation button states
            current_idx = self.file_combo.current()
            total_files = len(self.file_combo["values"])
            if total_files == 0:
                self.prev_btn.config(state="disabled")
                self.next_btn.config(state="disabled")
                self.All_btn.config(state="disabled")
            else:
                self.All_btn.config(state="normal")
                if current_idx <= 0:
                    self.prev_btn.config(state="disabled")
                else:
                    self.prev_btn.config(state="normal")
                if current_idx >= total_files - 1 or current_idx == -1:
                    self.next_btn.config(state="disabled")
                else:
                    self.next_btn.config(state="normal")
            
            # Check if we have saved corrections in our CSV database
            if filename in self.omr_csv_records:
                csv_row = self.omr_csv_records[filename]
                barcode = csv_row.get("Decoded Barcode", "")
                bubble = csv_row.get("OMR Bubble Reading", "")
                hw = csv_row.get("Handwritten OCR", "")
                final = csv_row.get("Resolved Register No", "")
                cand_sig = csv_row.get("Candidate Signed", "")
                inv_sig = csv_row.get("Invigilator Signed", "")
            else:
                barcode = res["barcode"]
                bubble = res["bubble_regno"]
                hw = res["handwritten_regno"]
                final = res["final_regno"]
                cand_sig = "YES" if res["cand_signed"] else "NO"
                inv_sig = "YES" if res["inv_signed"] else "NO"
                
                # Keep processed data in memory only. Export writes the file.
                self.omr_csv_records[filename] = self.build_export_row_from_result(res)
                
            # Load into editing inputs
            self.edit_barcode.delete(0, tk.END)
            self.edit_barcode.insert(0, barcode)
            
            self.edit_bubble.delete(0, tk.END)
            self.edit_bubble.insert(0, bubble)
            
            self.edit_hw.delete(0, tk.END)
            self.edit_hw.insert(0, hw)
            
            self.edit_final.delete(0, tk.END)
            self.edit_final.insert(0, final)
            
            self.edit_cand_sig.set(cand_sig)
            self.edit_inv_sig.set(inv_sig)
            
            
            self.edit_subject.delete(0, tk.END)
            self.edit_subject.insert(0, res["subject_code"])
            
            self.edit_booklet.delete(0, tk.END)
            self.edit_booklet.insert(0, res["booklet_number"])

            # Populate threshold (read-only diagnostic field)
            self.edit_booklet_threshold.config(state="normal")
            self.edit_booklet_threshold.delete(0, tk.END)
            self.edit_booklet_threshold.insert(0, str(res.get("omr_threshold", "")))
            self.edit_booklet_threshold.config(state="readonly")


            # Update Metadata Label
            type_str = ("B&W Padded" if res["is_padded_bw"]
                        else ("Grayscale" if res["is_bw"] else "Color"))
            self.meta_lbl.config(
                text=(f"File: {res['filename']}\n"
                      f"Res: {res['resolution']}  |  {type_str}  |  "
                      f"Sat: {res['avg_sat']}  |  IsBlack: {res['isblack']}")
            )
            
            # Update Discrepancy Status based on current values
            final_regno, has_disc, disc_detail = determine_final_regno(bubble, hw)
            if has_disc:
                self.disc_frame.config(bg="#c62828")
                self.disc_lbl.config(text=f"DISCREPANCY: MISMATCH\n{disc_detail}", bg="#c62828")
            else:
                self.disc_frame.config(bg="#2e7d32")
                self.disc_lbl.config(text=f"DISCREPANCY STATUS: MATCHED\n{disc_detail}", bg="#2e7d32")

            self.set_sheet_status(
                filename, extracted=self._extracted_status_from_result(res))
                
            # Convert and Display Images — sizes scale with panel layout
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            self._full_omr_cv_img = res["full_annotated_img"]
            self._refresh_full_omr_image()
            self.display_image_in_label(res["debug_grid_img"], self.grid_canvas_lbl,
                max_size=(int(sw*0.34), int(sh*0.46)))
            self.display_image_in_label(res["reg_box_crop"], self.hw_crop_lbl,
                max_size=(int(sw*0.34), int(sh*0.08)))
            self.display_image_in_label(res["cand_sig_crop"], self.cand_sig_lbl,
                max_size=(int(sw*0.16), int(sh*0.10)))
            self.display_image_in_label(res["inv_sig_crop"], self.inv_sig_lbl,
                max_size=(int(sw*0.16), int(sh*0.10)))
            
            self.status_lbl.config(text="Sheet loaded successfully", foreground="#00e676")
            audit.log("counter_foil", "sheet_processed", details={"file": filename})
            self.last_loaded_filename = filename
            self.last_loaded_folder = self.omr_dir
        except Exception as e:
            audit.log("counter_foil", "sheet_processed", outcome="failed",
                      details={"file": filename, "error": str(e)})
            self.status_lbl.config(text="Error processing sheet", foreground="#ff3d00")
            self.set_sheet_status(filename, extracted="error")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Execution Error", f"Failed during sheet processing:\n{e}")

    def load_omr_csv(self):
        self.omr_csv_records = {}
        if not self.omr_dir:
            return
        csv_path = os.path.join(self.omr_dir, "OMR_Sheet_Results.csv")
        if os.path.exists(csv_path):
            import csv
            try:
                with open(csv_path, mode="r", newline="", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        filename = row.get("Filename")
                        if filename:
                            self.omr_csv_records[os.path.basename(filename)] = row
            except Exception as e:
                print(f"Error loading CSV master: {e}")

    def build_export_row_from_result(self, res):
        return {
            "Filename": res.get("filename", ""),
            "Decoded Barcode": res.get("barcode", ""),
            "OMR Bubble Reading": res.get("bubble_regno", ""),
            "Handwritten OCR": res.get("handwritten_regno", ""),
            "Resolved Register No": res.get("final_regno", ""),
            "Candidate Signed": "YES" if res.get("cand_signed") else "NO",
            "Invigilator Signed": "YES" if res.get("inv_signed") else "NO",
            "Subject Code": res.get("subject_code", ""),
            "BookletSlNo": res.get("BookletSlNo", res.get("booklet_number", "")),
            "OMRThreshold": str(res.get("omr_threshold", "")),
            "IsBlack": str(res.get("isblack", ""))
        }

    def write_omr_csv(self, csv_path):
        import csv
        with open(csv_path, mode="w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Filename", "Decoded Barcode", "OMR Bubble Reading",
                "Handwritten OCR", "Resolved Register No",
                "Candidate Signed", "Invigilator Signed", "Subject Code",
                "BookletSlNo", "OMRThreshold", "IsBlack"
            ])
            for filename in sorted(self.filenames):
                # filenames list holds full paths; CSV key is basename
                key = os.path.basename(filename)
                if key in self.omr_csv_records:
                    row = self.omr_csv_records[key]
                    writer.writerow([
                        row.get("Filename", key),
                        row.get("Decoded Barcode", ""),
                        row.get("OMR Bubble Reading", ""),
                        row.get("Handwritten OCR", ""),
                        row.get("Resolved Register No", ""),
                        row.get("Candidate Signed", ""),
                        row.get("Invigilator Signed", ""),
                        row.get("Subject Code", ""),
                        row.get("BookletSlNo", ""),
                        row.get("OMRThreshold", ""),
                        row.get("IsBlack", "")
                    ])

    def export_results_to_excel(self):
        if not self.omr_csv_records:
            messagebox.showwarning("Warning", "No processed data available to export!")
            return

        initial_file = "OMR_Sheet_Results.csv"
        save_path = filedialog.asksaveasfilename(
            title="Export OMR results",
            initialdir=self.omr_dir if self.omr_dir else os.getcwd(),
            initialfile=initial_file,
            defaultextension=".csv",
            filetypes=[
                ("Excel CSV", "*.csv"),
                ("All Files", "*.*")
            ])
        if not save_path:
            return

        try:
            self.write_omr_csv(save_path)
            audit.log("counter_foil", "results_exported",
                      details={"file": os.path.basename(save_path), "records": len(self.omr_csv_records)})
            self.status_lbl.config(
                text=f"Exported to: {os.path.basename(save_path)}",
                foreground="#00e676")
            messagebox.showinfo("Success", f"Results exported to:\n{save_path}")
        except Exception as e:
            audit.log("counter_foil", "results_exported", outcome="failed", details={"error": str(e)})
            messagebox.showerror("Error", f"Failed to export results: {e}")

    def save_corrections(self, filename_to_save=None, show_msg=True):
        if filename_to_save is None:
            # combo holds full path; use basename as record key
            raw = self.file_combo.get()
            filename_to_save = os.path.basename(raw) if raw else ""

        if not filename_to_save:
            if show_msg:
                messagebox.showwarning("Warning", "No OMR sheet selected!")
            return
            
        barcode = self.edit_barcode.get().strip()
        bubble = self.edit_bubble.get().strip()
        hw = self.edit_hw.get().strip()
        final = self.edit_final.get().strip()
        cand_sig = self.edit_cand_sig.get()
        inv_sig = self.edit_inv_sig.get()
        
        # Update in-memory record
        image_path = ""
        if self.current_omr_res:
            image_path = self.current_omr_res.get("image_path", "")
        if not image_path:
            raw = self.file_combo.get()
            image_path = os.path.abspath(raw) if raw else filename_to_save

        self.omr_csv_records[filename_to_save] = {
            "Filename": image_path,
            "Decoded Barcode": barcode,
            "OMR Bubble Reading": bubble,
            "Handwritten OCR": hw,
            "Resolved Register No": final,
            "Candidate Signed": cand_sig,
            "Invigilator Signed": inv_sig,
            "Subject Code": self.edit_subject.get().strip(),
            "BookletSlNo": self.edit_booklet.get().strip(),
            "OMRThreshold": self.edit_booklet_threshold.get().strip(),
            "IsBlack": str(
                self.current_omr_res.get("isblack", "")
                if self.current_omr_res else "")
        }
        if show_msg:
            audit.log("counter_foil", "corrections_saved", details={"file": filename_to_save})

        self.status_lbl.config(
            text="Corrections saved in memory",
            foreground="#00e676")
        
        if show_msg:
            # Recalculate discrepancy status display for the current UI
            final_regno, has_disc, disc_detail = determine_final_regno(bubble, hw)
            if has_disc:
                self.disc_frame.config(bg="#c62828")
                self.disc_lbl.config(text=f"DISCREPANCY: MISMATCH\n{disc_detail}", bg="#c62828")
            else:
                self.disc_frame.config(bg="#2e7d32")
                self.disc_lbl.config(text=f"DISCREPANCY STATUS: MATCHED\n{disc_detail}", bg="#2e7d32")
                
            messagebox.showinfo(
                "Success",
                f"Corrections for {filename_to_save} saved in memory.\n"
                "Use Export to Excel to save a file.")
            
    def navigate_sheet(self, direction):
        if not self.file_combo["values"]:
            return
            
        current_idx = self.file_combo.current()
        new_idx = current_idx + direction
        
        if 0 <= new_idx < len(self.file_combo["values"]):
            # Auto-save changes of current sheet first silently (which is handled inside process_selected_sheet, 
            # but we explicitly do it here too just to be safe and logical)
            self.file_combo.current(new_idx)
            self.process_selected_sheet()
            
    def recalculate_discrepancy_and_final(self, event=None):
        bubble = self.edit_bubble.get().strip()
        hw = self.edit_hw.get().strip()
        
        # Determine final resolved register number based on the SOP rules
        final_regno, has_disc, disc_detail = determine_final_regno(bubble, hw)
        
        # Update the Resolved Register No entry field automatically
        self.edit_final.delete(0, tk.END)
        self.edit_final.insert(0, final_regno)
        
        # Update the discrepancy status label
        if has_disc:
            self.disc_frame.config(bg="#c62828")
            self.disc_lbl.config(text=f"DISCREPANCY: MISMATCH\n{disc_detail}", bg="#c62828")
        else:
            self.disc_frame.config(bg="#2e7d32")
            self.disc_lbl.config(text=f"DISCREPANCY STATUS: MATCHED\n{disc_detail}", bg="#2e7d32")
    #Subject Code Extraction
    def extract_subject_code(self, img, scale_x, scale_y):
        h, w, _ = img.shape
        
        x1 = int(40 * scale_x)
        x2 = int(400 * scale_x)
        y1 = int(20 * scale_y)
        y2 = int(140 * scale_y)
        
        crop = img[y1:y2, x1:x2]
        
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        _, th = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
        
        reader = get_ocr_reader()
        results = reader.readtext(th, detail=0)

        # Combine all detected text
        text = " ".join(results)
        
        # Extract only digits and keep the first three digits
        digits = ''.join(filter(str.isdigit, text))
        digits = digits[:3]

        return digits.strip(), crop

    # Booklet Serial Number Extraction — reads large printed 7-digit number below QCA label (bottom-right)
    def extract_booklet_number(self, img, scale_x, scale_y):
        """
        Reads the QCA Booklet Serial Number — a large bold printed number located in a
        bordered box at the bottom-right of the sheet, below the 'QCA Booklet Serial Number' label.
        At 1654x1090 reference: the number box is approx y=910-980, x=920-1580.
        Uses OCR on the cropped region.
        Returns (booklet_sl_no_str, ocr_confidence, debug_crop_img).
        """
        h, w, _ = img.shape

        # Tight crop around the booklet serial number box (bottom-right corner)
        # Purple box in reference image (1654x1090):
        #   x: ~920–1570  →  55.6% – 94.9% of width
        #   y: ~790–870   →  72.5% – 79.8% of height
        x1 = int(w * 0.556)
        x2 = int(w * 0.949)
        y1 = int(h * 0.725)
        y2 = int(h * 0.800)

        # Clamp to image bounds
        x1 = max(0, x1); x2 = min(w, x2)
        y1 = max(0, y1); y2 = min(h, y2)

        crop = img[y1:y2, x1:x2]

        # Save debug crop so operator can verify the region
        debug_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "OMR", "debug_qca.png")
        try:
            cv2.imwrite(debug_path, crop)
        except Exception:
            pass

        if crop.size == 0:
            return "", 0.0, img[max(0,y1-5):min(h,y2+5), max(0,x1-5):min(w,x2+5)]

        # ── Pre-processing for large bold printed digits ──────────────────────
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

        # Upscale 2× — EasyOCR performs better on larger text
        gray_up = cv2.resize(gray, (gray.shape[1] * 2, gray.shape[0] * 2),
                             interpolation=cv2.INTER_CUBIC)

        # Otsu threshold on upscaled image
        _, th = cv2.threshold(gray_up, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # If most pixels are black (inverted scan), flip
        if np.mean(th) < 127:
            th = cv2.bitwise_not(th)

        # Slight dilation to thicken thin strokes
        kernel = np.ones((2, 2), np.uint8)
        th = cv2.dilate(th, kernel, iterations=1)

        # ── OCR ──────────────────────────────────────────────────────────────
        reader = get_ocr_reader()

        # Try on processed image first, fallback to raw gray upscaled
        best_text = ""
        best_conf = 0.0

        for ocr_input in [th, gray_up]:
            results = reader.readtext(ocr_input, detail=1,
                                      allowlist='0123456789',
                                      paragraph=False,
                                      width_ths=0.9,
                                      height_ths=0.5)
            for (_, text, conf) in results:
                digits_only = ''.join(filter(str.isdigit, text))
                if len(digits_only) >= 4 and conf > best_conf:
                    best_text = digits_only
                    best_conf = conf
            if best_text:
                break

        # Last-resort fallback: grab all digits regardless of confidence
        if not best_text:
            results = reader.readtext(gray_up, detail=1, allowlist='0123456789')
            all_digits = ''.join(filter(str.isdigit, " ".join(r[1] for r in results)))
            best_text = all_digits

        # ── Debug overlay on original image ──────────────────────────────────
        debug = img.copy()
        cv2.rectangle(debug, (x1, y1), (x2, y2), (0, 200, 255), 3)
        cv2.putText(debug, f"BSN:{best_text}", (x1, max(25, y1 - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 255), 2)
        crop_debug = debug[max(0, y1 - 10):min(h, y2 + 10),
                           max(0, x1 - 10):min(w, x2 + 10)]

        return best_text.strip(), round(float(best_conf), 3), crop_debug
    #---------------
    #def display_image_in_label(self, cv_img, tk_label, max_size=(500, 300)):
    #    if cv_img is None or cv_img.size == 0:
    #       tk_label.config(image="", text="Crop Unavailable")
    #        return
            
    #    # Convert BGR to RGB
    #   rgb_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
    #   pil_img = Image.fromarray(rgb_img)
        
    #   # Resize preserving aspect ratio
    #   w, h = pil_img.size
    #   max_w, max_h = max_size
        
    #   ratio = min(max_w / w, max_h / h)
    #   new_w = int(w * ratio)
    #   new_h = int(h * ratio)
        
    #   pil_img_resized = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
    #   # Save photo image reference to avoid garbage collection
    #   photo = ImageTk.PhotoImage(pil_img_resized)
    #   tk_label.config(image=photo, text="")
    #   tk_label.image = photo

    
    def _label_max_size(self, label, pad=8):
        """Return (max_w, max_h) from a label widget's current layout size."""
        self.root.update_idletasks()
        return (
            max(label.winfo_width() - pad, 120),
            max(label.winfo_height() - pad, 120),
        )

    def adjust_original_zoom(self, delta):
        if not hasattr(self, "full_omr_zoom"):
            self.full_omr_zoom = 1.0
        self.full_omr_zoom = max(0.5, min(4.0, self.full_omr_zoom + delta))
        if hasattr(self, "full_omr_zoom_lbl"):
            self.full_omr_zoom_lbl.config(text=f"{int(self.full_omr_zoom * 100)}%")
        self._refresh_full_omr_image()

    def _refresh_full_omr_image(self):
        if not hasattr(self, "full_omr_img_lbl"):
            return

        cv_img = getattr(self, "_full_omr_cv_img", None)
        if cv_img is None or cv_img.size == 0:
            self.full_omr_img_lbl.config(image="", text="No image loaded")
            self.full_omr_canvas_frame.configure(width=1, height=1)
            self.full_omr_canvas.configure(scrollregion=(0, 0, 1, 1))
            return

        rgb_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb_img)
        zoom = getattr(self, "full_omr_zoom", 1.0)
        new_w = max(1, int(pil_img.width * zoom))
        new_h = max(1, int(pil_img.height * zoom))

        pil_img_resized = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(pil_img_resized)
        self._full_omr_photo = photo
        self.full_omr_img_lbl.config(image=photo, text="")
        self.full_omr_canvas_frame.configure(width=new_w + 10, height=new_h + 10)
        self.full_omr_canvas.configure(scrollregion=(0, 0, new_w + 10, new_h + 10))

    def display_image_in_label(self, cv_img, tk_label, max_size=(500, 300)):
        if cv_img is None or cv_img.size == 0:
            tk_label.config(image="", text="Crop Unavailable")
            return
    
        # Convert BGR to RGB
        rgb_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb_img)
    
        # Resize
        w, h = pil_img.size
        max_w, max_h = max_size
        ratio = min(max_w / w, max_h / h)
    
        new_w = int(w * ratio)
        new_h = int(h * ratio)
    
        pil_img_resized = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
        # Create Tk image
        photo = ImageTk.PhotoImage(pil_img_resized)
    
        # ✅ FIX: store reference INSIDE function using self
        if not hasattr(self, "_img_refs"):
            self._img_refs = []
    
        self._img_refs.append(photo)

        tk_label.config(image=photo, text="")
    
    
        # ✅ IMPORTANT: store reference at class level (not label)
       # if not hasattr(self, "_img_refs"):
       #     self._img_refs = []
    
       # self._img_refs.append(photo)
    
        #tk_label.config(image=photo, text="")
    #SQL Server Connection
    
    def get_sql_connection(self):
        from db_credentials import get_sql_connection
        return get_sql_connection()

    #Check for Table exesits
    def check_table_exists(self, conn, table_name):
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT COUNT(*) 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_NAME = ?
        """, (table_name,))
        
        result = cursor.fetchone()
        return result[0] == 1

    def check_column_exists(self, conn, table_name, column_name):
        cursor = conn.cursor()
        cursor.execute("""
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = ? AND COLUMN_NAME = ?
        """, (table_name, column_name))
        result = cursor.fetchone()
        return result[0] == 1

    def insert_omr_result_row(self, conn, cursor, table_name, result):
        columns = [
            "filename", "barcode", "bubble_regno", "handwritten_regno",
            "final_regno", "discrepancy", "discrepancy_detail",
            "candidate_signed", "invigilator_signed", "subject_code",
            "BookletSlNo", "omr_threshold", "whitenerflag"
        ]
        values = [
            result["filename"],
            result["barcode"],
            result["bubble_regno"],
            result["handwritten_regno"],
            result["final_regno"],
            int(result["has_disc"]),
            result["disc_detail"],
            int(result["cand_signed"]),
            int(result["inv_signed"]),
            result["subject_code"],
            result.get("BookletSlNo", result.get("booklet_number", "")),
            result.get("omr_threshold", 0.0),
            int(bool(result.get("whitenerflag", False)))
        ]

        if self.check_column_exists(conn, table_name, "bubble_Th_status"):
            columns.append("bubble_Th_status")
            values.append(int(result.get("bubble_Th_status", 0)))

        if self.check_column_exists(conn, table_name, "isblack"):
            columns.append("isblack")
            values.append(int(result.get("isblack", 0)))

        placeholders = ", ".join(["?"] * len(columns))
        column_sql = ", ".join(columns)
        cursor.execute(
            f"INSERT INTO {table_name} ({column_sql}) VALUES ({placeholders})",
            tuple(values))
    #Insert Only If Table Exists
    def insert_into_mssql(self,result):
        conn = self.get_sql_connection()
        cursor = conn.cursor()
        
        table_name = "omr_results"
        
        # ✅ Check table existence
        if not self.check_table_exists(conn, table_name):
            print(f"Table '{table_name}' does not exist. Skipping insert.")
            conn.close()
            return
        
        # ✅ Optional: Avoid duplicate insert by filename
        cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE filename = ?", (result["filename"],))
        exists = cursor.fetchone()[0]
        
        if exists > 0:
            print(f"Skipping duplicate: {result['filename']}")
            conn.close()
            return
        
        # ✅ Insert data
        self.insert_omr_result_row(conn, cursor, table_name, result)
        
        conn.commit()
        conn.close()
        # Update grid for the currently displayed sheet
        if hasattr(self, 'set_sheet_status'):
            fn = os.path.basename(result.get("filename", ""))
            if fn:
                self.set_sheet_status(fn, saved_db="imported")

    def _show_processing_dialog(self):
        if getattr(self, "_processing_dialog", None):
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Processing")
        dialog.transient(self.root)
        dialog.resizable(False, False)
        dialog.protocol("WM_DELETE_WINDOW", lambda: None)
        dialog.configure(bg="#1c1c22")

        tk.Label(
            dialog,
            text="Processing data...\nPlease do not click anything until the operation is complete.",
            bg="#1c1c22",
            fg="#ffffff",
            font=("Segoe UI", 11, "bold"),
            justify="center",
            padx=28,
            pady=18).pack(fill="both", expand=True)

        bar = ttk.Progressbar(dialog, mode="indeterminate", length=260)
        bar.pack(padx=28, pady=(0, 20))
        bar.start(12)

        dialog.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        dialog.grab_set()
        self.root.config(cursor="wait")
        self._processing_dialog = dialog
        self._processing_bar = bar

    def _close_processing_dialog(self):
        dialog = getattr(self, "_processing_dialog", None)
        if dialog:
            try:
                dialog.grab_release()
                dialog.destroy()
            except tk.TclError:
                pass
        self._processing_dialog = None
        self._processing_bar = None
        self.root.config(cursor="")

    def _set_bulk_controls_state(self, state):
        for attr in ("All_btn", "export_btn", "prev_btn", "next_btn"):
            widget = getattr(self, attr, None)
            if widget:
                try:
                    widget.config(state=state)
                except tk.TclError:
                    pass

    def _run_on_ui(self, callback, *args, **kwargs):
        self.root.after(0, lambda: callback(*args, **kwargs))

    def process_all_sheets_to_mssql(self):
        if not self.omr_dir or not os.path.exists(self.omr_dir):
            messagebox.showerror("Error", "Invalid folder path!")
            return
        
        image_paths = list(self.image_paths)  # already built from GUI folder
        
        if not image_paths:
            messagebox.showwarning("Warning", "No images found in selected folder!")
            return

        if getattr(self, "_bulk_processing", False):
            return

        self._bulk_processing = True
        total = len(image_paths)
        processed_count = 0
        self._init_status_grid()
        self.progress["value"] = 0
        self.progress["maximum"] = total
        self._set_bulk_controls_state("disabled")
        self._show_processing_dialog()

        def worker():
            conn = None
            processed = 0
            failed = 0
            try:
                conn = self.get_sql_connection()
                cursor = conn.cursor()
                table_name = "omr_results"
                cursor.execute("""
                SELECT COUNT(*)
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_NAME = ?
                """, (table_name,))

                if cursor.fetchone()[0] == 0:
                    raise RuntimeError(f"Table '{table_name}' does not exist!")

                for i, img_path in enumerate(image_paths, 1):
                    filename = os.path.basename(img_path)
                    self._run_on_ui(
                        self._update_counterfoil_bulk_progress,
                        i, total, filename, "pending", "pending")

                    try:
                        res = process_single_sheet_for_demo(img_path)
                        if not res:
                            failed += 1
                            self._run_on_ui(
                                self._update_counterfoil_bulk_progress,
                                i, total, filename, "error", "error")
                            continue

                        extracted = self._extracted_status_from_result(res)
                        self.omr_csv_records[filename] = self.build_export_row_from_result(res)
                        processed += 1

                        cursor.execute(
                            f"SELECT COUNT(*) FROM {table_name} WHERE filename = ?",
                            (res["filename"],)
                        )
                        if cursor.fetchone()[0] == 0:
                            self.insert_omr_result_row(conn, cursor, table_name, res)

                        self._run_on_ui(
                            self._update_counterfoil_bulk_progress,
                            i, total, filename, extracted, "imported")

                    except Exception as e:
                        failed += 1
                        print(f"Error processing {filename}: {e}")
                        self._run_on_ui(
                            self._update_counterfoil_bulk_progress,
                            i, total, filename, "error", "error")

                conn.commit()
                audit.log("counter_foil", "bulk_database_import",
                          details={"total": total, "processed": processed, "errors": failed})
                self._run_on_ui(self._finish_counterfoil_bulk_processing, processed, failed, None)

            except Exception as e:
                audit.log("counter_foil", "bulk_database_import", outcome="failed",
                          details={"error": str(e)})
                self._run_on_ui(self._finish_counterfoil_bulk_processing, processed, failed, e)
            finally:
                if conn:
                    try:
                        conn.close()
                    except Exception:
                        pass

        threading.Thread(target=worker, name="counterfoil-bulk-worker", daemon=True).start()

    def _update_counterfoil_bulk_progress(self, index, total, filename, extracted, saved_db):
        self.set_sheet_status(filename, extracted=extracted, saved_db=saved_db)
        self.status_lbl.config(
            text=f"Processing {index}/{total} - {filename}",
            foreground="#ffeb3b")
        self.progress["value"] = index

    def _finish_counterfoil_bulk_processing(self, processed_count, failed_count, error):
        self._bulk_processing = False
        self._close_processing_dialog()
        self._refresh_status_summary()
        self._set_bulk_controls_state("normal")
        if hasattr(self, "export_btn") and processed_count <= 0:
            self.export_btn.config(state="disabled")

        if error:
            self.status_lbl.config(text=f"Database Error: {error}", foreground="#ff3d00")
            messagebox.showerror("Database Error", str(error))
            return

        self.status_lbl.config(
            text="All sheets processed and saved to MSSQL",
            foreground="#00e676")
        messagebox.showinfo(
            "Success",
            f"Processed: {processed_count}/{self.progress['maximum']}\n"
            f"Errors: {failed_count}")

    
  

#if __name__ == "__main__":
#    root = tk.Tk()def insert_into_mssql(result):
#    conn = get_sql_connection()
#    cursor = conn.cursor()



if __name__ == "__main__":
    root = tk.Tk()
    app = VisualOMRViewerDemo(root)
    root.mainloop()
