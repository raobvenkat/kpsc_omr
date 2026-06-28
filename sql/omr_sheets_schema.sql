-- Adjust types, lengths, constraints to match your requirements.

CREATE TABLE dbo.omr_results
(
    omr_result_id BIGINT IDENTITY(1,1) NOT NULL PRIMARY KEY, -- clustered PK
    exam_id INT NOT NULL,
    student_id BIGINT NOT NULL,
    sheet_id NVARCHAR(100) NOT NULL,
    question_number INT NOT NULL,
    answer NVARCHAR(50) NULL,
    correct_answer NVARCHAR(50) NULL,
    is_correct BIT NOT NULL CONSTRAINT DF_omr_results_is_correct DEFAULT (0),
    score DECIMAL(5,2) NOT NULL CONSTRAINT DF_omr_results_score DEFAULT (0.00),
    confidence_score DECIMAL(5,4) NULL,
    raw_image VARBINARY(MAX) NULL,           -- optional: store scanned image
    processed_image_path NVARCHAR(400) NULL, -- optional reference to file share / blob
    graded_by SYSNAME NULL,
    graded_at DATETIME2(7) NULL,
    created_at DATETIME2(7) NOT NULL CONSTRAINT DF_omr_results_created_at DEFAULT (SYSUTCDATETIME()),
    updated_at DATETIME2(7) NULL,
    CONSTRAINT UQ_omr_results_exam_student_sheet_question UNIQUE (exam_id, student_id, sheet_id, question_number)
);
GO

-- Recommended nonclustered indexes (modify fillfactor, include columns as needed)
CREATE INDEX IX_omr_results_exam_student ON dbo.omr_results (exam_id, student_id);
CREATE INDEX IX_omr_results_sheet_question ON dbo.omr_results (sheet_id, question_number);
GO