-- =============================================================
-- KPSC OMR — Discrepancy Reports
-- All 11 discrepancy report stored procedures + supporting DDL
-- Run once against the KPSCOMRICRExtraction database
-- =============================================================
USE [KPSCOMRICRExtraction];
GO

-- ─────────────────────────────────────────────────────────────
-- 1.  Audit columns on omr_results (safe to run repeatedly)
-- ─────────────────────────────────────────────────────────────
IF COL_LENGTH(N'dbo.omr_results', N'edited_subject_code')    IS NULL
    ALTER TABLE dbo.omr_results ADD edited_subject_code  NVARCHAR(100) NULL;
IF COL_LENGTH(N'dbo.omr_results', N'edited_booklet_sl_no')   IS NULL
    ALTER TABLE dbo.omr_results ADD edited_booklet_sl_no NVARCHAR(100) NULL;
IF COL_LENGTH(N'dbo.omr_results', N'edited_barcode')         IS NULL
    ALTER TABLE dbo.omr_results ADD edited_barcode       NVARCHAR(100) NULL;
IF COL_LENGTH(N'dbo.omr_results', N'edited_bubble_regno')    IS NULL
    ALTER TABLE dbo.omr_results ADD edited_bubble_regno  NVARCHAR(50)  NULL;
IF COL_LENGTH(N'dbo.omr_results', N'edited_handwritten_regno') IS NULL
    ALTER TABLE dbo.omr_results ADD edited_handwritten_regno NVARCHAR(50) NULL;
IF COL_LENGTH(N'dbo.omr_results', N'edited_final_regno')     IS NULL
    ALTER TABLE dbo.omr_results ADD edited_final_regno   NVARCHAR(50)  NULL;
IF COL_LENGTH(N'dbo.omr_results', N'edited_candidate_signed') IS NULL
    ALTER TABLE dbo.omr_results ADD edited_candidate_signed NVARCHAR(10) NULL;
IF COL_LENGTH(N'dbo.omr_results', N'edited_invigilator_signed') IS NULL
    ALTER TABLE dbo.omr_results ADD edited_invigilator_signed NVARCHAR(10) NULL;
IF COL_LENGTH(N'dbo.omr_results', N'is_non_standard')        IS NULL
    ALTER TABLE dbo.omr_results ADD is_non_standard      BIT NULL CONSTRAINT DF_omr_results_is_non_standard DEFAULT (0);
IF COL_LENGTH(N'dbo.omr_results', N'disc_resolved')          IS NULL
    ALTER TABLE dbo.omr_results ADD disc_resolved        BIT NOT NULL CONSTRAINT DF_omr_results_disc_resolved DEFAULT (0);
IF COL_LENGTH(N'dbo.omr_results', N'disc_resolved_at')       IS NULL
    ALTER TABLE dbo.omr_results ADD disc_resolved_at     DATETIME2(0) NULL;
IF COL_LENGTH(N'dbo.omr_results', N'disc_resolved_by')       IS NULL
    ALTER TABLE dbo.omr_results ADD disc_resolved_by     INT NULL;
GO

-- Audit columns on attendance_sheet_data_1
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

