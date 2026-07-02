-- =============================================================
-- KPSC OMR — Discrepancy Reports (11 categories)
-- Run once in SSMS against KPSCOMRICRExtraction
-- =============================================================
USE [KPSCOMRICRExtraction];
GO

SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

-- ─────────────────────────────────────────────────────────────
-- Report catalogue (ReportID, ReportName, ProcedureName)
-- ─────────────────────────────────────────────────────────────
IF OBJECT_ID(N'dbo.DiscrepancyReportMaster', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.DiscrepancyReportMaster (
        ReportID        INT           NOT NULL CONSTRAINT PK_DiscrepancyReportMaster PRIMARY KEY,
        ReportName      NVARCHAR(250) NOT NULL,
        ProcedureName   SYSNAME       NOT NULL,
        IsActive        BIT           NOT NULL CONSTRAINT DF_DiscrepancyReportMaster_IsActive DEFAULT (1)
    );
END;
GO

MERGE dbo.DiscrepancyReportMaster AS tgt
USING (VALUES
    ( 1, N'Subject Code & Booklet Serial No Descripancy',              N'dbo.Sub_CodeAndBookletNoDesc'),
    ( 2, N'Barcode Descripancy',                                        N'dbo.BarcodeDesc'),
    ( 3, N'Written RegNo Descripancy',                                  N'dbo.WrittenRegNoDesc'),
    ( 4, N'OMR RegNo Descripancy',                                      N'dbo.BobbledRegNoDesc'),
    ( 5, N'Whiter Used in the boubles',                                 N'dbo.WhiterUsedDesc'),
    ( 6, N'Boubles marked <35% Threshold marking',                      N'dbo.ThresholdDesc'),
    ( 7, N'Candidate''s Signature Descripancy',                         N'dbo.Std_Sign_Desc'),
    ( 8, N'Invigilator''s Signature Descripancy',                       N'dbo.Inv_Sign_Desc'),
    ( 9, N'Non standard OMR sheet used',                                N'dbo.NonStandard_OMRDesc'),
    (10, N'Not signed by candidate in Nominal Rolll Descripancy',      N'dbo.NominalRoll1_Can_Sign_Desc'),
    (11, N'Not signed by Invigilator in Nominal Rolll Descripancy',     N'dbo.NominalRoll1_inv_Sign_Desc')
) AS src (ReportID, ReportName, ProcedureName)
ON tgt.ReportID = src.ReportID
WHEN MATCHED THEN
    UPDATE SET ReportName = src.ReportName, ProcedureName = src.ProcedureName
WHEN NOT MATCHED THEN
    INSERT (ReportID, ReportName, ProcedureName) VALUES (src.ReportID, src.ReportName, src.ProcedureName);
GO

-- ─────────────────────────────────────────────────────────────
-- Audit / correction columns on omr_results
-- ─────────────────────────────────────────────────────────────
IF COL_LENGTH(N'dbo.omr_results', N'edited_subject_code') IS NULL
    ALTER TABLE dbo.omr_results ADD edited_subject_code NVARCHAR(100) NULL;
IF COL_LENGTH(N'dbo.omr_results', N'edited_booklet_sl_no') IS NULL
    ALTER TABLE dbo.omr_results ADD edited_booklet_sl_no NVARCHAR(100) NULL;
IF COL_LENGTH(N'dbo.omr_results', N'edited_barcode') IS NULL
    ALTER TABLE dbo.omr_results ADD edited_barcode NVARCHAR(100) NULL;
IF COL_LENGTH(N'dbo.omr_results', N'edited_bubble_regno') IS NULL
    ALTER TABLE dbo.omr_results ADD edited_bubble_regno NVARCHAR(50) NULL;
IF COL_LENGTH(N'dbo.omr_results', N'edited_handwritten_regno') IS NULL
    ALTER TABLE dbo.omr_results ADD edited_handwritten_regno NVARCHAR(50) NULL;
IF COL_LENGTH(N'dbo.omr_results', N'edited_final_regno') IS NULL
    ALTER TABLE dbo.omr_results ADD edited_final_regno NVARCHAR(50) NULL;
IF COL_LENGTH(N'dbo.omr_results', N'edited_candidate_signed') IS NULL
    ALTER TABLE dbo.omr_results ADD edited_candidate_signed NVARCHAR(10) NULL;
IF COL_LENGTH(N'dbo.omr_results', N'edited_invigilator_signed') IS NULL
    ALTER TABLE dbo.omr_results ADD edited_invigilator_signed NVARCHAR(10) NULL;
IF COL_LENGTH(N'dbo.omr_results', N'is_non_standard') IS NULL
    ALTER TABLE dbo.omr_results ADD is_non_standard BIT NULL CONSTRAINT DF_omr_results_is_non_standard DEFAULT (0);
IF COL_LENGTH(N'dbo.omr_results', N'low_bubble_fill') IS NULL
    ALTER TABLE dbo.omr_results ADD low_bubble_fill BIT NOT NULL CONSTRAINT DF_omr_results_low_bubble_fill DEFAULT (0);
IF COL_LENGTH(N'dbo.omr_results', N'min_bubble_fill_pct') IS NULL
    ALTER TABLE dbo.omr_results ADD min_bubble_fill_pct FLOAT NULL;
IF COL_LENGTH(N'dbo.omr_results', N'disc_resolved') IS NULL
    ALTER TABLE dbo.omr_results ADD disc_resolved BIT NOT NULL CONSTRAINT DF_omr_results_disc_resolved DEFAULT (0);
IF COL_LENGTH(N'dbo.omr_results', N'disc_resolved_at') IS NULL
    ALTER TABLE dbo.omr_results ADD disc_resolved_at DATETIME2(0) NULL;
IF COL_LENGTH(N'dbo.omr_results', N'disc_resolved_by') IS NULL
    ALTER TABLE dbo.omr_results ADD disc_resolved_by INT NULL;
GO

-- Nominal roll Type 1 audit columns
IF COL_LENGTH(N'dbo.attendance_sheet_data_1', N'edited_registration_no') IS NULL
    ALTER TABLE dbo.attendance_sheet_data_1 ADD edited_registration_no NVARCHAR(50) NULL;
IF COL_LENGTH(N'dbo.attendance_sheet_data_1', N'edited_signature_present') IS NULL
    ALTER TABLE dbo.attendance_sheet_data_1 ADD edited_signature_present BIT NULL;
IF COL_LENGTH(N'dbo.attendance_sheet_data_1', N'edited_invigilator_signed') IS NULL
    ALTER TABLE dbo.attendance_sheet_data_1 ADD edited_invigilator_signed BIT NULL;
IF COL_LENGTH(N'dbo.attendance_sheet_data_1', N'disc_resolved') IS NULL
    ALTER TABLE dbo.attendance_sheet_data_1 ADD disc_resolved BIT NOT NULL CONSTRAINT DF_att1_disc_resolved DEFAULT (0);
IF COL_LENGTH(N'dbo.attendance_sheet_data_1', N'updated_at') IS NULL
    ALTER TABLE dbo.attendance_sheet_data_1 ADD updated_at DATETIME2(0) NULL;
IF COL_LENGTH(N'dbo.attendance_sheet_data_1', N'updated_by') IS NULL
    ALTER TABLE dbo.attendance_sheet_data_1 ADD updated_by INT NULL;
GO

-- Nominal roll Type 2 audit columns
IF COL_LENGTH(N'dbo.attendance_sheet_data2', N'edited_registration_no') IS NULL
    ALTER TABLE dbo.attendance_sheet_data2 ADD edited_registration_no NVARCHAR(50) NULL;
IF COL_LENGTH(N'dbo.attendance_sheet_data2', N'edited_qcab_serial_no') IS NULL
    ALTER TABLE dbo.attendance_sheet_data2 ADD edited_qcab_serial_no NVARCHAR(50) NULL;
IF COL_LENGTH(N'dbo.attendance_sheet_data2', N'edited_signature_present') IS NULL
    ALTER TABLE dbo.attendance_sheet_data2 ADD edited_signature_present BIT NULL;
IF COL_LENGTH(N'dbo.attendance_sheet_data2', N'edited_invigilator_signed') IS NULL
    ALTER TABLE dbo.attendance_sheet_data2 ADD edited_invigilator_signed BIT NULL;
IF COL_LENGTH(N'dbo.attendance_sheet_data2', N'disc_resolved') IS NULL
    ALTER TABLE dbo.attendance_sheet_data2 ADD disc_resolved BIT NOT NULL CONSTRAINT DF_att2_disc_resolved DEFAULT (0);
IF COL_LENGTH(N'dbo.attendance_sheet_data2', N'updated_at') IS NULL
    ALTER TABLE dbo.attendance_sheet_data2 ADD updated_at DATETIME2(0) NULL;
IF COL_LENGTH(N'dbo.attendance_sheet_data2', N'updated_by') IS NULL
    ALTER TABLE dbo.attendance_sheet_data2 ADD updated_by INT NULL;
GO

-- =============================================================
-- REPORT 1 — Subject Code & Booklet Serial No Descripancy
-- Procedure: Sub_CodeAndBookletNoDesc
-- =============================================================
CREATE OR ALTER PROCEDURE dbo.Sub_CodeAndBookletNoDesc
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
        id                                              AS ID,
        filename                                        AS FileName,
        barcode                                         AS Barcode,
        subject_code                                    AS Subject_Code,
        ISNULL(edited_subject_code, subject_code)       AS Edited_Subject_Code,
        BookletSlNo                                     AS Booklet_Sl_No,
        ISNULL(edited_booklet_sl_no, BookletSlNo)       AS Edited_Booklet_Sl_No,
        disc_resolved                                   AS IsResolved,
        updated_at                                      AS UpdatedAt
    FROM dbo.omr_results
    WHERE (
        ISNULL(LTRIM(RTRIM(subject_code)), N'') = N''
        OR ISNULL(LTRIM(RTRIM(BookletSlNo)),  N'') = N''
    )
    AND disc_resolved = 0
    ORDER BY id DESC;
END;
GO

-- =============================================================
-- REPORT 2 — Barcode Descripancy
-- Procedure: BarcodeDesc
-- =============================================================
CREATE OR ALTER PROCEDURE dbo.BarcodeDesc
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
        id                                              AS ID,
        filename                                        AS FileName,
        barcode                                         AS Detected_Barcode,
        ISNULL(edited_barcode, barcode)                 AS Edited_Barcode,
        bubble_regno                                    AS Bubble_RegNo,
        final_regno                                     AS Final_RegNo,
        disc_resolved                                   AS IsResolved,
        updated_at                                      AS UpdatedAt
    FROM dbo.omr_results
    WHERE (
        ISNULL(LTRIM(RTRIM(barcode)), N'') = N''
        OR barcode = N'Not Detected'
    )
    AND disc_resolved = 0
    ORDER BY id DESC;
END;
GO

-- =============================================================
-- REPORT 3 — Written RegNo Descripancy
-- Procedure: WrittenRegNoDesc
-- =============================================================
CREATE OR ALTER PROCEDURE dbo.WrittenRegNoDesc
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
        id                                              AS ID,
        filename                                        AS FileName,
        barcode                                         AS Barcode,
        handwritten_regno                               AS Handwritten_RegNo,
        ISNULL(edited_handwritten_regno, handwritten_regno) AS Edited_Handwritten_RegNo,
        bubble_regno                                    AS Bubble_RegNo,
        final_regno                                     AS Final_RegNo,
        disc_resolved                                   AS IsResolved,
        updated_at                                      AS UpdatedAt
    FROM dbo.omr_results
    WHERE (
        ISNULL(LTRIM(RTRIM(handwritten_regno)), N'') = N''
        OR LEN(REPLACE(ISNULL(handwritten_regno, N''), N' ', N'')) = 0
    )
    AND disc_resolved = 0
    ORDER BY id DESC;
END;
GO

-- =============================================================
-- REPORT 4 — OMR RegNo Descripancy (bubble vs handwritten mismatch)
-- Procedure: BobbledRegNoDesc
-- =============================================================
CREATE OR ALTER PROCEDURE dbo.BobbledRegNoDesc
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
        id                                              AS ID,
        filename                                        AS FileName,
        barcode                                         AS Barcode,
        bubble_regno                                    AS Bubble_RegNo,
        ISNULL(edited_bubble_regno, bubble_regno)       AS Edited_Bubble_RegNo,
        handwritten_regno                               AS Handwritten_RegNo,
        ISNULL(edited_handwritten_regno, handwritten_regno) AS Edited_Handwritten_RegNo,
        final_regno                                     AS Final_RegNo,
        ISNULL(edited_final_regno, final_regno)         AS Edited_Final_RegNo,
        discrepancy_detail                              AS Discrepancy_Detail,
        disc_resolved                                   AS IsResolved,
        updated_at                                      AS UpdatedAt
    FROM dbo.omr_results
    WHERE discrepancy = 1
    AND disc_resolved = 0
    ORDER BY id DESC;
END;
GO

-- =============================================================
-- REPORT 5 — Whitener Used in the Bubbles
-- Procedure: WhiterUsedDesc
-- =============================================================
CREATE OR ALTER PROCEDURE dbo.WhiterUsedDesc
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
        id                                              AS ID,
        filename                                        AS FileName,
        barcode                                         AS Barcode,
        bubble_regno                                    AS Bubble_RegNo,
        final_regno                                     AS Final_RegNo,
        ISNULL(edited_final_regno, final_regno)         AS Edited_Final_RegNo,
        whitenerflag                                    AS Whitener_Detected,
        disc_resolved                                   AS IsResolved,
        updated_at                                      AS UpdatedAt
    FROM dbo.omr_results
    WHERE whitenerflag = 1
    AND disc_resolved = 0
    ORDER BY id DESC;
END;
GO

-- =============================================================
-- REPORT 6 — Bubbles Marked <35% Threshold
-- Procedure: ThresholdDesc
-- =============================================================
CREATE OR ALTER PROCEDURE dbo.ThresholdDesc
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
        id                                              AS ID,
        filename                                        AS FileName,
        barcode                                         AS Barcode,
        bubble_regno                                    AS Bubble_RegNo,
        ISNULL(edited_bubble_regno, bubble_regno)       AS Edited_Bubble_RegNo,
        min_bubble_fill_pct                             AS Min_Bubble_Fill_Pct,
        final_regno                                     AS Final_RegNo,
        ISNULL(edited_final_regno, final_regno)         AS Edited_Final_RegNo,
        disc_resolved                                   AS IsResolved,
        updated_at                                      AS UpdatedAt
    FROM dbo.omr_results
    WHERE low_bubble_fill = 1
    AND disc_resolved = 0
    ORDER BY ISNULL(min_bubble_fill_pct, 0) ASC, id DESC;
END;
GO

-- =============================================================
-- REPORT 7 — Candidate Signature Descripancy (counter foil)
-- Procedure: Std_Sign_Desc
-- =============================================================
CREATE OR ALTER PROCEDURE dbo.Std_Sign_Desc
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
        id                                              AS ID,
        filename                                        AS FileName,
        barcode                                         AS Barcode,
        final_regno                                     AS Final_RegNo,
        candidate_signed                                AS Candidate_Signed,
        ISNULL(edited_candidate_signed, candidate_signed) AS Edited_Candidate_Signed,
        invigilator_signed                              AS Invigilator_Signed,
        ISNULL(edited_invigilator_signed, invigilator_signed) AS Edited_Invigilator_Signed,
        disc_resolved                                   AS IsResolved,
        updated_at                                      AS UpdatedAt
    FROM dbo.omr_results
    WHERE (
        ISNULL(candidate_signed, N'False') IN (N'False', N'0', N'0.0')
        OR LTRIM(RTRIM(ISNULL(candidate_signed, N''))) = N''
    )
    AND disc_resolved = 0
    ORDER BY id DESC;
END;
GO

-- =============================================================
-- REPORT 8 — Invigilator Signature Descripancy (counter foil)
-- Procedure: Inv_Sign_Desc
-- =============================================================
CREATE OR ALTER PROCEDURE dbo.Inv_Sign_Desc
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
        id                                              AS ID,
        filename                                        AS FileName,
        barcode                                         AS Barcode,
        final_regno                                     AS Final_RegNo,
        candidate_signed                                AS Candidate_Signed,
        ISNULL(edited_candidate_signed, candidate_signed) AS Edited_Candidate_Signed,
        invigilator_signed                              AS Invigilator_Signed,
        ISNULL(edited_invigilator_signed, invigilator_signed) AS Edited_Invigilator_Signed,
        disc_resolved                                   AS IsResolved,
        updated_at                                      AS UpdatedAt
    FROM dbo.omr_results
    WHERE (
        ISNULL(invigilator_signed, N'False') IN (N'False', N'0', N'0.0')
        OR LTRIM(RTRIM(ISNULL(invigilator_signed, N''))) = N''
    )
    AND disc_resolved = 0
    ORDER BY id DESC;
END;
GO

-- =============================================================
-- REPORT 9 — Non Standard OMR Sheet Used
-- Procedure: NonStandard_OMRDesc
-- =============================================================
CREATE OR ALTER PROCEDURE dbo.NonStandard_OMRDesc
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
        id                                              AS ID,
        filename                                        AS FileName,
        barcode                                         AS Barcode,
        final_regno                                     AS Final_RegNo,
        isblack                                         AS Is_BW,
        is_non_standard                                 AS Is_Non_Standard,
        subject_code                                    AS Subject_Code,
        BookletSlNo                                     AS Booklet_Sl_No,
        disc_resolved                                   AS IsResolved,
        updated_at                                      AS UpdatedAt
    FROM dbo.omr_results
    WHERE (
        ISNULL(is_non_standard, 0) = 1
        OR ISNULL(isblack, 0) = 1
    )
    AND disc_resolved = 0
    ORDER BY id DESC;
END;
GO

-- =============================================================
-- REPORT 10 — Candidate Not Signed on Nominal Roll
-- Procedure: NominalRoll1_Can_Sign_Desc
-- =============================================================
CREATE OR ALTER PROCEDURE dbo.NominalRoll1_Can_Sign_Desc
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
        a.id                                            AS ID,
        N'Type1'                                        AS Sheet_Type,
        a.filename                                      AS FileName,
        a.row_number                                    AS Row_Number,
        a.registration_no                               AS Registration_No,
        ISNULL(a.edited_registration_no, a.registration_no) AS Edited_Registration_No,
        a.omr_no                                        AS OMR_No,
        a.status                                        AS Status,
        a.signature_present                             AS Signature_Present,
        ISNULL(a.edited_signature_present, a.signature_present) AS Edited_Signature_Present,
        a.center_code                                   AS Center_Code,
        a.subject_code                                  AS Subject_Code,
        a.disc_resolved                                 AS IsResolved,
        a.updated_at                                    AS UpdatedAt
    FROM dbo.attendance_sheet_data_1 a
    WHERE a.signature_present = 0
    AND a.disc_resolved = 0
    AND ISNULL(a.status, N'') NOT IN (N'Absent', N'absent')

    UNION ALL

    SELECT
        b.id                                            AS ID,
        N'Type2'                                        AS Sheet_Type,
        b.filename                                      AS FileName,
        b.row_number                                    AS Row_Number,
        b.registration_no                               AS Registration_No,
        ISNULL(b.edited_registration_no, b.registration_no) AS Edited_Registration_No,
        b.qcab_serial_no                                AS OMR_No,
        b.status                                        AS Status,
        b.signature_present                             AS Signature_Present,
        ISNULL(b.edited_signature_present, b.signature_present) AS Edited_Signature_Present,
        b.center_code                                   AS Center_Code,
        b.subject_code                                  AS Subject_Code,
        b.disc_resolved                                 AS IsResolved,
        b.updated_at                                    AS UpdatedAt
    FROM dbo.attendance_sheet_data2 b
    WHERE b.signature_present = 0
    AND b.disc_resolved = 0
    AND ISNULL(b.status, N'') NOT IN (N'Absent', N'absent')

    ORDER BY FileName, Row_Number;
END;
GO

-- =============================================================
-- REPORT 11 — Invigilator Not Signed on Nominal Roll
-- Procedure: NominalRoll1_inv_Sign_Desc
-- =============================================================
CREATE OR ALTER PROCEDURE dbo.NominalRoll1_inv_Sign_Desc
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
        a.id                                            AS ID,
        N'Type1'                                        AS Sheet_Type,
        a.filename                                      AS FileName,
        a.invigilator_signed                            AS Invigilator_Signed,
        ISNULL(a.edited_invigilator_signed, a.invigilator_signed) AS Edited_Invigilator_Signed,
        a.center_code                                   AS Center_Code,
        a.subcenter_code                                AS SubCenter_Code,
        a.subject_code                                  AS Subject_Code,
        a.disc_resolved                                 AS IsResolved,
        a.updated_at                                    AS UpdatedAt
    FROM dbo.attendance_sheet_data_1 a
    WHERE a.invigilator_signed = 0
    AND a.disc_resolved = 0

    UNION ALL

    SELECT
        b.id                                            AS ID,
        N'Type2'                                        AS Sheet_Type,
        b.filename                                      AS FileName,
        b.invigilator_signed                            AS Invigilator_Signed,
        ISNULL(b.edited_invigilator_signed, b.invigilator_signed) AS Edited_Invigilator_Signed,
        b.center_code                                   AS Center_Code,
        b.subcenter_code                                AS SubCenter_Code,
        b.subject_code                                  AS Subject_Code,
        b.disc_resolved                                 AS IsResolved,
        b.updated_at                                    AS UpdatedAt
    FROM dbo.attendance_sheet_data2 b
    WHERE b.invigilator_signed = 0
    AND b.disc_resolved = 0

    ORDER BY FileName;
END;
GO

-- =============================================================
-- UPDATE PROCEDURES (called from DiscrepancyReports.py)
-- =============================================================

CREATE OR ALTER PROCEDURE dbo.Disc_Update_SubjectBooklet
    @ID INT, @SubjectCode NVARCHAR(100), @BookletSlNo NVARCHAR(100), @UpdatedBy INT = NULL
AS
BEGIN
    SET NOCOUNT ON; SET XACT_ABORT ON;
    UPDATE dbo.omr_results
    SET edited_subject_code  = NULLIF(LTRIM(RTRIM(@SubjectCode)), N''),
        edited_booklet_sl_no = NULLIF(LTRIM(RTRIM(@BookletSlNo)), N''),
        subject_code         = NULLIF(LTRIM(RTRIM(@SubjectCode)), N''),
        BookletSlNo          = NULLIF(LTRIM(RTRIM(@BookletSlNo)), N''),
        updated_by = @UpdatedBy, updated_at = SYSUTCDATETIME(),
        disc_resolved = 1, disc_resolved_at = SYSUTCDATETIME(), disc_resolved_by = @UpdatedBy
    WHERE id = @ID;
    IF @@ROWCOUNT = 0 THROW 50010, N'Record not found.', 1;
END;
GO

CREATE OR ALTER PROCEDURE dbo.Disc_Update_Barcode
    @ID INT, @Barcode NVARCHAR(100), @UpdatedBy INT = NULL
AS
BEGIN
    SET NOCOUNT ON; SET XACT_ABORT ON;
    UPDATE dbo.omr_results
    SET edited_barcode = NULLIF(LTRIM(RTRIM(@Barcode)), N''),
        barcode        = NULLIF(LTRIM(RTRIM(@Barcode)), N''),
        updated_by = @UpdatedBy, updated_at = SYSUTCDATETIME(),
        disc_resolved = 1, disc_resolved_at = SYSUTCDATETIME(), disc_resolved_by = @UpdatedBy
    WHERE id = @ID;
    IF @@ROWCOUNT = 0 THROW 50010, N'Record not found.', 1;
END;
GO

CREATE OR ALTER PROCEDURE dbo.Disc_Update_RegNo
    @ID INT, @BubbleRegNo NVARCHAR(50), @HandwrittenRegNo NVARCHAR(50),
    @FinalRegNo NVARCHAR(50), @UpdatedBy INT = NULL
AS
BEGIN
    SET NOCOUNT ON; SET XACT_ABORT ON;
    UPDATE dbo.omr_results
    SET edited_bubble_regno      = NULLIF(LTRIM(RTRIM(@BubbleRegNo)), N''),
        edited_handwritten_regno = NULLIF(LTRIM(RTRIM(@HandwrittenRegNo)), N''),
        edited_final_regno       = NULLIF(LTRIM(RTRIM(@FinalRegNo)), N''),
        bubble_regno             = NULLIF(LTRIM(RTRIM(@BubbleRegNo)), N''),
        handwritten_regno        = NULLIF(LTRIM(RTRIM(@HandwrittenRegNo)), N''),
        final_regno              = NULLIF(LTRIM(RTRIM(@FinalRegNo)), N''),
        discrepancy              = CASE
            WHEN NULLIF(LTRIM(RTRIM(@BubbleRegNo)), N'') IS NULL
              OR NULLIF(LTRIM(RTRIM(@HandwrittenRegNo)), N'') IS NULL THEN discrepancy
            WHEN REPLACE(LTRIM(RTRIM(@BubbleRegNo)), N' ', N'') =
                 REPLACE(LTRIM(RTRIM(@HandwrittenRegNo)), N' ', N'') THEN 0
            ELSE 1 END,
        updated_by = @UpdatedBy, updated_at = SYSUTCDATETIME(),
        disc_resolved = 1, disc_resolved_at = SYSUTCDATETIME(), disc_resolved_by = @UpdatedBy
    WHERE id = @ID;
    IF @@ROWCOUNT = 0 THROW 50010, N'Record not found.', 1;
END;
GO

CREATE OR ALTER PROCEDURE dbo.Disc_Update_BubbleIssue
    @ID INT, @FinalRegNo NVARCHAR(50), @UpdatedBy INT = NULL
AS
BEGIN
    SET NOCOUNT ON; SET XACT_ABORT ON;
    UPDATE dbo.omr_results
    SET edited_final_regno = NULLIF(LTRIM(RTRIM(@FinalRegNo)), N''),
        final_regno        = NULLIF(LTRIM(RTRIM(@FinalRegNo)), N''),
        updated_by = @UpdatedBy, updated_at = SYSUTCDATETIME(),
        disc_resolved = 1, disc_resolved_at = SYSUTCDATETIME(), disc_resolved_by = @UpdatedBy
    WHERE id = @ID;
    IF @@ROWCOUNT = 0 THROW 50010, N'Record not found.', 1;
END;
GO

CREATE OR ALTER PROCEDURE dbo.Disc_Update_CounterFoilSignature
    @ID INT, @CandidateSigned NVARCHAR(10), @InvigilatorSigned NVARCHAR(10), @UpdatedBy INT = NULL
AS
BEGIN
    SET NOCOUNT ON; SET XACT_ABORT ON;
    UPDATE dbo.omr_results
    SET edited_candidate_signed   = NULLIF(LTRIM(RTRIM(@CandidateSigned)), N''),
        edited_invigilator_signed = NULLIF(LTRIM(RTRIM(@InvigilatorSigned)), N''),
        candidate_signed          = NULLIF(LTRIM(RTRIM(@CandidateSigned)), N''),
        invigilator_signed        = NULLIF(LTRIM(RTRIM(@InvigilatorSigned)), N''),
        updated_by = @UpdatedBy, updated_at = SYSUTCDATETIME(),
        disc_resolved = 1, disc_resolved_at = SYSUTCDATETIME(), disc_resolved_by = @UpdatedBy
    WHERE id = @ID;
    IF @@ROWCOUNT = 0 THROW 50010, N'Record not found.', 1;
END;
GO

CREATE OR ALTER PROCEDURE dbo.Disc_Update_NonStandardOMR
    @ID INT, @IsNonStandard BIT, @UpdatedBy INT = NULL
AS
BEGIN
    SET NOCOUNT ON; SET XACT_ABORT ON;
    UPDATE dbo.omr_results
    SET is_non_standard = @IsNonStandard,
        updated_by = @UpdatedBy, updated_at = SYSUTCDATETIME(),
        disc_resolved = 1, disc_resolved_at = SYSUTCDATETIME(), disc_resolved_by = @UpdatedBy
    WHERE id = @ID;
    IF @@ROWCOUNT = 0 THROW 50010, N'Record not found.', 1;
END;
GO

CREATE OR ALTER PROCEDURE dbo.Disc_Update_NominalRollRow
    @ID INT, @SheetType NVARCHAR(10),
    @RegistrationNo NVARCHAR(50) = NULL, @QcabSerialNo NVARCHAR(50) = NULL,
    @SignaturePresent BIT = NULL, @InvigilatorSigned BIT = NULL,
    @UpdatedBy INT = NULL
AS
BEGIN
    SET NOCOUNT ON; SET XACT_ABORT ON;

    IF @SheetType = N'Type1'
    BEGIN
        UPDATE dbo.attendance_sheet_data_1
        SET edited_registration_no    = NULLIF(LTRIM(RTRIM(@RegistrationNo)), N''),
            registration_no           = COALESCE(NULLIF(LTRIM(RTRIM(@RegistrationNo)), N''), registration_no),
            edited_signature_present  = @SignaturePresent,
            signature_present         = COALESCE(@SignaturePresent, signature_present),
            edited_invigilator_signed = @InvigilatorSigned,
            invigilator_signed        = COALESCE(@InvigilatorSigned, invigilator_signed),
            updated_by = @UpdatedBy, updated_at = SYSUTCDATETIME(), disc_resolved = 1
        WHERE id = @ID;
    END
    ELSE
    BEGIN
        UPDATE dbo.attendance_sheet_data2
        SET edited_registration_no    = NULLIF(LTRIM(RTRIM(@RegistrationNo)), N''),
            registration_no           = COALESCE(NULLIF(LTRIM(RTRIM(@RegistrationNo)), N''), registration_no),
            edited_qcab_serial_no     = NULLIF(LTRIM(RTRIM(@QcabSerialNo)), N''),
            qcab_serial_no            = COALESCE(NULLIF(LTRIM(RTRIM(@QcabSerialNo)), N''), qcab_serial_no),
            edited_signature_present  = @SignaturePresent,
            signature_present         = COALESCE(@SignaturePresent, signature_present),
            edited_invigilator_signed = @InvigilatorSigned,
            invigilator_signed        = COALESCE(@InvigilatorSigned, invigilator_signed),
            updated_by = @UpdatedBy, updated_at = SYSUTCDATETIME(), disc_resolved = 1
        WHERE id = @ID;
    END;

    IF @@ROWCOUNT = 0 THROW 50010, N'Record not found.', 1;
END;
GO

-- Legacy update used by CounterFoilSubBSNoEdit.py
CREATE OR ALTER PROCEDURE dbo.USP_UpdateCounterFoilEditedData
    @ID INT, @Subject_Code NVARCHAR(100), @BookletSlNo NVARCHAR(100), @UpdatedBy INT = NULL
AS
BEGIN
    SET NOCOUNT ON; SET XACT_ABORT ON;
    EXEC dbo.Disc_Update_SubjectBooklet @ID, @Subject_Code, @BookletSlNo, @UpdatedBy;
END;
GO

-- Seed ExportReport catalogue
MERGE dbo.ExportReport AS tgt
USING (VALUES
    (N'1. Subject Code & Booklet Serial No Descripancy',  N'dbo.Sub_CodeAndBookletNoDesc'),
    (N'2. Barcode Descripancy',                            N'dbo.BarcodeDesc'),
    (N'3. Written RegNo Descripancy',                      N'dbo.WrittenRegNoDesc'),
    (N'4. OMR RegNo Descripancy',                          N'dbo.BobbledRegNoDesc'),
    (N'5. Whitener Used in Bubbles',                       N'dbo.WhiterUsedDesc'),
    (N'6. Bubbles Marked <35% Threshold',                  N'dbo.ThresholdDesc'),
    (N'7. Candidate Signature Descripancy',                N'dbo.Std_Sign_Desc'),
    (N'8. Invigilator Signature Descripancy',              N'dbo.Inv_Sign_Desc'),
    (N'9. Non Standard OMR Sheet',                         N'dbo.NonStandard_OMRDesc'),
    (N'10. Candidate Not Signed - Nominal Roll',           N'dbo.NominalRoll1_Can_Sign_Desc'),
    (N'11. Invigilator Not Signed - Nominal Roll',         N'dbo.NominalRoll1_inv_Sign_Desc')
) AS src (ReportName, ProcedureName)
ON tgt.ReportName = src.ReportName
WHEN MATCHED THEN
    UPDATE SET ProcedureName = src.ProcedureName
WHEN NOT MATCHED THEN
    INSERT (ReportName, ProcedureName, Parametres)
    VALUES (src.ReportName, src.ProcedureName, NULL);
GO

PRINT 'DiscrepancyReports.sql applied successfully.';
GO
