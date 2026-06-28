/*
    Attendance Sheets database schema for KPSCOMRICRExtraction
    Run this script in SSMS against the same database used by OMR_Sheets.py

    Database : KPSCOMRICRExtraction
    Tables   : attendance_sheet_data_1, attendance_sheet_data2, error_log
*/

USE [KPSCOMRICRExtraction];
GO

SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

/* ============================================================
   TABLE: attendance_sheet_data_1  (Attendance Sheet 1 / OMR)
   ============================================================ */
IF OBJECT_ID(N'dbo.attendance_sheet_data_1', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.attendance_sheet_data_1 (
        id                  INT IDENTITY(1,1) NOT NULL,
        filename            NVARCHAR(500)     NOT NULL,
        center_code         NVARCHAR(50)      NULL,
        subcenter_code      NVARCHAR(50)      NULL,
        subject_code        NVARCHAR(50)      NULL,
        invigilator_signed  BIT               NOT NULL CONSTRAINT DF_attendance_sheet_data_1_invigilator_signed DEFAULT (0),
        row_number          INT               NOT NULL,
        status              NVARCHAR(50)      NULL,
        signature_present   BIT               NOT NULL CONSTRAINT DF_attendance_sheet_data_1_signature_present DEFAULT (0),
        omr_no              NVARCHAR(50)      NULL,
        created_at          DATETIME2(0)      NOT NULL CONSTRAINT DF_attendance_sheet_data_1_created_at DEFAULT (SYSUTCDATETIME()),
        CONSTRAINT PK_attendance_sheet_data_1 PRIMARY KEY CLUSTERED (id ASC)
    );

    CREATE NONCLUSTERED INDEX IX_attendance_sheet_data_1_filename
        ON dbo.attendance_sheet_data_1 (filename ASC);

    CREATE UNIQUE NONCLUSTERED INDEX UX_attendance_sheet_data_1_filename_row
        ON dbo.attendance_sheet_data_1 (filename ASC, row_number ASC);
END;
GO

/* ============================================================
   TABLE: attendance_sheet_data2  (Attendance Sheet 2 / QCAB)
   ============================================================ */
IF OBJECT_ID(N'dbo.attendance_sheet_data2', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.attendance_sheet_data2 (
        id                  INT IDENTITY(1,1) NOT NULL,
        filename            NVARCHAR(500)     NOT NULL,
        center_code         NVARCHAR(50)      NULL,
        subcenter_code      NVARCHAR(50)      NULL,
        subject_code        NVARCHAR(50)      NULL,
        invigilator_signed  BIT               NOT NULL CONSTRAINT DF_attendance_sheet_data2_invigilator_signed DEFAULT (0),
        row_number          INT               NOT NULL,
        status              NVARCHAR(50)      NULL,
        signature_present   BIT               NOT NULL CONSTRAINT DF_attendance_sheet_data2_signature_present DEFAULT (0),
        registration_no     NVARCHAR(50)      NULL,
        created_at          DATETIME2(0)      NOT NULL CONSTRAINT DF_attendance_sheet_data2_created_at DEFAULT (SYSUTCDATETIME()),
        CONSTRAINT PK_attendance_sheet_data2 PRIMARY KEY CLUSTERED (id ASC)
    );

    CREATE NONCLUSTERED INDEX IX_attendance_sheet_data2_filename
        ON dbo.attendance_sheet_data2 (filename ASC);

    CREATE UNIQUE NONCLUSTERED INDEX UX_attendance_sheet_data2_filename_row
        ON dbo.attendance_sheet_data2 (filename ASC, row_number ASC);
END;
GO

/* ============================================================
   TABLE: error_log
   ============================================================ */
IF OBJECT_ID(N'dbo.error_log', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.error_log (
        id              INT IDENTITY(1,1) NOT NULL,
        source_module   NVARCHAR(100)     NOT NULL,
        sheet_type      NVARCHAR(100)     NULL,
        filename        NVARCHAR(500)     NULL,
        error_message   NVARCHAR(MAX)     NULL,
        created_at      DATETIME2(0)      NOT NULL CONSTRAINT DF_error_log_created_at DEFAULT (SYSUTCDATETIME()),
        CONSTRAINT PK_error_log PRIMARY KEY CLUSTERED (id ASC)
    );

    CREATE NONCLUSTERED INDEX IX_error_log_source_module
        ON dbo.error_log (source_module ASC, created_at DESC);
END;
GO

/* ============================================================
   STORED PROCEDURE: sp_insert_attendance_sheet_data_1
   ============================================================ */
CREATE OR ALTER PROCEDURE dbo.sp_insert_attendance_sheet_data_1
    @filename           NVARCHAR(500),
    @center_code        NVARCHAR(50) = NULL,
    @subcenter_code     NVARCHAR(50) = NULL,
    @subject_code       NVARCHAR(50) = NULL,
    @invigilator_signed BIT = 0,
    @row_number         INT,
    @status             NVARCHAR(50) = NULL,
    @signature_present  BIT = 0,
    @omr_no             NVARCHAR(50) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    IF EXISTS (
        SELECT 1
        FROM dbo.attendance_sheet_data_1
        WHERE filename = @filename
          AND row_number = @row_number
    )
    BEGIN
        RETURN;
    END;

    INSERT INTO dbo.attendance_sheet_data_1 (
        filename,
        center_code,
        subcenter_code,
        subject_code,
        invigilator_signed,
        row_number,
        status,
        signature_present,
        omr_no
    )
    VALUES (
        @filename,
        @center_code,
        @subcenter_code,
        @subject_code,
        @invigilator_signed,
        @row_number,
        @status,
        @signature_present,
        @omr_no
    );
END;
GO

/* ============================================================
   STORED PROCEDURE: sp_insert_attendance_sheet_data2
   ============================================================ */
CREATE OR ALTER PROCEDURE dbo.sp_insert_attendance_sheet_data2
    @filename           NVARCHAR(500),
    @center_code        NVARCHAR(50) = NULL,
    @subcenter_code     NVARCHAR(50) = NULL,
    @subject_code       NVARCHAR(50) = NULL,
    @invigilator_signed BIT = 0,
    @row_number         INT,
    @status             NVARCHAR(50) = NULL,
    @signature_present  BIT = 0,
    @registration_no    NVARCHAR(50) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    IF EXISTS (
        SELECT 1
        FROM dbo.attendance_sheet_data2
        WHERE filename = @filename
          AND row_number = @row_number
    )
    BEGIN
        RETURN;
    END;

    INSERT INTO dbo.attendance_sheet_data2 (
        filename,
        center_code,
        subcenter_code,
        subject_code,
        invigilator_signed,
        row_number,
        status,
        signature_present,
        registration_no
    )
    VALUES (
        @filename,
        @center_code,
        @subcenter_code,
        @subject_code,
        @invigilator_signed,
        @row_number,
        @status,
        @signature_present,
        @registration_no
    );
END;
GO

/* ============================================================
   STORED PROCEDURE: sp_insert_attendance_error_log
   ============================================================ */
CREATE OR ALTER PROCEDURE dbo.sp_insert_attendance_error_log
    @source_module  NVARCHAR(100),
    @sheet_type     NVARCHAR(100) = NULL,
    @filename       NVARCHAR(500) = NULL,
    @error_message  NVARCHAR(MAX) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    INSERT INTO dbo.error_log (
        source_module,
        sheet_type,
        filename,
        error_message
    )
    VALUES (
        @source_module,
        @sheet_type,
        @filename,
        @error_message
    );
END;
GO

PRINT 'Attendance Sheets schema and stored procedures created successfully.';
GO
