"""
Configuration file containing coordinate templates for Standard and Blind/Disabled OMR sheets,
Nominal Roll grids, database settings, and signature parameters.
"""

# Database Configuration
# Default connection string template for MS SQL Server
# Can be updated by editing db_config.json or passing via GUI
DB_CONFIG_DEFAULT = {
    "driver": "{SQL Server}",
    "server": "localhost",
    "database": "CLIENT_ICR",
    "username": "",
    "password": "",
    "use_sql_server": False  # Set to True to connect to SQL Server; False uses local Excel/SQLite fallback
}

# Standard OMR Dimensions & Coordinates (Images ~ 1654x1080)
STANDARD_OMR_TEMPLATE = {
    "name": "standard",
    "target_width": 1654,
    
    # signature crops (y_start, y_end, x_start, x_end)
    "cand_sig_detect": (390, 480, 70, 900),
    "cand_sig_save": (380, 510, 50, 920),
    "inv_sig_detect": (540, 640, 70, 900),
    "inv_sig_save": (530, 660, 50, 920),
    
    # barcode crop (y_start, y_end, x_start, x_end)
    "barcode": (40, 170, 940, 1570),
    
    # handwritten register number box (y_start, y_end, x_start, x_end)
    "reg_boxes": (330, 430, 960, 1520),
    
    # printed QCA Booklet Number label area (y_start, y_end, x_start, x_end)
    "qca": (780, 870, 1050, 1450),
    
    # Booklet Serial Number bubble grid (7 digits, 0-9 rows) — below QCA label, bottom-right
    # Coordinates at 1654x1080 reference resolution
    "booklet_bubble_grid": {
        "cols": 7,
        "rows": 10,
        "region": (870, 1080, 1050, 1550),   # (y_start, y_end, x_start, x_end) search region
        "col_start_offset": 20,
        "row_start_offset": 15,
        "col_spacing": 64.0,
        "row_spacing": 20.0,
        "sample_radius": 6
    },
    
    # OMR Bubble Grid Alignment Parameters
    # Target range for the red handwritten boxes contour to establish grid origin
    "handwritten_box_contour": {
        "w_min": 610, "w_max": 650,
        "h_min": 80, "h_max": 110,
        "y_min": 150, "y_max": 230
    },
    
    # Outermost header red contour to establish fallback origin
    "header_contour": {
        "w_min": 600,
        "h_min": 200
    },
    
    # Origin offsets
    "grid_offset_from_box": (19, 208),     # dx, dy relative to handwritten box contour
    "grid_offset_from_header": (124, 350),  # dx, dy relative to header contour
    "grid_hardcoded_fallback": (951, 398),  # absolute coordinates (grid_x, grid_y)
    
    # Bubble Grid spacing and cell size
    "bubble_grid": {
        "cols": 9,
        "rows": 10,
        "col_start_offset": 39,
        "row_start_offset": 22,
        "col_spacing": 63.75,
        "row_spacing": 29.2,
        "sample_radius": 6
    },
    
    # Thresholds
    "bubble_fill_threshold": 140, # Mean pixel value less than this = filled
    "bubble_contrast_threshold": 30, # Difference between 2nd darkest and darkest bubble must be greater than this
    "signature_ink_threshold": 0.002 # Ink ratio greater than this = signed
}

# Blind/Disabled OMR Template
# Placeholder values - update once sample image dimensions are confirmed
BLIND_DISABLED_OMR_TEMPLATE = {
    "name": "blind_disabled",
    "target_width": 1200, # Example placeholder dimension
    
    # signature crops (y_start, y_end, x_start, x_end)
    "cand_sig_detect": (300, 400, 50, 700),
    "cand_sig_save": (290, 420, 30, 720),
    "inv_sig_detect": (430, 530, 50, 700),
    "inv_sig_save": (420, 550, 30, 720),
    
    # barcode crop (y_start, y_end, x_start, x_end)
    "barcode": (30, 130, 720, 1150),
    
    # handwritten register number box (y_start, y_end, x_start, x_end)
    "reg_boxes": (250, 320, 730, 1120),
    
    # printed QCA Booklet Number label area (y_start, y_end, x_start, x_end)
    "qca": (600, 680, 800, 1100),
    
    # Booklet Serial Number bubble grid (7 digits, 0-9 rows) — below QCA label, bottom-right
    # Coordinates at 1200 target_width reference
    "booklet_bubble_grid": {
        "cols": 7,
        "rows": 10,
        "region": (680, 784, 800, 1150),    # (y_start, y_end, x_start, x_end) search region
        "col_start_offset": 15,
        "row_start_offset": 12,
        "col_spacing": 49.0,
        "row_spacing": 15.0,
        "sample_radius": 5
    },
    
    # OMR Bubble Grid Alignment Parameters
    "handwritten_box_contour": {
        "w_min": 450, "w_max": 500,
        "h_min": 60, "h_max": 90,
        "y_min": 120, "y_max": 180
    },
    
    "header_contour": {
        "w_min": 500,
        "h_min": 150
    },
    
    # Origin offsets
    "grid_offset_from_box": (15, 160),
    "grid_offset_from_header": (100, 280),
    "grid_hardcoded_fallback": (740, 310),
    
    # Bubble Grid spacing and cell size
    "bubble_grid": {
        "cols": 9,
        "rows": 10,
        "col_start_offset": 30,
        "row_start_offset": 18,
        "col_spacing": 48.0,
        "row_spacing": 22.0,
        "sample_radius": 5
    },
    
    # Thresholds
    "bubble_fill_threshold": 145,
    "bubble_contrast_threshold": 25,
    "signature_ink_threshold": 0.002
}

# List of templates
OMR_TEMPLATES = [STANDARD_OMR_TEMPLATE, BLIND_DISABLED_OMR_TEMPLATE]

def get_omr_template(img_width):
    """
    Selects the best OMR template based on image width.
    """
    # Find template with closest target_width
    best_tpl = STANDARD_OMR_TEMPLATE
    min_diff = abs(img_width - best_tpl["target_width"])
    
    for tpl in OMR_TEMPLATES:
        diff = abs(img_width - tpl["target_width"])
        if diff < min_diff:
            min_diff = diff
            best_tpl = tpl
            
    return best_tpl
