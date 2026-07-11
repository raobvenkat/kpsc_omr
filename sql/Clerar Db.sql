Select * from [dbo].[omr_results] where whitenerflag=1

Select * from [dbo].[CounterFoilEditedData]
Select * from [dbo].[CounterFoilEditedDataLog]
Select * from [dbo].[attendance_sheet_data_1]
Select * from [dbo].[attendance_sheet_data2]
--whitenerflag, bubble_Th_status



------------------- DB Clear Query
Truncate table [dbo].[omr_results]
Truncate table [dbo].[CounterFoilEditedDataLog]
Truncate table [dbo].[CounterFoilEditedData]
Truncate table [attendance_sheet_data_1]
Truncate table [attendance_sheet_data2]
Truncate table [dbo].[ErrorLog]
Truncate table [dbo].[application_audit_log]
---Truncate table 

ALTER TABLE dbo.omr_results
ADD bubble_Th_status BIT NOT NULL
    CONSTRAINT DF_omr_results_bubble_Th_status DEFAULT (0);