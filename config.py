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

    # Handwritten digit row offsets relative to grid_y (at 1654×1080 reference)
    # reg_boxes = (330, 430) → offsets = (330-398, 430-398) = (-68, +32)
    "hw_offset_top": -68,   # px above grid_y where handwritten row starts
    "hw_offset_bot":  32,   # px below grid_y where handwritten row ends
    
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

    # Handwritten digit row offsets relative to grid_y
    # reg_boxes = (250, 320) → grid_y_ref = 310 → offsets = (250-310, 320-310) = (-60, +10)
    "hw_offset_top": -60,
    "hw_offset_bot":  10,
    
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

# Counter Foil sheet — landscape scan, ~1040×760 px
# Layout: left ~50% = subject/date/signatures, right ~50% = barcode + bubble grid + QCA number
#
# Measured from actual scanned images at 1040×760 reference:
#   Sheet width  = 1040 px,  height = 760 px
#   Dividing line between left and right panels ≈ x = 520
#
#   Barcode:          y  15– 120,  x 530–1020
#   Register No box:  y 190– 250,  x 530–1020  (printed border)
#   Bubble grid:      y 255– 580,  x 545–1010  (9 cols × 10 rows)
#     first bubble col x ≈ 555,  last ≈ 1000
#     col_spacing ≈ (1000-555)/8 ≈ 56 px
#     row_spacing ≈ (580-265)/9  ≈ 35 px
#   QCA label:        y 585– 640,  x 530–1020
#   QCA number:       y 640– 720,  x 530–1020
#   Candidate sig:    y 335– 470,  x  10– 510
#   Invigilator sig:  y 490– 610,  x  10– 510
#   Subject Code:     y  10–  90,  x  10– 300
PORTRAIT_COUNTERFOIL_TEMPLATE = {
    "name": "portrait_counterfoil",
    "target_width": 1040,
    "target_height": 760,

    # signature crops (y_start, y_end, x_start, x_end) at 1040×760 reference
    "cand_sig_detect": (335, 470, 10, 510),
    "cand_sig_save":   (325, 480, 5,  515),
    "inv_sig_detect":  (490, 610, 10, 510),
    "inv_sig_save":    (480, 620, 5,  515),

    # barcode crop — right panel, top strip
    "barcode": (15, 120, 530, 1030),

    # handwritten register number box (printed border row above bubbles)
    "reg_boxes": (190, 255, 530, 1020),

    # printed QCA Booklet Serial Number label area
    "qca": (585, 645, 530, 1020),

    # Booklet Serial Number bubble grid — NOT present (large OCR number used instead)
    "booklet_bubble_grid": {
        "cols": 7,
        "rows": 10,
        "region": (645, 760, 530, 1020),
        "col_start_offset": 10,
        "row_start_offset": 10,
        "col_spacing": 70.0,
        "row_spacing": 16.0,
        "sample_radius": 5
    },

    # OMR Bubble Grid Alignment
    # The printed register-number border box (reg_boxes) is used as the anchor.
    # At 1040×760: box is approximately x=530–1020, y=190–255 → width ~490, height ~65
    "handwritten_box_contour": {
        "w_min": 380, "w_max": 560,
        "h_min": 45,  "h_max": 90,
        "y_min": 140, "y_max": 300
    },

    "header_contour": {
        "w_min": 380,
        "h_min": 100
    },

    # Origin offsets from handwritten box contour top-left → bubble grid origin
    # box top ~190, grid_y ~255  → dy = 65
    # box left ~530, first bubble col ~545 → dx = 15
    "grid_offset_from_box":    (15, 65),
    "grid_offset_from_header": (90, 200),
    "grid_hardcoded_fallback": (555, 258),

    # Handwritten digit row offsets relative to grid_y (at 1040×760 reference)
    # reg_boxes top=190, bot=255, grid_y_ref=258
    # offset_top = 190 - 258 = -68,  offset_bot = 255 - 258 = -3
    "hw_offset_top": -68,
    "hw_offset_bot":  -3,

    # Bubble Grid — 9 columns (register number digits 0–8), 10 rows (digits 0–9)
    # At 1040×760: grid spans x≈545–1000, y≈258–575
    #   col_spacing = (1000-545)/8 ≈ 56.9 px
    #   row_spacing = (575-258)/9  ≈ 35.2 px
    "bubble_grid": {
        "cols": 9,
        "rows": 10,
        "col_start_offset": 15,
        "row_start_offset": 15,
        "col_spacing": 56.0,
        "row_spacing": 35.0,
        "sample_radius": 5
    },

    # Thresholds
    "bubble_fill_threshold":    140,
    "bubble_contrast_threshold": 25,
    "signature_ink_threshold":  0.002
}

OMR_TEMPLATES = [
    STANDARD_OMR_TEMPLATE,
    BLIND_DISABLED_OMR_TEMPLATE,
    PORTRAIT_COUNTERFOIL_TEMPLATE,
]

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
