import os
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk, ImageOps
import db_credentials


class CounterFoilDataEdit:
    PAGE_SIZE = 50
    # Horizontal offset (pixels) for the status label inside the image panel
    STATUS_LABEL_LEFT_OFFSET = 110

    def __init__(self, root, user_id):
        self.root = root
        self.user_id = user_id
        self.root.title('Counter Foil Data Edit')
        try:
            self.root.state('zoomed')
        except Exception:
            self.root.geometry('1600x900')

        self.columns = []
        self.rows = []
        self.filtered_rows = []
        self.current_page = 1
        self.total_pages = 1
        self.current_image = None
        self.current_photo = None
        self.zoom_factor = 1.0
        self.crop_zoom_factor = 0.25

        self.message_var = tk.StringVar()
        self.edit_for_var = tk.StringVar()
        self.from_sheet_var = tk.StringVar()
        self.to_sheet_var = tk.StringVar()
        self.sheetno_var = tk.StringVar()
        self.filename_var = tk.StringVar()
        self.goto_row_var = tk.StringVar()
        self.edit_entry_widgets = {}
        self.current_focus_field = None

        self.create_controls()
        self.load_editfor_values()
        self.register_validators()
        self.wire_buttons()

    def create_controls(self):
        lbl_header = tk.Label(
            self.root,
            text='Counter Foil Data Edit',
            font=('Segoe UI', 16, 'bold'),
            bg='#0D47A1',
            fg='white',
            padx=10,
            pady=8
        )
        lbl_header.pack(fill='x', pady=5)

        body = tk.Frame(self.root)
        body.pack(fill='both', expand=True)

        left_frame = tk.Frame(body, width=650)
        left_frame.pack(side='left', fill='both', expand=False)
        left_frame.pack_propagate(False)

        right_frame = tk.LabelFrame(body, text='Full Image')
        right_frame.pack(side='right', fill='both', expand=True, padx=5, pady=0)

        self.create_filter_panel(left_frame)
        self.create_grid_panel(left_frame)
        self.create_edit_panel(left_frame)
        self.create_button_panel(left_frame)
        self.create_image_panel(right_frame)

    def create_filter_panel(self, parent):
        frame = ttk.LabelFrame(parent, text='Filter')
        frame.pack(fill='x', padx=5, pady=5)
        frame.configure(width=620)

        ttk.Label(frame, text='Edit For').grid(row=0, column=0, padx=3, pady=5)
        self.cbo_editfor = ttk.Combobox(frame, textvariable=self.edit_for_var, state='readonly', width=24)
        self.cbo_editfor.grid(row=0, column=1, padx=3)

        ttk.Label(frame, text='From Sheet No').grid(row=0, column=2, padx=3)
        self.txt_fromsheet = ttk.Entry(frame, textvariable=self.from_sheet_var, width=8)
        self.txt_fromsheet.grid(row=0, column=3, padx=3)

        ttk.Label(frame, text='To Sheet No').grid(row=0, column=4, padx=3)
        self.txt_tosheet = ttk.Entry(frame, textvariable=self.to_sheet_var, width=8)
        self.txt_tosheet.grid(row=0, column=5, padx=3)

        ttk.Button(frame, text='Load Data', command=self.load_data).grid(row=0, column=6, padx=3)

        ttk.Label(frame, text='SheetNo').grid(row=1, column=0, padx=3, pady=5)
        self.txt_sheetno = ttk.Entry(frame, textvariable=self.sheetno_var, width=8)
        self.txt_sheetno.grid(row=1, column=1, padx=3)

        ttk.Label(frame, text='File Name').grid(row=1, column=2, padx=3)
        self.txt_filename = ttk.Entry(frame, textvariable=self.filename_var, width=24)
        self.txt_filename.grid(row=1, column=3, columnspan=2, padx=3)

        ttk.Button(frame, text='Filter', command=self.filter_grid).grid(row=1, column=6, padx=3)

    def create_grid_panel(self, parent):

        frame = tk.LabelFrame(
            parent,
            text="Data Grid"
        )

        frame.pack(
            fill="x",
            padx=5,
            pady=5
        )

        frame.grid_rowconfigure(
            0,
            weight=1
        )

        frame.grid_columnconfigure(
            0,
            weight=1
        )

        cols = (
            'SlNo',
            'SheetNo',
            'FileName',
            'Barcode',
            'BubbleRegNo',
            'WrittenRegNo',
            'SubjectCode',
            'BookletSlNo',
            'CandSig',
            'InvSig',
            'Whitener',
            'NonStandard',
            'Threshold'
        )

        self.grid = ttk.Treeview(
            frame,
            columns=cols,
            show='headings',
            height=8
        )

        for c in cols:

            self.grid.heading(
                c,
                text=c
            )

            self.grid.column(
                c,
                width=140,
                minwidth=100,
                stretch=False,
                anchor='center'
            )

        self.grid.grid(
            row=0,
            column=0,
            sticky='nsew'
        )

        # Vertical Scroll Bar

        vs = ttk.Scrollbar(
            frame,
            orient='vertical',
            command=self.grid.yview
        )

        vs.grid(
            row=0,
            column=1,
            sticky='ns'
        )

        # Horizontal Scroll Bar

        hs = ttk.Scrollbar(
            frame,
            orient='horizontal',
            command=self.grid.xview
        )

        hs.grid(
            row=1,
            column=0,
            sticky='ew'
        )

        self.grid.configure(
            yscrollcommand=vs.set,
            xscrollcommand=hs.set
        )

        self.grid.bind(
            "<<TreeviewSelect>>",
            self.grid_row_selected
        )

        # Navigation

        nav = tk.Frame(frame)

        nav.grid(
            row=2,
            column=0,
            sticky="ew",
            pady=5
        )

        ttk.Button(
            nav,
            text="First",
            command=self.first_page
        ).pack(side="left")

        ttk.Button(
            nav,
            text="Previous",
            command=self.previous_page
        ).pack(side="left")

        ttk.Button(
            nav,
            text="Next",
            command=self.next_page
        ).pack(side="left")

        ttk.Button(
            nav,
            text="Last",
            command=self.last_page
        ).pack(side="left")

        ttk.Label(
            nav,
            text="Go To Row"
        ).pack(
            side="left",
            padx=(20,5)
        )

        self.txt_goto = ttk.Entry(
            nav,
            textvariable=self.goto_row_var,
            width=10
        )

        self.txt_goto.pack(
            side="left"
        )

        self.btn_goto = ttk.Button(
            nav,
            text="Go"
        )

        self.btn_goto.pack(
            side="left",
            padx=5
        )

    def create_edit_panel(self, parent):
        frame = ttk.LabelFrame(parent, text='Edit')
        frame.pack(fill='x', padx=5, pady=5)

        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=1)

        left_frame = ttk.Frame(frame)
        left_frame.grid(row=1, column=0, sticky='nsew', padx=(5, 10), pady=5)

        # Move ID label into the left frame so it stays with the left-side controls
        self.lbl_id = ttk.Label(left_frame, text='ID :', font=('Segoe UI', 14))
        self.lbl_id.grid(row=0, column=0, sticky='w', padx=5, pady=5, columnspan=2)

        # Left frame now holds the ID label at row 0; fields start at row 1
        
        right_frame = ttk.Frame(frame)
        right_frame.grid(row=1, column=1, sticky='nsew', padx=(10, 5), pady=5)

        self.crop_frame = ttk.LabelFrame(right_frame, text='Focus Crop')
        self.crop_frame.grid(row=0, column=0, columnspan=2, sticky='ew', padx=5, pady=(0, 2))

        crop_toolbar = tk.Frame(self.crop_frame)
        crop_toolbar.pack(fill='x', padx=4, pady=(4, 0))
        ttk.Button(crop_toolbar, text='+', width=3, command=self.crop_zoom_in).pack(side='left', padx=(0, 2))
        ttk.Button(crop_toolbar, text='-', width=3, command=self.crop_zoom_out).pack(side='left')

        crop_container = tk.Frame(self.crop_frame)
        crop_container.pack(fill='both', expand=True, padx=4, pady=4)
        crop_container.grid_rowconfigure(0, weight=1)
        crop_container.grid_columnconfigure(0, weight=1)

        self.crop_canvas = tk.Canvas(crop_container, width=140, height=90, bg='white', highlightthickness=1)
        self.crop_canvas.grid(row=0, column=0, sticky='nsew')

        crop_hscroll = ttk.Scrollbar(crop_container, orient='horizontal', command=self.crop_canvas.xview)
        crop_hscroll.grid(row=1, column=0, sticky='ew')
        crop_vscroll = ttk.Scrollbar(crop_container, orient='vertical', command=self.crop_canvas.yview)
        crop_vscroll.grid(row=0, column=1, sticky='ns')
        self.crop_canvas.configure(xscrollcommand=crop_hscroll.set, yscrollcommand=crop_vscroll.set)
        self.crop_canvas.bind('<MouseWheel>', self.crop_mouse_zoom)

        fields = [
            ('Subject Code', 'subject_code_var'),
            ('Booklet Sl No', 'booklet_var'),
            ('Barcode', 'barcode_var'),
            ('Bubble RegNo', 'bubble_var'),
            ('Handwritten RegNo', 'hand_var')
        ]

        self.editor_vars = {}
        for r, (lbl, varname) in enumerate(fields, start=1):
            ttk.Label(left_frame, text=lbl, font=('Segoe UI', 14)).grid(row=r, column=0, sticky='w', padx=5, pady=4)
            v = tk.StringVar()
            self.editor_vars[varname] = v
            entry = ttk.Entry(left_frame, textvariable=v, width=18, font=('Segoe UI', 13))
            entry.grid(row=r, column=1, padx=5, pady=4)
            entry.bind('<FocusIn>', lambda event, field=varname: self.on_focus_crop(field))
            self.edit_entry_widgets[varname] = entry

        yn = ['Yes', 'No']
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_columnconfigure(1, weight=1)
        for r, (lbl, varname) in enumerate([
            ('Candidate Signature', 'candsig'),
            ('Invigilator Signature', 'invsig'),
            ('Whitener Applied', 'whitener'),
            ('Non Standard Sheet', 'nonstd')
        ], start=0):
            ttk.Label(right_frame, text=lbl, font=('Segoe UI', 14)).grid(row=r+1, column=0, sticky='w', padx=5, pady=4)
            v = tk.StringVar()
            self.editor_vars[varname] = v
            combo = ttk.Combobox(right_frame, textvariable=v, values=yn, state='readonly', width=5, font=('Segoe UI', 13))
            combo.grid(row=r+1, column=1, padx=5, pady=4)
            combo.bind('<FocusIn>', lambda event, field=varname: self.on_focus_crop(field))

        # Move Threshold dropdown to the left frame below the handwritten field
        try:
            thr_row = len(fields) + 1
        except Exception:
            thr_row = 6
        ttk.Label(left_frame, text='Threshold < 35%', font=('Segoe UI', 14)).grid(row=thr_row, column=0, sticky='w', padx=5, pady=4)
        v = tk.StringVar()
        self.editor_vars['threshold'] = v
        thr_combo = ttk.Combobox(left_frame, textvariable=v, values=yn, state='readonly', width=5, font=('Segoe UI', 13))
        thr_combo.grid(row=thr_row, column=1, padx=5, pady=4)
        thr_combo.bind('<FocusIn>', lambda event, field='threshold': self.on_focus_crop(field))

    def on_focus_crop(self, field_name):
        self.current_focus_field = field_name
        self.show_focus_crop(field_name)

    def show_focus_crop(self, field_name):
        if self.current_image is None:
            return
        crop_image = self.get_focus_crop_image(field_name)
        self.display_focus_crop(crop_image)

    def get_focus_crop_image(self, field_name):
        if self.current_image is None:
            return None

        img = self.current_image.convert('RGB')
        w, h = img.size
        target_w = 1654
        target_h = 1080
        scale_x = w / target_w if target_w else 1.0
        scale_y = h / target_h if target_h else 1.0

        try:
            if field_name == 'subject_code_var':
                x1 = int(140 * scale_x)
                x2 = int(500 * scale_x)
                y1 = int(20 * scale_y)
                y2 = int(140 * scale_y)
            elif field_name == 'booklet_var':
               #x1 = int(w * 0.556) x2 = int(w * 0.949) y1 = int(h * 0.725)     y2 = int(h * 0.800
                
                x1 = int(w * 0.62)
                x2 = int(w * 0.95)
                y1 = int(h * 0.68)
                y2 = int(h * 0.78)
            elif field_name == 'barcode_var':
                x1 = int(w * 0.55)
                x2 = w
                y1 = int(h * 0.03)
                y2 = int(h * 0.18)
            elif field_name == 'bubble_var':
                # Bubble RegNo area is intentionally not shown as a focus crop
                # (too large / not useful). Return None to indicate no crop.
                #return None
                x1 = int(w * 0.55)
                x2 = w
                y1 = int(h * 0.30)
                y2 = int(h * 0.64)

            elif field_name == 'hand_var':
                # Crop for handwritten Register No (matches orange rectangle in 123.png)
                # Positioned top-right under the barcode area
                x1 = int(w * 0.55)
                x2 = w
                y1 = int(h * 0.30)
                y2 = int(h * 0.40)
            elif field_name == 'candsig':
                # Use the same area previously used for bubble_var so the
                # Candidate Signature focus shows that region instead.
                x1 = int(w * 0.04)
                x2 = int(w * 0.58)
                #y1 = int(h * 0.24)
                y1 = int(h * 0.34)
                y2 = int(h * 0.45)
            elif field_name == 'invsig':
                #x1 = int(130 * scale_x)
                #x2 = int(900 * scale_x)
                #y1 = int(152 * scale_y)
                #y2 = int(252 * scale_y)
                x1 = int(w * 0.04)
                x2 = int(w * 0.58)
                y1 = int(h * 0.50)
                y2 = int(h * 0.60)
            else:
                return None

            x1 = max(0, min(w, x1))
            y1 = max(0, min(h, y1))
            x2 = max(x1 + 1, min(w, x2))
            y2 = max(y1 + 1, min(h, y2))
            return img.crop((x1, y1, x2, y2))
        except Exception:
            return None

    def display_focus_crop(self, crop_image):
        self.crop_canvas.delete('all')
        if crop_image is None:
            self.crop_canvas.create_text(10, 10, anchor='nw', text='No crop available', fill='gray')
            return

        try:
            # Zoom the crop using the current crop zoom factor between 100% and 600%.
            img_rgb = crop_image.convert('RGB')
            zoom_ratio = max(0.25, min(6.0, self.crop_zoom_factor))
            zw = max(1, int(img_rgb.width * zoom_ratio))
            zh = max(1, int(img_rgb.height * zoom_ratio))
            zoomed = img_rgb.resize((zw, zh), Image.LANCZOS)

            self.current_crop_photo = ImageTk.PhotoImage(zoomed)
            self.crop_canvas.create_image(0, 0, anchor='nw', image=self.current_crop_photo)
            self.crop_canvas.configure(scrollregion=self.crop_canvas.bbox('all'))
        except Exception:
            self.crop_canvas.create_text(10, 10, anchor='nw', text='Unable to display crop', fill='gray')

    def create_button_panel(self, parent):
        frm = tk.Frame(parent)
        frm.pack(fill='x')

        button_row = tk.Frame(frm)
        button_row.pack(fill='x')

        self.btn_skip = ttk.Button(button_row, text='Skip', width=12)
        self.btn_skip.pack(side='left', padx=2)

        self.btn_update = ttk.Button(button_row, text='Update', width=12)
        self.btn_update.pack(side='left', padx=2)

        ttk.Button(button_row, text='Reset', command=self.reset_controls, width=12).pack(side='left', padx=2)
        ttk.Button(button_row, text='Close', command=self.root.destroy, width=12).pack(side='right', padx=2)

        # Status label moved to image panel (below full image)

    def create_image_panel(self, parent):
        toolbar = tk.Frame(parent)
        toolbar.pack(fill='x')
        ttk.Button(toolbar, text='+', command=self.zoom_in).pack(side='left')
        ttk.Button(toolbar, text='-', command=self.zoom_out).pack(side='left')

        self.canvas = tk.Canvas(parent, bg='gray')
        self.canvas.pack(fill='both', expand=True)

        hscroll = ttk.Scrollbar(parent, orient='horizontal', command=self.canvas.xview)
        vscroll = ttk.Scrollbar(parent, orient='vertical', command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=hscroll.set, yscrollcommand=vscroll.set)
        hscroll.pack(fill='x')
        vscroll.pack(side='right', fill='y')
        self.canvas.bind('<MouseWheel>', self.mouse_zoom)

        # Status message shown below the full image area.
        # Use a container so we can left-offset the label to align with
        # the "To be filled by" region in the scanned form. Adjust
        # `STATUS_LABEL_LEFT_OFFSET` above to fine-tune positioning.
        status_container = tk.Frame(parent)
        status_container.pack(fill='x')

        self.status_label = ttk.Label(
            status_container,
            textvariable=self.message_var,
            anchor='w',
            font=('Segoe UI', 14),
            wraplength=600,
            justify='left'
        )
        left_pad = self.STATUS_LABEL_LEFT_OFFSET
        self.status_label.pack(fill='x', padx=(left_pad, 10), pady=(4, 0))

    def load_editfor_values(self):
        try:
            conn = db_credentials.get_sql_connection()
            cur = conn.cursor()
            cur.execute('EXEC usp_CounterFoilEditFor')
            self.cbo_editfor['values'] = [r[0] for r in cur.fetchall()]
            conn.close()
        except Exception as ex:
            self.message_var.set(str(ex))

    def load_data(self):
        try:
            conn = db_credentials.get_sql_connection()
            cursor = conn.cursor()
            cursor.execute(
                'EXEC usp_LoadCounterfoilEditGrid @EditFor=?, @UserID=?, @FromID=?, @ToID=?',
                (self.edit_for_var.get(), self.user_id, self.from_sheet_var.get(), self.to_sheet_var.get())
            )
            self.columns = [c[0] for c in cursor.description]
            self.rows = cursor.fetchall()
            cursor.close()
            conn.close()
            self.bind_grid()
            self.message_var.set(f'{len(self.rows)} records loaded.')
        except Exception as ex:
            self.message_var.set(str(ex))

    def bind_grid(self):
        self.filtered_rows = list(self.rows)
        self.total_pages = max(1, (len(self.filtered_rows) + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        self.current_page = 1
        self.bind_page()

    def bind_page(self):
        self.grid.delete(*self.grid.get_children())
        if not self.columns:
            self.message_var.set('No columns available.')
            return

        self.grid['columns'] = self.columns
        self.grid['show'] = 'headings'
        self.grid.column('#0', width=0, stretch=False)

        for col in self.columns:
            self.grid.heading(col, text=col)
            self.grid.column(col, width=140, minwidth=100, stretch=False, anchor='center')

        start = (self.current_page - 1) * self.PAGE_SIZE
        end = start + self.PAGE_SIZE
        for idx, row in enumerate(self.filtered_rows[start:end], start=1):
            values = []
            for value in row:
                if value is None:
                    values.append('')
                elif isinstance(value, (bytes, bytearray)):
                    values.append(value.decode('utf-8', errors='ignore'))
                else:
                    values.append(str(value))
            if len(values) < len(self.columns):
                values.extend([''] * (len(self.columns) - len(values)))
            elif len(values) > len(self.columns):
                values = values[:len(self.columns)]
            self.grid.insert('', 'end', values=values)

        self.message_var.set(f'Page {self.current_page} of {self.total_pages}')

    def filter_grid(self):
        sheet = self.sheetno_var.get().strip()
        fname = self.filename_var.get().strip().lower()
        self.filtered_rows = []
        for row in self.rows:
            s1 = True
            s2 = True
            if sheet:
                s1 = str(row[1]) == sheet
            if fname:
                s2 = fname in str(row[2]).lower()
            if s1 and s2:
                self.filtered_rows.append(row)

        self.current_page = 1
        self.total_pages = max(1, (len(self.filtered_rows) + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        self.bind_page()

    def first_page(self):
        self.current_page = 1
        self.bind_page()

    def previous_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.bind_page()

    def next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.bind_page()

    def last_page(self):
        self.current_page = self.total_pages
        self.bind_page()

    def reset_controls(self):
        self.lbl_id.config(text='ID :')
        for v in self.editor_vars.values():
            v.set('')

    def grid_row_selected(self, event=None):
        selected = self.grid.selection()
        if not selected:
            return
        vals = self.grid.item(selected[0])['values']
        if not vals:
            return

        def safe_value(values, index):
            return values[index] if index < len(values) else ''

        row_id = safe_value(vals, 1)
        self.lbl_id.config(text=f'ID : {row_id}')

        if len(vals) > 7:
            self.editor_vars['barcode_var'].set(str(safe_value(vals, 3)))
            self.editor_vars['bubble_var'].set(str(safe_value(vals, 4)))
            self.editor_vars['hand_var'].set(str(safe_value(vals, 5)))
            self.editor_vars['subject_code_var'].set(str(safe_value(vals, 6)))
            self.editor_vars['booklet_var'].set(str(safe_value(vals, 7)))

        def boolmap(value):
            if isinstance(value, bool):
                return 'Yes' if value else 'No'
            text = str(value).strip().lower()
            if text in ('1', 'true', 'yes', 'y'):
                return 'Yes'
            if text in ('0', 'false', 'no', 'n'):
                return 'No'
            return ''

        def normalize_name(value):
            return ''.join(ch.lower() for ch in str(value) if ch.isalnum())

        def column_matches(column_name, desired_name):
            col_norm = normalize_name(column_name)
            desired_norm = normalize_name(desired_name)
            return (
                col_norm == desired_norm
                or desired_norm in col_norm
                or col_norm in desired_norm
                or col_norm.startswith(desired_norm)
                or desired_norm.startswith(col_norm)
            )

        column_index = []
        for idx, col in enumerate(self.columns):
            column_index.append((idx, str(col)))

        def get_column_value(*column_names):
            for name in column_names:
                for idx, col in column_index:
                    if column_matches(col, name) and idx < len(vals):
                        return safe_value(vals, idx)
            return ''

        self.editor_vars['candsig'].set(boolmap(get_column_value('CanSign', 'CandSigDesc', 'CandSig', 'CandidateSignature')))
        self.editor_vars['invsig'].set(boolmap(get_column_value('InvSign', 'InvSignDesc', 'InvSigDesc', 'InvigilatorSignature')))
        self.editor_vars['whitener'].set(boolmap(get_column_value('WhitenerDesc', 'WhitenerApplied')))
        self.editor_vars['nonstd'].set(boolmap(get_column_value('isBlackDesc', 'NonStandardSheet', 'NonStandard')))
        self.editor_vars['threshold'].set(boolmap(get_column_value('ThDesc', 'ThresholdDesc', 'Threshold', 'Threshold < 35%')))

        image_path = self.get_image_path_from_row(vals)
        if image_path:
            self.load_image(image_path)

    def get_image_path_from_row(self, values):
        if not self.columns:
            return ''

        for idx, col in enumerate(self.columns):
            col_name = str(col).strip().lower()
            if col_name in {'filename', 'filepath', 'imagepath', 'image', 'file'} and idx < len(values):
                return str(values[idx]).strip()

        for value in values:
            text = str(value).strip()
            if not text:
                continue
            if any(text.lower().endswith(ext) for ext in ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tif', '.tiff', '.webp')):
                return text
            if '/' in text or '\\' in text:
                return text
        return ''

    def load_image(self, image_path):
        if not image_path:
            return

        image_path = os.path.expandvars(os.path.expanduser(str(image_path).strip()))
        if not os.path.isabs(image_path):
            image_path = os.path.abspath(image_path)

        if not os.path.exists(image_path):
            self.message_var.set(f'Image not found: {image_path}')
            return

        self.current_image = Image.open(image_path)
        self.display_image()
        if self.current_focus_field:
            self.show_focus_crop(self.current_focus_field)

    def display_image(self):
        if self.current_image is None:
            return
        w = max(1, int(self.current_image.width * self.zoom_factor))
        h = max(1, int(self.current_image.height * self.zoom_factor))
        resized = self.current_image.resize((w, h))
        self.current_photo = ImageTk.PhotoImage(resized)
        self.canvas.delete('all')
        self.canvas.create_image(0, 0, image=self.current_photo, anchor='nw')
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def zoom_in(self):
        self.zoom_factor *= 1.2
        self.display_image()

    def zoom_out(self):
        self.zoom_factor /= 1.2
        self.display_image()

    def crop_zoom_in(self):
        self.crop_zoom_factor = min(6.0, self.crop_zoom_factor * 1.2)
        if self.current_focus_field:
            self.show_focus_crop(self.current_focus_field)

    def crop_zoom_out(self):
        self.crop_zoom_factor = max(0.25, self.crop_zoom_factor / 1.2)
        if self.current_focus_field:
            self.show_focus_crop(self.current_focus_field)

    def mouse_zoom(self, event):
        if event.delta > 0:
            self.zoom_in()
        else:
            self.zoom_out()

    def crop_mouse_zoom(self, event):
        if event.delta > 0:
            self.crop_zoom_in()
        else:
            self.crop_zoom_out()

    def log_error(self, screen, module, error_text):
        try:
            conn = db_credentials.get_sql_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO ErrorLog
                (
                    ErrorScreen,
                    ErrorModule,
                    ErrorText,
                    ErrorTime
                )
                VALUES
                (
                    ?, ?, ?, GETDATE()
                )
                """,
                (screen, module, str(error_text))
            )
            conn.commit()
            cursor.close()
            conn.close()
        except Exception:
            pass

    def yes_no_to_bit(self, value):
        if isinstance(value, bool):
            return 1 if value else 0
        text = str(value).strip().lower()
        if text in ('1', 'true', 'yes', 'y'):
            return 1
        if text in ('0', 'false', 'no', 'n', ''):
            return 0
        return 0

    def update_record(self):
        try:
            id_text = self.lbl_id.cget('text')
            if ':' not in id_text:
                self.message_var.set('Please select a record.')
                return

            record_id = int(id_text.split(':')[1].strip())
            conn = db_credentials.get_sql_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                EXEC usp_CounterFoilEditUpdate
                     @EditFor=?,
                     @UserID=?,
                     @ID=?,
                     @barcode=?,
                     @bubble_regno=?,
                     @handwritten_regno=?,
                     @subject_code=?,
                     @BookletSlNo=?,
                     @CandSig=?,
                     @InvSign=?,
                     @WhitenerDesc=?,
                     @isBlackDesc=?,
                     @ThDesc=?
                """,
                (
                    self.edit_for_var.get(),
                    self.user_id,
                    record_id,
                    self.editor_vars['barcode_var'].get(),
                    self.editor_vars['bubble_var'].get(),
                    self.editor_vars['hand_var'].get(),
                    self.editor_vars['subject_code_var'].get(),
                    self.editor_vars['booklet_var'].get(),
                    self.yes_no_to_bit(self.editor_vars['candsig'].get()),
                    self.yes_no_to_bit(self.editor_vars['invsig'].get()),
                    self.yes_no_to_bit(self.editor_vars['whitener'].get()),
                    self.yes_no_to_bit(self.editor_vars['nonstd'].get()),
                    self.yes_no_to_bit(self.editor_vars['threshold'].get())
                )
            )
            conn.commit()
            cursor.close()
            conn.close()
            self.message_var.set('Record updated successfully.')
            self.load_data()
            self.select_next_row_after_update(record_id)
        except Exception as ex:
            self.log_error('CounterFoilDataEdit', 'Update', ex)
            self.message_var.set(str(ex))

    def select_next_row_after_update(self, updated_id):
        children = list(self.grid.get_children())
        if not children:
            return

        current_selection = self.grid.selection()
        selected_index = None
        for idx, child in enumerate(children):
            values = self.grid.item(child)['values']
            if not values:
                continue
            if str(values[1]) == str(updated_id):
                selected_index = idx
                break

        if selected_index is None:
            if current_selection:
                self.grid.selection_set(current_selection)
                self.grid_row_selected()
            return

        next_index = selected_index + 1
        if next_index >= len(children):
            next_index = len(children) - 1

        next_item = children[next_index]
        self.grid.selection_set(next_item)
        self.grid.focus(next_item)
        self.grid_row_selected()

    def skip_record(self):
        try:
            id_text = self.lbl_id.cget('text')
            if ':' not in id_text:
                self.message_var.set('Please select a record.')
                return

            record_id = int(id_text.split(':')[1].strip())
            conn = db_credentials.get_sql_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                EXEC usp_CounterFoilEditSkip
                     @EditFor=?,
                     @UserID=?,
                     @ID=?
                """,
                (self.edit_for_var.get(), self.user_id, record_id)
            )
            conn.commit()
            cursor.close()
            conn.close()
            self.message_var.set('Record skipped successfully.')
            self.load_data()
        except Exception as ex:
            self.log_error('CounterFoilDataEdit', 'Skip', ex)
            self.message_var.set(str(ex))

    def goto_row(self):
        try:
            row_no = int(self.goto_row_var.get())
            if row_no <= 0:
                return
            self.current_page = ((row_no - 1) // self.PAGE_SIZE) + 1
            if self.current_page > self.total_pages:
                self.current_page = self.total_pages
            self.bind_page()
        except Exception:
            self.message_var.set('Invalid Row Number.')

    def validate_7_digit(self, value):
        if value == '':
            return True
        if not value.isdigit():
            return False
        if len(value) > 7:
            return False
        return True

    def validate_15_chars(self, value):
        if value == '':
            return True
        return len(value) <= 15 and value.isalnum()

    def validate_filename(self, value):
        return len(value) <= 200

    def register_validators(self):
        v1 = (self.root.register(self.validate_7_digit), '%P')
        v2 = (self.root.register(self.validate_filename), '%P')
        v3 = (self.root.register(self.validate_15_chars), '%P')

        self.txt_fromsheet.config(validate='key', validatecommand=v1)
        self.txt_tosheet.config(validate='key', validatecommand=v1)
        self.txt_sheetno.config(validate='key', validatecommand=v1)
        self.txt_filename.config(validate='key', validatecommand=v2)

        for var_name in ['subject_code_var', 'booklet_var', 'barcode_var', 'bubble_var', 'hand_var']:
            entry = self.edit_entry_widgets.get(var_name)
            if entry is not None:
                entry.config(validate='key', validatecommand=v3)

    def refresh_current_row(self):
        selected = self.grid.selection()
        if not selected:
            return
        self.grid_row_selected()

    def wire_buttons(self):
        self.btn_update.configure(command=self.update_record)
        self.btn_skip.configure(command=self.skip_record)
        self.btn_goto.configure(command=self.goto_row)


if __name__ == '__main__':
    root = tk.Tk()
    app = CounterFoilDataEdit(root, 1)
    root.mainloop()