-- Audit columns on attendance_sheet_data2
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
-- REPORT 1 — Subject Code & Booklet Serial No Discrepancy
--   Records where subject_code OR BookletSlNo is missing/blank
-- =============================================================
CREATE OR ALTER PROCEDURE dbo.Disc_SubjectCodeBookletNo
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
        id                   AS ID,
        filename             AS FileName,
        barcode              AS Barcode,
        subject_code         AS Subject_Code,
        ISNULL(edited_subject_code,  subject_code)  AS Edited_Subject_Code,
        BookletSlNo          AS Booklet_Sl_No,
        ISNULL(edited_booklet_sl_no, BookletSlNo)   AS Edited_Booklet_Sl_No,
        disc_resolved        AS IsResolved,
        updated_at           AS UpdatedAt
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
-- REPORT 2 — Barcode Discrepancy
--   Records where barcode was not detected or equals 'Not Detected'
-- =============================================================
CREATE OR ALTER PROCEDURE dbo.Disc_BarcodeDiscrepancy
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
        id                   AS ID,
        filename             AS FileName,
        barcode              AS Detected_Barcode,
        ISNULL(edited_barcode, barcode) AS Edited_Barcode,
        bubble_regno         AS Bubble_RegNo,
        final_regno          AS Final_RegNo,
        disc_resolved        AS IsResolved,
        updated_at           AS UpdatedAt
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
-- REPORT 3 — Written RegNo Discrepancy
--   Handwritten registration number was blank or unreadable
-- =============================================================
CREATE OR ALTER PROCEDURE dbo.Disc_WrittenRegNoDiscrepancy
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
        id                       AS ID,
        filename                 AS FileName,
        barcode                  AS Barcode,
        handwritten_regno        AS Handwritten_RegNo,
        ISNULL(edited_handwritten_regno, handwritten_regno) AS Edited_Handwritten_RegNo,
        bubble_regno             AS Bubble_RegNo,
        final_regno              AS Final_RegNo,
        disc_resolved            AS IsResolved,
        updated_at               AS UpdatedAt
    FROM dbo.omr_results
    WHERE (
        ISNULL(LTRIM(RTRIM(handwritten_regno)), N'') = N''
        OR LTRIM(RTRIM(handwritten_regno)) = REPLICATE(N' ', LEN(LTRIM(RTRIM(handwritten_regno))))
    )
    AND disc_resolved = 0
    ORDER BY id DESC;
END;
GO

-- =============================================================
-- REPORT 4 — OMR RegNo Discrepancy
--   Bubble-read register number does not match handwritten,
--   OR bubble RegNo contains spaces/missing digits
-- =============================================================
CREATE OR ALTER PROCEDURE dbo.Disc_OMRRegNoDiscrepancy
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
        id                       AS ID,
        filename                 AS FileName,
        barcode                  AS Barcode,
        bubble_regno             AS Bubble_RegNo,
        ISNULL(edited_bubble_regno, bubble_regno)   AS Edited_Bubble_RegNo,
        handwritten_regno        AS Handwritten_RegNo,
        final_regno              AS Final_RegNo,
        discrepancy_detail       AS Discrepancy_Detail,
        disc_resolved            AS IsResolved,
        updated_at               AS UpdatedAt
    FROM dbo.omr_results
    WHERE discrepancy = 1
    AND disc_resolved = 0
    ORDER BY id DESC;
END;
GO

-- =============================================================
-- REPORT 5 — Whitener Used in Bubbles
--   whitenerflag = 1 means correction fluid was detected
-- =============================================================
CREATE OR ALTER PROCEDURE dbo.Disc_WhitenerUsed
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
        id                   AS ID,
        filename             AS FileName,
        barcode              AS Barcode,
        bubble_regno         AS Bubble_RegNo,
        final_regno          AS Final_RegNo,
        ISNULL(edited_final_regno, final_regno) AS Edited_Final_RegNo,
        whitenerflag         AS Whitener_Detected,
        disc_resolved        AS IsResolved,
        updated_at           AS UpdatedAt
    FROM dbo.omr_results
    WHERE whitenerflag = 1
    AND disc_resolved = 0
    ORDER BY id DESC;
END;
GO

-- =============================================================
-- REPORT 6 — Bubbles Marked < 35% Threshold
--   omr_threshold (OCR confidence) below 0.35 — weak/ambiguous mark
-- =============================================================
CREATE OR ALTER PROCEDURE dbo.Disc_BubbleThreshold
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
        id                   AS ID,
        filename             AS FileName,
        barcode              AS Barcode,
        bubble_regno         AS Bubble_RegNo,
        ISNULL(edited_bubble_regno, bubble_regno) AS Edited_Bubble_RegNo,
        omr_threshold        AS OMR_Threshold,
        final_regno          AS Final_RegNo,
        disc_resolved        AS IsResolved,
        updated_at           AS UpdatedAt
    FROM dbo.omr_results
    WHERE TRY_CAST(omr_threshold AS FLOAT) < 0.35
    AND omr_threshold IS NOT NULL
    AND disc_resolved = 0
    ORDER BY TRY_CAST(omr_threshold AS FLOAT) ASC;
