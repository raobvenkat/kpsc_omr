/*
    Application audit schema for KPSC OMR suite.
    Run this script in the application database.

    The SQL Server Agent job is optional. It is created only when SQL Server
    Agent is available and the executing account has permission in msdb.
    SQL Server Express does not include SQL Server Agent; in that case the
    purge procedure can be run manually or through Windows Task Scheduler/sqlcmd.
*/

SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

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
END;
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID(N'dbo.application_audit_log')
      AND name = N'IX_application_audit_log_category_time'
)
BEGIN
    CREATE INDEX IX_application_audit_log_category_time
        ON dbo.application_audit_log(category, occurred_at DESC);
END;
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID(N'dbo.application_audit_log')
      AND name = N'IX_application_audit_log_user_time'
)
BEGIN
    CREATE INDEX IX_application_audit_log_user_time
        ON dbo.application_audit_log(user_id, occurred_at DESC)
        WHERE user_id IS NOT NULL;
END;
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID(N'dbo.application_audit_log')
      AND name = N'IX_application_audit_log_purge'
)
BEGIN
    CREATE INDEX IX_application_audit_log_purge
        ON dbo.application_audit_log(occurred_at, id);
END;
GO

CREATE OR ALTER PROCEDURE dbo.usp_purge_application_audit_log
    @retention_days INT = 31,
    @batch_size INT = 5000
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    IF @retention_days < 1
        THROW 50001, 'retention_days must be at least 1.', 1;

    IF @batch_size < 100 OR @batch_size > 50000
        THROW 50002, 'batch_size must be between 100 and 50000.', 1;

    DECLARE @cutoff DATETIME2(3) = DATEADD(DAY, -@retention_days, SYSUTCDATETIME());

    WHILE 1 = 1
    BEGIN
        DELETE TOP (@batch_size)
        FROM dbo.application_audit_log
        WHERE occurred_at < @cutoff;

        IF @@ROWCOUNT = 0
            BREAK;
    END;
END;
GO

USE msdb;
GO

BEGIN TRY
    IF EXISTS (SELECT 1 FROM msdb.dbo.syssubsystems WHERE subsystem = N'TSQL')
       AND NOT EXISTS (SELECT 1 FROM msdb.dbo.sysjobs WHERE name = N'KPSC OMR - Purge Audit Logs')
    BEGIN
        EXEC msdb.dbo.sp_add_job
            @job_name = N'KPSC OMR - Purge Audit Logs',
            @enabled = 1,
            @description = N'Deletes KPSC OMR application audit logs older than 31 days.';

        EXEC msdb.dbo.sp_add_jobstep
            @job_name = N'KPSC OMR - Purge Audit Logs',
            @step_name = N'Purge old audit rows',
            @subsystem = N'TSQL',
            @database_name = N'KPSCOMRICRExtraction',
            @command = N'EXEC dbo.usp_purge_application_audit_log @retention_days = 31, @batch_size = 5000;',
            @retry_attempts = 2,
            @retry_interval = 5;

        EXEC msdb.dbo.sp_add_schedule
            @schedule_name = N'KPSC OMR - Daily Audit Purge',
            @enabled = 1,
            @freq_type = 4,
            @freq_interval = 1,
            @active_start_time = 020000;

        EXEC msdb.dbo.sp_attach_schedule
            @job_name = N'KPSC OMR - Purge Audit Logs',
            @schedule_name = N'KPSC OMR - Daily Audit Purge';

        EXEC msdb.dbo.sp_add_jobserver
            @job_name = N'KPSC OMR - Purge Audit Logs';
    END;
END TRY
BEGIN CATCH
    PRINT 'Audit purge SQL Server Agent job was not created. This is expected on SQL Server Express or without msdb job permissions.';
    PRINT ERROR_MESSAGE();
END CATCH;
GO

USE [KPSCOMRICRExtraction];
GO

PRINT 'Application audit schema and retention purge setup completed.';
GO
