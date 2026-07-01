"""
KPSC OMR & Attendance Suite — production launcher.

First launch prompts for SQL Server connection details, stores them securely,
then presents a hub to open OMR Sheets or Attendance Sheets extraction tools.
"""

from __future__ import annotations

import os
import sys
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, Optional

try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    BASE_DIR = os.getcwd()

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import db_credentials


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
        super().__init__(parent, bg="#1f1f2a", highlightthickness=0)
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

        accent_bar = tk.Frame(self, bg=accent, height=px(4))
        accent_bar.pack(fill="x", side="top")

        body = tk.Frame(self, bg="#1f1f2a", padx=px(24), pady=px(22))
        body.pack(fill="both", expand=True)
        for widget in (self, body):
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)
            widget.bind("<Button-1>", lambda _e: command())

        tk.Label(
            body,
            text=title,
            bg="#1f1f2a",
            fg="#ffffff",
            font=("Segoe UI", fs(18), "bold"),
        ).pack(anchor="w")

        tk.Label(
            body,
            text=subtitle,
            bg="#1f1f2a",
            fg="#9aa0b4",
            font=("Segoe UI", fs(10)),
            wraplength=px(320),
            justify="left",
        ).pack(anchor="w", pady=(px(10), px(16)))

        tk.Label(
            body,
            text="Open module →",
            bg="#1f1f2a",
            fg=accent,
            font=("Segoe UI", fs(10), "bold"),
        ).pack(anchor="w")

        self._widgets = [self, accent_bar, body] + list(body.winfo_children())

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
                    widget.configure(bg="#1f1f2a")
            except tk.TclError:
                pass