END;
GO

-- =============================================================
-- REPORT 7 — Candidate Signature Discrepancy
--   candidate_signed = 'False' or NULL on the counter foil
-- =============================================================
CREATE OR ALTER PROCEDURE dbo.Disc_CandidateSignature
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
        id                       AS ID,
        filename                 AS FileName,
        barcode                  AS Barcode,
        final_regno              AS Final_RegNo,
        candidate_signed         AS Candidate_Signed,
        ISNULL(edited_candidate_signed, candidate_signed) AS Edited_Candidate_Signed,
        disc_resolved            AS IsResolved,
        updated_at               AS UpdatedAt
    FROM dbo.omr_results
    WHERE (
        ISNULL(candidate_signed, N'False') = N'False'
        OR candidate_signed = N'0'
    )
    AND disc_resolved = 0
    ORDER BY id DESC;
END;
GO

-- =============================================================
-- REPORT 8 — Invigilator Signature Discrepancy
--   invigilator_signed = 'False' or NULL on the counter foil
-- =============================================================
CREATE OR ALTER PROCEDURE dbo.Disc_InvigilatorSignature
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
        id                         AS ID,
        filename                   AS FileName,
        barcode                    AS Barcode,
        final_regno                AS Final_RegNo,
        invigilator_signed         AS Invigilator_Signed,
        ISNULL(edited_invigilator_signed, invigilator_signed) AS Edited_Invigilator_Signed,
        disc_resolved              AS IsResolved,
        updated_at                 AS UpdatedAt
    FROM dbo.omr_results
    WHERE (
        ISNULL(invigilator_signed, N'False') = N'False'
        OR invigilator_signed = N'0'
    )
    AND disc_resolved = 0
    ORDER BY id DESC;
END;
GO

-- =============================================================
-- REPORT 9 — Non-Standard OMR Sheet Used
--   isblack = 0 AND is_non_standard = 1,
--   or records flagged as non-standard via manual review
-- =============================================================
CREATE OR ALTER PROCEDURE dbo.Disc_NonStandardOMR
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
        id                   AS ID,
        filename             AS FileName,
        barcode              AS Barcode,
        final_regno          AS Final_RegNo,
        isblack              AS Is_BW,
        is_non_standard      AS Is_Non_Standard,
        subject_code         AS Subject_Code,
        BookletSlNo          AS Booklet_Sl_No,
        disc_resolved        AS IsResolved,
        updated_at           AS UpdatedAt
    FROM dbo.omr_results
    WHERE ISNULL(is_non_standard, 0) = 1
    AND disc_resolved = 0
    ORDER BY id DESC;
END;
GO

