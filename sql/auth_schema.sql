/*
    Application authentication schema for KPSC OMR suite.
    Passwords are stored as PBKDF2-HMAC-SHA256 hashes with per-user salts.
*/

SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

IF OBJECT_ID(N'dbo.app_users', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.app_users (
        id              INT IDENTITY(1,1) NOT NULL,
        username        NVARCHAR(80)      NOT NULL,
        full_name       NVARCHAR(160)     NULL,
        role            NVARCHAR(20)      NOT NULL CONSTRAINT DF_app_users_role DEFAULT ('user'),
        password_salt   VARBINARY(32)     NOT NULL,
        password_hash   VARBINARY(32)     NOT NULL,
        is_active       BIT               NOT NULL CONSTRAINT DF_app_users_is_active DEFAULT (1),
        created_at      DATETIME2(0)      NOT NULL CONSTRAINT DF_app_users_created_at DEFAULT (SYSUTCDATETIME()),
        updated_at      DATETIME2(0)      NULL,
        CONSTRAINT PK_app_users PRIMARY KEY CLUSTERED (id ASC),
        CONSTRAINT UX_app_users_username UNIQUE (username),
        CONSTRAINT CK_app_users_role CHECK (role IN ('admin', 'user'))
    );
END;
GO

PRINT 'Application authentication schema created successfully.';
GO
