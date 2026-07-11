# CounterFoilDataEdit_Part2.py
# Part-2: Edit Panel, Paging, Filtering, Grid Binding
import tkinter as tk
from tkinter import ttk

class CounterFoilDataEditPart2Mixin:

    def create_edit_panel(self,parent):
        frame=ttk.LabelFrame(parent,text='Edit')
        frame.pack(fill='x',padx=5,pady=5)

        self.lbl_id=ttk.Label(frame,text='ID :')
        self.lbl_id.grid(row=0,column=0,sticky='w',padx=5,pady=2)

        fields=[('Subject Code','subject_code_var'),('Booklet Sl No','booklet_var'),
                ('Barcode','barcode_var'),('Bubble RegNo','bubble_var'),
                ('Handwritten RegNo','hand_var')]

        self.editor_vars={}
        r=1
        for lbl,varname in fields:
            ttk.Label(frame,text=lbl).grid(row=r,column=0,sticky='w',padx=5,pady=2)
            v=tk.StringVar()
            self.editor_vars[varname]=v
            ttk.Entry(frame,textvariable=v,width=40).grid(row=r,column=1,padx=5,pady=2)
            r+=1

        yn=['Yes','No']
        for lbl,varname in [('Candidate Signature','candsig'),('Invigilator Signature','invsig'),
                            ('Whitener Applied','whitener'),('Non Standard Sheet','nonstd'),
                            ('Threshold < 35%','threshold')]:
            ttk.Label(frame,text=lbl).grid(row=r,column=0,sticky='w',padx=5,pady=2)
            v=tk.StringVar()
            self.editor_vars[varname]=v
            ttk.Combobox(frame,textvariable=v,values=yn,state='readonly',width=20).grid(row=r,column=1,padx=5,pady=2)
            r+=1

    def create_button_panel(self,parent):
        frm=tk.Frame(parent)
        frm.pack(fill='x')
        self.btn_skip = ttk.Button(
            frm,
            text="Skip"
        )
        self.btn_skip.pack(
            side="left",
            padx=2
        )

        self.btn_update = ttk.Button(
            frm,
            text="Update"
        )
        self.btn_update.pack(
            side="left",
            padx=2
        )

        ttk.Button(
            frm,
            text="Reset",
            command=self.reset_controls
        ).pack(
            side="left",
            padx=2
        )

        ttk.Button(
            frm,
            text="Close",
            command=self.root.destroy
        ).pack(
            side="right",
            padx=2
        )
        
    def filter_grid(self):
        sheet=self.sheetno_var.get().strip()
        fname=self.filename_var.get().strip().lower()
        self.filtered_rows=[]
        for row in self.rows:
            s1=True
            s2=True
            if sheet:
                s1=str(row[1])==sheet
            if fname:
                s2=fname in str(row[2]).lower()
            if s1 and s2:
                self.filtered_rows.append(row)

        self.current_page=1
        self.total_pages=max(1,(len(self.filtered_rows)+self.PAGE_SIZE-1)//self.PAGE_SIZE)
        self.bind_page()

    def bind_grid(self):
        self.filtered_rows=list(self.rows)
        self.total_pages=max(1,(len(self.filtered_rows)+self.PAGE_SIZE-1)//self.PAGE_SIZE)
        self.current_page=1
        self.bind_page()

    def bind_page(self):
        self.tree.delete(*self.tree.get_children())
        self.tree['columns']=self.columns
        self.tree['show']='headings'
        for col in self.columns:
            self.tree.heading(col,text=col)
            self.tree.column(col,width=120)

        start=(self.current_page-1)*self.PAGE_SIZE
        end=start+self.PAGE_SIZE
        for row in self.filtered_rows[start:end]:
            self.tree.insert('', 'end', values=row)

        self.message_var.set(f'Page {self.current_page} of {self.total_pages}')

    def first_page(self):
        self.current_page=1
        self.bind_page()

    def previous_page(self):
        if self.current_page>1:
            self.current_page-=1
            self.bind_page()

    def next_page(self):
        if self.current_page<self.total_pages:
            self.current_page+=1
            self.bind_page()

    def last_page(self):
        self.current_page=self.total_pages
        self.bind_page()

    def reset_controls(self):
        self.lbl_id.config(text='ID :')
        for v in self.editor_vars.values():
            v.set('')

    def grid_row_selected(self,event=None):
        selected=self.tree.selection()
        if not selected:return
        vals=self.tree.item(selected[0])['values']
        if not vals:return
        self.lbl_id.config(text=f'ID : {vals[1]}')

        if len(vals)>7:
            self.editor_vars['barcode_var'].set(str(vals[3]))
            self.editor_vars['bubble_var'].set(str(vals[4]))
            self.editor_vars['hand_var'].set(str(vals[5]))
            self.editor_vars['subject_code_var'].set(str(vals[6]))
            self.editor_vars['booklet_var'].set(str(vals[7]))

        boolmap=lambda x:'Yes' if str(x) in ('1','True','true') else 'No'

        if len(vals)>13:
            self.editor_vars['candsig'].set(boolmap(vals[11]))
            self.editor_vars['invsig'].set(boolmap(vals[12]))
            self.editor_vars['whitener'].set(boolmap(vals[15]))
            self.editor_vars['nonstd'].set(boolmap(vals[16]))
            self.editor_vars['threshold'].set(boolmap(vals[17]))

        self.load_image(str(vals[2]))
