import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import pyodbc
import db_credentials

class UserGroupMaster:
    def __init__(self, root):
        self.root=root
        self.root.title('User Group Master')
        self.root.geometry('1200x750')
        self.create_ui()
        self.load_data()
        self.clear_fields()

    def get_connection(self):
        return pyodbc.connect(CONN_STR)

    def get_next_groupid(self):
        con=self.get_connection(); cur=con.cursor()
        cur.execute('SELECT ISNULL(MAX(GroupID),0)+1 FROM UserGroupM')
        n=cur.fetchone()[0]
        con.close(); return n

    def create_ui(self):
        tk.Label(self.root,text='USER GROUP MASTER',font=('Segoe UI',18,'bold')).pack(pady=10)

        sfrm=tk.LabelFrame(self.root,text='Search')
        sfrm.pack(fill='x',padx=10,pady=5)
        self.txt_search=tk.Entry(sfrm,width=50)
        self.txt_search.pack(side='left',padx=5,pady=5)
        tk.Button(sfrm,text='Search',command=self.load_data).pack(side='left',padx=5)

        frm=tk.LabelFrame(self.root,text='Group Details')
        frm.pack(fill='x',padx=10,pady=5)

        tk.Label(frm,text='Group ID').grid(row=0,column=0,padx=5,pady=5,sticky='w')
        self.txt_groupid=tk.Entry(frm,state='readonly',width=15)
        self.txt_groupid.grid(row=0,column=1)

        tk.Label(frm,text='Group Name').grid(row=0,column=2,padx=5,pady=5)
        self.txt_groupname=tk.Entry(frm,width=40)
        self.txt_groupname.grid(row=0,column=3)

        tk.Label(frm,text='Description').grid(row=1,column=0,padx=5,pady=5)
        self.txt_descr=tk.Entry(frm,width=80)
        self.txt_descr.grid(row=1,column=1,columnspan=3,sticky='we')

        tk.Label(frm,text='Super User').grid(row=2,column=0,padx=5,pady=5)
        self.superuser=tk.StringVar(value='N')
        ttk.Combobox(frm,textvariable=self.superuser,values=['Y','N'],state='readonly',width=10).grid(row=2,column=1)

        bfrm=tk.Frame(self.root)
        bfrm.pack(fill='x',pady=5)
        tk.Button(bfrm,text='Add',width=12,command=self.clear_fields).pack(side='left',padx=3)
        tk.Button(bfrm,text='Save',width=12,command=self.save_record).pack(side='left',padx=3)
        tk.Button(bfrm,text='Update',width=12,command=self.update_record).pack(side='left',padx=3)
        tk.Button(bfrm,text='Delete',width=12,command=self.delete_record).pack(side='left',padx=3)
        tk.Button(bfrm,text='Cancel',width=12,command=self.clear_fields).pack(side='left',padx=3)

        grid_frame=tk.LabelFrame(self.root,text='Existing User Groups')
        grid_frame.pack(fill='both',expand=True,padx=10,pady=5)

        self.grid=ttk.Treeview(grid_frame,columns=('ID','NAME','DESC','SU'),show='headings')
        self.grid.heading('ID',text='Group ID')
        self.grid.heading('NAME',text='Group Name')
        self.grid.heading('DESC',text='Description')
        self.grid.heading('SU',text='Super User')
        self.grid.pack(fill='both',expand=True)
        self.grid.bind('<Double-1>',self.load_selected)

        self.lbl_count=tk.Label(self.root,text='Records : 0')
        self.lbl_count.pack(anchor='e',padx=10)

        audit=tk.LabelFrame(self.root,text='Audit Trail')
        audit.pack(fill='x',padx=10,pady=5)
        self.audit_text=tk.Text(audit,height=6)
        self.audit_text.pack(fill='x')

    def audit_log(self,msg):
        self.audit_text.insert('end',f'{datetime.now()} - {msg}\n')
        self.audit_text.see('end')

    def load_data(self):
        for i in self.grid.get_children():
            self.grid.delete(i)
        con=self.get_connection(); cur=con.cursor()
        txt=self.txt_search.get().strip()
        if txt:
            cur.execute("SELECT GroupID,GroupName,GroupDescr,SuperUser FROM UserGroupM WHERE DeleteDate IS NULL AND (GroupName LIKE ? OR GroupDescr LIKE ?) ORDER BY GroupID",'%'+txt+'%','%'+txt+'%')
        else:
            cur.execute('SELECT GroupID,GroupName,GroupDescr,SuperUser FROM UserGroupM WHERE DeleteDate IS NULL ORDER BY GroupID')
        rows=cur.fetchall()
        for r in rows:
            self.grid.insert('', 'end', values=r)
        self.lbl_count.config(text=f'Records : {len(rows)}')
        con.close()

    def save_record(self):
        if not self.txt_groupname.get().strip():
            messagebox.showwarning('Validation','Group Name required')
            return
        con=self.get_connection(); cur=con.cursor()
        cur.execute('SELECT COUNT(*) FROM UserGroupM WHERE GroupName=? AND DeleteDate IS NULL',self.txt_groupname.get())
        if cur.fetchone()[0]>0:
            messagebox.showwarning('Duplicate','Group Name already exists')
            con.close(); return
        cur.execute('INSERT INTO UserGroupM(GroupID,GroupName,GroupDescr,AddDate,AddUserID,SuperUser) VALUES(?,?,?,?,?,?)',int(self.txt_groupid.get()),self.txt_groupname.get(),self.txt_descr.get(),datetime.now(),1,self.superuser.get())
        con.commit(); con.close()
        self.audit_log('Created '+self.txt_groupname.get())
        self.load_data(); self.clear_fields()

    def update_record(self):
        con=self.get_connection(); cur=con.cursor()
        cur.execute('UPDATE UserGroupM SET GroupName=?,GroupDescr=?,ModifyDate=?,ModifyUserID=?,SuperUser=? WHERE GroupID=?',self.txt_groupname.get(),self.txt_descr.get(),datetime.now(),1,self.superuser.get(),int(self.txt_groupid.get()))
        con.commit(); con.close()
        self.audit_log('Updated '+self.txt_groupname.get())
        self.load_data()

    def delete_record(self):
        if not self.txt_groupid.get(): return
        if not messagebox.askyesno('Confirm Delete',f"Delete Group '{self.txt_groupname.get()}'?"):
            return
        con=self.get_connection(); cur=con.cursor()
        cur.execute('UPDATE UserGroupM SET DeleteDate=? WHERE GroupID=?',datetime.now(),int(self.txt_groupid.get()))
        con.commit(); con.close()
        self.audit_log('Deleted '+self.txt_groupname.get())
        self.load_data(); self.clear_fields()

    def load_selected(self,event=None):
        item=self.grid.focus()
        if not item:return
        v=self.grid.item(item,'values')
        self.txt_groupid.config(state='normal')
        self.txt_groupid.delete(0,'end'); self.txt_groupid.insert(0,v[0])
        self.txt_groupid.config(state='readonly')
        self.txt_groupname.delete(0,'end'); self.txt_groupname.insert(0,v[1])
        self.txt_descr.delete(0,'end'); self.txt_descr.insert(0,v[2])
        self.superuser.set(v[3])

    def clear_fields(self):
        self.txt_groupid.config(state='normal')
        self.txt_groupid.delete(0,'end')
        self.txt_groupid.insert(0,str(self.get_next_groupid()))
        self.txt_groupid.config(state='readonly')
        self.txt_groupname.delete(0,'end')
        self.txt_descr.delete(0,'end')
        self.superuser.set('N')

if __name__=='__main__':
    root=tk.Tk()
    UserGroupMaster(root)
    root.mainloop()
