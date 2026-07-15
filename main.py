"""
KPSC OMR & Attendance Suite — production launcher.

First launch prompts for SQL Server connection details, stores them securely,
then presents a hub to open OMR Sheets or Attendance Sheets extraction tools.
"""

from __future__ import annotations

import os
import sys
import traceback
import importlib
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Optional
from AllDiscrepancyGeneration import AllDiscrepancyGeneration

try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    BASE_DIR = os.getcwd()

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import db_credentials
import auth
import audit


APP_TITLE = "KPSC Counter Foil & Nominal Roll Data extraction Suite"
APP_VERSION = "1.0.0"


class ResponsiveScaler:
    """Scale fonts and spacing from screen size and current window size."""

    def __init__(self, root: tk.Misc):
        self.root = root
        self._screen_w = root.winfo_screenwidth()
        self._screen_h = root.winfo_screenheight()
        self._win_w = max(1, self._screen_w)
        self._win_h = max(1, self._screen_h)
        self._bind_resize()

    def _bind_resize(self) -> None:
        self.root.bind("<Configure>", self._on_configure, add="+")

    def _on_configure(self, event) -> None:
        if event.widget is not self.root:
            return
        self._win_w = max(1, event.width)
        self._win_h = max(1, event.height)

    @property
    def scale(self) -> float:
        screen_factor = min(self._screen_w / 1920.0, self._screen_h / 1080.0)
        window_factor = min(self._win_w / 1280.0, self._win_h / 760.0)
        return max(0.75, min(1.6, (screen_factor + window_factor) / 2.0))

    def fs(self, size: int) -> int:
        return max(8, int(size * self.scale))

    def px(self, size: int) -> int:
        return max(2, int(size * self.scale))


class DatabaseSetupDialog(tk.Toplevel):
    """Collect and validate SQL Server connection details."""

    def __init__(
        self,
        parent: tk.Misc,
        scaler: ResponsiveScaler,
        *,
        title: str = "Database Setup",
        initial: Optional[dict] = None,
        on_success: Optional[Callable[[], None]] = None,
    ):
        super().__init__(parent)
        self.scaler = scaler
        self.on_success = on_success
        self.result_saved = False

        self.title(title)
        self.configure(bg="#14141c")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        sw = parent.winfo_screenwidth()
        sh = parent.winfo_screenheight()
        w = max(420, int(sw * 0.34))
        h = max(460, int(sh * 0.52))
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        initial = initial or {}
        self._build_ui(initial)
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.after(50, self._bring_to_front)

    def _bring_to_front(self) -> None:
        self.deiconify()
        self.lift()
        self.focus_force()

    def _build_ui(self, initial: dict) -> None:
        fs = self.scaler.fs
        px = self.scaler.px

        outer = tk.Frame(self, bg="#14141c", padx=px(28), pady=px(24))
        outer.pack(fill="both", expand=True)

        tk.Label(
            outer,
            text="SQL Server Connection",
            bg="#14141c",
            fg="#00e676",
            font=("Segoe UI", fs(16), "bold"),
        ).pack(anchor="w")

        tk.Label(
            outer,
            text="Enter connection details once. They are encrypted and stored locally.",
            bg="#14141c",
            fg="#9aa0b4",
            font=("Segoe UI", fs(10)),
            wraplength=px(420),
            justify="left",
        ).pack(anchor="w", pady=(px(6), px(18)))

        self.entries = {}
        fields = [
            ("server", "Server name", initial.get("server", "")),
            ("database", "Database name", initial.get("database", "")),
            ("username", "Username", initial.get("username", "")),
            ("password", "Password", ""),
        ]

        for key, label, value in fields:
            row = tk.Frame(outer, bg="#14141c")
            row.pack(fill="x", pady=(0, px(10)))
            tk.Label(
                row,
                text=label,
                bg="#14141c",
                fg="#d8dce8",
                font=("Segoe UI", fs(10)),
                width=14,
                anchor="w",
            ).pack(side="left")
            entry = tk.Entry(
                row,
                bg="#24242f",
                fg="#ffffff",
                insertbackground="#ffffff",
                relief="flat",
                font=("Segoe UI", fs(10)),
                show="*" if key == "password" else "",
            )
            entry.pack(side="left", fill="x", expand=True, ipady=px(4))
            if value:
                entry.insert(0, value)
            self.entries[key] = entry

        self.status_lbl = tk.Label(
            outer,
            text="",
            bg="#14141c",
            fg="#ff8a80",
            font=("Segoe UI", fs(9)),
            wraplength=px(420),
            justify="left",
        )
        self.status_lbl.pack(fill="x", pady=(px(4), px(8)))

        btn_row = tk.Frame(outer, bg="#14141c")
        btn_row.pack(fill="x", pady=(px(8), 0))

        tk.Button(
            btn_row,
            text="Test Connection",
            command=self._test_connection,
            bg="#2b2b36",
            fg="#ffffff",
            activebackground="#3a3a48",
            activeforeground="#ffffff",
            relief="flat",
            font=("Segoe UI", fs(10), "bold"),
            padx=px(14),
            pady=px(6),
            cursor="hand2",
        ).pack(side="left")

        tk.Button(
            btn_row,
            text="Save & Continue",
            command=self._save,
            bg="#00c853",
            fg="#ffffff",
            activebackground="#00e676",
            activeforeground="#ffffff",
            relief="flat",
            font=("Segoe UI", fs(10), "bold"),
            padx=px(14),
            pady=px(6),
            cursor="hand2",
        ).pack(side="right")

        self.entries["server"].focus_set()

    def _values(self) -> dict:
        return {key: entry.get().strip() for key, entry in self.entries.items()}

    def _test_connection(self) -> None:
        values = self._values()
        try:
            db_credentials.test_connection(
                values["server"],
                values["database"],
                values["username"],
                self.entries["password"].get(),
            )
        except Exception as exc:
            self.status_lbl.config(text=f"Connection failed: {exc}", fg="#ff8a80")
            return

        self.status_lbl.config(text="Connection successful.", fg="#00e676")

    def _save(self) -> None:
        values = self._values()
        password = self.entries["password"].get()
        try:
            db_credentials.test_connection(
                values["server"],
                values["database"],
                values["username"],
                password,
            )
            db_credentials.save_credentials(
                values["server"],
                values["database"],
                values["username"],
                password,
            )
        except Exception as exc:
            self.status_lbl.config(text=str(exc), fg="#ff8a80")
            return

        self.result_saved = True
        if self.on_success:
            self.on_success()
        self.destroy()

    def _cancel(self) -> None:
        if not db_credentials.credentials_exist():
            if not messagebox.askyesno(
                "Exit Setup",
                "Database setup is required to use this application.\n\nExit now?",
                parent=self,
            ):
                return
        self.destroy()


class UserFormDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        scaler: ResponsiveScaler,
        *,
        title: str,
        user: Optional[dict] = None,
        require_password: bool = False,
    ):
        super().__init__(parent)
        self.scaler = scaler
        self.user = user or {}
        self.require_password = require_password
        self.result: Optional[dict] = None

        self.title(title)
        self.configure(bg="#14141c")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        sw = parent.winfo_screenwidth()
        sh = parent.winfo_screenheight()
        w = max(430, int(sw * 0.32))
        h = max(420, int(sh * 0.48))
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
        self._build_ui(title)

    def _build_ui(self, title: str) -> None:
        fs = self.scaler.fs
        px = self.scaler.px
        outer = tk.Frame(self, bg="#14141c", padx=px(28), pady=px(24))
        outer.pack(fill="both", expand=True)

        tk.Label(
            outer, text=title, bg="#14141c", fg="#00e676",
            font=("Segoe UI", fs(16), "bold")
        ).pack(anchor="w", pady=(0, px(16)))

        self.entries = {}
        fields = [
            ("username", "Username", self.user.get("username", "")),
            ("full_name", "Full name", self.user.get("full_name", "")),
            ("password", "Password", ""),
        ]
        for key, label, value in fields:
            row = tk.Frame(outer, bg="#14141c")
            row.pack(fill="x", pady=(0, px(10)))
            tk.Label(
                row, text=label, bg="#14141c", fg="#d8dce8",
                font=("Segoe UI", fs(10)), width=13, anchor="w"
            ).pack(side="left")
            entry = tk.Entry(
                row, bg="#24242f", fg="#ffffff", insertbackground="#ffffff",
                relief="flat", font=("Segoe UI", fs(10)),
                show="*" if key == "password" else "",
            )
            entry.pack(side="left", fill="x", expand=True, ipady=px(4))
            if value:
                entry.insert(0, value)
            self.entries[key] = entry

        role_row = tk.Frame(outer, bg="#14141c")
        role_row.pack(fill="x", pady=(0, px(10)))
        tk.Label(
            role_row, text="Role", bg="#14141c", fg="#d8dce8",
            font=("Segoe UI", fs(10)), width=13, anchor="w"
        ).pack(side="left")
        self.role_var = tk.StringVar(value=self.user.get("role", "user"))
        role_combo = ttk.Combobox(
            role_row, textvariable=self.role_var,
            values=["admin", "user"], state="readonly", width=18
        )
        role_combo.pack(side="left", fill="x", expand=True)

        self.active_var = tk.BooleanVar(value=bool(self.user.get("is_active", True)))
        tk.Checkbutton(
            outer, text="Active", variable=self.active_var,
            bg="#14141c", fg="#d8dce8", activebackground="#14141c",
            activeforeground="#ffffff", selectcolor="#24242f",
            font=("Segoe UI", fs(10))
        ).pack(anchor="w", pady=(0, px(8)))

        self.status_lbl = tk.Label(
            outer, text="", bg="#14141c", fg="#ff8a80",
            font=("Segoe UI", fs(9)), anchor="w", justify="left"
        )
        self.status_lbl.pack(fill="x", pady=(0, px(8)))

        btn_row = tk.Frame(outer, bg="#14141c")
        btn_row.pack(fill="x", pady=(px(8), 0))
        tk.Button(
            btn_row, text="Cancel", command=self.destroy,
            bg="#2b2b36", fg="#ffffff", relief="flat",
            font=("Segoe UI", fs(10), "bold"), padx=px(14), pady=px(6)
        ).pack(side="left")
        tk.Button(
            btn_row, text="Save", command=self._save,
            bg="#00c853", fg="#ffffff", relief="flat",
            font=("Segoe UI", fs(10), "bold"), padx=px(14), pady=px(6)
        ).pack(side="right")
        self.entries["username"].focus_set()

    def _save(self) -> None:
        password = self.entries["password"].get()
        if self.require_password and not password:
            self.status_lbl.config(text="Password is required.")
            return
        if password and len(password) < 8:
            self.status_lbl.config(text="Password must be at least 8 characters.")
            return
        self.result = {
            "username": self.entries["username"].get().strip(),
            "full_name": self.entries["full_name"].get().strip(),
            "password": password,
            "role": self.role_var.get(),
            "is_active": self.active_var.get(),
        }
        self.destroy()


class AdminSetupDialog(UserFormDialog):
    def __init__(self, parent: tk.Misc, scaler: ResponsiveScaler):
        super().__init__(
            parent,
            scaler,
            title="Create First Administrator",
            user={"role": "admin", "is_active": True},
            require_password=True,
        )
        self.role_var.set("admin")


class LoginDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, scaler: ResponsiveScaler):
        super().__init__(parent)
        self.scaler = scaler
        self.user: Optional[auth.AuthenticatedUser] = None
        self.database_error = ""
        self.title("Login")
        self.configure(bg="#14141c")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        sw = parent.winfo_screenwidth()
        sh = parent.winfo_screenheight()
        w = max(390, int(sw * 0.28))
        h = max(320, int(sh * 0.36))
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.after(50, self._bring_to_front)

    def _bring_to_front(self) -> None:
        self.deiconify()
        self.lift()
        self.focus_force()

    def _build_ui(self) -> None:
        fs = self.scaler.fs
        px = self.scaler.px
        outer = tk.Frame(self, bg="#14141c", padx=px(28), pady=px(26))
        outer.pack(fill="both", expand=True)
        tk.Label(
            outer, text="Application Login", bg="#14141c", fg="#00e676",
            font=("Segoe UI", fs(16), "bold")
        ).pack(anchor="w", pady=(0, px(18)))

        self.username = self._entry_row(outer, "Username", show="")
        self.password = self._entry_row(outer, "Password", show="*")
        self.status_lbl = tk.Label(
            outer, text="", bg="#14141c", fg="#ff8a80",
            font=("Segoe UI", fs(9)), anchor="w"
        )
        self.status_lbl.pack(fill="x", pady=(px(4), px(8)))

        tk.Button(
            outer, text="Login", command=self._login,
            bg="#00c853", fg="#ffffff", relief="flat",
            font=("Segoe UI", fs(10), "bold"), padx=px(14), pady=px(7)
        ).pack(anchor="e")
        self.bind("<Return>", lambda _e: self._login())
        self.username.focus_set()

    def _entry_row(self, parent: tk.Misc, label: str, *, show: str) -> tk.Entry:
        fs = self.scaler.fs
        px = self.scaler.px
        row = tk.Frame(parent, bg="#14141c")
        row.pack(fill="x", pady=(0, px(10)))
        tk.Label(
            row, text=label, bg="#14141c", fg="#d8dce8",
            font=("Segoe UI", fs(10)), width=11, anchor="w"
        ).pack(side="left")
        entry = tk.Entry(
            row, bg="#24242f", fg="#ffffff", insertbackground="#ffffff",
            relief="flat", font=("Segoe UI", fs(10)), show=show
        )
        entry.pack(side="left", fill="x", expand=True, ipady=px(4))
        return entry

    def _login(self) -> None:
        username = self.username.get().strip()
        try:
            user = auth.authenticate(username, self.password.get())
        except Exception as exc:
            self.database_error = str(exc)
            self.destroy()
            return
        if user is None:
            audit.log("authentication", "login", outcome="failed", username=username)
            self.status_lbl.config(text="Invalid username or password.")
            return
        self.user = user
        self.destroy()

    def _cancel(self) -> None:
        self.destroy()


class UserMasterDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, scaler: ResponsiveScaler, current_user: auth.AuthenticatedUser):
        super().__init__(parent)
        self.scaler = scaler
        self.current_user = current_user
        self.title("User Master")
        self.configure(bg="#14141c")
        self.transient(parent)

        sw = parent.winfo_screenwidth()
        sh = parent.winfo_screenheight()
        w = max(760, int(sw * 0.56))
        h = max(500, int(sh * 0.58))
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        fs = self.scaler.fs
        px = self.scaler.px
        header = tk.Frame(self, bg="#14141c", padx=px(20), pady=px(16))
        header.pack(fill="x")
        tk.Label(
            header, text="User Master", bg="#14141c", fg="#00e676",
            font=("Segoe UI", fs(17), "bold")
        ).pack(side="left")
        tk.Button(
            header, text="Create User", command=self.create_user,
            bg="#00c853", fg="#ffffff", relief="flat",
            font=("Segoe UI", fs(10), "bold"), padx=px(12), pady=px(6)
        ).pack(side="right")

        cols = ("id", "username", "full_name", "role", "active")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", selectmode="browse")
        for col, text, width in [
            ("id", "ID", 60),
            ("username", "Username", 160),
            ("full_name", "Full Name", 230),
            ("role", "Role", 90),
            ("active", "Active", 80),
        ]:
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, anchor="center" if col in {"id", "role", "active"} else "w")
        self.tree.pack(fill="both", expand=True, padx=px(20), pady=(0, px(10)))

        btn_row = tk.Frame(self, bg="#14141c", padx=px(20), pady=px(12))
        btn_row.pack(fill="x")
        tk.Button(
            btn_row, text="Update", command=self.update_selected,
            bg="#2979ff", fg="#ffffff", relief="flat",
            font=("Segoe UI", fs(10), "bold"), padx=px(12), pady=px(6)
        ).pack(side="left", padx=(0, px(8)))
        tk.Button(
            btn_row, text="Delete", command=self.delete_selected,
            bg="#3a2028", fg="#ffb4ab", relief="flat",
            font=("Segoe UI", fs(10), "bold"), padx=px(12), pady=px(6)
        ).pack(side="left")
        self.status_lbl = tk.Label(
            btn_row, text="", bg="#14141c", fg="#8b93a7",
            font=("Segoe UI", fs(9)), anchor="w"
        )
        self.status_lbl.pack(side="left", padx=px(14))
        tk.Button(
            btn_row, text="Close", command=self.destroy,
            bg="#2b2b36", fg="#ffffff", relief="flat",
            font=("Segoe UI", fs(10), "bold"), padx=px(12), pady=px(6)
        ).pack(side="right")

    def refresh(self) -> None:
        self.users = auth.list_users()
        self.tree.delete(*self.tree.get_children())
        for user in self.users:
            self.tree.insert(
                "", "end", iid=str(user["id"]),
                values=(
                    user["id"], user["username"], user["full_name"],
                    user["role"], "Yes" if user["is_active"] else "No",
                )
            )
        self.status_lbl.config(text=f"{len(self.users)} user(s)")

    def create_user(self) -> None:
        dialog = UserFormDialog(self, self.scaler, title="Create User", require_password=True)
        self.wait_window(dialog)
        if not dialog.result:
            return
        try:
            auth.create_user(**dialog.result)
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Create User Failed", str(exc), parent=self)

    def _selected_user(self) -> Optional[dict]:
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Select User", "Select a user first.", parent=self)
            return None
        user_id = int(selection[0])
        return next((u for u in self.users if u["id"] == user_id), None)

    def update_selected(self) -> None:
        user = self._selected_user()
        if not user:
            return
        dialog = UserFormDialog(self, self.scaler, title="Update User", user=user)
        self.wait_window(dialog)
        if not dialog.result:
            return
        try:
            auth.update_user(user["id"], **dialog.result)
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Update User Failed", str(exc), parent=self)

    def delete_selected(self) -> None:
        user = self._selected_user()
        if not user:
            return
        if user["id"] == self.current_user.user_id:
            messagebox.showerror("Delete User", "You cannot delete the logged-in user.", parent=self)
            return
        if not messagebox.askyesno("Delete User", f"Delete user '{user['username']}'?", parent=self):
            return
        try:
            auth.delete_user(user["id"])
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Delete User Failed", str(exc), parent=self)


