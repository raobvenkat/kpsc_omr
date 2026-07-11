import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import os
import db_credentials

class CounterFoilDataEdit:
    PAGE_SIZE = 50

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
        self.current_page = 1
        self.total_pages = 1
        self.current_image = None
        self.current_photo = None
        self.zoom_factor = 1.0

        self.message_var = tk.StringVar()
        self.edit_for_var = tk.StringVar()
        self.from_sheet_var = tk.StringVar()
        self.to_sheet_var = tk.StringVar()
        self.sheetno_var = tk.StringVar()
        self.filename_var = tk.StringVar()
        self.goto_row_var = tk.StringVar()

        self.create_controls()
        self.load_editfor_values()

    def create_controls(self):
        lbl_header = tk.Label(self.root,text='Counter Foil Data Edit',font=('Segoe UI',16,'bold'))
        lbl_header.pack(fill='x', pady=5)

        body = tk.Frame(self.root)
        body.pack(fill='both', expand=True)

        left_frame = tk.Frame(body)
        left_frame.pack(side='left', fill='both', expand=True)

        right_frame = tk.LabelFrame(body, text='Full Image')
        right_frame.pack(side='right', fill='both', padx=5, pady=5)

        self.create_filter_panel(left_frame)
        self.create_grid_panel(left_frame)
        self.create_edit_panel(left_frame)
        self.create_button_panel(left_frame)
        self.create_image_panel(right_frame)

    def create_filter_panel(self,parent):
        frame = ttk.LabelFrame(parent,text='Filter')
        frame.pack(fill='x', padx=5, pady=5)

        ttk.Label(frame,text='Edit For').grid(row=0,column=0,padx=5,pady=5)
        self.cbo_editfor = ttk.Combobox(frame,textvariable=self.edit_for_var,state='readonly',width=35)
        self.cbo_editfor.grid(row=0,column=1,padx=5)

        ttk.Label(frame,text='From Sheet No').grid(row=0,column=2)
        ttk.Entry(frame,textvariable=self.from_sheet_var,width=12).grid(row=0,column=3)

        ttk.Label(frame,text='To Sheet No').grid(row=0,column=4)
        ttk.Entry(frame,textvariable=self.to_sheet_var,width=12).grid(row=0,column=5)

        ttk.Button(frame,text='Load Data',command=self.load_data).grid(row=0,column=6,padx=5)

        ttk.Label(frame,text='SheetNo').grid(row=1,column=0)
        ttk.Entry(frame,textvariable=self.sheetno_var,width=12).grid(row=1,column=1)

        ttk.Label(frame,text='File Name').grid(row=1,column=2)
        ttk.Entry(frame,textvariable=self.filename_var,width=40).grid(row=1,column=3,columnspan=2)

        ttk.Button(frame,text='Filter',command=self.filter_grid).grid(row=1,column=6)

    def create_grid_panel(self,parent):
        frame = ttk.LabelFrame(parent,text='Data Grid')
        frame.pack(fill='both', expand=True,padx=5,pady=5)

        tree_frame = tk.Frame(frame)
        tree_frame.pack(fill='both',expand=True)

        self.tree = ttk.Treeview(tree_frame)
        self.tree.pack(side='left',fill='both',expand=True)
        self.tree.bind('<<TreeviewSelect>>', self.grid_row_selected)

        yscroll = ttk.Scrollbar(tree_frame,orient='vertical',command=self.tree.yview)
        xscroll = ttk.Scrollbar(frame,orient='horizontal',command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set,xscrollcommand=xscroll.set)
        yscroll.pack(side='right',fill='y')
        xscroll.pack(fill='x')

        nav = tk.Frame(frame)
        nav.pack(fill="x")

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

        # =====================================
        # GO TO ROW CONTROLS
        # =====================================

        ttk.Label(
            nav,
            text="Go To Row"
        ).pack(
            side="left",
            padx=(20, 5)
        )

        self.txt_goto = ttk.Entry(
            nav,
            textvariable=self.goto_row_var,
            width=10
        )

        self.txt_goto.pack(
            side="left",
            padx=5
        )

        self.btn_goto = ttk.Button(
            nav,
            text="Go"
        )

        self.btn_goto.pack(
            side="left",
            padx=5
        )


    def create_edit_panel(self,parent):
        frame = ttk.LabelFrame(parent,text='Edit')
        frame.pack(fill='x',padx=5,pady=5)
        ttk.Label(frame,text='Part-1 placeholder for edit controls').pack(anchor='w')

    def create_button_panel(self,parent):
        frame = tk.Frame(parent)
        frame.pack(fill='x')
        ttk.Label(frame,textvariable=self.message_var).pack(side='left',padx=10)

    def create_image_panel(self,parent):
        toolbar = tk.Frame(parent)
        toolbar.pack(fill='x')
        ttk.Button(toolbar,text='+',command=self.zoom_in).pack(side='left')
        ttk.Button(toolbar,text='-',command=self.zoom_out).pack(side='left')

        self.canvas = tk.Canvas(parent,bg='gray')
        self.canvas.pack(fill='both',expand=True)

        hscroll = ttk.Scrollbar(parent,orient='horizontal',command=self.canvas.xview)
        vscroll = ttk.Scrollbar(parent,orient='vertical',command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=hscroll.set,yscrollcommand=vscroll.set)
        hscroll.pack(fill='x')
        vscroll.pack(side='right',fill='y')
        self.canvas.bind('<MouseWheel>', self.mouse_zoom)

    def load_editfor_values(self):
        try:
            conn=db_credentials.get_sql_connection()
            cur=conn.cursor()
            cur.execute('EXEC usp_CounterFoilEditFor')
            self.cbo_editfor['values']=[r[0] for r in cur.fetchall()]
            conn.close()
        except Exception as ex:
            self.message_var.set(str(ex))

    def load_data(self):
        try:
            conn=db_credentials.get_sql_connection()
            cursor=conn.cursor()
            cursor.execute('EXEC usp_LoadCounterfoilEditGrid @EditFor=?, @UserID=?',(self.edit_for_var.get(),self.user_id))
            self.columns=[c[0] for c in cursor.description]
            self.rows=cursor.fetchall()
            self.bind_grid()
            cursor.close(); conn.close()
            self.message_var.set(f'{len(self.rows)} records loaded.')
        except Exception as ex:
            self.message_var.set(str(ex))

    def bind_grid(self):
        self.tree.delete(*self.tree.get_children())
        self.tree['columns']=self.columns
        self.tree['show']='headings'
        for col in self.columns:
            self.tree.heading(col,text=col)
            self.tree.column(col,width=150,anchor='center')
        for row in self.rows:
            self.tree.insert('', 'end', values=row)

    def filter_grid(self):
        pass

    def grid_row_selected(self,event=None):
        selected=self.tree.selection()
        if not selected:
            return
        row=self.tree.item(selected[0])['values']
        if len(row)>2:
            self.load_image(str(row[2]))

    def load_image(self,image_path):
        if not os.path.exists(image_path):
            return
        self.current_image=Image.open(image_path)
        self.display_image()

    def display_image(self):
        if self.current_image is None:
            return
        w=max(1,int(self.current_image.width*self.zoom_factor))
        h=max(1,int(self.current_image.height*self.zoom_factor))
        resized=self.current_image.resize((w,h))
        self.current_photo=ImageTk.PhotoImage(resized)
        self.canvas.delete('all')
        self.canvas.create_image(0,0,image=self.current_photo,anchor='nw')
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def zoom_in(self):
        self.zoom_factor*=1.2
        self.display_image()

    def zoom_out(self):
        self.zoom_factor/=1.2
        self.display_image()

    def mouse_zoom(self,event):
        if event.delta>0:
            self.zoom_in()
        else:
            self.zoom_out()

    def first_page(self):
        pass
    def previous_page(self):
        pass
    def next_page(self):
        pass
    def last_page(self):
        pass
