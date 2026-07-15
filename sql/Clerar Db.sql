Select * from [dbo].[omr_results] where whitenerflag=1

Select * from [dbo].[CounterFoilData]
Select * from [dbo].[CounterFoilDataEditLog]
Select * from [dbo].[attendance_sheet_data_1]
Select * from [dbo].[attendance_sheet_data2]
Select * from [dbo].[NominalRoll1]
Select * from [dbo].[NominalRoll1EditLog]
Select * from [dbo].[ErrorLog]
Select ID, ReportFor, ReportName, ProcedureName from [dbo].[ExportReport]
--whitenerflag, bubble_Th_status
('42S02', "[42S02] [Microsoft][ODBC Driver 17 for SQL Server][SQL Server]Invalid object name 'CounterFoilDataEdit'. (208) (SQLExecDirectW)")
Select * from [dbo].[error_log]
------------------- DB Clear Query
Truncate table [dbo].[omr_results]
Truncate table [dbo].[CounterFoilEditedDataLog]
Truncate table [dbo].[CounterFoilEditedData]
Truncate table [attendance_sheet_data_1]
Truncate table [attendance_sheet_data2]
Truncate table [dbo].[CounterFoilData]
Truncate table [dbo].[CounterFoilDataEditLog]
Truncate table [dbo].[CounterFoilEditedDataLog]
Truncate table [dbo].[CounterFoilEditedData]
Truncate table [dbo].[NominalRoll1]
Truncate table [dbo].[NominalRoll2]
Truncate table [dbo].[NominalRoll1EditLog]
Truncate table [dbo].[NominalRoll2EditLog]

Truncate table [dbo].[ErrorLog]
Truncate table [dbo].[application_audit_log]
---Truncate table 

ALTER TABLE dbo.omr_results
ADD bubble_Th_status BIT NOT NULL
    CONSTRAINT DF_omr_results_bubble_Th_status DEFAULT (0);