class ModuleCard(tk.Frame):
    """Clickable module tile for the hub."""

    def __init__(
        self,
        parent: tk.Misc,
        scaler: ResponsiveScaler,
        *,
        title: str,
        subtitle: str,
        accent: str,
        command: Callable[[], None],
    ):
        super().__init__(parent, bg="#181c24", highlightthickness=1,
                         highlightbackground="#2b313d")
        self.scaler = scaler
        self.command = command
        self.accent = accent
        self._hover = False

        px = scaler.px
        fs = scaler.fs

        self.configure(cursor="hand2")
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", lambda _e: command())

        accent_bar = tk.Frame(self, bg=accent, height=px(3))
        accent_bar.pack(fill="x", side="top")

        body = tk.Frame(self, bg="#181c24", padx=px(24), pady=px(22))
        body.pack(fill="both", expand=True)
        for widget in (self, body):
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)
            widget.bind("<Button-1>", lambda _e: command())

        self.title_label = tk.Label(
            body,
            text=title,
            bg="#181c24",
            fg="#ffffff",
            font=("Segoe UI", fs(18), "bold"),
        )
        self.title_label.pack(anchor="w")

        self.subtitle_label = tk.Label(
            body,
            text=subtitle,
            bg="#181c24",
            fg="#aeb7c6",
            font=("Segoe UI", fs(10)),
            wraplength=px(320),
            justify="left",
        )
        self.subtitle_label.pack(anchor="w", pady=(px(10), px(18)))

        self.open_label = tk.Label(
            body,
            text="Open module  >",
            bg="#181c24",
            fg=accent,
            font=("Segoe UI", fs(10), "bold"),
        )
        self.open_label.pack(anchor="w")

        self._widgets = [self, accent_bar, body] + list(body.winfo_children())

    def resize(self, width: int, compact: bool) -> None:
        self.subtitle_label.configure(wraplength=max(220, width - self.scaler.px(52)))
        self.title_label.configure(
            font=("Segoe UI", self.scaler.fs(15 if compact else 18), "bold"))

    def _on_enter(self, _event=None) -> None:
        if self._hover:
            return
        self._hover = True
        for widget in self._widgets:
            try:
                widget.configure(bg="#262633")
            except tk.TclError:
                pass

    def _on_leave(self, _event=None) -> None:
        self._hover = False
        for widget in self._widgets:
            try:
                if isinstance(widget, tk.Frame) and widget.winfo_height() <= 8:
                    widget.configure(bg=self.accent)
                else:
                    widget.configure(bg="#181c24")
            except tk.TclError:
                pass


