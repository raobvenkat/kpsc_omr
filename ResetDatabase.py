import tkinter as tk
from tkinter import messagebox
import pyodbc


# ==========================================
# SQL SERVER CONNECTION
# ==========================================
def get_connection():
    conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=172.16.16.134;"
        "DATABASE=KPSCDataExtraction;"
        "UID=sysadm;"
        "PWD=SgFgkU7E4BSn;"
    )
    return conn


# ==========================================
# PROCESS BUTTON EVENT
# ==========================================
def process_reset():
    password = txt_passcode.get().strip()

    if len(password) < 10:
        lbl_message.config(
            text="Kindly enter the passcode",
            fg="red"
        )
        txt_passcode.focus()
        return

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "EXEC usp_Resetdatabase ?",
            password
        )

        result = cursor.fetchone()

        if result:
            lbl_message.config(
                text=str(result[0]),
                fg="green"
            )
        else:
            lbl_message.config(
                text="Procedure executed successfully.",
                fg="green"
            )

        conn.commit()
        cursor.close()
        conn.close()

    except Exception as e:
        lbl_message.config(
            text=f"Error : {str(e)}",
            fg="red"
        )


# ==========================================
# CLOSE BUTTON EVENT
# ==========================================
def close_screen():
    root.destroy()


# ==========================================
# MAIN WINDOW
# ==========================================
root = tk.Tk()
root.title("Clear Database / Reset Database")
root.geometry("600x250")
root.resizable(False, False)

# ==========================================
# HEADER
# ==========================================
header = tk.Label(
    root,
    text="Clear Database / Reset Database",
    font=("Arial", 16, "bold"),
    fg="navy"
)
header.pack(pady=15)

# ==========================================
# FRAME
# ==========================================
frame = tk.LabelFrame(
    root,
    text="Database Reset",
    padx=10,
    pady=10
)
frame.pack(fill="both", padx=20, pady=10)

# Passcode Label
lbl_passcode = tk.Label(
    frame,
    text="Enter Security PassCode:"
)
lbl_passcode.grid(
    row=0,
    column=0,
    padx=5,
    pady=10,
    sticky="w"
)

# Passcode Textbox
txt_passcode = tk.Entry(
    frame,
    width=30,
    show="*"
)
txt_passcode.grid(
    row=0,
    column=1,
    padx=5,
    pady=10
)

# Process Button
btn_process = tk.Button(
    frame,
    text="Process",
    width=12,
    bg="#4CAF50",
    fg="white",
    command=process_reset
)
btn_process.grid(
    row=0,
    column=2,
    padx=10
)

# Close Button
btn_close = tk.Button(
    frame,
    text="Close",
    width=12,
    bg="#d9534f",
    fg="white",
    command=close_screen
)
btn_close.grid(
    row=0,
    column=3,
    padx=5
)

# ==========================================
# MESSAGE LABEL
# ==========================================
lbl_message = tk.Label(
    root,
    text="",
    font=("Arial", 10, "bold"),
    fg="blue"
)
lbl_message.pack(pady=15)

# ==========================================
# START APPLICATION
# ==========================================
root.mainloop()