-- =============================================================
-- REPORT 10 — Not Signed by Candidate in Nominal Roll
--   attendance_sheet_data_1 rows where signature_present = 0
--   attendance_sheet_data2  rows where signature_present = 0
-- =============================================================
CREATE OR ALTER PROCEDURE dbo.Disc_NominalRollCandidateSignature
AS
BEGIN
    SET NOCOUNT ON;

    -- Type 1 nominal rolls
    SELECT
        a.id                     AS ID,
        N'Type1'                 AS Sheet_Type,
        a.filename               AS FileName,
        a.row_number             AS Row_Number,
        a.registration_no        AS Registration_No,
        ISNULL(a.edited_registration_no, a.registration_no) AS Edited_Registration_No,
        a.omr_no                 AS OMR_No,
        a.status                 AS Status,
        a.signature_present      AS Signature_Present,
        ISNULL(a.edited_signature_present, a.signature_present) AS Edited_Signature_Present,
        a.center_code            AS Center_Code,
        a.subject_code           AS Subject_Code,
        a.disc_resolved          AS IsResolved,
        a.updated_at             AS UpdatedAt
    FROM dbo.attendance_sheet_data_1 a
    WHERE a.signature_present = 0
    AND a.disc_resolved = 0
    AND ISNULL(a.status, N'') NOT IN (N'Absent', N'absent')

    UNION ALL

    -- Type 2 nominal rolls
    SELECT
        b.id                     AS ID,
        N'Type2'                 AS Sheet_Type,
        b.filename               AS FileName,
        b.row_number             AS Row_Number,
        b.registration_no        AS Registration_No,
        ISNULL(b.edited_registration_no, b.registration_no) AS Edited_Registration_No,
        b.qcab_serial_no         AS OMR_No,
        b.status                 AS Status,
        b.signature_present      AS Signature_Present,
        ISNULL(b.edited_signature_present, b.signature_present) AS Edited_Signature_Present,
        b.center_code            AS Center_Code,
        b.subject_code           AS Subject_Code,
        b.disc_resolved          AS IsResolved,
        b.updated_at             AS UpdatedAt
    FROM dbo.attendance_sheet_data2 b
    WHERE b.signature_present = 0
    AND b.disc_resolved = 0
    AND ISNULL(b.status, N'') NOT IN (N'Absent', N'absent')

    ORDER BY FileName, Row_Number;
END;
GO

-- =============================================================
-- REPORT 11 — Not Signed by Invigilator in Nominal Roll
--   attendance_sheet_data_1 / data2 where invigilator_signed = 0
-- =============================================================
CREATE OR ALTER PROCEDURE dbo.Disc_NominalRollInvigilatorSignature
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
        a.id                       AS ID,
        N'Type1'                   AS Sheet_Type,
        a.filename                 AS FileName,
        a.invigilator_signed       AS Invigilator_Signed,
        ISNULL(a.edited_invigilator_signed, a.invigilator_signed) AS Edited_Invigilator_Signed,
        a.center_code              AS Center_Code,
        a.subcenter_code           AS SubCenter_Code,
        a.subject_code             AS Subject_Code,
        a.disc_resolved            AS IsResolved,
        a.updated_at               AS UpdatedAt
    FROM dbo.attendance_sheet_data_1 a
    WHERE a.invigilator_signed = 0
    AND a.disc_resolved = 0

    UNION ALL

    SELECT
        b.id                       AS ID,
        N'Type2'                   AS Sheet_Type,
        b.filename                 AS FileName,
        b.invigilator_signed       AS Invigilator_Signed,
        ISNULL(b.edited_invigilator_signed, b.invigilator_signed) AS Edited_Invigilator_Signed,
        b.center_code              AS Center_Code,
        b.subcenter_code           AS SubCenter_Code,
        b.subject_code             AS Subject_Code,
        b.disc_resolved            AS IsResolved,
        b.updated_at               AS UpdatedAt
    FROM dbo.attendance_sheet_data2 b
    WHERE b.invigilator_signed = 0
    AND b.disc_resolved = 0

    ORDER BY FileName;
END;
GO

-- =============================================================
-- UPDATE PROCEDURES — one per applicable report
-- =============================================================

-- Update Report 1: Subject Code & Booklet Serial No
CREATE OR ALTER PROCEDURE dbo.Disc_Update_SubjectBooklet
    @ID       INT,
    @SubjectCode   NVARCHAR(100),
    @BookletSlNo   NVARCHAR(100),
    @UpdatedBy     INT = NULL
AS
BEGIN
    SET NOCOUNT ON; SET XACT_ABORT ON;
    UPDATE dbo.omr_results
    SET edited_subject_code  = NULLIF(LTRIM(RTRIM(@SubjectCode)),  N''),
        edited_booklet_sl_no = NULLIF(LTRIM(RTRIM(@BookletSlNo)),  N''),
        updated_by = @UpdatedBy,
        updated_at = SYSUTCDATETIME(),
        disc_resolved = 1,
        disc_resolved_at = SYSUTCDATETIME(),
        disc_resolved_by = @UpdatedBy
    WHERE id = @ID;
    IF @@ROWCOUNT = 0 THROW 50010, 'Record not found.', 1;
