/*
    KPSC OMR database setup script.
    Database: KPSCOMRICRExtraction

    Idempotent setup for a fresh machine or an existing installation:
    no hardcoded MDF/LDF paths, no hardcoded SQL login, robust object checks,
    and best-effort audit-log auto-purge after 31 days.
*/

USE [master];
GO

IF DB_ID(N'KPSCOMRICRExtraction') IS NULL
BEGIN
    CREATE DATABASE [KPSCOMRICRExtraction];
END;
GO

ALTER DATABASE [KPSCOMRICRExtraction] SET AUTO_CLOSE OFF;
ALTER DATABASE [KPSCOMRICRExtraction] SET AUTO_SHRINK OFF;
ALTER DATABASE [KPSCOMRICRExtraction] SET AUTO_UPDATE_STATISTICS ON;
ALTER DATABASE [KPSCOMRICRExtraction] SET PAGE_VERIFY CHECKSUM;
GO

USE [KPSCOMRICRExtraction];
GO

SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

IF OBJECT_ID(N'dbo.app_users', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.app_users (
        id INT IDENTITY(1,1) NOT NULL,
        username NVARCHAR(80) NOT NULL,
        full_name NVARCHAR(160) NULL,
        role NVARCHAR(20) NOT NULL CONSTRAINT DF_app_users_role DEFAULT (N'user'),
        password_salt VARBINARY(32) NOT NULL,
        password_hash VARBINARY(32) NOT NULL,
        is_active BIT NOT NULL CONSTRAINT DF_app_users_is_active DEFAULT (1),
        created_at DATETIME2(0) NOT NULL CONSTRAINT DF_app_users_created_at DEFAULT (SYSUTCDATETIME()),
        updated_at DATETIME2(0) NULL,
        CONSTRAINT PK_app_users PRIMARY KEY CLUSTERED (id ASC),
        CONSTRAINT UX_app_users_username UNIQUE (username),
        CONSTRAINT CK_app_users_role CHECK (role IN (N'admin', N'user'))
    );
END;
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

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.application_audit_log') AND name = N'IX_application_audit_log_category_time')
    CREATE INDEX IX_application_audit_log_category_time ON dbo.application_audit_log(category, occurred_at DESC);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.application_audit_log') AND name = N'IX_application_audit_log_user_time')
    CREATE INDEX IX_application_audit_log_user_time ON dbo.application_audit_log(user_id, occurred_at DESC) WHERE user_id IS NOT NULL;
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.application_audit_log') AND name = N'IX_application_audit_log_purge')
    CREATE INDEX IX_application_audit_log_purge ON dbo.application_audit_log(occurred_at, id);
GO

CREATE OR ALTER PROCEDURE dbo.usp_purge_application_audit_log
    @retention_days INT = 31,
    @batch_size INT = 5000
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    IF @retention_days < 1 THROW 50001, 'retention_days must be at least 1.', 1;
    IF @batch_size < 100 OR @batch_size > 50000 THROW 50002, 'batch_size must be between 100 and 50000.', 1;

    DECLARE @cutoff DATETIME2(3) = DATEADD(DAY, -@retention_days, SYSUTCDATETIME());

    WHILE 1 = 1
    BEGIN
        DELETE TOP (@batch_size)
        FROM dbo.application_audit_log
        WHERE occurred_at < @cutoff;

        IF @@ROWCOUNT = 0 BREAK;
    END;
END;
GO

/* ============================================================
   CounterFoilScanning
   ============================================================ */
IF OBJECT_ID(N'dbo.omr_results', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.omr_results (
        id INT IDENTITY(1,1) NOT NULL,
        filename NVARCHAR(500) NOT NULL,
        barcode NVARCHAR(100) NULL,
        bubble_regno NVARCHAR(50) NULL,
        handwritten_regno NVARCHAR(50) NULL,
        final_regno NVARCHAR(50) NULL,
        discrepancy BIT NULL,
        discrepancy_detail NVARCHAR(MAX) NULL,
        candidate_signed NVARCHAR(10) NULL,
        invigilator_signed NVARCHAR(10) NULL,
        subject_code NVARCHAR(100) NULL,
        BookletSlNo NVARCHAR(100) NULL,
        created_at DATETIME2(0) NULL CONSTRAINT DF_omr_results_created_at DEFAULT (SYSUTCDATETIME()),
        omr_threshold VARCHAR(10) NULL,
        whitenerflag BIT NOT NULL CONSTRAINT DF_omr_results_whitenerflag DEFAULT (0),
        isblack BIT NOT NULL CONSTRAINT DF_omr_results_isblack DEFAULT (0),
        updated_at DATETIME2(0) NULL,
        updated_by INT NULL,
        CONSTRAINT PK_omr_results PRIMARY KEY CLUSTERED (id ASC),
        CONSTRAINT UX_omr_results_filename UNIQUE (filename)
    );
END;
GO

IF COL_LENGTH(N'dbo.omr_results', N'BookletSlNo') IS NULL ALTER TABLE dbo.omr_results ADD BookletSlNo NVARCHAR(100) NULL;
IF COL_LENGTH(N'dbo.omr_results', N'omr_threshold') IS NULL ALTER TABLE dbo.omr_results ADD omr_threshold VARCHAR(10) NULL;
IF COL_LENGTH(N'dbo.omr_results', N'whitenerflag') IS NULL ALTER TABLE dbo.omr_results ADD whitenerflag BIT NOT NULL CONSTRAINT DF_omr_results_whitenerflag DEFAULT (0);
IF COL_LENGTH(N'dbo.omr_results', N'isblack') IS NULL ALTER TABLE dbo.omr_results ADD isblack BIT NOT NULL CONSTRAINT DF_omr_results_isblack DEFAULT (0);
IF COL_LENGTH(N'dbo.omr_results', N'updated_at') IS NULL ALTER TABLE dbo.omr_results ADD updated_at DATETIME2(0) NULL;
IF COL_LENGTH(N'dbo.omr_results', N'updated_by') IS NULL ALTER TABLE dbo.omr_results ADD updated_by INT NULL;
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.omr_results') AND name = N'IX_omr_results_filename')
    CREATE INDEX IX_omr_results_filename ON dbo.omr_results(filename);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.omr_results') AND name = N'IX_omr_results_discrepancy')
    CREATE INDEX IX_omr_results_discrepancy ON dbo.omr_results(discrepancy, id) INCLUDE (filename, barcode, subject_code, BookletSlNo);
GO

CREATE OR ALTER PROCEDURE dbo.InsertOMRResult
    @filename NVARCHAR(500),
    @barcode NVARCHAR(100) = NULL,
    @bubble_regno NVARCHAR(50) = NULL,
    @handwritten_regno NVARCHAR(50) = NULL,
    @final_regno NVARCHAR(50) = NULL,
    @discrepancy BIT = NULL,
    @discrepancy_detail NVARCHAR(MAX) = NULL,
    @candidate_signed NVARCHAR(10) = NULL,
    @invigilator_signed NVARCHAR(10) = NULL,
    @subject_code NVARCHAR(100) = NULL,
    @BookletSlNo NVARCHAR(100) = NULL,
    @omr_threshold VARCHAR(10) = NULL,
    @whitenerflag BIT = 0,
    @isblack BIT = 0
AS
BEGIN
    SET NOCOUNT ON;

    IF NOT EXISTS (SELECT 1 FROM dbo.omr_results WHERE filename = @filename)
    BEGIN
        INSERT INTO dbo.omr_results (
            filename, barcode, bubble_regno, handwritten_regno, final_regno,
            discrepancy, discrepancy_detail, candidate_signed, invigilator_signed,
            subject_code, BookletSlNo, omr_threshold, whitenerflag, isblack
        )
        VALUES (
            @filename, @barcode, @bubble_regno, @handwritten_regno, @final_regno,
            @discrepancy, @discrepancy_detail, @candidate_signed, @invigilator_signed,
            @subject_code, @BookletSlNo, @omr_threshold, @whitenerflag, @isblack
        );
    END;
END;
GO

CREATE OR ALTER PROCEDURE dbo.Sub_CodeAndBookletNoDesc
AS
BEGIN
    SET NOCOUNT ON;

    SELECT id AS ID, filename AS FileName, barcode AS Barcode, subject_code AS Subject_code, BookletSlNo
    FROM dbo.omr_results
    WHERE ISNULL(LTRIM(RTRIM(subject_code)), N'') = N''
       OR ISNULL(LTRIM(RTRIM(BookletSlNo)), N'') = N''
       OR discrepancy = 1
    ORDER BY id DESC;
END;
GO

CREATE OR ALTER PROCEDURE dbo.USP_UpdateCounterFoilEditedData
    @ID INT,
    @Subject_Code NVARCHAR(100),
    @BookletSlNo NVARCHAR(100),
    @UpdatedBy INT = NULL
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    UPDATE dbo.omr_results
    SET subject_code = NULLIF(LTRIM(RTRIM(@Subject_Code)), N''),
        BookletSlNo = NULLIF(LTRIM(RTRIM(@BookletSlNo)), N''),
        updated_by = @UpdatedBy,
        updated_at = SYSUTCDATETIME()
    WHERE id = @ID;

    IF @@ROWCOUNT = 0 THROW 50010, 'Counter Foil record was not found.', 1;
END;
GO

/* ============================================================
   NominalRolls
   ============================================================ */
IF OBJECT_ID(N'dbo.attendance_sheet_data_1', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.attendance_sheet_data_1 (
        id INT IDENTITY(1,1) NOT NULL,
        filename NVARCHAR(500) NOT NULL,
        center_code NVARCHAR(50) NULL,
        subcenter_code NVARCHAR(50) NULL,
        subject_code NVARCHAR(50) NULL,
        invigilator_signed BIT NOT NULL CONSTRAINT DF_attendance_sheet_data_1_invigilator_signed DEFAULT (0),
        row_number INT NOT NULL,
        status NVARCHAR(50) NULL,
        signature_present BIT NOT NULL CONSTRAINT DF_attendance_sheet_data_1_signature_present DEFAULT (0),
        omr_no NVARCHAR(50) NULL,
        registration_no NVARCHAR(50) NULL,
        created_at DATETIME2(0) NOT NULL CONSTRAINT DF_attendance_sheet_data_1_created_at DEFAULT (SYSUTCDATETIME()),
        CONSTRAINT PK_attendance_sheet_data_1 PRIMARY KEY CLUSTERED (id ASC)
    );
END;
GO
IF COL_LENGTH(N'dbo.attendance_sheet_data_1', N'registration_no') IS NULL ALTER TABLE dbo.attendance_sheet_data_1 ADD registration_no NVARCHAR(50) NULL;
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.attendance_sheet_data_1') AND name = N'IX_attendance_sheet_data_1_filename')
    CREATE INDEX IX_attendance_sheet_data_1_filename ON dbo.attendance_sheet_data_1(filename);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.attendance_sheet_data_1') AND name = N'UX_attendance_sheet_data_1_filename_row')
    CREATE UNIQUE INDEX UX_attendance_sheet_data_1_filename_row ON dbo.attendance_sheet_data_1(filename, row_number);
GO

IF OBJECT_ID(N'dbo.attendance_sheet_data2', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.attendance_sheet_data2 (
        id INT IDENTITY(1,1) NOT NULL,
        filename NVARCHAR(500) NOT NULL,
        center_code NVARCHAR(50) NULL,
        subcenter_code NVARCHAR(50) NULL,
        subject_code NVARCHAR(50) NULL,
        invigilator_signed BIT NOT NULL CONSTRAINT DF_attendance_sheet_data2_invigilator_signed DEFAULT (0),
        row_number INT NOT NULL,
        status NVARCHAR(50) NULL,
        signature_present BIT NOT NULL CONSTRAINT DF_attendance_sheet_data2_signature_present DEFAULT (0),
        registration_no NVARCHAR(50) NULL,
        qcab_serial_no NVARCHAR(50) NULL,
        created_at DATETIME2(0) NOT NULL CONSTRAINT DF_attendance_sheet_data2_created_at DEFAULT (SYSUTCDATETIME()),
        CONSTRAINT PK_attendance_sheet_data2 PRIMARY KEY CLUSTERED (id ASC)
    );
END;
GO
IF COL_LENGTH(N'dbo.attendance_sheet_data2', N'qcab_serial_no') IS NULL ALTER TABLE dbo.attendance_sheet_data2 ADD qcab_serial_no NVARCHAR(50) NULL;
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.attendance_sheet_data2') AND name = N'IX_attendance_sheet_data2_filename')
    CREATE INDEX IX_attendance_sheet_data2_filename ON dbo.attendance_sheet_data2(filename);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.attendance_sheet_data2') AND name = N'UX_attendance_sheet_data2_filename_row')
    CREATE UNIQUE INDEX UX_attendance_sheet_data2_filename_row ON dbo.attendance_sheet_data2(filename, row_number);
GO

IF OBJECT_ID(N'dbo.error_log', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.error_log (
        id INT IDENTITY(1,1) NOT NULL,
        source_module NVARCHAR(100) NOT NULL,
        sheet_type NVARCHAR(100) NULL,
        filename NVARCHAR(500) NULL,
        error_message NVARCHAR(MAX) NULL,
        created_at DATETIME2(0) NOT NULL CONSTRAINT DF_error_log_created_at DEFAULT (SYSUTCDATETIME()),
        CONSTRAINT PK_error_log PRIMARY KEY CLUSTERED (id ASC)
    );
END;
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.error_log') AND name = N'IX_error_log_source_module')
    CREATE INDEX IX_error_log_source_module ON dbo.error_log(source_module, created_at DESC);
GO

IF OBJECT_ID(N'dbo.ErrorLog', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.ErrorLog (
        ID INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_ErrorLog PRIMARY KEY,
        ErrorScreen NVARCHAR(200) NULL,
        ErrorModule NVARCHAR(200) NULL,
        ErrorText NVARCHAR(MAX) NULL,
        ErrorTime DATETIME2(0) NOT NULL CONSTRAINT DF_ErrorLog_ErrorTime DEFAULT (SYSUTCDATETIME())
    );
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_insert_attendance_sheet_data_1
    @filename NVARCHAR(500),
    @center_code NVARCHAR(50) = NULL,
    @subcenter_code NVARCHAR(50) = NULL,
    @subject_code NVARCHAR(50) = NULL,
    @invigilator_signed BIT = 0,
    @row_number INT,
    @status NVARCHAR(50) = NULL,
    @signature_present BIT = 0,
    @omr_no NVARCHAR(50) = NULL,
    @registration_no NVARCHAR(50) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    IF EXISTS (SELECT 1 FROM dbo.attendance_sheet_data_1 WHERE filename = @filename AND row_number = @row_number) RETURN;
    INSERT INTO dbo.attendance_sheet_data_1 (filename, center_code, subcenter_code, subject_code, invigilator_signed, row_number, status, signature_present, omr_no, registration_no)
    VALUES (@filename, @center_code, @subcenter_code, @subject_code, @invigilator_signed, @row_number, @status, @signature_present, @omr_no, @registration_no);
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_insert_attendance_sheet_data2
    @filename NVARCHAR(500),
    @center_code NVARCHAR(50) = NULL,
    @subcenter_code NVARCHAR(50) = NULL,
    @subject_code NVARCHAR(50) = NULL,
    @invigilator_signed BIT = 0,
    @row_number INT,
    @status NVARCHAR(50) = NULL,
    @signature_present BIT = 0,
    @registration_no NVARCHAR(50) = NULL,
    @qcab_serial_no NVARCHAR(50) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    IF EXISTS (SELECT 1 FROM dbo.attendance_sheet_data2 WHERE filename = @filename AND row_number = @row_number) RETURN;
    INSERT INTO dbo.attendance_sheet_data2 (filename, center_code, subcenter_code, subject_code, invigilator_signed, row_number, status, signature_present, registration_no, qcab_serial_no)
    VALUES (@filename, @center_code, @subcenter_code, @subject_code, @invigilator_signed, @row_number, @status, @signature_present, @registration_no, @qcab_serial_no);
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_insert_attendance_error_log
    @source_module NVARCHAR(100),
    @sheet_type NVARCHAR(100) = NULL,
    @filename NVARCHAR(500) = NULL,
    @error_message NVARCHAR(MAX) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    INSERT INTO dbo.error_log (source_module, sheet_type, filename, error_message)
    VALUES (@source_module, @sheet_type, @filename, @error_message);
END;
GO

IF OBJECT_ID(N'dbo.ExportReport', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.ExportReport (
        ID INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_ExportReport PRIMARY KEY,
        ReportName NVARCHAR(200) NOT NULL,
        ProcedureName SYSNAME NOT NULL,
        Parametres NVARCHAR(500) NULL,
        IsActive BIT NOT NULL CONSTRAINT DF_ExportReport_IsActive DEFAULT (1),
        CreatedAt DATETIME2(0) NOT NULL CONSTRAINT DF_ExportReport_CreatedAt DEFAULT (SYSUTCDATETIME()),
        CONSTRAINT UX_ExportReport_ReportName UNIQUE (ReportName)
    );
END;
GO

CREATE OR ALTER PROCEDURE dbo.Report_CounterFoilDiscrepancies
AS
BEGIN
    SET NOCOUNT ON;
    SELECT id, filename, barcode, bubble_regno, handwritten_regno, final_regno, discrepancy_detail, subject_code, BookletSlNo, created_at
    FROM dbo.omr_results
    WHERE discrepancy = 1
       OR ISNULL(LTRIM(RTRIM(subject_code)), N'') = N''
       OR ISNULL(LTRIM(RTRIM(BookletSlNo)), N'') = N''
    ORDER BY id DESC;
END;
GO

CREATE OR ALTER PROCEDURE dbo.Report_NominalRollErrors
AS
BEGIN
    SET NOCOUNT ON;
    SELECT source_module, sheet_type, filename, error_message, created_at
    FROM dbo.error_log
    ORDER BY created_at DESC;
END;
GO

IF NOT EXISTS (SELECT 1 FROM dbo.ExportReport WHERE ReportName = N'Counter Foil Discrepancies')
    INSERT INTO dbo.ExportReport (ReportName, ProcedureName, Parametres) VALUES (N'Counter Foil Discrepancies', N'dbo.Report_CounterFoilDiscrepancies', NULL);
GO
IF NOT EXISTS (SELECT 1 FROM dbo.ExportReport WHERE ReportName = N'Nominal Roll Errors')
    INSERT INTO dbo.ExportReport (ReportName, ProcedureName, Parametres) VALUES (N'Nominal Roll Errors', N'dbo.Report_NominalRollErrors', NULL);
GO

USE [msdb];
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
PRINT 'KPSC OMR database setup completed successfully.';
GO
