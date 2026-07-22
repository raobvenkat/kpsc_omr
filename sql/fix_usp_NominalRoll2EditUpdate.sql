-- ============================================================
-- PATCH: Fix usp_NominalRoll2EditUpdate
-- Problem : second UPDATE was writing 0/1 flags back into
--           [center_code] and [subcenter_code] instead of into
--           their descriptor columns CenterCodeDesc / SubCenterCodeDesc.
-- Fix     : route those calculations to the correct columns.
-- Run this script in SSMS against your CLIENT_ICR database.
-- ============================================================

ALTER PROCEDURE [dbo].[usp_NominalRoll2EditUpdate]
(
    @EditFor      varchar(200),
    @UserID       int,
    @ID           int,
    @CenterCode   varchar(20),
    @SubCenterCode varchar(20),
    @SubCode      varchar(10),
    @OMRNo        varchar(20),
    @RegNo        varchar(20),
    @CandSig      bit,
    @InvSign      bit
)
AS
BEGIN

    SET NOCOUNT ON;

    BEGIN TRY

        BEGIN

            -- 1. Audit: snapshot the row before editing
            INSERT INTO NominalRoll2EditLog (
                [id], [filename], [center_code], [subcenter_code],
                [subject_code], [invigilator_signed], [row_number], [status],
                [signature_present], qcab_serial_no, [registration_no],
                [created_at], [CreatedBy], [CenterCodeDesc], [SubCenterCodeDesc],
                [SubDesc], [StatusDesc], [CandSignDesc], [InvSignDesc],
                QCABDesc, [RegNoDesc], [FinalDesc],
                [EditFor], [EditSkip], [EditUserID], [EditedOn]
            )
            SELECT
                [id], [filename], [center_code], [subcenter_code],
                [subject_code], [invigilator_signed], [row_number], [status],
                [signature_present], qcab_serial_no, registration_no,
                [created_at], [CreatedBy], [CenterCodeDesc], [SubCenterCodeDesc],
                [SubDesc], [StatusDesc], [CandSignDesc], [InvSignDesc],
                QCABDesc, [RegNoDesc], [FinalDesc],
                [EditFor], [EditSkip], [EditUserID], [EditedOn]
            FROM NominalRoll2
            WHERE ID = @ID;

            -- 2. Save the user-supplied values
            UPDATE NominalRoll2
            SET
                [center_code]       = @CenterCode,
                [subcenter_code]    = @SubCenterCode,
                [subject_code]      = @SubCode,
                [signature_present] = @CandSig,
                [invigilator_signed]= @InvSign,
                qcab_serial_no      = @OMRNo,
                [registration_no]   = @RegNo,
                [EditFor]           = @EditFor,
                [EditUserID]        = @UserID,
                [EditedOn]          = GETDATE()
            WHERE ID = @ID;

            -- 3. Recalculate descriptor / validation flags
            --    NOTE: CenterCodeDesc and SubCenterCodeDesc are written here,
            --          NOT center_code / subcenter_code (that was the original bug).
            UPDATE NominalRoll2
            SET
                CenterCodeDesc    = iif(len(Replace([center_code],   ' ', '')) < 1, 1, 0),
                SubCenterCodeDesc = iif(len(Replace([subcenter_code],' ', '')) < 1, 1, 0),
                [SubDesc]         = iif(len(Replace([subject_code],  ' ', '')) < 3, 1, 0),
                QCABDesc          = iif(len(Replace(qcab_serial_no,  ' ', '')) < 7, 1, 0),
                RegNoDesc         = iif(len(Replace([registration_no],' ','')) < 9, 1, 0),
                CandSignDesc      = iif([signature_present]  = 1, 0, 1),
                InvSignDesc       = iif([invigilator_signed] = 1, 0, 1),
                AnsentAndSigPresent  = iif(([status] = 'Absent'  AND [Signature_Present] = 1), 'True', 'False'),
                PresentAndNoSignature= iif(([status] = 'Present' AND [Signature_Present] = 0), 'True', 'False')
            WHERE ID = @ID;

            -- 4. Roll up FinalDesc
            UPDATE NominalRoll2
            SET FinalDesc = 1
            WHERE ID = @ID
              AND (   CenterCodeDesc    = 1
                   OR SubCenterCodeDesc = 1
                   OR [SubDesc]         = 1
                   OR StatusDesc        = 1
                   OR PresentAndNoSignature = 1
                   OR AnsentAndSigPresent   = 1
                   OR InvSignDesc       = 1
                   OR RegNoDesc         = 1
                   OR QCABDesc          = 1 );

            UPDATE NominalRoll2
            SET FinalDesc = 0
            WHERE ID = @ID
              AND CenterCodeDesc    = 0
              AND SubCenterCodeDesc = 0
              AND [SubDesc]         = 0
              AND StatusDesc        = 0
              AND PresentAndNoSignature = 0
              AND AnsentAndSigPresent   = 0
              AND InvSignDesc       = 0
              AND RegNoDesc         = 0
              AND QCABDesc          = 0;

        END

    END TRY
    BEGIN CATCH

        INSERT INTO ErrorLog ([ErrorScreen], [ErrorModule], ErrorText, ErrorTime)
        VALUES (
            'NominalRoll2Edited',
            'usp_NominalRoll2EditUpdate',
            ERROR_MESSAGE(),
            GETDATE()
        );

    END CATCH

END
GO
