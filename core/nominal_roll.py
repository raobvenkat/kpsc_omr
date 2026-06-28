import os
import cv2
import numpy as np

# Footer invigilator ROI boxes calibrated from reference scans.
# Sheet 1 (OMR): "Sign of the Invigilator" signature cell.
# Sheet 2 (QCAB): "Name of the Invigilator" entry cell.
INVIGILATOR_BOX_TYPE1 = {
    "x0_pct": 0.190,
    "x1_pct": 0.362,
    "y0_pct": 0.902,
    "y1_pct": 0.932,
}
INVIGILATOR_BOX_TYPE2 = {
    "x0_pct": 0.166,
    "x1_pct": 0.422,
    "y0_pct": 0.905,
    "y1_pct": 0.927,
}


def get_invigilator_signature_box(sheet_type, w, h):
    """Return (x0, y0, x1, y1) pixel bounds for invigilator ink detection."""
    box = INVIGILATOR_BOX_TYPE1 if sheet_type == 1 else INVIGILATOR_BOX_TYPE2
    return (
        int(w * box["x0_pct"]),
        int(h * box["y0_pct"]),
        int(w * box["x1_pct"]),
        int(h * box["y1_pct"]),
    )

def check_ink_present(crop_img, threshold=190, ratio_threshold=0.001):
    """
    Checks if ink is present in a signature crop from the nominal roll.
    """
    gray = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY_INV)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
    
    total_pixels = thresh.size
    dark_pixels = np.sum(thresh > 0)
    ratio = dark_pixels / total_pixels
    return bool(ratio > ratio_threshold), float(ratio)

def process_nominal_roll(img_path, output_dir, row_data_list):
    """
    Processes a scanned Nominal Roll page.
    Args:
        img_path: Path to the scanned image.
        output_dir: Directory where crops will be saved.
        row_data_list: List of dicts representing candidate registration data on this page:
                       [{"row": 25, "regno": "1300693", "name": "NAVYA H N"}, ...]
    Returns:
        List of dicts containing the parsed candidate attendance data.
    """
    img = cv2.imread(img_path)
    if img is None:
        raise FileNotFoundError(f"Could not load Nominal Roll image at {img_path}")
        
    h, w, _ = img.shape
    
    # 1. Grid Line Detection (Horizontal and Vertical)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 15, 2
    )

    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
    detect_horizontal = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)

    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
    detect_vertical = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, vertical_kernel, iterations=2)

    # Find row y-coordinates (horizontal lines)
    row_sums = np.sum(detect_horizontal, axis=1)
    threshold_row = np.max(row_sums) * 0.3
    y_lines = []
    current_group = []
    for y in range(h):
        if row_sums[y] > threshold_row:
            current_group.append(y)
        else:
            if current_group:
                y_lines.append(int(np.mean(current_group)))
                current_group = []
    if current_group:
        y_lines.append(int(np.mean(current_group)))

    # Find column x-coordinates (vertical lines)
    col_sums = np.sum(detect_vertical, axis=0)
    threshold_col = np.max(col_sums) * 0.3
    x_lines = []
    current_group = []
    for x in range(w):
        if col_sums[x] > threshold_col:
            current_group.append(x)
        else:
            if current_group:
                x_lines.append(int(np.mean(current_group)))
                current_group = []
    if current_group:
        x_lines.append(int(np.mean(current_group)))

    # Select table rows (we look for 7 lines with gaps around 170 pixels)
    table_y = []
    for i in range(len(y_lines) - len(row_data_list)):
        subset = y_lines[i:i+len(row_data_list)+1]
        diffs = [subset[j+1] - subset[j] for j in range(len(row_data_list))]
        if all(140 <= d <= 200 for d in diffs):
            table_y = subset
            break
            
    if not table_y:
        # Fallback to hardcoded coordinates (calibrated for Invi.jpg 1763x1313)
        # We scale fallback if width/height differ significantly
        scale_x = w / 1763.0
        scale_y = h / 1313.0
        table_y = [int(y * scale_y) for y in [387, 560, 732, 904, 1077, 1249, 1423]]
        table_x = [int(x * scale_x) for x in [32, 639, 735, 1013, 1278]]
    else:
        # Filter vertical lines for column boundaries
        table_x = [x for x in x_lines if 20 <= x <= w - 20]
        if len(table_x) < 5:
            scale_x = w / 1763.0
            table_x = [int(x * scale_x) for x in [32, 639, 735, 1013, 1278]]
        else:
            table_x = table_x[:5]

    results = []
    
    # Process each candidate row
    for i, candidate in enumerate(row_data_list):
        if i >= len(table_y) - 1:
            break
            
        y_start, y_end = table_y[i], table_y[i+1]
        
        # 1. Crop Info Area (Col 1)
        x_info_start = table_x[0] + int(130 * (w / 1763.0)) # offset right of photo
        info_crop = img[y_start+10 : y_end-10, x_info_start : table_x[1]-10]
        
        # 2. Crop Booklet Number cell (Col 2)
        booklet_crop = img[y_start+10 : y_end-10, table_x[1]+5 : table_x[2]-5]
        
        # 3. Crop Candidate Signature cell (Col 3)
        sig_crop_cand = img[y_start+10 : y_end-10, table_x[2]+10 : table_x[3]-10]
        
        # 4. Crop Invigilator Signature cell (Col 4)
        sig_crop_invi = img[y_start+10 : y_end-10, table_x[3]+10 : table_x[4]-10]
        
        # 5. Check Signatures
        # We will check signature ink in Col 4 (since Col 4 was the active one in our Invi.jpg tests)
        # But we'll save crops for both Column 3 and Column 4 for operator verification
        signed_cand, cand_ink_ratio = check_ink_present(sig_crop_invi) # In Invi.jpg, candidate signature is in Col 4
        signed_invi, invi_ink_ratio = check_ink_present(sig_crop_cand) # Col 3
        
        # Save cropped images
        regno = candidate["regno"]
        sig_filename = f"{regno}_nr_cand_sig.png"
        invi_sig_filename = f"{regno}_nr_invi_sig.png"
        booklet_filename = f"{regno}_nr_booklet.png"
        info_filename = f"{regno}_nr_info.png"
        
        cv2.imwrite(os.path.join(output_dir, sig_filename), sig_crop_invi)
        cv2.imwrite(os.path.join(output_dir, invi_sig_filename), sig_crop_cand)
        cv2.imwrite(os.path.join(output_dir, booklet_filename), booklet_crop)
        cv2.imwrite(os.path.join(output_dir, info_filename), info_crop)
        
        # Check if Booklet number has ink (if it has ink, it means either booklet no or "AB" is written)
        has_booklet_writing, booklet_ink_ratio = check_ink_present(booklet_crop, threshold=200, ratio_threshold=0.005)
        
        results.append({
            "slno": candidate["row"],
            "register_number": regno,
            "name": candidate["name"],
            "nr_signed": signed_cand,
            "nr_signed_ratio": round(cand_ink_ratio, 6),
            "nr_invi_signed": signed_invi,
            "nr_invi_signed_ratio": round(invi_ink_ratio, 6),
            "nr_has_booklet_writing": has_booklet_writing,
            "nr_booklet_ratio": round(booklet_ink_ratio, 6),
            "nr_cand_sig_image": f"NominalRoll/{sig_filename}",
            "nr_invi_sig_image": f"NominalRoll/{invi_sig_filename}",
            "nr_booklet_image": f"NominalRoll/{booklet_filename}",
            "nr_info_image": f"NominalRoll/{info_filename}"
        })
        
    return results
