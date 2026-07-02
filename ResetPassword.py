import tkinter as tk
from tkinter import messagebox
import pyodbc
import hashlib
import secrets
import base64

# =====================================================
# DATABASE CONNECTION
# =====================================================

CONNECTION_STRING = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=3.109.160.126;"
    "DATABASE=KPSCOMRICRExtraction;"
    "UID=KPSCDev;"
    "PWD=kpscD5v;"
    "TrustServerCertificate=yes;"
)

# =====================================================
# HASH & SALT
# =====================================================

def generate_salt():

    return base64.b64encode(
        secrets.token_bytes(32)
    ).decode("utf-8")


def generate_hash(password, salt):

    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100000
    ).hex()

# =====================================================
# RESET PASSWORD
# =====================================================

class ResetPassword:

    def __init__(self, parent):

        self.window = tk.Toplevel(parent)

        self.window.title("Reset Password")

        self.window.geometry("550x300")

        self.window.resizable(
            False,
            False
        )

        self.window.grab_set()

        self.create_screen()

    # =================================================

    def get_connection(self):

        return pyodbc.connect(
            CONNECTION_STRING
        )

    # =================================================

    def create_screen(self):

        tk.Label(
            self.window,
            text="Reset Password",
            font=("Arial",18,"bold")
        ).pack(
            pady=15
        )

        frame = tk.Frame(
            self.window
        )

        frame.pack(
            pady=10
        )

        # USER NAME

        tk.Label(
            frame,
            text="User Name"
        ).grid(
            row=0,
            column=0,
            padx=10,
            pady=10,
            sticky="w"
        )

        self.txt_user = tk.Entry(
            frame,
            width=30
        )

        self.txt_user.grid(
            row=0,
            column=1,
            padx=10
        )

        # NEW PASSWORD

        tk.Label(
            frame,
            text="New Password"
        ).grid(
            row=1,
            column=0,
            padx=10,
            pady=10,
            sticky="w"
        )

        self.txt_new = tk.Entry(
            frame,
            width=30,
            show="*"
        )

        self.txt_new.grid(
            row=1,
            column=1
        )

        # CONFIRM PASSWORD

        tk.Label(
            frame,
            text="Confirm Password"
        ).grid(
            row=2,
            column=0,
            padx=10,
            pady=10,
            sticky="w"
        )

        self.txt_confirm = tk.Entry(
            frame,
            width=30,
            show="*"
        )

        self.txt_confirm.grid(
            row=2,
            column=1
        )

        # BUTTONS

        button_frame = tk.Frame(
            self.window
        )

        button_frame.pack(
            pady=20
        )

        tk.Button(
            button_frame,
            text="Reset Password",
            width=18,
            bg="green",
            fg="white",
            command=self.reset_password
        ).pack(
            side="left",
            padx=10
        )

        tk.Button(
            button_frame,
            text="Cancel",
            width=18,
            bg="red",
            fg="white",
            command=self.window.destroy
        ).pack(
            side="left",
            padx=10
        )

    # =================================================

    def reset_password(self):

        username = self.txt_user.get().strip()

        new_password = self.txt_new.get().strip()

        confirm_password = self.txt_confirm.get().strip()

        if username == "":

            messagebox.showwarning(
                "Warning",
                "Enter User Name."
            )

            return

        if new_password == "":

            messagebox.showwarning(
                "Warning",
                "Enter New Password."
            )

            return

        if confirm_password == "":

            messagebox.showwarning(
                "Warning",
                "Enter Confirm Password."
            )

            return

        if new_password != confirm_password:

            messagebox.showerror(
                "Error",
                "New Password and Confirm Password do not match."
            )

            return

        try:

            conn = self.get_connection()

            cur = conn.cursor()

            cur.execute("""
                SELECT COUNT(*)
                FROM UserMaster
                WHERE UserName = ?
            """,
            username)

            count = cur.fetchone()[0]

            if count == 0:

                conn.close()

                messagebox.showerror(
                    "Error",
                    "User Name not found."
                )

                return

            salt = generate_salt()

            password_hash = generate_hash(
                new_password,
                salt
            )

            cur.execute("""
                UPDATE UserMaster
                   SET UserPassword = ?,
                       Salt = ?
                 WHERE UserName = ?
            """,
            (
                password_hash,
                salt,
                username
            )
            )

            conn.commit()

            conn.close()

            messagebox.showinfo(
                "Success",
                "Password Reset Successfully."
            )

            self.window.destroy()

        except Exception as ex:

            self.log_error(str(ex))

            messagebox.showerror(
                "Error",
                str(ex)
            )

    # =================================================

    def log_error(self, error_text):

        try:

            conn = self.get_connection()

            cur = conn.cursor()

            cur.execute("""
                INSERT INTO ErrorLog
                (
                    ErrorScreen,
                    ErrorModule,
                    ErrorText,
                    ErrorTime
                )
                VALUES
                (
                    ?,
                    ?,
                    ?,
                    GETDATE()
                )
            """,
            (
                "Reset Password",
                "ResetPassword",
                error_text
            ))

            conn.commit()

            conn.close()

        except:
            pass


# =====================================================
# TEST
# =====================================================

if __name__ == "__main__":

    root = tk.Tk()

    root.withdraw()

    ResetPassword(root)

    root.mainloop()