END;
GO

-- Update Report 2: Barcode
CREATE OR ALTER PROCEDURE dbo.Disc_Update_Barcode
    @ID INT, @Barcode NVARCHAR(100), @UpdatedBy INT = NULL
AS
BEGIN
    SET NOCOUNT ON; SET XACT_ABORT ON;
    UPDATE dbo.omr_results
    SET edited_barcode = NULLIF(LTRIM(RTRIM(@Barcode)), N''),
        updated_by = @UpdatedBy, updated_at = SYSUTCDATETIME(),
        disc_resolved = 1, disc_resolved_at = SYSUTCDATETIME(), disc_resolved_by = @UpdatedBy
    WHERE id = @ID;
    IF @@ROWCOUNT = 0 THROW 50010, 'Record not found.', 1;
END;
GO

-- Update Reports 3 & 4: Register Numbers
CREATE OR ALTER PROCEDURE dbo.Disc_Update_RegNo
    @ID INT,
    @BubbleRegNo       NVARCHAR(50),
    @HandwrittenRegNo  NVARCHAR(50),
    @FinalRegNo        NVARCHAR(50),
    @UpdatedBy INT = NULL
AS
BEGIN
    SET NOCOUNT ON; SET XACT_ABORT ON;
    UPDATE dbo.omr_results
    SET edited_bubble_regno       = NULLIF(LTRIM(RTRIM(@BubbleRegNo)), N''),
        edited_handwritten_regno  = NULLIF(LTRIM(RTRIM(@HandwrittenRegNo)), N''),
        edited_final_regno        = NULLIF(LTRIM(RTRIM(@FinalRegNo)), N''),
        updated_by = @UpdatedBy, updated_at = SYSUTCDATETIME(),
        disc_resolved = 1, disc_resolved_at = SYSUTCDATETIME(), disc_resolved_by = @UpdatedBy
    WHERE id = @ID;
    IF @@ROWCOUNT = 0 THROW 50010, 'Record not found.', 1;
END;
GO

-- Update Reports 5 & 6: Whitener / Bubble threshold — just mark resolved + override final
CREATE OR ALTER PROCEDURE dbo.Disc_Update_BubbleIssue
    @ID INT, @FinalRegNo NVARCHAR(50), @UpdatedBy INT = NULL
AS
BEGIN
    SET NOCOUNT ON; SET XACT_ABORT ON;
    UPDATE dbo.omr_results
    SET edited_final_regno = NULLIF(LTRIM(RTRIM(@FinalRegNo)), N''),
        updated_by = @UpdatedBy, updated_at = SYSUTCDATETIME(),
        disc_resolved = 1, disc_resolved_at = SYSUTCDATETIME(), disc_resolved_by = @UpdatedBy
    WHERE id = @ID;
    IF @@ROWCOUNT = 0 THROW 50010, 'Record not found.', 1;
END;
GO

-- Update Reports 7 & 8: Counter Foil Signatures
CREATE OR ALTER PROCEDURE dbo.Disc_Update_CounterFoilSignature
    @ID INT, @CandidateSigned NVARCHAR(10), @InvigilatorSigned NVARCHAR(10),
    @UpdatedBy INT = NULL
AS
BEGIN
    SET NOCOUNT ON; SET XACT_ABORT ON;
    UPDATE dbo.omr_results
    SET edited_candidate_signed   = NULLIF(LTRIM(RTRIM(@CandidateSigned)), N''),
        edited_invigilator_signed = NULLIF(LTRIM(RTRIM(@InvigilatorSigned)), N''),
        updated_by = @UpdatedBy, updated_at = SYSUTCDATETIME(),
        disc_resolved = 1, disc_resolved_at = SYSUTCDATETIME(), disc_resolved_by = @UpdatedBy
    WHERE id = @ID;
    IF @@ROWCOUNT = 0 THROW 50010, 'Record not found.', 1;
