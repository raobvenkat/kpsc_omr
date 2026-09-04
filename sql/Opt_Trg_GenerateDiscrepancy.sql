USE [KPSCDataExtraction]
GO

/****** Object:  Trigger [dbo].[Trg_GenerateDiscrepancy] ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

-- ============================================================================
-- Optimized Trigger: Trg_GenerateDiscrepancy
-- Description: Inserts discrepancy records into CounterFoilData in a single
--              statement directly from the inserted table without secondary UPDATE
--              queries or redundant table joins.
-- ============================================================================
ALTER TRIGGER [dbo].[Trg_GenerateDiscrepancy]
ON [dbo].[omr_results]
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;

    INSERT INTO CounterFoilData
    (
        id,
        filename,
        barcode,
        bubble_regno,
        handwritten_regno,
        final_regno,
        discrepancy,
        discrepancy_detail,
        candidate_signed,
        invigilator_signed,
        subject_code,
        BookletSlNo,
        created_at,
        omr_threshold,
        whitenerflag,
        isblack,
        bubble_Th_status,
        BarcodeDesc,
        OMRRegNoDesc,
        ICRRegNoDesc,
        CandSigDesc,
        InvSignDesc,
        SubCodeDesc,
        BSlNoDesc,
        whitenerDesc,
        isBlackDesc,
        ThDesc,
        FinalDesc,
        updated_at,
        updated_by
    )
    SELECT
        I.id,
        I.filename,
        I.barcode,
        I.bubble_regno,
        I.handwritten_regno,
        I.final_regno,
        I.discrepancy,
        I.discrepancy_detail,
        I.candidate_signed,
        I.invigilator_signed,
        I.subject_code,
        I.BookletSlNo,
        I.created_at,
        I.omr_threshold,
        I.whitenerflag,
        I.isblack,
        I.bubble_Th_status,

        -- Flag logic
        IIF(REPLACE(ISNULL(I.barcode,''),' ','')='',1,0) AS BarcodeDesc,
        IIF(LEN(REPLACE(ISNULL(I.bubble_regno,''),' ',''))<9,1,0) AS OMRRegNoDesc,
        IIF(LEN(REPLACE(ISNULL(I.handwritten_regno,''),' ',''))<9,1,0) AS ICRRegNoDesc,
        IIF(I.candidate_signed=1,0,1) AS CandSigDesc,
        IIF(I.invigilator_signed=1,0,1) AS InvSignDesc,
        IIF(LEN(REPLACE(ISNULL(I.subject_code,''),' ',''))<3,1,0) AS SubCodeDesc,
        IIF(LEN(REPLACE(ISNULL(I.BookletSlNo,''),' ',''))<7,1,0) AS BSlNoDesc,

        I.whitenerflag AS whitenerDesc,
        I.isblack AS isBlackDesc,
        I.bubble_Th_status AS ThDesc,

        -- Inline calculation of FinalDesc to avoid secondary UPDATE statement
        CASE
            WHEN REPLACE(ISNULL(I.barcode,''),' ','')=''
              OR LEN(REPLACE(ISNULL(I.bubble_regno,''),' ',''))<9
              OR LEN(REPLACE(ISNULL(I.handwritten_regno,''),' ',''))<9
              OR I.candidate_signed <> 1
              OR I.invigilator_signed <> 1
              OR LEN(REPLACE(ISNULL(I.subject_code,''),' ',''))<3
              OR LEN(REPLACE(ISNULL(I.BookletSlNo,''),' ',''))<7
              OR I.whitenerflag = 1
              OR I.isblack = 1
              OR I.bubble_Th_status = 1
            THEN 1
            ELSE 0
        END AS FinalDesc,

        GETDATE(),
        1
    FROM inserted I;

END;
GO