class MainApplication:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{APP_TITLE} v{APP_VERSION}")
        self.root.configure(bg="#101018")

        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        win_w = int(sw * 0.72)
        win_h = int(sh * 0.72)
        self.root.geometry(
            f"{win_w}x{win_h}+{(sw - win_w) // 2}+{(sh - win_h) // 2}"
        )
        self.root.minsize(max(900, int(sw * 0.5)), max(560, int(sh * 0.5)))

        self.scaler = ResponsiveScaler(root)
        self._open_module_window: Optional[tk.Toplevel] = None

        self._build_ui()
        self.root.after(100, self._ensure_database_setup)

    def _build_ui(self) -> None:
        fs = self.scaler.fs
        px = self.scaler.px

        self.header = tk.Frame(self.root, bg="#101018", padx=px(32), pady=px(22))
        self.header.pack(fill="x")

        title_block = tk.Frame(self.header, bg="#101018")
        title_block.pack(side="left")

        tk.Label(
            title_block,
            text=APP_TITLE,
            bg="#101018",
            fg="#ffffff",
            font=("Segoe UI", fs(22), "bold"),
        ).pack(anchor="w")

        tk.Label(
            title_block,
            text="Production hub for OMR and Attendance sheet extraction",
            bg="#101018",
            fg="#8b93a7",
            font=("Segoe UI", fs(10)),
        ).pack(anchor="w", pady=(px(4), 0))

        actions = tk.Frame(self.header, bg="#101018")
        actions.pack(side="right")

        tk.Button(
            actions,
            text="Database Settings",
            command=self._open_database_settings,
            bg="#24242f",
            fg="#ffffff",
            activebackground="#323242",
            activeforeground="#ffffff",
            relief="flat",
            font=("Segoe UI", fs(10), "bold"),
            padx=px(14),
            pady=px(6),
            cursor="hand2",
        ).pack(side="left", padx=(0, px(8)))

        tk.Button(
            actions,
            text="Exit",
            command=self.root.destroy,
            bg="#3a2028",
            fg="#ffb4ab",
            activebackground="#4a2830",
            activeforeground="#ffb4ab",
            relief="flat",
            font=("Segoe UI", fs(10), "bold"),
            padx=px(14),
            pady=px(6),
            cursor="hand2",
        ).pack(side="left")

        self.center = tk.Frame(self.root, bg="#101018")
        self.center.pack(fill="both", expand=True, padx=px(40), pady=(0, px(24)))

        cards = tk.Frame(self.center, bg="#101018")
        cards.place(relx=0.5, rely=0.46, anchor="center")

        self.omr_card = ModuleCard(
            cards,
            self.scaler,
            title="Counter Foil Sheets",
            subtitle=(
                "Extract barcode, bubble responses, handwritten register numbers, "
                "signatures, and QCA booklet data from Counter Foil sheets."
            ),
            accent="#00c853",
            command=self.open_omr_module,
        )
        self.omr_card.grid(row=0, column=0, padx=px(16), pady=px(12), sticky="nsew")

        self.attendance_card = ModuleCard(
            cards,
            self.scaler,
            title="Nominal Roll  Sheets",
            subtitle=(
                "Process Nominal Roll Sheet Type 1 (OMR) and Type 2 (QCAB), "
                "validate invigilator signatures, and export to SQL Server."
            ),
            accent="#2979ff",
            command=self.open_attendance_module,
        )
        self.attendance_card.grid(row=0, column=1, padx=px(16), pady=px(12), sticky="nsew")

        cards.grid_columnconfigure(0, weight=1)
        cards.grid_columnconfigure(1, weight=1)

        self.footer = tk.Frame(self.root, bg="#101018", padx=px(32), pady=px(16))
        self.footer.pack(fill="x", side="bottom")

        self.db_status_lbl = tk.Label(
            self.footer,
            text="Database: checking…",
            bg="#101018",
            fg="#8b93a7",
            font=("Segoe UI", fs(9)),
            anchor="w",
        )
        self.db_status_lbl.pack(side="left")

        tk.Label(
            self.footer,
            text=f"v{APP_VERSION}",
            bg="#101018",
            fg="#555d70",
            font=("Segoe UI", fs(9)),
        ).pack(side="right")

        self.root.bind("<Configure>", self._layout_cards, add="+")

    def _layout_cards(self, event=None) -> None:
        if event is not None and event.widget is not self.root:
            return

        px = self.scaler.px
        card_w = max(px(300), int(self.root.winfo_width() * 0.28))
        card_h = max(px(220), int(self.root.winfo_height() * 0.34))

        for card in (self.omr_card, self.attendance_card):
            card.configure(width=card_w, height=card_h)
            card.pack_propagate(False)

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

    def _ensure_database_setup(self) -> None:
        if db_credentials.credentials_exist():
            self._refresh_db_status()
            return

        dialog = DatabaseSetupDialog(
            self.root,
            self.scaler,
            on_success=self._refresh_db_status,
        )
        self.root.wait_window(dialog)

        if not db_credentials.credentials_exist():
            messagebox.showwarning(
                "Setup Required",
                "Database configuration was not completed.\n"
                "Modules that write to SQL Server will not work until setup is finished.",
            )
        self._refresh_db_status()

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

    def _open_module(self, factory: Callable[[tk.Misc], object], title: str) -> None:
        if self._open_module_window is not None and self._open_module_window.winfo_exists():
            self._open_module_window.lift()
            self._open_module_window.focus_force()
            return

        try:
            db_credentials.load_credentials()
        except Exception as exc:
            messagebox.showerror(
                "Database Not Configured",
                f"Configure the database before opening modules.\n\n{exc}",
            )
            self._open_database_settings()
            return

        self.root.withdraw()

        module_root = tk.Toplevel(self.root)
        module_root.title(title)
        self._open_module_window = module_root

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        win_w = int(sw * 0.92)
        win_h = int(sh * 0.90)
        module_root.geometry(
            f"{win_w}x{win_h}+{(sw - win_w) // 2}+{(sh - win_h) // 2}"
        )
        module_root.minsize(max(1024, int(sw * 0.65)), max(620, int(sh * 0.62)))
        module_root.configure(bg="#1a1a22")

        factory(module_root)

        def on_close() -> None:
            self._open_module_window = None
            module_root.destroy()
            self.root.deiconify()
            self.root.lift()

        module_root.protocol("WM_DELETE_WINDOW", on_close)

    def open_omr_module(self) -> None:
        from CounterFoilScanning import VisualOMRViewerDemo

        self._open_module(
            VisualOMRViewerDemo,
            "OMR ICR OCR Extraction Engine",
        )

    def open_attendance_module(self) -> None:
        from NominalRolls import AttendanceViewerDemo

        self._open_module(
            AttendanceViewerDemo,
            "Attendance Sheet Extraction",
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
