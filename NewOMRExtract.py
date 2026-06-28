# Generated from: NewOMRExtract.ipynb
# Converted at: 2026-06-28T08:23:47.242Z
# Next step (optional): refactor into modules & generate tests with RunCell
# Quick start: pip install runcell

import os
import glob
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
import numpy as np
from PIL import Image, ImageTk
from pyzbar.pyzbar import decode
import onnxruntime as ort
import pyodbc
import easyocr
import torch

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
    
    return bubble_regno, crop_debug, grid_x, grid_y, align_method

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

# ──────────────────────────────────────────────────────────
# MAIN PROCESSING WRAPPER
# ──────────────────────────────────────────────────────────
def process_single_sheet_for_demo(img_path):
    img = cv2.imread(img_path)
    if img is None:
        return None
        
    h, w, _ = img.shape
    tpl = get_omr_template(w)
    
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    avg_sat = np.mean(hsv[:, :, 1])
    is_bw = avg_sat < 8.0
    
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
    bubble_regno, debug_grid_img, grid_x, grid_y, align_method = read_bubbles_custom(img, tpl, scale_x, scale_y, is_bw)
            
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
    
    subject_code, subject_crop = VisualOMRViewerDemo.extract_subject_code(None, img, scale_x, scale_y)
    booklet_sl_no, omr_threshold, booklet_crop = VisualOMRViewerDemo.extract_booklet_number(None, img, scale_x, scale_y)

    return {
        "filename": os.path.basename(img_path),
        "resolution": f"{w}x{h}",
        "avg_sat": round(avg_sat, 2),
        "is_bw": is_bw,
        "is_padded_bw": is_padded_bw,
        "barcode": barcode_val,
        "bubble_regno": bubble_regno,
        "handwritten_regno": handwritten_regno,
        "final_regno": final_regno,
        
        "subject_code": subject_code,
        "booklet_number": booklet_sl_no,        # kept as "booklet_number" for UI compat
        "BookletSlNo": booklet_sl_no,           # canonical field name
        "omr_threshold": omr_threshold,         # OCR confidence score for booklet number
        "subject_crop": subject_crop,
        "booklet_crop": booklet_crop,

        "has_disc": has_disc,
        "disc_detail": disc_detail,
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
        s.map("TButton", background=[("active", self._ACCH), ("disabled", "#44445a")])
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
               font_size=9, bold=False, readonly=False):
        px = self._px
        tk.Label(parent, text=label,
                 bg=self._PANEL, fg=self._FG,
                 font=("Segoe UI", self._fs(8), "bold"),
                 anchor="w").pack(fill="x", padx=px(8), pady=(px(3), 0))
        e = ttk.Entry(parent,
                      font=(font_name, self._fs(font_size),
                            "bold" if bold else "normal"))
        if readonly:
            e.config(state="readonly")
        e.pack(fill="x", padx=px(8), pady=(1, px(2)))
        return e

    def build_ui(self):
        px = self._px; fs = self._fs
        BG = self._BG; P = self._PANEL; AC = self._ACCENT; FG = self._FG; FGD = self._FGD

        # ── HEADER ROW ─────────────────────────────────────────────────────
        header = tk.Frame(self.root, bg=P, height=px(46))
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        tk.Label(header,
                 text="OMR ICR OCR Extraction Engine",
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
                  font=("Segoe UI", fs(9), "bold")).pack(
                      side="left", padx=(px(10), px(3)))

        self.prev_btn = ttk.Button(top, text="◀", width=3,
            command=lambda: self.navigate_sheet(-1), state="disabled")
        self.prev_btn.pack(side="left", padx=px(2))

        self.file_combo = ttk.Combobox(top, values=[], state="readonly",
                                       width=52, font=("Segoe UI", fs(9)))
        self.file_combo.pack(side="left", padx=px(3))
        self.file_combo.bind("<<ComboboxSelected>>",
                             lambda e: self.process_selected_sheet())

        self.next_btn = ttk.Button(top, text="▶", width=3,
            command=lambda: self.navigate_sheet(1), state="disabled")
        self.next_btn.pack(side="left", padx=px(2))

        ttk.Button(top, text="📂 Select Folder",
                   command=self.browse_folder).pack(side="left", padx=px(6))

        self.status_lbl = ttk.Label(top, text="Ready",
            style="Pan.TLabel",
            font=("Segoe UI", fs(9), "italic"),
            foreground="#ffeb3b")
        self.status_lbl.pack(side="left", padx=px(8))

        self.progress = ttk.Progressbar(
            top, orient="horizontal", length=px(150), mode="determinate",
            style="Thin.Horizontal.TProgressbar")
        self.progress.pack(side="left", padx=px(4))

        # Right side: Process All button
        self.All_btn = ttk.Button(top, text="⚙  Process All",
            command=self.process_all_sheets_to_mssql, width=14)
        self.All_btn.pack(side="right", padx=px(12))

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
        self.full_omr_lbl = tk.Label(col0, bg=P)
        self.full_omr_lbl.pack(fill="both", expand=True,
                               padx=px(3), pady=px(3))

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

        # COL 2 — Results (scrollable)
        col2_outer = tk.LabelFrame(content,
            text=" Extraction & Processing Results ",
            bg=P, fg=AC,
            font=("Segoe UI", fs(8), "bold"), bd=1, relief="solid")
        col2_outer.grid(row=0, column=2, sticky="nsew")

        col2_canvas = tk.Canvas(col2_outer, bg=P,
                                highlightthickness=0, bd=0)
        col2_scroll = ttk.Scrollbar(col2_outer, orient="vertical",
                                    command=col2_canvas.yview)
        col2_canvas.configure(yscrollcommand=col2_scroll.set)
        col2_scroll.pack(side="right", fill="y")
        col2_canvas.pack(side="left", fill="both", expand=True)

        self.right_frame = tk.Frame(col2_canvas, bg=P)
        _win = col2_canvas.create_window((0, 0),
                                         window=self.right_frame, anchor="nw")

        col2_canvas.bind("<Configure>",
            lambda e: col2_canvas.itemconfig(_win, width=e.width))
        self.right_frame.bind("<Configure>",
            lambda e: col2_canvas.configure(
                scrollregion=col2_canvas.bbox("all")))
        col2_canvas.bind_all("<MouseWheel>",
            lambda e: col2_canvas.yview_scroll(
                int(-1*(e.delta/120)), "units"))

        self.build_results_panel()
        
    def build_results_panel(self):
        """Populate the scrollable right panel with all result fields."""
        px = self._px; fs = self._fs
        P = self._PANEL; FG = self._FG; FGD = self._FGD

        # Metadata
        self.meta_lbl = tk.Label(self.right_frame,
            text="File: —\nResolution: —\nType: —",
            justify="left", anchor="w",
            bg=P, fg=FGD, font=("Segoe UI", fs(8)))
        self.meta_lbl.pack(fill="x", padx=px(8), pady=(px(4), px(2)))

        self._sep(self.right_frame)

        # Subject Code
        self.edit_subject = self._field(
            self.right_frame, "Subject Code", bold=True)

        # Booklet Serial No
        self.edit_booklet = self._field(
            self.right_frame, "Booklet Serial No  (BookletSlNo)", bold=True)

        tk.Label(self.right_frame, text="OCR Confidence:",
                 bg=P, fg=FGD, font=("Segoe UI", fs(7)),
                 anchor="w").pack(fill="x", padx=px(8))
        self.edit_booklet_threshold = ttk.Entry(
            self.right_frame, font=("Consolas", fs(8)))
        self.edit_booklet_threshold.config(state="readonly")
        self.edit_booklet_threshold.pack(fill="x", padx=px(8), pady=(1, px(3)))

        self._sep(self.right_frame)

        # Barcode — inline label + entry
        bc_row = tk.Frame(self.right_frame, bg=P)
        bc_row.pack(fill="x", padx=px(8), pady=(px(3), px(1)))
        tk.Label(bc_row, text="Decoded Barcode:",
                 bg=P, fg=FG,
                 font=("Segoe UI", fs(8), "bold")).pack(side="left")
        self.edit_barcode = ttk.Entry(
            bc_row, font=("Consolas", fs(8), "bold"))
        self.edit_barcode.pack(side="right", fill="x",
                               expand=True, padx=(px(6), 0))

        self._sep(self.right_frame)

        # OMR Bubble reading
        self.edit_bubble = self._field(
            self.right_frame, "OMR Bubble Reading",
            font_size=10, bold=True)

        # Handwritten OCR
        self.edit_hw = self._field(
            self.right_frame, "Handwritten OCR Reading",
            font_size=10, bold=True)

        # Resolved Register No
        self.edit_final = self._field(
            self.right_frame, "Resolved Register No  (SOP Output)",
            font_size=11, bold=True)

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
            font=("Segoe UI", fs(8), "bold"), height=2)
        self.disc_lbl.pack(fill="x")

        self._sep(self.right_frame)

        # Signatures — side by side on one row
        sig_row = tk.Frame(self.right_frame, bg=P)
        sig_row.pack(fill="x", padx=px(8), pady=px(3))

        tk.Label(sig_row, text="Candidate Signed:",
                 bg=P, fg=FG,
                 font=("Segoe UI", fs(8), "bold")).grid(
                     row=0, column=0, sticky="w", pady=px(2))
        self.edit_cand_sig = ttk.Combobox(
            sig_row, values=["YES", "NO"],
            state="readonly", width=7,
            font=("Segoe UI", fs(8)))
        self.edit_cand_sig.grid(row=0, column=1,
                                sticky="w", padx=(px(4), px(14)))

        tk.Label(sig_row, text="Invigilator Signed:",
                 bg=P, fg=FG,
                 font=("Segoe UI", fs(8), "bold")).grid(
                     row=0, column=2, sticky="w")
        self.edit_inv_sig = ttk.Combobox(
            sig_row, values=["YES", "NO"],
            state="readonly", width=7,
            font=("Segoe UI", fs(8)))
        self.edit_inv_sig.grid(row=0, column=3,
                               sticky="w", padx=(px(4), 0))

        # Save button
        self.save_btn = ttk.Button(self.right_frame,
            text="💾  Save Corrections",
            command=self.save_corrections)
        self.save_btn.pack(fill="x", padx=px(8), pady=px(6))

        self._sep(self.right_frame)

        # ── Sheet Process Status grid ──────────────────────────────────────
        status_hdr = tk.Frame(self.right_frame, bg=P)
        status_hdr.pack(fill="x", padx=px(8), pady=(px(4), px(1)))

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

        # Treeview + scrollbar wrapper
        grid_frame = tk.Frame(self.right_frame, bg=P)
        grid_frame.pack(fill="both", expand=True, padx=px(8), pady=(0, px(6)))

        cols = ("img", "extracted", "saved_db")
        self.status_tree = ttk.Treeview(
            grid_frame, columns=cols, show="headings",
            height=8, selectmode="browse")

        # Column headings & widths
        self.status_tree.heading("img",       text="Image")
        self.status_tree.heading("extracted", text="Extracted")
        self.status_tree.heading("saved_db",  text="Saved to DB")
        self.status_tree.column("img",       width=px(130), anchor="w",   stretch=True)
        self.status_tree.column("extracted", width=px(90),  anchor="center", stretch=True)
        self.status_tree.column("saved_db",  width=px(90),  anchor="center", stretch=True)

        # Row tag colours
        self.status_tree.tag_configure("ok",       background="#1b5e20", foreground="#a5d6a7")
        self.status_tree.tag_configure("warning",  background="#4e2600", foreground="#ffcc80")
        self.status_tree.tag_configure("error",    background="#4e0000", foreground="#ef9a9a")
        self.status_tree.tag_configure("imported", background="#0d2f5e", foreground="#90caf9")
        self.status_tree.tag_configure("pending",  background="#2a2a3a", foreground="#888899")

        # Style the treeview to match dark theme
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

        # Internal lookup: filename -> treeview iid
        self._status_iids = {}
        self._status_state = {}   # filename -> {"extracted": ..., "saved_db": ...}

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
                if current_idx <= 0:
                    self.prev_btn.config(state="disabled")
                else:
                    self.prev_btn.config(state="normal")
                    self.All_btn.config(state="normal")
                if current_idx >= total_files - 1 or current_idx == -1:
                    self.next_btn.config(state="disabled")
                    self.All_btn.config(state="disabled")
                else:
                    self.next_btn.config(state="normal")
                    self.All_btn.config(state="normal")
            
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
                
                # Auto-populate in-memory record
                self.omr_csv_records[filename] = {
                    "Filename": filename,
                    "Decoded Barcode": barcode,
                    "OMR Bubble Reading": bubble,
                    "Handwritten OCR": hw,
                    "Resolved Register No": final,
                    "Candidate Signed": cand_sig,
                    "Invigilator Signed": inv_sig,
                    "Subject Code": res.get("subject_code", ""),
                    "BookletSlNo": res.get("BookletSlNo", ""),
                    "OMRThreshold": str(res.get("omr_threshold", ""))
                }
                
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
                text=f"File: {res['filename']}\nRes: {res['resolution']}  |  {type_str}  |  Sat: {res['avg_sat']}"
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
            self.display_image_in_label(
                res["full_annotated_img"], self.full_omr_lbl,
                max_size=self._label_max_size(self.full_omr_lbl))
            self.display_image_in_label(res["debug_grid_img"], self.grid_canvas_lbl,
                max_size=(int(sw*0.34), int(sh*0.46)))
            self.display_image_in_label(res["reg_box_crop"], self.hw_crop_lbl,
                max_size=(int(sw*0.34), int(sh*0.08)))
            self.display_image_in_label(res["cand_sig_crop"], self.cand_sig_lbl,
                max_size=(int(sw*0.16), int(sh*0.10)))
            self.display_image_in_label(res["inv_sig_crop"], self.inv_sig_lbl,
                max_size=(int(sw*0.16), int(sh*0.10)))
            
            self.status_lbl.config(text="Sheet loaded successfully", foreground="#00e676")
            self.last_loaded_filename = filename
            self.last_loaded_folder = self.omr_dir
        except Exception as e:
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
                            self.omr_csv_records[filename] = row
            except Exception as e:
                print(f"Error loading CSV master: {e}")

    def save_omr_csv(self):
        import csv
        csv_path = os.path.join(self.omr_dir, "OMR_Sheet_Results.csv")
        try:
            with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Filename", "Decoded Barcode", "OMR Bubble Reading", 
                    "Handwritten OCR", "Resolved Register No", 
                    "Candidate Signed", "Invigilator Signed", "Subject Code",
                    "BookletSlNo", "OMRThreshold"
                ])
                for filename in sorted(self.filenames):
                    # filenames list holds full paths; CSV key is basename
                    key = os.path.basename(filename)
                    if key in self.omr_csv_records:
                        row = self.omr_csv_records[key]
                        writer.writerow([
                            key,
                            row.get("Decoded Barcode", ""),
                            row.get("OMR Bubble Reading", ""),
                            row.get("Handwritten OCR", ""),
                            row.get("Resolved Register No", ""),
                            row.get("Candidate Signed", ""),
                            row.get("Invigilator Signed", ""),
                            row.get("Subject Code", ""),
                            row.get("BookletSlNo", ""),
                            row.get("OMRThreshold", "")
                        ])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save CSV database: {e}")

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
        self.omr_csv_records[filename_to_save] = {
            "Filename": filename_to_save,
            "Decoded Barcode": barcode,
            "OMR Bubble Reading": bubble,
            "Handwritten OCR": hw,
            "Resolved Register No": final,
            "Candidate Signed": cand_sig,
            "Invigilator Signed": inv_sig,
            "Subject Code": self.edit_subject.get().strip(),
            "BookletSlNo": self.edit_booklet.get().strip(),
            "OMRThreshold": self.edit_booklet_threshold.get().strip()
        }

        
        # Write to master CSV file
        self.save_omr_csv()
        
        csv_path = os.path.join(self.omr_dir, "OMR_Sheet_Results.csv")
        self.status_lbl.config(text="Saved to: OMR_Sheet_Results.csv", foreground="#00e676")
        
        if show_msg:
            # Recalculate discrepancy status display for the current UI
            final_regno, has_disc, disc_detail = determine_final_regno(bubble, hw)
            if has_disc:
                self.disc_frame.config(bg="#c62828")
                self.disc_lbl.config(text=f"DISCREPANCY: MISMATCH\n{disc_detail}", bg="#c62828")
            else:
                self.disc_frame.config(bg="#2e7d32")
                self.disc_lbl.config(text=f"DISCREPANCY STATUS: MATCHED\n{disc_detail}", bg="#2e7d32")
                
            messagebox.showinfo("Success", f"Corrections for {filename_to_save} saved successfully to:\n{csv_path}")
            
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
        
        # Extract only digits
        digits = ''.join(filter(str.isdigit, text))

        
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
        return pyodbc.connect(
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=RAO-PC;"
            "DATABASE=KPSCOMRICRExtraction;"
            "UID=kpsc;PWD=qwer"
        )
        #return conn

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
        cursor.execute(f"""
        INSERT INTO {table_name} (
            filename,
            barcode,
            bubble_regno,
            handwritten_regno,
            final_regno,
            discrepancy,
            discrepancy_detail,
            candidate_signed,
            invigilator_signed,
            subject_code,
            BookletSlNo,
            omr_threshold
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result["filename"],
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
            result.get("omr_threshold", 0.0)
        ))
        
        conn.commit()
        conn.close()
        # Update grid for the currently displayed sheet
        if hasattr(self, 'set_sheet_status'):
            fn = os.path.basename(result.get("filename", ""))
            if fn:
                self.set_sheet_status(fn, saved_db="imported")

    def process_all_sheets_to_mssql(self):
        if not self.omr_dir or not os.path.exists(self.omr_dir):
            messagebox.showerror("Error", "Invalid folder path!")
            return
        
        image_paths = self.image_paths  # ✅ already built from GUI folder
        
        if not image_paths:
            messagebox.showwarning("Warning", "No images found in selected folder!")
            return
    
        try:
            conn = self.get_sql_connection()
            cursor = conn.cursor()
    
            table_name = "omr_results"
    
            # ✅ Check if table exists
            cursor.execute("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_NAME = ?
            """, (table_name,))
            
            if cursor.fetchone()[0] == 0:
                messagebox.showerror("Error", f"Table '{table_name}' does not exist!")
                conn.close()
                return
    
            total = len(image_paths)
            self._init_status_grid()
            self.progress["value"] = 0
            self.progress["maximum"] = total
            
            for i, img_path in enumerate(image_paths, 1):
                filename = os.path.basename(img_path)

                self.set_sheet_status(filename, extracted="pending", saved_db="pending")
                self.status_lbl.config(
                    text=f"Processing {i}/{total} — {filename}",
                    foreground="#ffeb3b")
                self.root.update_idletasks()

                try:
                    res = process_single_sheet_for_demo(img_path)
                    if not res:
                        self.set_sheet_status(
                            filename, extracted="error", saved_db="error")
                        continue

                    extracted = self._extracted_status_from_result(res)

                    cursor.execute(
                        f"SELECT COUNT(*) FROM {table_name} WHERE filename = ?",
                        (res["filename"],)
                    )
                    if cursor.fetchone()[0] > 0:
                        self.set_sheet_status(
                            filename, extracted=extracted, saved_db="imported")
                        continue

                    cursor.execute(f"""
                    INSERT INTO {table_name} (
                        filename, barcode, bubble_regno, handwritten_regno,
                        final_regno, discrepancy, discrepancy_detail,
                        candidate_signed, invigilator_signed, subject_code,
                        BookletSlNo, omr_threshold
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        res["filename"],
                        res["barcode"],
                        res["bubble_regno"],
                        res["handwritten_regno"],
                        res["final_regno"],
                        int(res["has_disc"]),
                        res["disc_detail"],
                        int(res["cand_signed"]),
                        int(res["inv_signed"]),
                        res["subject_code"],
                        res.get("BookletSlNo", res.get("booklet_number", "")),
                        res.get("omr_threshold", 0.0)
                    ))
                    self.set_sheet_status(
                        filename, extracted=extracted, saved_db="imported")

                except Exception as e:
                    self.set_sheet_status(
                        filename, extracted="error", saved_db="error")
                    print(f"Error processing {filename}: {e}")

                self.progress["value"] = i
                self.root.update_idletasks()

            conn.commit()
            conn.close()

            self._refresh_status_summary()
            self.status_lbl.config(
                text="✅ All sheets processed & saved to MSSQL",
                foreground="#00e676")
            messagebox.showinfo("Success",
                "All sheets processed and saved to database!")
    
        except Exception as e:
            messagebox.showerror("Database Error", str(e))

    
  

#if __name__ == "__main__":
#    root = tk.Tk()def insert_into_mssql(result):
#    conn = get_sql_connection()
#    cursor = conn.cursor()



if __name__ == "__main__":
    root = tk.Tk()
    app = VisualOMRViewerDemo(root)
    root.mainloop()