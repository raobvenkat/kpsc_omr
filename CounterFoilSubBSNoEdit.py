
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from db_credentials import get_sql_connection

LOGGED_USER_ID = 1
SUBJECT_BOX=(30,35,530,130)
BOOKLET_BOX=(930,690,1425,890)

class SubjectBookletDiscrepancy:
    def __init__(self, root):
        self.root=root
        self.root.title('Subject Code & QCA Booklet Serial Number Descripancy')
        self.root.geometry('1600x900')
        self.current_image=None
        self.create_screen()

    def get_connection(self):
        return get_sql_connection()

    def create_screen(self):
        tk.Label(self.root,text='Subject Code & QCA Booklet Serial Number Descripancy',bg='#1976D2',fg='white',font=('Arial',18,'bold')).pack(fill='x')
        main=tk.Frame(self.root)
        main.pack(fill='both',expand=True)

        self.left=tk.Frame(main,width=800)
        self.left.pack(side='left',fill='both',expand=True)
        self.left.pack_propagate(False)

        self.right=tk.Frame(main)
        self.right.pack(side='right',fill='both',expand=True)

        self.create_search_panel()
        self.create_grid_panel()
        self.create_edit_panel()
        self.create_message_panel()
        self.create_button_panel()

        self.full_image=tk.Label(self.right)
        self.full_image.pack(fill='both',expand=True)

    def create_search_panel(self):
        f=tk.Frame(self.left)
        f.pack(fill='x',padx=5,pady=5)
        tk.Label(f,text='ID').grid(row=0,column=0)
        self.txt_id=tk.Entry(f,width=10)
        self.txt_id.grid(row=0,column=1)
        tk.Label(f,text='File Name').grid(row=0,column=2)
        self.txt_file=tk.Entry(f,width=25)
        self.txt_file.grid(row=0,column=3)
        tk.Label(f,text='Barcode').grid(row=0,column=4)
        self.txt_barcode=tk.Entry(f,width=25)
        self.txt_barcode.grid(row=0,column=5)
        tk.Button(f,text='Load Data',command=self.load_data).grid(row=0,column=6,padx=3)
        tk.Button(f,text='Search',command=self.search_data).grid(row=0,column=7,padx=3)
        tk.Button(f,text='Clear Search',command=self.clear_search).grid(row=0,column=8,padx=3)

    def create_grid_panel(self):
        frame=tk.Frame(self.left)
        frame.pack(fill='x',padx=5)
        cols=('ID','FileName','Barcode','Subject_Code','Booklet_Sl_No')
        self.grid=ttk.Treeview(frame,columns=cols,show='headings',height=8)
        for c in cols:
            self.grid.heading(c,text=c)
            self.grid.column(c,width=150)
        vs=ttk.Scrollbar(frame,orient='vertical',command=self.grid.yview)
        hs=ttk.Scrollbar(frame,orient='horizontal',command=self.grid.xview)
        self.grid.configure(yscrollcommand=vs.set,xscrollcommand=hs.set)
        self.grid.grid(row=0,column=0,sticky='nsew')
        vs.grid(row=0,column=1,sticky='ns')
        hs.grid(row=1,column=0,sticky='ew')
        self.grid.bind('<<TreeviewSelect>>',self.row_selected)

    def create_edit_panel(self):
        f=tk.Frame(self.left)
        f.pack(fill='x',padx=5,pady=10)
        tk.Label(f,text='ID').grid(row=0,column=0,sticky='w')
        self.lbl_id=tk.Label(f,text='')
        self.lbl_id.grid(row=0,column=1,sticky='w')

        tk.Label(f,text='Subject Code').grid(row=1,column=0,sticky='w',pady=15)
        self.txt_subject=tk.Entry(f,width=25)
        self.txt_subject.grid(row=1,column=1,sticky='w')
        self.subject_zoom=tk.Label(f)
        self.subject_zoom.grid(row=1,column=2,padx=20)

        tk.Label(f,text='Booklet Serial No').grid(row=3,column=0,sticky='w',pady=15)
        self.txt_booklet=tk.Entry(f,width=25)
        self.txt_booklet.grid(row=3,column=1,sticky='w')
        self.booklet_zoom=tk.Label(f)
        self.booklet_zoom.grid(row=3,column=2,padx=20)

    def create_message_panel(self):
        self.lbl_message=tk.Label(self.left,text='',anchor='w')
        self.lbl_message.pack(fill='x',padx=5)

    def create_button_panel(self):
        f=tk.Frame(self.left)
        f.pack(fill='x',pady=10)
        tk.Button(f,text='Update',width=15,command=self.update_record).pack(side='left',padx=5)
        tk.Button(f,text='Reset',width=15,command=self.reset_fields).pack(side='left',padx=5)
        tk.Button(f,text='Close',width=15,command=self.root.destroy).pack(side='left',padx=5)

    def load_data(self):
        try:
            self.grid.delete(*self.grid.get_children())
            conn=self.get_connection(); cur=conn.cursor()
            cur.execute('EXEC dbo.Sub_CodeAndBookletNoDesc')
            rows=cur.fetchall()
            for r in rows:
                self.grid.insert('', 'end', values=(r.ID,r.FileName,r.Barcode,r.Subject_Code,r.Booklet_Sl_No))
            conn.close()
            self.lbl_message.config(text=f'{len(rows)} record(s) loaded.',fg='green')
        except Exception as ex:
            self.lbl_message.config(text=str(ex),fg='red')
            self.log_error(ex)

    def search_data(self):
        sid=self.txt_id.get().lower(); sf=self.txt_file.get().lower(); sb=self.txt_barcode.get().lower()
        for item in self.grid.get_children():
            vals=self.grid.item(item)['values']
            visible=((not sid or sid in str(vals[0]).lower()) and (not sf or sf in str(vals[1]).lower()) and (not sb or sb in str(vals[2]).lower()))
            if not visible:
                self.grid.detach(item)

    def clear_search(self):
        self.txt_id.delete(0,'end'); self.txt_file.delete(0,'end'); self.txt_barcode.delete(0,'end')

    def row_selected(self,event):
        item=self.grid.selection()[0]
        row=self.grid.item(item)['values']
        self.lbl_message.config(text='')
        self.lbl_id.config(text=row[0])
        self.txt_subject.delete(0,'end'); self.txt_subject.insert(0,row[3])
        self.txt_booklet.delete(0,'end'); self.txt_booklet.insert(0,row[4])
        self.current_image=row[1]
        self.display_images()

    def display_images(self):
        img=Image.open(self.current_image)
        full=img.copy(); full.thumbnail((700,850))
        p=ImageTk.PhotoImage(full)
        self.full_image.configure(image=p); self.full_image.image=p
        s=img.crop(SUBJECT_BOX).resize((320,120),Image.Resampling.LANCZOS)
        ps=ImageTk.PhotoImage(s); self.subject_zoom.configure(image=ps); self.subject_zoom.image=ps
        b=img.crop(BOOKLET_BOX).resize((320,120),Image.Resampling.LANCZOS)
        pb=ImageTk.PhotoImage(b); self.booklet_zoom.configure(image=pb); self.booklet_zoom.image=pb

    def update_record(self):
        try:
            conn=self.get_connection(); cur=conn.cursor()
            cur.execute('EXEC USP_UpdateCounterFoilEditedData ?,?,?,?', int(self.lbl_id.cget('text')), self.txt_subject.get().strip(), self.txt_booklet.get().strip(), LOGGED_USER_ID)
            conn.commit(); conn.close()
            self.lbl_message.config(text=f'Record ID {self.lbl_id.cget("text")} Updated Successfully.',fg='green')
        except Exception as ex:
            self.lbl_message.config(text=str(ex),fg='red')
            self.log_error(ex)

    def reset_fields(self):
        self.lbl_id.config(text='')
        self.txt_subject.delete(0,'end')
        self.txt_booklet.delete(0,'end')
        self.lbl_message.config(text='')
        self.subject_zoom.configure(image='')
        self.booklet_zoom.configure(image='')
        self.full_image.configure(image='')

    def log_error(self,error_msg):
        try:
            conn=self.get_connection(); cur=conn.cursor()
            cur.execute('INSERT INTO ErrorLog(ErrorScreen,ErrorModule,ErrorText,ErrorTime) VALUES (?,?,?,GETDATE())','Subject Code & Booklet Discrepancy','SubjectBookletDiscrepancy',str(error_msg))
            conn.commit(); conn.close()
        except Exception:
            pass

if __name__=='__main__':
    root=tk.Tk()
    app=SubjectBookletDiscrepancy(root)
    root.mainloop()
