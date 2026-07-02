import tkinter as tk
from tkinter import messagebox
import pyodbc
import hashlib
import secrets
import base64

# =====================================================
# DATABASE
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


def verify_password(
        password,
        stored_hash,
        salt):

    new_hash = generate_hash(
        password,
        salt
    )

    return new_hash == stored_hash


# =====================================================
# CHANGE PASSWORD SCREEN
# =====================================================

class ChangePassword:

    def __init__(
            self,
            parent,
            username):

        self.username = username

        self.window = tk.Toplevel(parent)

        self.window.title(
            "Change Password"
        )

        self.window.geometry(
            "550x320"
        )

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
            text="Change Password",
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

        self.txt_user.insert(
            0,
            self.username
        )

        self.txt_user.config(
            state="readonly"
        )

        # CURRENT PASSWORD

        tk.Label(
            frame,
            text="Current Password"
        ).grid(
            row=1,
            column=0,
            padx=10,
            pady=10,
            sticky="w"
        )

        self.txt_current = tk.Entry(
            frame,
            width=30,
            show="*"
        )

        self.txt_current.grid(
            row=1,
            column=1,
            padx=10
        )

        # NEW PASSWORD

        tk.Label(
            frame,
            text="New Password"
        ).grid(
            row=2,
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
            row=2,
            column=1,
            padx=10
        )

        # CONFIRM PASSWORD

        tk.Label(
            frame,
            text="Confirm Password"
        ).grid(
            row=3,
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
            row=3,
            column=1,
            padx=10
        )

        # BUTTONS

        btn_frame = tk.Frame(
            self.window
        )

        btn_frame.pack(
            pady=20
        )

        tk.Button(
            btn_frame,
            text="Change Password",
            width=18,
            bg="green",
            fg="white",
            command=self.change_password
        ).pack(
            side="left",
            padx=10
        )

        tk.Button(
            btn_frame,
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

    def change_password(self):

        current_password = (
            self.txt_current.get().strip()
        )

        new_password = (
            self.txt_new.get().strip()
        )

        confirm_password = (
            self.txt_confirm.get().strip()
        )

        if current_password == "":

            messagebox.showwarning(
                "Warning",
                "Enter Current Password."
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
                SELECT
                    UserPassword,
                    Salt
                FROM UserMaster
                WHERE UserName=?
            """,
            self.username)

            row = cur.fetchone()

            if row is None:

                messagebox.showerror(
                    "Error",
                    "User not found."
                )

                conn.close()

                return

            stored_hash = row.UserPassword
            salt = row.Salt

            if not verify_password(
                    current_password,
                    stored_hash,
                    salt):

                messagebox.showerror(
                    "Error",
                    "Current Password is incorrect."
                )

                conn.close()

                return

            new_salt = generate_salt()

            new_hash = generate_hash(
                new_password,
                new_salt
            )

            cur.execute("""
                UPDATE UserMaster
                SET
                    UserPassword=?,
                    Salt=?
                WHERE UserName=?
            """,
            (
                new_hash,
                new_salt,
                self.username
            ))

            conn.commit()

            conn.close()

            messagebox.showinfo(
                "Success",
                "Password changed successfully."
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
                "Change Password",
                "ChangePassword",
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

    ChangePassword(
        root,
        "Admin"
    )

    root.mainloop()