END;
GO

-- Update Report 9: Non-Standard OMR
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
    IF @@ROWCOUNT = 0 THROW 50010, 'Record not found.', 1;
END;
GO

-- Update Reports 10 & 11: Nominal Roll rows
CREATE OR ALTER PROCEDURE dbo.Disc_Update_NominalRollRow
    @ID             INT,
    @SheetType      NVARCHAR(10),   -- 'Type1' or 'Type2'
    @RegistrationNo NVARCHAR(50) = NULL,
    @QcabSerialNo   NVARCHAR(50) = NULL,
    @SignaturePresent BIT = NULL,
    @InvigilatorSigned BIT = NULL,
    @UpdatedBy      INT = NULL
AS
BEGIN
    SET NOCOUNT ON; SET XACT_ABORT ON;

    IF @SheetType = N'Type1'
    BEGIN
        UPDATE dbo.attendance_sheet_data_1
        SET edited_registration_no   = NULLIF(LTRIM(RTRIM(@RegistrationNo)), N''),
            edited_signature_present  = @SignaturePresent,
            edited_invigilator_signed = @InvigilatorSigned,
            updated_by = @UpdatedBy, updated_at = SYSUTCDATETIME(), disc_resolved = 1
        WHERE id = @ID;
    END
    ELSE
    BEGIN
        UPDATE dbo.attendance_sheet_data2
        SET edited_registration_no   = NULLIF(LTRIM(RTRIM(@RegistrationNo)), N''),
            edited_qcab_serial_no    = NULLIF(LTRIM(RTRIM(@QcabSerialNo)), N''),
            edited_signature_present  = @SignaturePresent,
            edited_invigilator_signed = @InvigilatorSigned,
            updated_by = @UpdatedBy, updated_at = SYSUTCDATETIME(), disc_resolved = 1
        WHERE id = @ID;
    END;

    IF @@ROWCOUNT = 0 THROW 50010, 'Record not found.', 1;
END;
GO

-- =============================================================
-- Seed the 11 reports into ExportReport (for download panel)
-- =============================================================
MERGE dbo.ExportReport AS tgt
USING (VALUES
    (N'1. Subject Code & Booklet Serial No',  N'dbo.Disc_SubjectCodeBookletNo',           NULL),
    (N'2. Barcode Discrepancy',               N'dbo.Disc_BarcodeDiscrepancy',             NULL),
    (N'3. Written RegNo Discrepancy',         N'dbo.Disc_WrittenRegNoDiscrepancy',        NULL),
    (N'4. OMR RegNo Discrepancy',             N'dbo.Disc_OMRRegNoDiscrepancy',            NULL),
    (N'5. Whitener Used in Bubbles',          N'dbo.Disc_WhitenerUsed',                   NULL),
    (N'6. Bubbles Marked <35% Threshold',     N'dbo.Disc_BubbleThreshold',                NULL),
    (N'7. Candidate Signature Discrepancy',   N'dbo.Disc_CandidateSignature',             NULL),
    (N'8. Invigilator Signature Discrepancy', N'dbo.Disc_InvigilatorSignature',           NULL),
    (N'9. Non-Standard OMR Sheet',            N'dbo.Disc_NonStandardOMR',                 NULL),
    (N'10. Candidate Not Signed - Nominal Roll', N'dbo.Disc_NominalRollCandidateSignature', NULL),
    (N'11. Invigilator Not Signed - Nominal Roll',N'dbo.Disc_NominalRollInvigilatorSignature',NULL)
) AS src (ReportName, ProcedureName, Parametres)
ON tgt.ReportName = src.ReportName
WHEN NOT MATCHED THEN
    INSERT (ReportName, ProcedureName, Parametres)
    VALUES (src.ReportName, src.ProcedureName, src.Parametres);
GO

PRINT 'DiscrepancyReports.sql applied successfully.';
GO
