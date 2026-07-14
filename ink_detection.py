import cv2
import numpy as np
import os
import sys

def classify_ink_type(cell_bgr):
    """
    Classifies a cropped bubble image into:
    'Blue Pen', 'Black Pen', 'Pencil', or 'Empty / Unmarked'
    
    Args:
        cell_bgr: Crop of the bubble (numpy array, BGR color space)
    Returns:
        string: The classified ink type
    """
    if cell_bgr is None or cell_bgr.size == 0:
        return "Empty / Unmarked"
        
    # Convert crop to Grayscale and HSV
    cell_gray = cv2.cvtColor(cell_bgr, cv2.COLOR_BGR2GRAY)
    cell_hsv = cv2.cvtColor(cell_bgr, cv2.COLOR_BGR2HSV)
    
    # Red mask to ignore template boundaries (dropout red lines)
    lower_red1 = np.array([0, 30, 40])
    upper_red1 = np.array([15, 255, 255])
    lower_red2 = np.array([165, 30, 40])
    upper_red2 = np.array([180, 255, 255])
    red_mask = cv2.bitwise_or(
        cv2.inRange(cell_hsv, lower_red1, upper_red1),
        cv2.inRange(cell_hsv, lower_red2, upper_red2)
    )
    
    # Segment ink pixels (dark pixels that are not red dropout lines)
    ink_mask = (cell_gray < 165) & (red_mask == 0)
    ink_pixels_bgr = cell_bgr[ink_mask]
    ink_pixels_hsv = cell_hsv[ink_mask]
    
    # If there are very few dark pixels, the bubble is empty
    if len(ink_pixels_bgr) < 20:
        return "Empty / Unmarked"
        
    # Compute the average color signature of the ink
    mean_b, mean_g, mean_r = np.mean(ink_pixels_bgr, axis=0)
    mean_h, mean_s, mean_v = np.mean(ink_pixels_hsv, axis=0)
    
    # Rule 1: Check if Blue Pen
    is_blue = False
    if 85 <= mean_h <= 140 and mean_s > 35:
        is_blue = True
    elif mean_b > mean_r + 12 and mean_b > mean_g + 12:
        is_blue = True
        
    if is_blue:
        return "Blue Pen"
        
    # Rule 2: Check if Black Pen vs Pencil
    if mean_v < 65:
        return "Black Pen"
    else:
        return "Pencil"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ink_detection.py <path_to_cropped_bubble_image>")
        sys.exit(1)
        
    image_path = sys.argv[1]
    if not os.path.exists(image_path):
        print(f"Error: File not found at '{image_path}'")
        sys.exit(1)
        
    img = cv2.imread(image_path)
    if img is None:
        print("Error: Could not read image.")
        sys.exit(1)
        
    ink_type = classify_ink_type(img)
    print(f"Detected Ink Type: {ink_type}")
