USE [KPSCOMRICRExtractionV2]
GO

/****** Object:  Table [dbo].[attendance_sheet_data_1]    Script Date: 08/07/2026 02:07 PM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[NominalRoll1](
	[id] [int] NOT NULL,
	[filename] [varchar](500) NOT NULL,
	[center_code] [varchar](50) NULL,
	[subcenter_code] [varchar](50) NULL,
	[subject_code] [varchar](50) NULL,
	[invigilator_signed] [bit] NOT NULL,
	[row_number] [int] NOT NULL,
	[status] [varchar](50) NULL,
	[signature_present] [bit] NOT NULL,
	[omr_no] [varchar](50) NULL,
	[registration_no] [varchar](50) NULL,
	[qpvc] [varchar](1) NULL,
	[created_at] [datetime2](0) NOT NULL,
	CreatedBy	int	NULL,
	CenterCodeDesc [bit]  NULL,
	SubCenterCodeDesc [bit]  NULL,
	SubDesc [bit]  NULL,
	StatusDesc [bit]  NULL,
	CandSignDesc [bit]  NULL,
	InvSignDesc [bit]  NULL,
	OMRDesc [bit]  NULL,
	RegNoDesc [bit]  NULL,
	QPVCDesc [bit]  NULL,
	FinalDesc [bit]  NULL,
	EditFor  [varchar](100) NULL,
	[EditUserID] int null,
	[EditedOn] int null,
 CONSTRAINT [PK_NominalRoll1] PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
CREATE TABLE [dbo].[NominalRoll1EditLog](
	[EditID] [int] IDENTITY(1,1) NOT NULL,
	[id] [int]  NOT NULL,
	[filename] [varchar](500) NOT NULL,
	[center_code] [varchar](50) NULL,
	[subcenter_code] [varchar](50) NULL,
	[subject_code] [varchar](50) NULL,
	[invigilator_signed] [bit] NOT NULL,
	[row_number] [int] NOT NULL,
	[status] [varchar](50) NULL,
	[signature_present] [bit] NOT NULL,
	[omr_no] [varchar](50) NULL,
	[registration_no] [varchar](50) NULL,
	[qpvc] [varchar](1) NULL,
	[created_at] [datetime2](0) NOT NULL,
	CreatedBy	int	NULL,
	CenterCodeDesc [bit]  NULL,
	SubCenterCodeDesc [bit]  NULL,
	SubDesc [bit]  NULL,
	StatusDesc [bit]  NULL,
	CandSignDesc [bit]  NULL,
	InvSignDesc [bit]  NULL,
	OMRDesc [bit]  NULL,
	RegNoDesc [bit]  NULL,
	QPVCDesc [bit]  NULL,
	FinalDesc [bit]  NULL,
	EditFor  [varchar](100) NULL,
	[EditUserID] int null,
	[EditedOn] int null,
 CONSTRAINT [PK_NominalRoll1EditLog] PRIMARY KEY CLUSTERED 
(
	[EditID] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO

SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[NominalRoll2](
	[id] [int]  NOT NULL,
	[filename] [varchar](500) NOT NULL,
	[center_code] [varchar](50) NULL,
	[subcenter_code] [varchar](50) NULL,
	[subject_code] [varchar](50) NULL,
	[invigilator_signed] [bit] NOT NULL,
	[row_number] [int] NOT NULL,
	[status] [varchar](50) NULL,
	[signature_present] [bit] NOT NULL,
	[registration_no] [varchar](50) NULL,
	[qcab_serial_no] [varchar](50) NULL,
	[created_at] [datetime2](0) NOT NULL,
	[CreatedBy] [int] NULL,
	CenterCodeDesc [bit]  NULL,
	SubCenterCodeDesc [bit]  NULL,
	SubDesc [bit]  NULL,
	StatusDesc [bit]  NULL,
	CandSignDesc [bit]  NULL,
	InvSignDesc [bit]  NULL,	
	RegNoDesc [bit]  NULL,
	QCABDesc [bit]  NULL,
	FinalDesc [bit]  NULL,
	EditFor  [varchar](100) NULL,
	[EditUserID] int null,
	[EditedOn] int null,
 CONSTRAINT [PK_NominalRoll2] PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO

CREATE TABLE [dbo].[NominalRoll2EditLog](
	[EditID] [int] IDENTITY(1,1) NOT NULL,
	[id] [int],
	[filename] [varchar](500) NOT NULL,
	[center_code] [varchar](50) NULL,
	[subcenter_code] [varchar](50) NULL,
	[subject_code] [varchar](50) NULL,
	[invigilator_signed] [bit] NOT NULL,
	[row_number] [int] NOT NULL,
	[status] [varchar](50) NULL,
	[signature_present] [bit] NOT NULL,
	[registration_no] [varchar](50) NULL,
	[qcab_serial_no] [varchar](50) NULL,
	[created_at] [datetime2](0) NOT NULL,
	[CreatedBy] [int] NULL,
	CenterCodeDesc [bit]  NULL,
	SubCenterCodeDesc [bit]  NULL,
	SubDesc [bit]  NULL,
	StatusDesc [bit]  NULL,
	CandSignDesc [bit]  NULL,
	InvSignDesc [bit]  NULL,	
	RegNoDesc [bit]  NULL,
	QCABDesc [bit]  NULL,
	FinalDesc [bit]  NULL,
	EditFor  [varchar](100) NULL,
	[EditUserID] int null,
	[EditedOn] int null,
 CONSTRAINT [PK_NominalRoll2EditLog] PRIMARY KEY CLUSTERED 
(
	[EditID] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO


SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
-- =============================================
-- Author:		<Venkat Rao>
-- Create date: <07/07/2026>
-- Description:	<Generating discrepancies for counter Foil sheet, Nominal Roll 1 & 2 >
-- =============================================
CREATE or Alter PROCEDURE USP_GenerateDiscrepancy 
	@DiscrFor VARCHAR(50),@UserID int
	AS
BEGIN
	-- SET NOCOUNT ON added to prevent extra result sets from
	-- interfering with SELECT statements.
	SET NOCOUNT ON;

    -- Insert statements for procedure here
	if @DiscrFor = 'Counter Foil'
		Begin
		--Declare @UserID int =1;
			Insert into CounterFoilData ([id],
			[filename], [barcode], [bubble_regno], [handwritten_regno],
			[final_regno], [discrepancy], [discrepancy_detail], [candidate_signed],
			[invigilator_signed], [subject_code], [BookletSlNo], [created_at],
			[omr_threshold], [whitenerflag], [isblack],[bubble_Th_status],
			BarcodeDesc, OMRRegNoDesc, ICRRegNoDesc, CandSigDesc, InvSignDesc, SubCodeDesc,
			BSlNoDesc, whitenerDesc, isBlackDesc, ThDesc,updated_at,updated_by)
			Select O.id,O.[filename], O.[barcode], O.[bubble_regno],O.[handwritten_regno], O.[final_regno], O.[discrepancy],
				O.[discrepancy_detail], O.[candidate_signed], O.[invigilator_signed],O.[subject_code], O.[BookletSlNo],
				 O.[created_at], O.[omr_threshold], O.[whitenerflag],O.[isblack],O.[bubble_Th_status],
				iif(Replace(O.[barcode],' ','')='','1',0) BarcodeDesc, iif(len(Replace(O.[bubble_regno],' ',''))<9,'1',0) OMRRegNoDesc, iif(len(Replace(O.[handwritten_regno],' ',''))<9,'1',0) ICRRegNoDesc,
				O.[candidate_signed] CandSigDesc, O.[invigilator_signed] InvSignDesc, iif(len(Replace(O.[subject_code],' ',''))<3,'1',0) SubCodeDesc, iif(len(Replace(O.[BookletSlNo],' ',''))<7,'1',0) BSlNoDesc,
				O.[whitenerflag] whitenerDesc, O.[isblack] isBlackDesc, O.[bubble_Th_status] ThDesc, Getdate(),@UserID  
			from [dbo].[omr_results] O Left join CounterFoilData D on O.id = D.id
			where D.ID is Null
			Update CounterFoilData Set FinalDesc = 1 where BarcodeDesc=1 or OMRRegNoDesc =1 or ICRRegNoDesc=1 or CandSigDesc=0 or InvSignDesc=0 or SubCodeDesc=1 or 
				BSlNoDesc=1 or whitenerDesc=1 or isBlackDesc =1 or ThDesc = 1
			Update CounterFoilData Set FinalDesc = 0 where BarcodeDesc=0 AND OMRRegNoDesc =0 AND ICRRegNoDesc=0 AND CandSigDesc=1 AND InvSignDesc=1 AND SubCodeDesc=0 AND 
				BSlNoDesc=0 AND whitenerDesc=0 AND isBlackDesc =0 AND ThDesc = 0
			Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], [barcode], [bubble_regno], [handwritten_regno],
			--[final_regno], [discrepancy], [discrepancy_detail], [candidate_signed],[invigilator_signed],
			 [subject_code], [BookletSlNo],-- [created_at],[omr_threshold], 
			--[whitenerflag], isblack ,[updated_at], [updated_by],
			 BarcodeDesc, OMRRegNoDesc, ICRRegNoDesc, CandSigDesc, 
			InvSignDesc, SubCodeDesc, BSlNoDesc,  WhitenerDesc WhitenerApplied, isBlackDesc [Non Standard Sheet], ThDesc [Threshold < 35%], FinalDesc FinalStatus from CounterFoilData where FinalDesc =1
			--Select
		end
	else if @DiscrFor = 'Nominal Roll 1 (Descriptive Test)'
		Begin
		--Declare @UserID int =1;
		  insert into NominalRoll1 ([id],[filename],[center_code]
			,[subcenter_code],[subject_code],[invigilator_signed],[row_number]
			,[status],[signature_present],[omr_no],[registration_no],[qpvc]
			,[CenterCodeDesc],[SubCenterCodeDesc],[SubDesc]
			,[StatusDesc],[CandSignDesc],[InvSignDesc],[OMRDesc]
			,[RegNoDesc],[QPVCDesc],[created_at],[CreatedBy])
		  Select A.[id],A.[filename],A.[center_code]
			,A.[subcenter_code],A.[subject_code],A.[invigilator_signed],A.[row_number]
			,A.[status],A.[signature_present],A.[omr_no],A.[registration_no],A.[qpvc]
			,iif(len(Replace(A.[center_code],' ',''))<1,1,0) CenterCodeDesc,iif(len(Replace(A.[subcenter_code],' ',''))<1,1,0) [SubCenterCodeDesc],iif(len(Replace(A.[subject_code],' ',''))<3,1,0) [SubDesc]
			,iif(len(Replace(A.[status],' ',''))<1,1,0) StatusDesc, A.[signature_present] CandSignDesc,A.[invigilator_signed] [InvSignDesc],iif(len(Replace(A.[omr_no],' ',''))<7,'1',0) OMRoDesc
			,iif(len(Replace(A.[registration_no],' ',''))<9,'1',0) RegNoDesc ,iif(len(Replace(A.[qpvc],' ',''))<1,1,0)  QPVCDesc ,getdate() created_at,@UserID CreatedBy 
			from [dbo].[attendance_sheet_data_1] A  Left join [dbo].[NominalRoll1] N 
			on A.ID=N.ID where N.id is null
		 Update [NominalRoll1] set  [FinalDesc] =1 where CenterCodeDesc =1 or SubCenterCodeDesc =1 or SubDesc =1 or StatusDesc=1 or CandSignDesc =0 or InvSignDesc=0 or  OMRDesc=1 or  RegNoDesc=1 or QPVCDesc =1  
		 Update [NominalRoll1] set  [FinalDesc] =0 where CenterCodeDesc =0 AND SubCenterCodeDesc =0 AND SubDesc =0 AND StatusDesc=0 AND CandSignDesc =1 AND InvSignDesc=1 AND OMRDesc=0 AND   RegNoDesc=0 AND QPVCDesc =0  
		 SELECT ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,[id],[filename],[center_code],[subcenter_code],[subject_code]
			,[row_number],[omr_no],[registration_no],[qpvc],[CenterCodeDesc],
			[SubCenterCodeDesc],[SubDesc],[StatusDesc] Attendance,[CandSignDesc],[InvSignDesc],[OMRDesc]
			,[RegNoDesc],[QPVCDesc],[FinalDesc] from [NominalRoll1] where FinalDesc =1
		end
	else if @DiscrFor = 'Nominal Roll 2 (OMR Test)'
		Begin
		--Declare @UserID int =1;
		 insert into NominalRoll2 ([id],[filename],[center_code]
			,[subcenter_code],[subject_code],[invigilator_signed],[row_number]
			,[status],[signature_present],[registration_no],[qcab_serial_no]
			,[CenterCodeDesc],[SubCenterCodeDesc],[SubDesc]
			,[StatusDesc],[CandSignDesc],[InvSignDesc]
			,[RegNoDesc],[QCABDesc],[created_at],[CreatedBy])
		  Select A.[id],A.[filename],A.[center_code]
			,A.[subcenter_code],A.[subject_code],A.[invigilator_signed],A.[row_number]
			,A.[status],A.[signature_present],A.[registration_no],A.[qcab_serial_no]
			,iif(len(Replace(A.[center_code],' ',''))<1,1,0) CenterCodeDesc,iif(len(Replace(A.[subcenter_code],' ',''))<1,1,0) [SubCenterCodeDesc],iif(len(Replace(A.[subject_code],' ',''))<3,1,0) [SubDesc]
			,iif(len(Replace(A.[status],' ',''))<1,1,0) StatusDesc, A.[signature_present] CandSignDesc,A.[invigilator_signed] [InvSignDesc]
			,iif(len(Replace(A.[registration_no],' ',''))<9,1,0) RegNoDesc,iif(len(Replace(A.[qcab_serial_no],' ',''))<7,1,0)  QCABDesc ,getdate() created_at,@UserID CreatedBy 
			from [dbo].[attendance_sheet_data2] A  Left join [dbo].[NominalRoll2] N 
			on A.ID=N.ID where N.id is null
		 Update [NominalRoll2] set  [FinalDesc] =1 where CenterCodeDesc =1 or SubCenterCodeDesc =1 or SubDesc =1 or StatusDesc=1 or CandSignDesc =0 or InvSignDesc=0 or  RegNoDesc=1 or QCABDesc =1  
		 Update [NominalRoll2] set  [FinalDesc] =0 where CenterCodeDesc =0 AND SubCenterCodeDesc =0 AND SubDesc =0 AND StatusDesc=0 AND CandSignDesc =1 AND InvSignDesc=1 AND  RegNoDesc=0 AND QCABDesc =0  
		 SELECT ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,[id],[filename],[center_code],[subcenter_code],[subject_code]
			,[row_number],[status]
			,[registration_no],[qcab_serial_no],[CenterCodeDesc],
			[SubCenterCodeDesc],[SubDesc],[StatusDesc] Attendance,[CandSignDesc],[InvSignDesc]
			,[RegNoDesc],[QCABDesc],[FinalDesc] from [NominalRoll2] where FinalDesc =1
		end

END
GO

Create or Alter Procedure usp_LoadCounterfoilEditGrid 
	@EditFor varchar (200), @UserID int
As
Begin
	if @EditFor ='Full Data'
	begin
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], [barcode], [bubble_regno], [handwritten_regno],
			 [subject_code], [BookletSlNo], CandSigDesc, 
			InvSignDesc, WhitenerDesc WhitenerApplied, isBlackDesc [Non Standard Sheet], ThDesc [Threshold < 35%], FinalDesc FinalStatus from CounterFoilData --where FinalDesc =1
	end
	else if @EditFor ='All discrepancy data'
	begin
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], [barcode], [bubble_regno], [handwritten_regno],
			 [subject_code], [BookletSlNo], CandSigDesc, 
			InvSignDesc, WhitenerDesc WhitenerApplied, isBlackDesc [Non Standard Sheet], ThDesc [Threshold < 35%], FinalDesc FinalStatus from CounterFoilData where FinalDesc =1
	end
	else if @EditFor ='Subject Code & Booklet Serial No discrepancy'
	begin
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], [barcode], [bubble_regno], [handwritten_regno],
			 [subject_code], [BookletSlNo], CandSigDesc, 
			InvSignDesc, WhitenerDesc WhitenerApplied, isBlackDesc [Non Standard Sheet], ThDesc [Threshold < 35%], FinalDesc FinalStatus from CounterFoilData where SubCodeDesc =1 or BSlNoDesc =1
	end
	else if @EditFor ='Barcode discrepancy'
	begin
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], [barcode], [bubble_regno], [handwritten_regno],
			 [subject_code], [BookletSlNo], CandSigDesc, 
			InvSignDesc, WhitenerDesc WhitenerApplied, isBlackDesc [Non Standard Sheet], ThDesc [Threshold < 35%], FinalDesc FinalStatus from CounterFoilData where BarcodeDesc =1 
	end
	else if @EditFor ='Written RegNo discrepancy'
	begin
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], [barcode], [bubble_regno], [handwritten_regno],
			 [subject_code], [BookletSlNo], CandSigDesc, 
			InvSignDesc, WhitenerDesc WhitenerApplied, isBlackDesc [Non Standard Sheet], ThDesc [Threshold < 35%], FinalDesc FinalStatus from CounterFoilData where ICRRegNoDesc=1
	end
	else if @EditFor ='OMR RegNo discrepancy'
	begin
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], [barcode], [bubble_regno], [handwritten_regno],
			 [subject_code], [BookletSlNo], CandSigDesc, 
			InvSignDesc, WhitenerDesc WhitenerApplied, isBlackDesc [Non Standard Sheet], ThDesc [Threshold < 35%], FinalDesc FinalStatus from CounterFoilData where OMRRegNoDesc=1
	end
	else if @EditFor ='Whiter Used in the boubles'
	begin
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], [barcode], [bubble_regno], [handwritten_regno],
			 [subject_code], [BookletSlNo], CandSigDesc, 
			InvSignDesc, WhitenerDesc WhitenerApplied, isBlackDesc [Non Standard Sheet], ThDesc [Threshold < 35%], FinalDesc FinalStatus from CounterFoilData where WhitenerDesc=1
	end
	else if @EditFor ='Boubles marked <35% Threshold marking'
	begin
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], [barcode], [bubble_regno], [handwritten_regno],
			 [subject_code], [BookletSlNo], CandSigDesc, 
			InvSignDesc, WhitenerDesc WhitenerApplied, isBlackDesc [Non Standard Sheet], ThDesc [Threshold < 35%], FinalDesc FinalStatus from CounterFoilData where ThDesc=1
	end
	else if @EditFor ='Candidate''s Signature discrepancy'
	begin
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], [barcode], [bubble_regno], [handwritten_regno],
			 [subject_code], [BookletSlNo], CandSigDesc, 
			InvSignDesc, WhitenerDesc WhitenerApplied, isBlackDesc [Non Standard Sheet], ThDesc [Threshold < 35%], FinalDesc FinalStatus from CounterFoilData where CandSigDesc=1
	end
	else if @EditFor ='Invigilator''s Signature discrepancy'
	begin
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], [barcode], [bubble_regno], [handwritten_regno],
			 [subject_code], [BookletSlNo], CandSigDesc, 
			InvSignDesc, WhitenerDesc WhitenerApplied, isBlackDesc [Non Standard Sheet], ThDesc [Threshold < 35%], FinalDesc FinalStatus from CounterFoilData where InvSignDesc=1
	end
	else if @EditFor ='Non standard OMR sheet used'
	begin
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], [barcode], [bubble_regno], [handwritten_regno],
			 [subject_code], [BookletSlNo], CandSigDesc, 
			InvSignDesc, WhitenerDesc WhitenerApplied, isBlackDesc [Non Standard Sheet], ThDesc [Threshold < 35%], FinalDesc FinalStatus from CounterFoilData where isBlackDesc=1
	end

End

go

Create or Alter Procedure usp_CounterFoilEditSkip @EditFor varchar(200), @UserID int ,@ID int
As
Begin
	Insert into [dbo].[CounterFoilDataEditLog] select * from CounterFoilData where ID = @ID;
	update CounterFoilData set EditSkip =1,[EditFor]= @EditFor,[EditUserID]= @UserID,[EditedOn]=getdate() where id = @ID;
end

go

Create or Alter Procedure usp_NominalRoll1EditSkip @EditFor varchar(200), @UserID int ,@ID int
As
Begin
	Insert into [dbo].[NominalRoll1EditLog] select * from NominalRoll1 where ID = @ID;
	update NominalRoll1 set EditSkip =1,[EditFor]= @EditFor,[EditUserID]= @UserID,[EditedOn]=getdate() where id = @ID;
end
Go
Create or Alter Procedure usp_NominalRoll2EditSkip @EditFor varchar(200), @UserID int ,@ID int
As
Begin
	Insert into [dbo].[NominalRoll2EditLog] select * from NominalRoll2 where ID = @ID;
	update NominalRoll2 set EditSkip =1,[EditFor]= @EditFor,[EditUserID]= @UserID,[EditedOn]=getdate() where id = @ID;
end
Go

create procedure usp_CounterFoilEditFor
As
Begin
	Select ReportName EditFor from [dbo].[ExportReport] where ReportFor = 'Counter Foil' and id <10
	union
	Select 'All discrepancy data' EditFor
	union
	Select 'Full Data' EditFor
End
go
create or alter procedure usp_NominalRoll1EditFor
As
Begin
	Select ReportName EditFor from [dbo].[ExportReport] where ReportFor = 'Nominal Roll 1 (Descriptive Test)' and id <20
	union
	Select 'All discrepancy data' EditFor
	union
	Select 'Full Data' EditFor
End
go

create or alter procedure usp_NominalRoll2EditFor
As
Begin
	Select ReportName EditFor from [dbo].[ExportReport] where ReportFor = 'Nominal Roll 2 (OMR Test)' and id <28
	union
	Select 'All discrepancy data' EditFor
	union
	Select 'Full Data' EditFor
End

go

Create or Alter Procedure usp_LoadNominalRoll1EditGrid 
	@EditFor varchar (200), @UserID int
As
Begin
	if @EditFor ='Full Data'
	begin
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], OMR_No,[Registration_No] ,[qpvc], [signature_present] [Candidate Signed], [Invigilator_Signed], 
			 FinalDesc FinalStatus from NominalRoll1 
			 --WhitenerDesc WhitenerApplied, ThDesc [Threshold < 35%], --where FinalDesc =1
	end
	else if @EditFor ='All discrepancy data'
	begin
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], OMR_No,[Registration_No] ,[qpvc], [signature_present] [Candidate Signed], [Invigilator_Signed], 
			 FinalDesc FinalStatus from NominalRoll1 where FinalDesc =1
	end
	else if @EditFor ='Subject Code discrepancy'
	begin
		Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], OMR_No,[Registration_No] ,[qpvc], [signature_present] [Candidate Signed], [Invigilator_Signed], 
			 FinalDesc FinalStatus from NominalRoll1 where SubDesc =1
	end
	else if @EditFor ='Center Code discrepancy'
	begin
		Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], OMR_No,[Registration_No] ,[qpvc], [signature_present] [Candidate Signed], [Invigilator_Signed], 
			 FinalDesc FinalStatus from NominalRoll1 where CenterCodeDesc =1 
	end
	else if @EditFor ='Sub Center Code discrepancy'
	begin
		Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], OMR_No,[Registration_No] ,[qpvc], [signature_present] [Candidate Signed], [Invigilator_Signed], 
			 FinalDesc FinalStatus from NominalRoll1 where SubCenterCodeDesc =1 
	end
	--else if @EditFor ='Written RegNo discrepancy'
	--begin
	--Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], [barcode], [bubble_regno], [handwritten_regno],
	--		 [subject_code], [BookletSlNo], CandSigDesc, 
	--		InvSignDesc, WhitenerDesc WhitenerApplied, isBlackDesc [Non Standard Sheet], ThDesc [Threshold < 35%], FinalDesc FinalStatus from CounterFoilData where ICRRegNoDesc=1
	--end
	else if @EditFor ='OMR No discrepancy'
	begin
		Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], OMR_No,[Registration_No] ,[qpvc], [signature_present] [Candidate Signed], [Invigilator_Signed], 
			 FinalDesc FinalStatus from NominalRoll1  where [OMRDesc]=1
	end
	else if @EditFor ='Roll No discrepancy'
	begin
		Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], OMR_No,[Registration_No] ,[qpvc], [signature_present] [Candidate Signed], [Invigilator_Signed], 
			 FinalDesc FinalStatus from NominalRoll1  where [RegNoDesc]=1
	end
	else if @EditFor ='QBVC discrepancy'
	begin
		Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], OMR_No,[Registration_No] ,[qpvc], [signature_present] [Candidate Signed], [Invigilator_Signed], 
			 FinalDesc FinalStatus from NominalRoll1  where QPVCDesc=1
	end
	--else if @EditFor ='Whiter Used in the boubles'
	--begin
	--Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], [barcode], [bubble_regno], [handwritten_regno],
	--		 [subject_code], [BookletSlNo], CandSigDesc, 
	--		InvSignDesc, WhitenerDesc WhitenerApplied, isBlackDesc [Non Standard Sheet], ThDesc [Threshold < 35%], FinalDesc FinalStatus from CounterFoilData where WhitenerDesc=1
	--end
	--else if @EditFor ='Boubles marked <35% Threshold marking'
	--begin
	--Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], [barcode], [bubble_regno], [handwritten_regno],
	--		 [subject_code], [BookletSlNo], CandSigDesc, 
	--		InvSignDesc, WhitenerDesc WhitenerApplied, isBlackDesc [Non Standard Sheet], ThDesc [Threshold < 35%], FinalDesc FinalStatus from CounterFoilData where ThDesc=1
	--end
	else if @EditFor ='Candidate''s Signature discrepancy'
	begin
		Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], OMR_No,[Registration_No] ,[qpvc], [signature_present] [Candidate Signed], [Invigilator_Signed], 
			 FinalDesc FinalStatus from NominalRoll1  where CandSignDesc=1
	end
	else if @EditFor ='Invigilator''s Signature discrepancy'
	begin
		Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], OMR_No,[Registration_No] ,[qpvc], [signature_present] [Candidate Signed], [Invigilator_Signed], 
			 FinalDesc FinalStatus from NominalRoll1  where InvSignDesc=1
	end
	--else if @EditFor ='Non standard OMR sheet used'
	--begin
	--Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], [barcode], [bubble_regno], [handwritten_regno],
	--		 [subject_code], [BookletSlNo], CandSigDesc, 
	--		InvSignDesc, WhitenerDesc WhitenerApplied, isBlackDesc [Non Standard Sheet], ThDesc [Threshold < 35%], FinalDesc FinalStatus from CounterFoilData where isBlackDesc=1
	--end

End

go
Create or Alter Procedure usp_LoadNominalRoll2EditGrid 
	@EditFor varchar (200), @UserID int
As
Begin
	if @EditFor ='Full Data'
	begin
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], QCAB_Serial_No,[Registration_No] , [signature_present] [Candidate Signed], [Invigilator_Signed], 
			 FinalDesc FinalStatus from NominalRoll2 
			 --WhitenerDesc WhitenerApplied, ThDesc [Threshold < 35%], --where FinalDesc =1
	end
	else if @EditFor ='All discrepancy data'
	begin
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], QCAB_Serial_No,[Registration_No] , [signature_present] [Candidate Signed], [Invigilator_Signed], 
			 FinalDesc FinalStatus from NominalRoll2 where FinalDesc =1
	end
	else if @EditFor ='Subject Code discrepancy'
	begin
		Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], QCAB_Serial_No,[Registration_No] , [signature_present] [Candidate Signed], [Invigilator_Signed], 
			 FinalDesc FinalStatus from NominalRoll2 where SubDesc =1
	end
	else if @EditFor ='Center Code discrepancy'
	begin
		Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], QCAB_Serial_No,[Registration_No] , [signature_present] [Candidate Signed], [Invigilator_Signed], 
			 FinalDesc FinalStatus from NominalRoll2 where CenterCodeDesc =1 
	end
	else if @EditFor ='Sub Center Code discrepancy'
	begin
		Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], QCAB_Serial_No,[Registration_No] , [signature_present] [Candidate Signed], [Invigilator_Signed], 
			 FinalDesc FinalStatus from NominalRoll2 where SubCenterCodeDesc =1 
	end
	--else if @EditFor ='Written RegNo discrepancy'
	--begin
	--Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], [barcode], [bubble_regno], [handwritten_regno],
	--		 [subject_code], [BookletSlNo], CandSigDesc, 
	--		InvSignDesc, WhitenerDesc WhitenerApplied, isBlackDesc [Non Standard Sheet], ThDesc [Threshold < 35%], FinalDesc FinalStatus from CounterFoilData where ICRRegNoDesc=1
	--end
	else if @EditFor ='OMR No discrepancy'
	begin
		Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], QCAB_Serial_No,[Registration_No] , [signature_present] [Candidate Signed], [Invigilator_Signed], 
			 FinalDesc FinalStatus from NominalRoll2  where [QCABDesc]=1
	end
	else if @EditFor ='Roll No discrepancy'
	begin
		Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], QCAB_Serial_No,[Registration_No] , [signature_present] [Candidate Signed], [Invigilator_Signed], 
			 FinalDesc FinalStatus from NominalRoll2  where [RegNoDesc]=1
	end
	
	--else if @EditFor ='Whiter Used in the boubles'
	--begin
	--Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], [barcode], [bubble_regno], [handwritten_regno],
	--		 [subject_code], [BookletSlNo], CandSigDesc, 
	--		InvSignDesc, WhitenerDesc WhitenerApplied, isBlackDesc [Non Standard Sheet], ThDesc [Threshold < 35%], FinalDesc FinalStatus from CounterFoilData where WhitenerDesc=1
	--end
	--else if @EditFor ='Boubles marked <35% Threshold marking'
	--begin
	--Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], [barcode], [bubble_regno], [handwritten_regno],
	--		 [subject_code], [BookletSlNo], CandSigDesc, 
	--		InvSignDesc, WhitenerDesc WhitenerApplied, isBlackDesc [Non Standard Sheet], ThDesc [Threshold < 35%], FinalDesc FinalStatus from CounterFoilData where ThDesc=1
	--end
	else if @EditFor ='Candidate''s Signature discrepancy'
	begin
		Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], QCAB_Serial_No,[Registration_No] , [signature_present] [Candidate Signed], [Invigilator_Signed], 
			 FinalDesc FinalStatus from NominalRoll2  where CandSignDesc=1
	end
	else if @EditFor ='Invigilator''s Signature discrepancy'
	begin
		Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], QCAB_Serial_No,[Registration_No] , [signature_present] [Candidate Signed], [Invigilator_Signed], 
			 FinalDesc FinalStatus from NominalRoll2  where InvSignDesc=1
	end
	--else if @EditFor ='Non standard OMR sheet used'
	--begin
	--Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], [barcode], [bubble_regno], [handwritten_regno],
	--		 [subject_code], [BookletSlNo], CandSigDesc, 
	--		InvSignDesc, WhitenerDesc WhitenerApplied, isBlackDesc [Non Standard Sheet], ThDesc [Threshold < 35%], FinalDesc FinalStatus from CounterFoilData where isBlackDesc=1
	--end

End
go



usp_CounterFoilEditFor
usp_LoadCounterfoilEditGrid @EditFor, @UserID
usp_CounterFoilEditSkip @EditFor, @UserID
usp_CounterFoilEditUpdate @EditFor, @UserID, @ID, @barcode,@bubble_regno,@handwritten_regno,@subject_code,@BookletSlNo,@CandSig, @InvSign, @WhitenerDesc, @isBlackDesc, @ThDesc

Create usp_LoadCounterfoilEditGrid @EditFor, @UserID

SlNo, ID, [filename], [barcode], [bubble_regno], [handwritten_regno], [subject_code], [BookletSlNo],  OMRRegNoDesc, ICRRegNoDesc, CandSigDesc, InvSignDesc, SubCodeDesc, BSlNoDesc,  WhitenerDesc [WhitenerApplied], isBlackDesc [Non Standard Sheet], ThDesc [Threshold < 35%]