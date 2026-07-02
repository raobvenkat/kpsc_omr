IF OBJECT_ID(N'dbo.application_audit_log', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.application_audit_log (
        id BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_application_audit_log PRIMARY KEY,
        occurred_at DATETIME2(3) NOT NULL CONSTRAINT DF_application_audit_log_occurred_at DEFAULT SYSUTCDATETIME(),
        category VARCHAR(24) NOT NULL,
        action VARCHAR(64) NOT NULL,
        outcome VARCHAR(16) NOT NULL,
        user_id INT NULL,
        username NVARCHAR(80) NULL,
        machine_name NVARCHAR(128) NULL,
        details NVARCHAR(2000) NULL
    );
    CREATE INDEX IX_application_audit_log_category_time
        ON dbo.application_audit_log(category, occurred_at DESC);
    CREATE INDEX IX_application_audit_log_user_time
        ON dbo.application_audit_log(user_id, occurred_at DESC) WHERE user_id IS NOT NULL;
END;
