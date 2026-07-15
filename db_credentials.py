"""
Secure SQL Server credential storage for the KPSC OMR suite.

Credentials are encrypted with Windows DPAPI (user-scoped) and stored in
%APPDATA%\\KPSC_OMR\\db_config.kpsc with a SHA-256 integrity hash.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
from typing import Any, Dict, Optional

DEFAULT_DRIVER = "{ODBC Driver 17 for SQL Server}"
CONFIG_VERSION = 1

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    class _DATA_BLOB(ctypes.Structure):
        _fields_ = [
            ("cbData", wintypes.DWORD),
            ("pbData", ctypes.POINTER(ctypes.c_byte)),
        ]

    _crypt32 = ctypes.windll.crypt32
    _kernel32 = ctypes.windll.kernel32

    def _bytes_to_blob(data: bytes) -> _DATA_BLOB:
        buffer = ctypes.create_string_buffer(data)
        blob = _DATA_BLOB()
        blob.cbData = len(data)
        blob.pbData = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte))
        return blob

    def _blob_to_bytes(blob: _DATA_BLOB) -> bytes:
        return ctypes.string_at(blob.pbData, blob.cbData)

    def _dpapi_encrypt(data: bytes) -> bytes:
        input_blob = _bytes_to_blob(data)
        output_blob = _DATA_BLOB()
        description = ctypes.c_wchar_p("KPSC OMR DB credentials")
        if not _crypt32.CryptProtectData(
            ctypes.byref(input_blob),
            description,
            None,
            None,
            None,
            0,
            ctypes.byref(output_blob),
        ):
            raise OSError("Failed to encrypt credentials with Windows DPAPI.")
        try:
            return _blob_to_bytes(output_blob)
        finally:
            _kernel32.LocalFree(output_blob.pbData)

    def _dpapi_decrypt(data: bytes) -> bytes:
        input_blob = _bytes_to_blob(data)
        output_blob = _DATA_BLOB()
        if not _crypt32.CryptUnprotectData(
            ctypes.byref(input_blob),
            None,
            None,
            None,
            None,
            0,
            ctypes.byref(output_blob),
        ):
            raise OSError("Failed to decrypt credentials. Re-run database setup.")
        try:
            return _blob_to_bytes(output_blob)
        finally:
            _kernel32.LocalFree(output_blob.pbData)

else:
    def _dpapi_encrypt(data: bytes) -> bytes:
        raise OSError("Secure credential storage is supported on Windows only.")

    def _dpapi_decrypt(data: bytes) -> bytes:
        raise OSError("Secure credential storage is supported on Windows only.")


#def get_config_dir() -> str:
#    appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
#    return os.path.join(appdata, "KPSC_OMR")

def get_config_dir() -> str:
    appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(appdata, "KPSC_OMR")


def get_config_path() -> str:
    return os.path.join(get_config_dir(), "db_config.kpsc")


def credentials_exist() -> bool:
    return os.path.isfile(get_config_path())


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def save_credentials(
    server: str,
    database: str,
    username: str,
    password: str,
    driver: str = DEFAULT_DRIVER,
) -> None:
    payload = {
        "version": CONFIG_VERSION,
        "driver": driver.strip() or DEFAULT_DRIVER,
        "server": server.strip(),
        "database": database.strip(),
        "username": username.strip(),
        "password": password,
    }

    if not all(payload[key] for key in ("server", "database", "username", "password")):
        raise ValueError("Server, database, username, and password are required.")

    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    encrypted = _dpapi_encrypt(raw)
    digest = _sha256_hex(encrypted)
    encoded = base64.b64encode(encrypted).decode("ascii")

    config_dir = get_config_dir()
    os.makedirs(config_dir, exist_ok=True)

    config_path = get_config_path()
    with open(config_path, "w", encoding="utf-8") as handle:
        handle.write(f"v{CONFIG_VERSION}\n")
        handle.write(f"{encoded}\n")
        handle.write(f"{digest}\n")


def load_credentials() -> Dict[str, Any]:
    config_path = get_config_path()
    if not os.path.isfile(config_path):
        raise FileNotFoundError("Database configuration has not been set up yet.")

    with open(config_path, "r", encoding="utf-8") as handle:
        lines = [line.strip() for line in handle.readlines() if line.strip()]

    if len(lines) != 3:
        raise ValueError("Database configuration file is corrupt.")

    version_line, encoded, digest = lines
    if version_line != f"v{CONFIG_VERSION}":
        raise ValueError("Unsupported database configuration version.")

    encrypted = base64.b64decode(encoded.encode("ascii"))
    if _sha256_hex(encrypted) != digest:
        raise ValueError("Database configuration integrity check failed.")

    raw = _dpapi_decrypt(encrypted)
    payload = json.loads(raw.decode("utf-8"))

    required = ("server", "database", "username", "password", "driver")
    if not all(payload.get(key) for key in required):
        raise ValueError("Database configuration is incomplete.")

    return payload


def build_connection_string(creds: Optional[Dict[str, Any]] = None) -> str:
    if creds is None:
        creds = load_credentials()

    return (
        f"DRIVER={creds['driver']};"
        f"SERVER={creds['server']};"
        f"DATABASE={creds['database']};"
        f"UID={creds['username']};"
        f"PWD={creds['password']};"
        "TrustServerCertificate=yes;"
    )


def get_sql_connection():
    import pyodbc

    return pyodbc.connect(build_connection_string())


def test_connection(
    server: str,
    database: str,
    username: str,
    password: str,
    driver: str = DEFAULT_DRIVER,
) -> None:
    import pyodbc

    conn_str = (
        f"DRIVER={driver};"
        f"SERVER={server.strip()};"
        f"DATABASE={database.strip()};"
        f"UID={username.strip()};"
        f"PWD={password};"
        "TrustServerCertificate=yes;"
        f"Connection Timeout=8;"
    )
    conn = pyodbc.connect(conn_str, timeout=8)
    cursor = conn.cursor()
    cursor.execute("SELECT 1")
    cursor.fetchone()
    conn.close()


def delete_credentials() -> None:
    config_path = get_config_path()
    if os.path.isfile(config_path):
        os.remove(config_path)
