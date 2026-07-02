import tkinter as tk
from tkinter import ttk,messagebox
import pyodbc
from datetime import datetime

SERVER='3.109.160.126'
DATABASE='KPSCOMRICRExtraction'
USERNAME='KPSCDev'
PASSWORD='kpscD5v'
CONN=f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER};DATABASE={DATABASE};UID={USERNAME};PWD={PASSWORD};TrustServerCertificate=yes"

class ToolTip:
    def __init__(self,w,t):
        self.w=w; self.t=t
        w.bind('<Enter>',self.show); w.bind('<Leave>',self.hide)
    def show(self,e=None):
        self.tw=tk.Toplevel(self.w); self.tw.wm_overrideredirect(True)
        self.tw.geometry(f'+{self.w.winfo_rootx()+15}+{self.w.winfo_rooty()+15}')
        tk.Label(self.tw,text=self.t,bg='lightyellow',relief='solid',borderwidth=1).pack()
    def hide(self,e=None):
        if hasattr(self,'tw'): self.tw.destroy()

class App:
    def __init__(self,r):
        self.r=r; r.title('Set Group Permissions'); r.geometry('1500x900')
        self.groups={}; self.rows=[]

        tk.Label(r,text='SET GROUP PERMISSIONS',font=('Segoe UI',20,'bold')).pack(pady=10)

        top=tk.Frame(r); top.pack(fill='x',padx=10)
        tk.Label(top,text='User Group').pack(side='left')
        self.grp=ttk.Combobox(top,width=60,state='readonly'); self.grp.pack(side='left',padx=5)
        self.grp.bind('<<ComboboxSelected>>',self.load_permissions)

        self.canvas=tk.Canvas(r,height=450)
        self.scr=ttk.Scrollbar(r,orient='vertical',command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scr.set)
        self.scr.pack(side='right',fill='y'); self.canvas.pack(fill='both',expand=True,padx=10)

        self.frm=tk.Frame(self.canvas)
        self.canvas.create_window((0,0),window=self.frm,anchor='nw')
        self.frm.bind('<Configure>',lambda e:self.canvas.configure(scrollregion=self.canvas.bbox('all')))

        hdr=['Screen Name','All','View','Add','Edit','Delete','Override']
        for i,h in enumerate(hdr):
            tk.Label(self.frm,text=h,bg='#1f497d',fg='white',font=('Segoe UI',10,'bold'),width=20).grid(row=0,column=i,sticky='nsew')

        bf=tk.Frame(r); bf.pack(pady=5)
        for t,c in [('Save',self.save),('Update',self.save),('Delete',self.delete),('Close',r.destroy)]:
            tk.Button(bf,text=t,width=12,command=c).pack(side='left',padx=5)

        self.audit=tk.Text(r,height=5); self.audit.pack(fill='x',padx=10,pady=5)
        self.load_groups(); self.build_grid()

    def conn(self): return pyodbc.connect(CONN)
    def log(self,m): self.audit.insert('end',f'{datetime.now()} - {m}\n')

    def load_groups(self):
        con=self.conn(); cur=con.cursor()
        cur.execute('select GroupID,GroupName from UserGroupM where DeleteDate is null order by GroupName')
        vals=[]
        for x in cur.fetchall():
            k=f'{x.GroupName} ({x.GroupID})'; self.groups[k]=int(x.GroupID); vals.append(k)
        self.grp['values']=vals; con.close()

    def grants(self,row):
        return ''.join('Y' if row[k].get() else 'N' for k in ['view','add','edit','delete','override'])

    def all_click(self,row):
        v=row['all'].get()
        for k in ['view','add','edit','delete','override']: row[k].set(v)

    def build_grid(self):
        for w in self.frm.grid_slaves():
            if int(w.grid_info()['row'])>0: w.destroy()
        self.rows=[]
        con=self.conn(); cur=con.cursor()
        cur.execute('select ModuleID,ScreenID,ScreenName from ModulesAndScreens order by ModuleID,ScreenOrder')
        current=None; r=1
        for rec in cur.fetchall():
            if current!=rec.ModuleID:
                current=rec.ModuleID
                tk.Label(self.frm,text=f'Module {current}',bg='#b7c7d8',font=('Segoe UI',10,'bold')).grid(row=r,column=0,columnspan=7,sticky='ew')
                r+=1
            row={'sid':int(rec.ScreenID)}
            tk.Label(self.frm,text=str(rec.ScreenName),anchor='w',width=45).grid(row=r,column=0,sticky='w')
            for k in ['all','view','add','edit','delete','override']: row[k]=tk.BooleanVar()
            tips={'all':'Grant all permissions','view':'View permission','add':'Add permission','edit':'Edit permission','delete':'Delete permission','override':'Override permission'}
            for c,k in enumerate(['all','view','add','edit','delete','override'],start=1):
                cb=tk.Checkbutton(self.frm,variable=row[k],command=(lambda rw=row:self.all_click(rw)) if k=='all' else None)
                cb.grid(row=r,column=c)
                ToolTip(cb,tips[k])
            self.rows.append(row); r+=1
        con.close()

    def load_permissions(self,e=None):
        if not self.grp.get(): return
        gid=self.groups[self.grp.get()]
        self.build_grid()
        con=self.conn(); cur=con.cursor()
        cur.execute('select ScreenID,Grants from Permission where GroupID=?',gid)
        d={int(x.ScreenID):str(x.Grants).ljust(5,'N') for x in cur.fetchall()}
        con.close()
        for row in self.rows:
            g=d.get(row['sid'],'NNNNN')
            row['view'].set(g[0]=='Y'); row['add'].set(g[1]=='Y'); row['edit'].set(g[2]=='Y'); row['delete'].set(g[3]=='Y'); row['override'].set(g[4]=='Y')
            row['all'].set(g=='YYYYY')

    def save(self):
        if not self.grp.get(): return messagebox.showwarning('Warning','Select User Group')
        gid=self.groups[self.grp.get()]
        con=self.conn(); cur=con.cursor()
        cur.execute('delete from Permission where GroupID=?',gid)
        for row in self.rows:
            cur.execute('insert into Permission(GroupID,ScreenID,Grants,AddUserId,AddDate) values(?,?,?,?,?)',gid,row['sid'],self.grants(row),1,datetime.now())
        con.commit(); con.close()
        self.log(f'Saved permissions for GroupID {gid}')
        messagebox.showinfo('Success','Permissions Saved')

    def delete(self):
        if not self.grp.get(): return
        if not messagebox.askyesno('Confirm Delete','Delete all permissions for selected group?'): return
        gid=self.groups[self.grp.get()]
        con=self.conn(); cur=con.cursor(); cur.execute('delete from Permission where GroupID=?',gid); con.commit(); con.close()
        self.log(f'Deleted permissions for GroupID {gid}')

if __name__=='__main__':
    root=tk.Tk(); App(root); root.mainloop()