class MainApplication:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{APP_TITLE} v{APP_VERSION}")
        self.root.configure(bg="#0d1117")

        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        win_w = min(1440, max(900, int(sw * 0.78)))
        win_h = min(860, max(600, int(sh * 0.78)))
        self.root.geometry(
            f"{win_w}x{win_h}+{(sw - win_w) // 2}+{(sh - win_h) // 2}"
        )
        self.root.minsize(min(820, sw - 40), min(540, sh - 80))

        self.scaler = ResponsiveScaler(root)
        self._open_module_window: Optional[tk.Toplevel] = None
        self.current_user: Optional[auth.AuthenticatedUser] = None
        self._layout_mode = ""

        self._build_ui()
        self.root.after(100, self._startup_flow)

    def _build_ui(self) -> None:
        fs = self.scaler.fs
        px = self.scaler.px
        BG     = "#0d1117"
        HDR_BG = "#0d1117"
        BORDER = "#1e2733"
        CARD   = "#161b22"

        # ── style ttk.Combobox for dark theme ─────────────────────
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Dark.TCombobox",
            fieldbackground="#1e2430",
            background="#1e2430",
            foreground="#e6edf3",
            arrowcolor="#8b93a7",
            selectbackground="#1e2430",
            selectforeground="#e6edf3",
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
            insertcolor="#e6edf3",
        )
        style.map("Dark.TCombobox",
            fieldbackground=[("readonly", "#1e2430"), ("focus", "#1e2430")],
            foreground=[("readonly", "#e6edf3")],
            selectbackground=[("readonly", "#1e2430")],
        )
        self.root.option_add("*TCombobox*Listbox.background", "#1e2430")
        self.root.option_add("*TCombobox*Listbox.foreground", "#e6edf3")
        self.root.option_add("*TCombobox*Listbox.selectBackground", "#2979ff")
        self.root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
        self.root.option_add("*TCombobox*Listbox.font", ("Segoe UI", fs(10)))

        # ── HEADER ────────────────────────────────────────────────
        self.header = tk.Frame(self.root, bg=HDR_BG, padx=px(28), pady=px(20))
        self.header.pack(fill="x")
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x")

        self.title_block = tk.Frame(self.header, bg=HDR_BG)
        # packed by _layout_cards

        self._title_lbl = tk.Label(
            self.title_block, text="KPSC OMR OPERATIONS",
            bg=HDR_BG, fg="#e6edf3",
            font=("Segoe UI", fs(20), "bold")
        )
        self._title_lbl.pack(anchor="w")

        self._subtitle_lbl = tk.Label(
            self.title_block,
            text="Counter Foil & Nominal Roll Processing Workspace",
            bg=HDR_BG, fg="#8b93a7",
            font=("Segoe UI", fs(10))
        )
        self._subtitle_lbl.pack(anchor="w", pady=(px(2), 0))

        self.actions = tk.Frame(self.header, bg=HDR_BG)
        # packed by _layout_cards

        def _hdr_btn(text, command, bg="#21262d", fg="#c9d1d9", abg="#30363d"):
            return tk.Button(
                self.actions, text=text, command=command,
                bg=bg, fg=fg,
                activebackground=abg, activeforeground=fg,
                relief="flat", font=("Segoe UI", fs(9), "bold"),
                padx=px(12), pady=px(5), cursor="hand2",
                bd=0, highlightthickness=0
            )

        self.database_btn    = _hdr_btn("Database",     self._open_database_settings)
        self.user_master_btn = _hdr_btn("Users",        self._open_user_master)
        self.audit_export_btn = _hdr_btn("Audit Export", self._export_audit_logs)
        self.logout_btn      = _hdr_btn("Logout",       self._logout)
        self.exit_btn        = _hdr_btn("Exit",         self.root.destroy,
                                        bg="#3a2028", fg="#ffb4ab", abg="#4a2830")

        for btn in (self.database_btn, self.user_master_btn,
                    self.logout_btn, self.exit_btn):
            btn.pack(side="left", padx=(0, px(6)))
        self.user_master_btn.config(state="disabled")

        # ── CENTRE (full expand area) ─────────────────────────────
        self.center = tk.Frame(self.root, bg=BG)
        self.center.pack(fill="both", expand=True)

        # ── LAUNCH PANEL (centred card) ───────────────────────────
        self.launch_panel = tk.Frame(
            self.center,
            bg=CARD,
            highlightthickness=1,
            highlightbackground="#30363d",
        )
        # placed via _layout_cards

        # Panel header bar
        panel_hdr = tk.Frame(self.launch_panel, bg="#1c2230")
        panel_hdr.pack(fill="x")
        tk.Frame(self.launch_panel, bg="#2979ff", height=2).pack(fill="x")

        tk.Label(
            panel_hdr, text="  Quick Launch",
            bg="#1c2230", fg="#e6edf3",
            font=("Segoe UI", fs(12), "bold"),
            pady=px(12)
        ).pack(side="left")

        # Panel body
        panel_body = tk.Frame(self.launch_panel, bg=CARD, padx=px(28), pady=px(24))
        panel_body.pack(fill="both", expand=True)

        # ── Helper: one labelled row with dropdown + Open button ──
        def _combo_row(parent, label_text, var_name, values, on_select):
            tk.Label(
                parent, text=label_text,
                bg=CARD, fg="#8b93a7",
                font=("Segoe UI", fs(9), "bold"),
                anchor="w"
            ).pack(anchor="w", pady=(0, px(4)))

            row = tk.Frame(parent, bg=CARD)
            row.pack(fill="x", pady=(0, px(18)))

            var = tk.StringVar()
            setattr(self, var_name, var)

            combo = ttk.Combobox(
                row, textvariable=var,
                values=values,
                state="readonly",
                style="Dark.TCombobox",
                font=("Segoe UI", fs(11)),
            )
            combo.set("Select...")
            combo.pack(side="left", fill="x", expand=True, ipady=px(5))

            open_btn = tk.Button(
                row, text="Open",
                command=on_select,
                bg="#2979ff", fg="#ffffff",
                activebackground="#1565c0", activeforeground="#ffffff",
                relief="flat", font=("Segoe UI", fs(10), "bold"),
                padx=px(18), pady=px(6), cursor="hand2",
                bd=0, highlightthickness=0
            )
            open_btn.pack(side="left", padx=(px(10), 0))

            combo.bind("<<ComboboxSelected>>", lambda e: on_select())

            return combo, open_btn

        # Divider helper
        def _divider():
            tk.Frame(panel_body, bg=BORDER, height=1).pack(fill="x", pady=(0, px(18)))

        # ── ROW 1: Data Extraction ────────────────────────────────
        self._extract_combo, self._extract_open_btn = _combo_row(
            panel_body,
            "DATA EXTRACTION",
            "extraction_type_var",
            ["OMR Ink Detection", "Counter Foil Scanning", "Nominal Rolls Scanning"],
            self._on_extraction_type_selected,
        )

        _divider()

        # ── ROW 2: Discrepancies ─────────────────────────────────
        self._disc_combo, self._disc_open_btn = _combo_row(
            panel_body,
            "Edit Extracted Data",
            "discrepancy_var",
            [
                "Counter Foil Data Edit",
                "Nominal Roll 1 Data Edit",
                "Nominal Roll 2 Data Edit"
            ],
            self._on_discrepancy_selected,
        )

        # ── ROW 3: Download Reports (Audit Export + Discrepancy Reports)
        self._download_combo, self._download_open_btn = _combo_row(
            panel_body,
            "DOWNLOAD REPORTS",
            "download_reports_var",
            ["Audit Export", "Discrepancy Reports","All Discrepancy Generation"],
            self._on_download_report_selected,
        )

        # ── FOOTER ────────────────────────────────────────────────
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x")
        self.footer = tk.Frame(self.root, bg=BG, padx=px(28), pady=px(10))
        self.footer.pack(fill="x", side="bottom")

        self.db_status_lbl = tk.Label(
            self.footer, text="Database: checking...",
            bg=BG, fg="#8b93a7",
            font=("Segoe UI", fs(9)), anchor="w"
        )
        self.db_status_lbl.pack(side="left")

        tk.Frame(self.footer, bg=BORDER, width=1).pack(
            side="left", fill="y", padx=px(14))

        self.user_status_lbl = tk.Label(
            self.footer, text="Not logged in",
            bg=BG, fg="#8b93a7",
            font=("Segoe UI", fs(9)), anchor="w"
        )
        self.user_status_lbl.pack(side="left")

        tk.Label(
            self.footer, text=f"v{APP_VERSION}",
            bg=BG, fg="#484f58",
            font=("Segoe UI", fs(9))
        ).pack(side="right")

        self.root.bind("<Configure>", self._layout_cards, add="+")
        self.root.after_idle(self._layout_cards)
    def open_all_discrepancy_generation(self):

        if self.current_user is None:
            if not self._show_login():
                return

        win = tk.Toplevel(self.root)

        AllDiscrepancyGeneration(
            win,
            self.current_user.user_id
        )
    def _open_disc_report(self, report_id: int) -> None:
        """Open the DiscrepancyReports window pre-selected on the given report."""
        try:
            ok, error = self._validate_database_connection()
            if not ok:
                raise RuntimeError(error)
        except Exception as exc:
            messagebox.showerror(
                "Database Not Configured",
                f"Configure a working database connection first.\n\n{exc}",
            )
            return
        if self.current_user is None:
            if not self._show_login():
                return

        win = tk.Toplevel(self.root)
        #win.transient(self.root)
        
        win.resizable(True, True)
        win.minsize(800, 600)

        import DiscrepancyReports as _dr_mod
        _dr_mod.LOGGED_USER_ID = self.current_user.user_id if self.current_user else 1
        audit.log("application", "module_open",
                  details={"module": "DiscrepancyReports", "report_id": report_id})
        app = _dr_mod.DiscrepancyReports(win)
        win.lift()
        win.focus_force()
        # Pre-select the specific report after the window is ready
        win.after(250, lambda: app._select_report(report_id))

        def _on_close():
            audit.log("application", "module_close",
                      details={"module": "DiscrepancyReports"})
            win.destroy()

        win.protocol("WM_DELETE_WINDOW", _on_close)

    def _layout_cards(self, event=None) -> None:
        if event is not None and event.widget is not self.root:
            return

        px = self.scaler.px
        fs = self.scaler.fs
        width  = max(1, self.root.winfo_width())
        height = max(1, self.root.winfo_height())
        HDR_BG = "#0d1117"

        # ── Header responsive stacking ────────────────────────────
        compact = width < 1100
        self.title_block.pack_forget()
        self.actions.pack_forget()

        if compact:
            self.header.configure(padx=px(20), pady=px(14))
            self.title_block.pack(fill="x", anchor="w")
            self.actions.pack(fill="x", anchor="w", pady=(px(8), 0))
            self._title_lbl.configure(font=("Segoe UI", fs(15), "bold"))
            self._subtitle_lbl.configure(font=("Segoe UI", fs(9)))
        else:
            self.header.configure(padx=px(28), pady=px(20))
            self.title_block.pack(side="left", anchor="w")
            self.actions.pack(side="right", anchor="e")
            self._title_lbl.configure(font=("Segoe UI", fs(20), "bold"))
            self._subtitle_lbl.configure(font=("Segoe UI", fs(10)))

        # ── Launch panel size & position (responsive) ────────────
        # Compute a target size but place the panel using relative sizing
        panel_w = max(360, min(800, width - px(48)))
        panel_h = max(320, min(int(height * 0.9), int(height * 0.75)))

        relwidth = max(0.5, min(0.98, panel_w / max(1, width)))
        relheight = max(0.35, min(0.95, panel_h / max(1, height)))

        # Place the launch panel responsively so it adapts to window size
        self.launch_panel.place(
            in_=self.center,
            relx=0.5, rely=0.5, anchor="center",
            relwidth=relwidth, relheight=relheight,
        )

        # ── Footer wraplength ─────────────────────────────────────
        self.db_status_lbl.configure(wraplength=max(200, int(width * 0.35)))
        self.user_status_lbl.configure(wraplength=max(160, int(width * 0.25)))

    def _on_extraction_type_selected(self, _event=None) -> None:
        selection = self.extraction_type_var.get()
        if not selection or selection == "Select...":
            return
        # Reset to placeholder after opening
        self.root.after(100, lambda: self.extraction_type_var.set("Select..."))
        if "OMR Ink Detection" in selection:
            self.open_omr_ink_detection()
        elif "Counter Foil" in selection:
            self.open_omr_module()
        elif "Nominal" in selection:
            self.open_attendance_module()

    def _on_discrepancy_selected(self, _event=None) -> None:
        selection = self.discrepancy_var.get()
        if not selection or selection == "Select...":
            return

        self.root.after(100, lambda: self.discrepancy_var.set("Select..."))

        if selection == "Subject Code & Booklet Serial No Discrepancy":
            self.open_subject_booklet_discrepancy()
            return

        if selection == "Counter Foil Data Edit":
            self.CounterFoilDataEdit()
            return

        if selection == "Nominal Roll 1 Data Edit":
            self.NominalRoll1DataEdit()
            return

        if selection == "Nominal Roll 2 Data Edit":
            self.NominalRoll2DataEdit()
            return

        self.open_pending_discrepancy(selection)

    def _on_download_report_selected(self, _event=None) -> None:
        selection = self.download_reports_var.get()
        if not selection or selection == "Select...":
            return

        # Reset to placeholder
        self.root.after(100, lambda: self.download_reports_var.set("Select..."))

        if selection == "Audit Export":
            self._export_audit_logs()
            return

        if selection == "Discrepancy Reports":
            # Open the DiscrepancyReports module
            try:
                ok, error = self._validate_database_connection()
                if not ok:
                    raise RuntimeError(error)
            except Exception as exc:
                messagebox.showerror(
                    "Database Not Configured",
                    f"Configure a working database connection first.\n\n{exc}",
                )
                return

            if self.current_user is None:
                if not self._show_login():
                    return

            win = tk.Toplevel(self.root)
            win.transient(self.root)
            import DiscrepancyReports as _dr_mod
            _dr_mod.LOGGED_USER_ID = self.current_user.user_id if self.current_user else 1
            audit.log("application", "module_open", details={"module": "DiscrepancyReports"})
            app = _dr_mod.DiscrepancyReports(win)
            win.lift()
            win.focus_force()
            def _on_close():
                audit.log("application", "module_close", details={"module": "DiscrepancyReports"})
                win.destroy()
            win.protocol("WM_DELETE_WINDOW", _on_close)
            return
        
        if selection == "All Discrepancy Generation":
            self.open_all_discrepancy_generation()
            return

    def _refresh_db_status(self) -> None:
        try:
            creds = db_credentials.load_credentials()
            self.db_status_lbl.config(
                text=f"Database: {creds['server']} / {creds['database']} (configured)",
                fg="#00e676",
            )
        except Exception as exc:
            self.db_status_lbl.config(
                text=f"Database: not configured ({exc})",
                fg="#ff8a80",
            )

    def _validate_database_connection(self) -> tuple[bool, str]:
        try:
            creds = db_credentials.load_credentials()
            conn = db_credentials.get_sql_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            conn.close()
            self.db_status_lbl.config(
                text=f"Database: {creds['server']} / {creds['database']} (connected)",
                fg="#00e676",
            )
            return True, ""
        except Exception as exc:
            self.db_status_lbl.config(
                text=f"Database: not connected ({exc})",
                fg="#ff8a80",
            )
            return False, str(exc)

    def _ensure_database_setup(self) -> bool:
        while True:
            ok, error = self._validate_database_connection()
            if ok:
                return True

            initial = {}
            try:
                saved = db_credentials.load_credentials()
                initial = {
                    "server": saved.get("server", ""),
                    "database": saved.get("database", ""),
                    "username": saved.get("username", ""),
                }
            except Exception:
                pass

            if error:
                messagebox.showwarning(
                    "Database Setup Required",
                    "The application cannot connect to the configured database.\n"
                    "Please enter valid SQL Server connection details.\n\n"
                    f"Reason: {error}",
                )

            dialog = DatabaseSetupDialog(
                self.root,
                self.scaler,
                initial=initial,
                on_success=self._refresh_db_status,
            )
            self.root.wait_window(dialog)

            if not dialog.result_saved:
                messagebox.showwarning(
                    "Setup Required",
                    "Database configuration must be completed before using the application.",
                )
                return False

    def _startup_flow(self) -> None:
        self.root.deiconify()
        self.root.lift()
        if not self._ensure_database_setup():
            return

        while True:
            try:
                auth.initialize_auth_schema()
                audit.initialize_schema()
                break
            except Exception as exc:
                messagebox.showwarning(
                    "Database Connection Required",
                    "Authentication setup could not reach the database. "
                    "Please verify the connection again.\n\n"
                    f"{exc}",
                )
                if not self._ensure_database_setup():
                    return

        if not auth.admin_exists():
            dialog = AdminSetupDialog(self.root, self.scaler)
            self.root.wait_window(dialog)
            if not dialog.result:
                messagebox.showwarning(
                    "Admin Required",
                    "Create an administrator account before using the application.",
                )
                return
            try:
                data = dialog.result
                data["role"] = "admin"
                data["is_active"] = True
                auth.create_user(**data)
            except Exception as exc:
                messagebox.showerror("Admin Setup Failed", str(exc))
                return

            admin_user = auth.authenticate(data["username"], data["password"])
            if admin_user is None:
                messagebox.showerror("Login Failed", "Admin was created, but login failed.")
                return
            self._set_current_user(admin_user)
            self.root.deiconify()
            self._open_user_master()
            return

        if self._show_login():
            self.root.deiconify()
        else:
            self.root.destroy()

    def _show_login(self) -> bool:
        while True:
            dialog = LoginDialog(self.root, self.scaler)
            self.root.wait_window(dialog)
            if dialog.database_error:
                messagebox.showwarning(
                    "Database Connection Lost",
                    "The application could not connect to the database. "
                    "Please configure the database connection again.\n\n"
                    f"{dialog.database_error}",
                )
                if not self._ensure_database_setup():
                    return False
                continue
            if dialog.user is None:
                return False
            self._set_current_user(dialog.user)
            return True

    def _set_current_user(self, user: auth.AuthenticatedUser) -> None:
        self.current_user = user
        audit.set_user(user.user_id, user.username)
        audit.log("authentication", "login")
        label = user.full_name or user.username
        self.user_status_lbl.config(
            text=f"User: {label} ({user.role})",
            fg="#00e676",
        )
        self.user_master_btn.config(state="normal" if user.is_admin else "disabled")
        # Audit export is now available through the Download Reports combo
        # (do not show header button separately)

    def _logout(self) -> None:
        audit.log("authentication", "logout")
        audit.shutdown()
        audit.set_user(None, None)
        self.current_user = None
        self._open_module_window = None
        self.root.quit()
        self.root.destroy()

    def _open_user_master(self) -> None:
        if not self.current_user or not self.current_user.is_admin:
            messagebox.showerror("Access Denied", "Only administrators can manage users.")
            return
        UserMasterDialog(self.root, self.scaler, self.current_user)

    def _export_audit_logs(self) -> None:
        if not self.current_user or not self.current_user.is_admin:
            return
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Export Audit Logs",
            initialfile="KPSC_Audit_Logs.xlsx",
            defaultextension=".xlsx",
            filetypes=[("Excel Workbook", "*.xlsx")],
        )
        if not path:
            return

        self.audit_export_btn.config(state="disabled", text="Exporting...")

        def export() -> None:
            try:
                count = audit.export_to_excel(path)
                audit.log("authentication", "audit_logs_exported",
                          details={"rows": count, "file": os.path.basename(path)})
                self.root.after(0, lambda: complete(count, None))
            except Exception as exc:
                self.root.after(0, lambda error=str(exc): complete(0, error))

        def complete(count: int, error: Optional[str]) -> None:
            if not self.root.winfo_exists():
                return
            self.audit_export_btn.config(state="normal", text="Export Audit Logs")
            if error:
                messagebox.showerror("Export Failed", error, parent=self.root)
            else:
                messagebox.showinfo(
                    "Export Complete",
                    f"Exported {count:,} audit log records.",
                    parent=self.root,
                )

        threading.Thread(target=export, name="audit-export", daemon=True).start()

    def _open_database_settings(self) -> None:
        initial = {}
        try:
            initial = db_credentials.load_credentials()
            initial = {
                "server": initial.get("server", ""),
                "database": initial.get("database", ""),
                "username": initial.get("username", ""),
            }
        except Exception:
            pass

        DatabaseSetupDialog(
            self.root,
            self.scaler,
            title="Database Settings",
            initial=initial,
            on_success=self._refresh_db_status,
        )

    def _open_module(self, factory: Callable[..., object], title: str, *args: object) -> None:
        if self._open_module_window is not None and self._open_module_window.winfo_exists():
            self._open_module_window.lift()
            self._open_module_window.focus_force()
            return

        try:
            ok, error = self._validate_database_connection()
            if not ok:
                raise RuntimeError(error)
        except Exception as exc:
            messagebox.showerror(
                "Database Not Configured",
                f"Configure a working database connection before opening modules.\n\n{exc}",
            )
            self._ensure_database_setup()
            return
        if self.current_user is None:
            if not self._show_login():
                return

        self.root.withdraw()

        module_root = tk.Toplevel(self.root)
        module_root.title(title)
        self._open_module_window = module_root
        audit.log("application", "module_open", details={"module": title})

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        win_w = int(sw * 0.92)
        win_h = int(sh * 0.90)
        module_root.geometry(
            f"{win_w}x{win_h}+{(sw - win_w) // 2}+{(sh - win_h) // 2}"
        )
        module_root.minsize(max(1024, int(sw * 0.65)), max(620, int(sh * 0.62)))
        module_root.configure(bg="#1a1a22")

        try:
            factory(module_root, *args)
        except Exception as exc:
            audit.log(
                "application",
                "module_open_failed",
                outcome="failed",
                details={"module": title, "error": str(exc)},
            )
            module_root.destroy()
            self._open_module_window = None
            self.root.deiconify()
            self.root.lift()
            messagebox.showerror(
                f"{title} Failed",
                f"The module could not be opened.\n\n{exc}\n\n{traceback.format_exc()}",
                parent=self.root,
            )
            return

        def on_close() -> None:
            audit.log("application", "module_close", details={"module": title})
            self._open_module_window = None
            module_root.destroy()
            self.root.deiconify()
            self.root.lift()

        module_root.protocol("WM_DELETE_WINDOW", on_close)

    def _open_module_from_import(
        self,
        module_name: str,
        class_name: str,
        title: str,
        *args: object,
        configure_module: Optional[Callable[[object], None]] = None,
    ) -> None:
        try:
            module = importlib.import_module(module_name)
            if configure_module is not None:
                configure_module(module)
            factory = getattr(module, class_name)
        except Exception as exc:
            audit.log(
                "application",
                "module_import_failed",
                outcome="failed",
                details={"module": module_name, "error": str(exc)},
            )
            messagebox.showerror(
                f"{title} Failed",
                f"The module could not be loaded.\n\n{exc}\n\n{traceback.format_exc()}",
                parent=self.root,
            )
            return

        self._open_module(factory, title, *args)

    def _open_reports(self) -> None:
        try:
            ok, error = self._validate_database_connection()
            if not ok:
                raise RuntimeError(error)
        except Exception as exc:
            messagebox.showerror(
                "Database Not Configured",
                f"Configure a working database connection before opening Reports.\n\n{exc}",
            )
            return
        if self.current_user is None:
            if not self._show_login():
                return

        win = tk.Toplevel(self.root)
        from DiscrepancyReports import DiscrepancyReports, LOGGED_USER_ID
        import DiscrepancyReports as _dr_mod
        if self.current_user is not None:
            _dr_mod.LOGGED_USER_ID = self.current_user.user_id
        audit.log("application", "module_open",
                  details={"module": "DiscrepancyReports"})
        app = DiscrepancyReports(win)

        def _on_close():
            audit.log("application", "module_close",
                      details={"module": "DiscrepancyReports"})
            win.destroy()

        win.protocol("WM_DELETE_WINDOW", _on_close)

    def open_omr_module(self) -> None:
        self._open_module_from_import(
            "CounterFoilScanning",
            "VisualOMRViewerDemo",
            "Counterfoil Extraction Engine",
        )

    def open_subject_booklet_discrepancy(self) -> None:
        user_id = self.current_user.user_id if self.current_user else 1
        self._open_module_from_import(
            "CounterFoilSubBSNoEdit",
            "SubjectBookletDiscrepancy",
            "Subject Code & Booklet Serial No Discrepancy",
            configure_module=lambda module: setattr(module, "LOGGED_USER_ID", user_id),
        )

    def open_attendance_module(self) -> None:
        self._open_module_from_import(
            "NominalRolls",
            "AttendanceViewerDemo",
            "Nominal Roll Extraction",
        )

    def open_omr_ink_detection(self) -> None:
        user_id = self.current_user.user_id if self.current_user is not None else 1
        self._open_module_from_import(
            "OMRInkDetection",
            "OMRInkDetection",
            "OMR Ink Detection",
            user_id,
        )

    def CounterFoilDataEdit(self) -> None:
        user_id = self.current_user.user_id if self.current_user is not None else 1
        self._open_module_from_import(
            "CounterFoilDataEdit",
            "CounterFoilDataEdit",
            "Counter Foil Data Edit",
            user_id,
        )

    def NominalRoll1DataEdit(self) -> None:
        user_id = self.current_user.user_id if self.current_user is not None else 1
        self._open_module_from_import(
            "NominalRoll1DataEdit",
            "NominalRoll1DataEdit",
            "Nominal Roll 1 Data Edit",
            user_id,
        )

    def NominalRoll2DataEdit(self) -> None:
        user_id = self.current_user.user_id if self.current_user is not None else 1
        self._open_module_from_import(
            "NominalRoll2DataEdit",
            "NominalRoll2DataEdit",
            "Nominal Roll 2 Data Edit",
            user_id,
        )

    def ink_detection(self) -> None:
        user_id = self.current_user.user_id if self.current_user is not None else 1
        self._open_module_from_import(
            "ink_detection",
            "ink_detection",
            "Ink Detection",
            user_id,
        )
    def open_pending_discrepancy(self, title: str) -> None:
        # Add future discrepancy module imports here, for example:
        # from MyDiscrepancyFile import MyDiscrepancyClass
        # self._open_module(MyDiscrepancyClass, title)
        messagebox.showinfo(
            "Discrepancy Module Pending",
            f"{title} is listed and ready to be wired. Add the Python module import and handler in this method when you are ready.",
            parent=self.root,
        )
    def CounterFoilDataEdit(self) -> None:
        user_id = self.current_user.user_id if self.current_user is not None else 1
        self._open_module_from_import(
            "CounterFoilDataEdit",
            "CounterFoilDataEdit",
            "Counter Foil Data Edit",
            user_id,
        )

def main() -> None:
    if sys.platform != "win32":
        messagebox.showerror(
            "Unsupported Platform",
            "This application requires Windows for secure credential storage.",
        )
        sys.exit(1)

    root = tk.Tk()
    try:
        ttk.Style().theme_use("clam")
    except tk.TclError:
        pass

    app = MainApplication(root)
    root.mainloop()


if __name__ == "__main__":
    main()
