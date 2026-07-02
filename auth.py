from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass
from typing import List, Optional

from db_credentials import get_sql_connection


PBKDF2_ITERATIONS = 260000


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: int
    username: str
    full_name: str
    role: str

    @property
    def is_admin(self) -> bool:
        return self.role.lower() == "admin"


def hash_password(password: str, salt: Optional[bytes] = None) -> tuple[bytes, bytes]:
    if salt is None:
        salt = os.urandom(32)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
        dklen=32,
    )
    return salt, digest


def verify_password(password: str, salt: bytes, expected_hash: bytes) -> bool:
    _, actual_hash = hash_password(password, salt)
    return hmac.compare_digest(actual_hash, expected_hash)


def initialize_auth_schema() -> None:
    conn = get_sql_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
        IF OBJECT_ID(N'dbo.app_users', N'U') IS NULL
        BEGIN
            CREATE TABLE dbo.app_users (
                id INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_app_users PRIMARY KEY,
                username NVARCHAR(80) NOT NULL,
                full_name NVARCHAR(160) NULL,
                role NVARCHAR(20) NOT NULL CONSTRAINT DF_app_users_role DEFAULT ('user'),
                password_salt VARBINARY(32) NOT NULL,
                password_hash VARBINARY(32) NOT NULL,
                is_active BIT NOT NULL CONSTRAINT DF_app_users_is_active DEFAULT (1),
                created_at DATETIME2(0) NOT NULL CONSTRAINT DF_app_users_created_at DEFAULT (SYSUTCDATETIME()),
                updated_at DATETIME2(0) NULL,
                CONSTRAINT UX_app_users_username UNIQUE (username),
                CONSTRAINT CK_app_users_role CHECK (role IN ('admin', 'user'))
            );
        END
        """)
        conn.commit()
    finally:
        conn.close()


def admin_exists() -> bool:
    initialize_auth_schema()
    conn = get_sql_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM dbo.app_users WHERE role = 'admin' AND is_active = 1"
        )
        return cursor.fetchone()[0] > 0
    finally:
        conn.close()


def create_user(
    username: str,
    password: str,
    *,
    full_name: str = "",
    role: str = "user",
    is_active: bool = True,
) -> int:
    username = username.strip()
    full_name = full_name.strip()
    role = role.strip().lower()
    if not username:
        raise ValueError("Username is required.")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")
    if role not in {"admin", "user"}:
        raise ValueError("Role must be admin or user.")

    salt, digest = hash_password(password)
    conn = get_sql_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO dbo.app_users (
                username, full_name, role, password_salt, password_hash, is_active
            )
            OUTPUT INSERTED.id
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            username,
            full_name,
            role,
            salt,
            digest,
            int(is_active),
        )
        user_id = int(cursor.fetchone()[0])
        conn.commit()
        return user_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def authenticate(username: str, password: str) -> Optional[AuthenticatedUser]:
    initialize_auth_schema()
    conn = get_sql_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, username, full_name, role, password_salt, password_hash
            FROM dbo.app_users
            WHERE username = ? AND is_active = 1
            """,
            username.strip(),
        )
        row = cursor.fetchone()
        if not row:
            return None
        if not verify_password(password, bytes(row.password_salt), bytes(row.password_hash)):
            return None
        return AuthenticatedUser(
            user_id=int(row.id),
            username=str(row.username),
            full_name=str(row.full_name or ""),
            role=str(row.role),
        )
    finally:
        conn.close()


def list_users() -> List[dict]:
    initialize_auth_schema()
    conn = get_sql_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, full_name, role, is_active, created_at, updated_at
            FROM dbo.app_users
            ORDER BY username
        """)
        users = []
        for row in cursor.fetchall():
            users.append({
                "id": int(row.id),
                "username": str(row.username),
                "full_name": str(row.full_name or ""),
                "role": str(row.role),
                "is_active": bool(row.is_active),
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            })
        return users
    finally:
        conn.close()


def update_user(
    user_id: int,
    *,
    username: str,
    full_name: str,
    role: str,
    is_active: bool,
    password: str = "",
) -> None:
    username = username.strip()
    role = role.strip().lower()
    if not username:
        raise ValueError("Username is required.")
    if role not in {"admin", "user"}:
        raise ValueError("Role must be admin or user.")
    if password and len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")

    conn = get_sql_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role, is_active FROM dbo.app_users WHERE id = ?",
            int(user_id),
        )
        existing = cursor.fetchone()
        if not existing:
            raise ValueError("User not found.")
        if str(existing.role) == "admin" and bool(existing.is_active):
            if role != "admin" or not is_active:
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM dbo.app_users
                    WHERE role = 'admin' AND is_active = 1 AND id <> ?
                    """,
                    int(user_id),
                )
                if cursor.fetchone()[0] == 0:
                    raise ValueError("At least one active administrator is required.")

        if password:
            salt, digest = hash_password(password)
            cursor.execute(
                """
                UPDATE dbo.app_users
                SET username = ?, full_name = ?, role = ?, is_active = ?,
                    password_salt = ?, password_hash = ?, updated_at = SYSUTCDATETIME()
                WHERE id = ?
                """,
                username,
                full_name.strip(),
                role,
                int(is_active),
                salt,
                digest,
                int(user_id),
            )
        else:
            cursor.execute(
                """
                UPDATE dbo.app_users
                SET username = ?, full_name = ?, role = ?, is_active = ?,
                    updated_at = SYSUTCDATETIME()
                WHERE id = ?
                """,
                username,
                full_name.strip(),
                role,
                int(is_active),
                int(user_id),
            )
        if cursor.rowcount == 0:
            raise ValueError("User not found.")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def delete_user(user_id: int) -> None:
    conn = get_sql_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role, is_active FROM dbo.app_users WHERE id = ?",
            int(user_id),
        )
        existing = cursor.fetchone()
        if not existing:
            raise ValueError("User not found.")
        if str(existing.role) == "admin" and bool(existing.is_active):
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM dbo.app_users
                WHERE role = 'admin' AND is_active = 1 AND id <> ?
                """,
                int(user_id),
            )
            if cursor.fetchone()[0] == 0:
                raise ValueError("At least one active administrator is required.")

        cursor.execute(
            "DELETE FROM dbo.app_users WHERE id = ?",
            int(user_id),
        )
        if cursor.rowcount == 0:
            raise ValueError("User not found.")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
