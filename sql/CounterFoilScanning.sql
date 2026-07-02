/*
    Counter Foil Scanning database schema for KPSCOMRICRExtraction.
    Run this script in SSMS against the same database configured in db_credentials.py.

    Tables     : omr_results, ErrorLog
    Procedures : InsertOMRResult, Sub_CodeAndBookletNoDesc,
                 USP_UpdateCounterFoilEditedData
*/

USE [KPSCOMRICRExtraction];
GO

SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

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

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID(N'dbo.omr_results')
      AND name = N'IX_omr_results_filename'
)
BEGIN
    CREATE INDEX IX_omr_results_filename ON dbo.omr_results(filename);
END;
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID(N'dbo.omr_results')
      AND name = N'IX_omr_results_discrepancy'
)
BEGIN
    CREATE INDEX IX_omr_results_discrepancy
        ON dbo.omr_results(discrepancy, id)
        INCLUDE (filename, barcode, subject_code, BookletSlNo);
END;
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

    SELECT
        id AS ID,
        filename AS FileName,
        barcode AS Barcode,
        subject_code AS Subject_code,
        BookletSlNo
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

    IF @@ROWCOUNT = 0
        THROW 50010, 'Counter Foil record was not found.', 1;
END;
GO

PRINT 'Counter Foil Scanning schema and stored procedures created successfully.';
GO
