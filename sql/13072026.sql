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
		Declare @UserID int =1;
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
				iif(O.[candidate_signed]=1 ,0,1) CandSignDesc,iif(O.[invigilator_signed]=1 ,0,1)  InvSignDesc, iif(len(Replace(O.[subject_code],' ',''))<3,'1',0) SubCodeDesc, iif(len(Replace(O.[BookletSlNo],' ',''))<7,'1',0) BSlNoDesc,
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
			,iif(len(Replace(A.[status],' ',''))<1,1,0) StatusDesc, iif(A.[signature_present]=1 ,0,1) CandSignDesc,iif(A.[invigilator_signed]=1 ,0,1) [InvSignDesc]
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
	@EditFor varchar (200), @UserID int, @FromID int, @ToID int
As
Begin
	if @EditFor ='Full Data'
	begin
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], [barcode], [bubble_regno], [handwritten_regno],
			 [subject_code], [BookletSlNo], iif(candidate_signed=1,'True','False') CanSign,  iif(invigilator_signed =1,'True','False') InvSign
			,WhitenerDesc WhitenerApplied, isBlackDesc [Non Standard Sheet], ThDesc [Threshold < 35%], FinalDesc FinalStatus from CounterFoilData where ID >= @FromID and ID <= @ToID--where FinalDesc =1
	end
	else if @EditFor ='All discrepancy data'
	begin
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], [barcode], [bubble_regno], [handwritten_regno],
			 [subject_code], [BookletSlNo], iif(candidate_signed=1,'True','False') CanSign,  iif(invigilator_signed =1,'True','False') InvSign
			,WhitenerDesc WhitenerApplied, isBlackDesc [Non Standard Sheet], ThDesc [Threshold < 35%], FinalDesc FinalStatus from CounterFoilData where FinalDesc =1 and ID >= @FromID and ID <= @ToID
	end
	else if @EditFor ='Subject Code & Booklet Serial No discrepancy'
	begin
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], [barcode], [bubble_regno], [handwritten_regno],
			 [subject_code], [BookletSlNo], iif(candidate_signed=1,'True','False') CanSign,  iif(invigilator_signed =1,'True','False') InvSign
			,WhitenerDesc WhitenerApplied, isBlackDesc [Non Standard Sheet], ThDesc [Threshold < 35%], FinalDesc FinalStatus from CounterFoilData where (SubCodeDesc =1 or BSlNoDesc =1) and ID >= @FromID and ID <= @ToID
	end
	else if @EditFor ='Barcode discrepancy'
	begin
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], [barcode], [bubble_regno], [handwritten_regno],
			 [subject_code], [BookletSlNo], iif(candidate_signed=1,'True','False') CanSign,  iif(invigilator_signed =1,'True','False') InvSign
			,WhitenerDesc WhitenerApplied, isBlackDesc [Non Standard Sheet], ThDesc [Threshold < 35%], FinalDesc FinalStatus from CounterFoilData where BarcodeDesc =1 and ID >= @FromID and ID <= @ToID
	end
	else if @EditFor ='Written RegNo discrepancy'
	begin
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], [barcode], [bubble_regno], [handwritten_regno],
			 [subject_code], [BookletSlNo], iif(candidate_signed=1,'True','False') CanSign,  iif(invigilator_signed =1,'True','False') InvSign
			,WhitenerDesc WhitenerApplied, isBlackDesc [Non Standard Sheet], ThDesc [Threshold < 35%], FinalDesc FinalStatus from CounterFoilData where ICRRegNoDesc=1 and ID >= @FromID and ID <= @ToID
	end
	else if @EditFor ='OMR RegNo discrepancy'
	begin
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], [barcode], [bubble_regno], [handwritten_regno],
			 [subject_code], [BookletSlNo], iif(candidate_signed=1,'True','False') CanSign,  iif(invigilator_signed =1,'True','False') InvSign
			,WhitenerDesc WhitenerApplied, isBlackDesc [Non Standard Sheet], ThDesc [Threshold < 35%], FinalDesc FinalStatus from CounterFoilData where OMRRegNoDesc=1 and ID >= @FromID and ID <= @ToID
	end
	else if @EditFor ='Whiter Used in the boubles'
	begin
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], [barcode], [bubble_regno], [handwritten_regno],
			 [subject_code], [BookletSlNo], iif(candidate_signed=1,'True','False') CanSign,  iif(invigilator_signed =1,'True','False') InvSign
			,WhitenerDesc WhitenerApplied, isBlackDesc [Non Standard Sheet], ThDesc [Threshold < 35%], FinalDesc FinalStatus from CounterFoilData where WhitenerDesc=1 and ID >= @FromID and ID <= @ToID
	end
	else if @EditFor ='Boubles marked <35% Threshold marking'
	begin
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], [barcode], [bubble_regno], [handwritten_regno],
			 [subject_code], [BookletSlNo], iif(candidate_signed=1,'True','False') CanSign,  iif(invigilator_signed =1,'True','False') InvSign
			,WhitenerDesc WhitenerApplied, isBlackDesc [Non Standard Sheet], ThDesc [Threshold < 35%], FinalDesc FinalStatus from CounterFoilData where ThDesc=1 and ID >= @FromID and ID <= @ToID
	end
	else if @EditFor ='Candidate''s Signature discrepancy'
	begin
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], [barcode], [bubble_regno], [handwritten_regno],
			 [subject_code], [BookletSlNo], iif(candidate_signed=1,'True','False') CanSign,  iif(invigilator_signed =1,'True','False') InvSign
			,WhitenerDesc WhitenerApplied, isBlackDesc [Non Standard Sheet], ThDesc [Threshold < 35%], FinalDesc FinalStatus from CounterFoilData where CandSigDesc=1 and ID >= @FromID and ID <= @ToID
	end
	else if @EditFor ='Invigilator''s Signature discrepancy'
	begin
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], [barcode], [bubble_regno], [handwritten_regno],
			 [subject_code], [BookletSlNo], iif(candidate_signed=1,'True','False') CanSign,  iif(invigilator_signed =1,'True','False') InvSign
			,WhitenerDesc WhitenerApplied, isBlackDesc [Non Standard Sheet], ThDesc [Threshold < 35%], FinalDesc FinalStatus from CounterFoilData where InvSignDesc=1 and ID >= @FromID and ID <= @ToID
	end
	else if @EditFor ='Non standard OMR sheet used'
	begin
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], [barcode], [bubble_regno], [handwritten_regno],
			 [subject_code], [BookletSlNo], iif(candidate_signed=1,'True','False') CanSign,  iif(invigilator_signed =1,'True','False') InvSign
			,WhitenerDesc WhitenerApplied, isBlackDesc [Non Standard Sheet], ThDesc [Threshold < 35%], FinalDesc FinalStatus from CounterFoilData where isBlackDesc=1 and ID >= @FromID and ID <= @ToID
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

create or alter procedure usp_CounterFoilEditFor
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
	@EditFor varchar (200), @UserID int, @FromID int, @ToID int
As
Begin
	if @EditFor ='Full Data'
	begin
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[Row_Number],[filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], OMR_No,[Registration_No] ,[qpvc], [signature_present] CandSig, [Invigilator_Signed] InvSig, 
			 FinalDesc FinalStatus from NominalRoll1 where ID >= @FromID and ID <= @ToID
			 --WhitenerDesc WhitenerApplied, ThDesc [Threshold < 35%], --where FinalDesc =1
	end
	else if @EditFor ='All discrepancy data'
	begin
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[Row_Number],[filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], OMR_No,[Registration_No] ,[qpvc], [signature_present] CandSig, [Invigilator_Signed] InvSig, 
			 FinalDesc FinalStatus from NominalRoll1 where  FinalDesc =1 and ID >= @FromID and ID <= @ToID 
	end
	else if @EditFor ='Subject Code discrepancy'
	begin
		Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[Row_Number],[filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], OMR_No,[Registration_No] ,[qpvc], [signature_present] CandSig, [Invigilator_Signed] InvSig, 
			 FinalDesc FinalStatus from NominalRoll1 where SubDesc =1 and ID >= @FromID and ID <= @ToID 
	end
	else if @EditFor ='Center Code discrepancy'
	begin
		Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[Row_Number],[filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], OMR_No,[Registration_No] ,[qpvc], [signature_present] CandSig, [Invigilator_Signed] InvSig, 
			 FinalDesc FinalStatus from NominalRoll1 where CenterCodeDesc =1 and ID >= @FromID and ID <= @ToID 
	end
	else if @EditFor ='Sub Center Code discrepancy'
	begin
		Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[Row_Number],[filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], OMR_No,[Registration_No] ,[qpvc], [signature_present] CandSig, [Invigilator_Signed] InvSig, 
			 FinalDesc FinalStatus from NominalRoll1 where SubCenterCodeDesc =1 and ID >= @FromID and ID <= @ToID 
	end
	--else if @EditFor ='Written RegNo discrepancy'
	--begin
	--Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], [barcode], [bubble_regno], [handwritten_regno],
	--		 [subject_code], [BookletSlNo], CandSigDesc, 
	--		InvSignDesc, WhitenerDesc WhitenerApplied, isBlackDesc [Non Standard Sheet], ThDesc [Threshold < 35%], FinalDesc FinalStatus from CounterFoilData where ICRRegNoDesc=1
	--end
	else if @EditFor ='OMR No discrepancy'
	begin
		Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[Row_Number],[filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], OMR_No,[Registration_No] ,[qpvc], [signature_present] CandSig, [Invigilator_Signed] InvSig, 
			 FinalDesc FinalStatus from NominalRoll1  where [OMRDesc]=1 and ID >= @FromID and ID <= @ToID 
	end
	else if @EditFor ='Roll No discrepancy'
	begin
		Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[Row_Number],[filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], OMR_No,[Registration_No] ,[qpvc], [signature_present] CandSig, [Invigilator_Signed] InvSig,[Status] 
			 ,FinalDesc FinalStatus from NominalRoll1  where [RegNoDesc]=1 and ID >= @FromID and ID <= @ToID 
	end
	else if @EditFor ='QBVC discrepancy'
	begin
		Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[Row_Number],[filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], OMR_No,[Registration_No] ,[qpvc], [signature_present] CandSig, [Invigilator_Signed] InvSig, 
			 FinalDesc FinalStatus from NominalRoll1  where QPVCDesc=1 and ID >= @FromID and ID <= @ToID 
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
		Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[Row_Number],[filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], OMR_No,[Registration_No] ,[qpvc], [signature_present] CandSig, [Invigilator_Signed] InvSig, 
			 FinalDesc FinalStatus from NominalRoll1  where CandSignDesc=1 and ID >= @FromID and ID <= @ToID 
	end
	else if @EditFor ='Invigilator''s Signature discrepancy'
	begin
		Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[Row_Number],[filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], OMR_No,[Registration_No] ,[qpvc], [signature_present] CandSig, [Invigilator_Signed] InvSig, 
			 FinalDesc FinalStatus from NominalRoll1  where InvSignDesc=1 and ID >= @FromID and ID <= @ToID 
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
	@EditFor varchar (200), @UserID int, @FromID int, @ToID int
As
Begin
	if @EditFor ='Full Data'
	begin
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[Row_Number],[Filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], QCAB_Serial_No,[Registration_No] , [signature_present] CandSig, [Invigilator_Signed] InvSig, [Status],
			 FinalDesc FinalStatus from NominalRoll2 where ID >= @FromID and ID <= @ToID--where FinalDesc =1
				 --WhitenerDesc WhitenerApplied, ThDesc [Threshold < 35%], --where FinalDesc =1
	end
	else if @EditFor ='All discrepancy data'
	begin
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[Row_Number],[Filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], QCAB_Serial_No,[Registration_No] , [signature_present] CandSig, [Invigilator_Signed] InvSig, 
			 FinalDesc FinalStatus from NominalRoll2 where FinalDesc =1 and ID >= @FromID and ID <= @ToID
	end
	else if @EditFor ='Subject Code discrepancy'
	begin
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[Row_Number],[Filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], QCAB_Serial_No,[Registration_No] , [signature_present] CandSig, [Invigilator_Signed] InvSig, 
			 FinalDesc FinalStatus from NominalRoll2 where SubDesc =1 and ID >= @FromID and ID <= @ToID
	end
	else if @EditFor ='Center Code discrepancy'
	begin
		Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[Row_Number],[Filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], QCAB_Serial_No,[Registration_No] , [signature_present] [Candidate Signed], [Invigilator_Signed], 
			 FinalDesc FinalStatus from NominalRoll2 where CenterCodeDesc =1  and ID >= @FromID and ID <= @ToID
	end
	else if @EditFor ='Sub Center Code discrepancy'
	begin
		Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[Row_Number],[Filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], QCAB_Serial_No,[Registration_No] , [signature_present] [Candidate Signed], [Invigilator_Signed], 
			 FinalDesc FinalStatus from NominalRoll2 where SubCenterCodeDesc =1  and ID >= @FromID and ID <= @ToID
	end
	--else if @EditFor ='Written RegNo discrepancy'
	--begin
	--Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], [barcode], [bubble_regno], [handwritten_regno],
	--		 [subject_code], [BookletSlNo], CandSigDesc, 
	--		InvSignDesc, WhitenerDesc WhitenerApplied, isBlackDesc [Non Standard Sheet], ThDesc [Threshold < 35%], FinalDesc FinalStatus from CounterFoilData where ICRRegNoDesc=1
	--end
	else if @EditFor ='QCAB discrepancy'
	begin
		Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[Row_Number],[Filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], QCAB_Serial_No,[Registration_No] , [signature_present] [Candidate Signed], [Invigilator_Signed], 
			 FinalDesc FinalStatus from NominalRoll2  where [QCABDesc]=1 and ID >= @FromID and ID <= @ToID
	end
	else if @EditFor ='Roll No discrepancy'
	begin
		Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[Row_Number],[Filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], QCAB_Serial_No,[Registration_No] , [signature_present] [Candidate Signed], [Invigilator_Signed], 
			 FinalDesc FinalStatus from NominalRoll2  where [RegNoDesc]=1 and ID >= @FromID and ID <= @ToID
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
		Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[Row_Number],[Filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], QCAB_Serial_No,[Registration_No] , [signature_present] [Candidate Signed], [Invigilator_Signed], 
			 FinalDesc FinalStatus from NominalRoll2  where CandSignDesc=1 and ID >= @FromID and ID <= @ToID
	end
	else if @EditFor ='Invigilator''s Signature discrepancy'
	begin
		Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[Row_Number],[Filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], QCAB_Serial_No,[Registration_No] , [signature_present] [Candidate Signed], [Invigilator_Signed], 
			 FinalDesc FinalStatus from NominalRoll2  where InvSignDesc=1 and ID >= @FromID and ID <= @ToID
	end
	--else if @EditFor ='Non standard OMR sheet used'
	--begin
	--Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[filename], [barcode], [bubble_regno], [handwritten_regno],
	--		 [subject_code], [BookletSlNo], CandSigDesc, 
	--		InvSignDesc, WhitenerDesc WhitenerApplied, isBlackDesc [Non Standard Sheet], ThDesc [Threshold < 35%], FinalDesc FinalStatus from CounterFoilData where isBlackDesc=1
	--end

End
go
--drop procedure [USP_UpdateCounterFoilDataEdit]
Create or ALTER PROCEDURE [dbo].usp_CounterFoilEditUpdate 
(
      @EditFor varchar(200), @UserID int, @ID int, @barcode varchar(20),
	  @bubble_regno varchar(20),@handwritten_regno varchar(20),@subject_code varchar(10),@BookletSlNo varchar(20),
	  @CandSig bit, @InvSign bit, @WhitenerDesc bit, @isBlackDesc bit, @ThDesc bit
)
AS
BEGIN

    SET NOCOUNT ON;
    
    BEGIN TRY

        BEGIN
		   INSERT INTO CounterFoilDataEditLog ([id]
			  ,[filename]
			  ,[barcode]
			  ,[bubble_regno]
			  ,[handwritten_regno]
			  ,[final_regno]
			  ,[discrepancy]
			  ,[discrepancy_detail]
			  ,[candidate_signed]
			  ,[invigilator_signed]
			  ,[subject_code]
			  ,[BookletSlNo]
			  ,[created_at]
			  ,[omr_threshold]
			  ,[whitenerflag]
			  ,[isblack]
			  ,[updated_at]
			  ,[updated_by]
			  ,[bubble_Th_status]
			  ,[BarcodeDesc]
			  ,[OMRRegNoDesc]
			  ,[ICRRegNoDesc]
			  ,[CandSigDesc]
			  ,[InvSignDesc]
			  ,[SubCodeDesc]
			  ,[BSlNoDesc]
			  ,[whitenerDesc]
			  ,[isBlackDesc]
			  ,[ThDesc]
			  ,[FinalDesc]
			  ,[EditFor]
			  ,[EditSkip]
			  ,[EditUserID]
			  ,[EditedOn])
             
             SELECT
				  [id]
				  ,[filename]
				  ,[barcode]
				  ,[bubble_regno]
				  ,[handwritten_regno]
				  ,[final_regno]
				  ,[discrepancy]
				  ,[discrepancy_detail]
				  ,[candidate_signed]
				  ,[invigilator_signed]
				  ,[subject_code]
				  ,[BookletSlNo]
				  ,[created_at]
				  ,[omr_threshold]
				  ,[whitenerflag]
				  ,[isblack]
				  ,[updated_at]
				  ,[updated_by]
				  ,[bubble_Th_status]
				  ,[BarcodeDesc]
				  ,[OMRRegNoDesc]
				  ,[ICRRegNoDesc]
				  ,[CandSigDesc]
				  ,[InvSignDesc]
				  ,[SubCodeDesc]
				  ,[BSlNoDesc]
				  ,[whitenerDesc]
				  ,[isBlackDesc]
				  ,[ThDesc]
				  ,[FinalDesc]
				  ,[EditFor]
				  ,[EditSkip]
				  ,[EditUserID]
				  ,[EditedOn]
             FROM CounterFoilData
             WHERE ID=@ID
            
             UPDATE CounterFoilData
             SET [barcode] =@barcode
				  ,[bubble_regno] = @bubble_regno 
				  ,[handwritten_regno] = @handwritten_regno
				  ,[candidate_signed] = @CandSig
				  ,[invigilator_signed] =  @InvSign
				  ,[subject_code] = @subject_code
				  ,[BookletSlNo] = @BookletSlNo
				  ,whitenerDesc = @WhitenerDesc
				  ,isBlackDesc = @isBlackDesc
				  ,[ThDesc] = @ThDesc
				  ,[EditFor] = @EditFor
				  ,[EditUserID]= @UserID
				  ,[EditedOn]=GETDATE()                 
             WHERE ID=@ID
			 update CounterFoilData 
			    set BarcodeDesc = iif(len(Replace([barcode],' ',''))!=10,1,0), OMRRegNoDesc = iif(len(Replace([bubble_regno],' ',''))<9,'1',0) , ICRRegNoDesc= iif(len(Replace([handwritten_regno],' ',''))<9,'1',0) ,
				CandSigDesc = iif([candidate_signed] = 1,0,1) ,InvSignDesc=iif( invigilator_signed = 1,0,1) , SubCodeDesc= iif(len(Replace([subject_code],' ',''))<3,'1',0) , BSlNoDesc= iif(len(Replace([BookletSlNo],' ',''))<7,'1',0) ,
				[whitenerflag] = whitenerDesc, [isblack] = isBlackDesc, [bubble_Th_status] = ThDesc
			WHERE ID=@ID
			Update CounterFoilData Set FinalDesc = 1 where (BarcodeDesc=1 or OMRRegNoDesc =1 or ICRRegNoDesc=1 or CandSigDesc=0 or InvSignDesc=0 or SubCodeDesc=1 or 
				BSlNoDesc=1 or whitenerDesc=1 or isBlackDesc =1 or ThDesc = 1) and ID=@ID
			Update CounterFoilData Set FinalDesc = 0 where (BarcodeDesc=0 AND OMRRegNoDesc =0 AND ICRRegNoDesc=0 AND CandSigDesc=1 AND InvSignDesc=1 AND SubCodeDesc=0 AND 
				BSlNoDesc=0 AND whitenerDesc=0 AND isBlackDesc =0 AND ThDesc = 0 ) and ID=@ID

			 --@EditFor, @UserID, @ID, @barcode,@bubble_regno,@handwritten_regno,@subject_code,
			 --@BookletSlNo,@CandSig, @InvSign, @WhitenerDesc, @isBlackDesc, @ThDesc

        END
        

    END TRY

    BEGIN CATCH

         INSERT INTO ErrorLog
         (
			[ErrorScreen],[ErrorModule],
             ErrorText,
             ErrorTime
         )
         VALUES
         (
             'CounterFoilEditedData','usp_CounterFoilEditUpdate',
			 ERROR_MESSAGE(),
             GETDATE()
         )

    END CATCH

END
go

Create or ALTER PROCEDURE [dbo].usp_NominalRoll1EditUpdate 
(
      @EditFor varchar(200), @UserID int, @ID int, @CenterCode varchar(20),
	  @SubCenterCode varchar(20),@SubCode varchar(10),@OMRNo varchar(20),@RegNo varchar(20), @QPVC varchar(2),
	  @CandSig bit, @InvSign bit
)
AS
BEGIN

    SET NOCOUNT ON;
    
    BEGIN TRY

        BEGIN
		   INSERT INTO NominalRoll1EditLog ([id]
			  ,[filename]
			  ,[center_code]
			  ,[subcenter_code]
			  ,[subject_code]
			  ,[invigilator_signed]
			  ,[row_number]
			  ,[status]
			  ,[signature_present]
			  ,[omr_no]
			  ,[registration_no]
			  ,[qpvc]
			  ,[created_at]
			  ,[CreatedBy]
			  ,[CenterCodeDesc]
			  ,[SubCenterCodeDesc]
			  ,[SubDesc]
			  ,[StatusDesc]
			  ,[CandSignDesc]
			  ,[InvSignDesc]
			  ,[OMRDesc]
			  ,[RegNoDesc]
			  ,[QPVCDesc]
			  ,[FinalDesc]
			  ,[EditFor]
			  ,[EditSkip]
			  ,[EditUserID]
			  ,[EditedOn])
             
             SELECT
				  [id]
				  ,[filename]
				  ,[center_code]
				  ,[subcenter_code]
				  ,[subject_code]
				  ,[invigilator_signed]
				  ,[row_number]
				  ,[status]
				  ,[signature_present]
				  ,[omr_no]
				  ,[registration_no]
				  ,[qpvc]
				  ,[created_at]
				  ,[CreatedBy]
				  ,[CenterCodeDesc]
				  ,[SubCenterCodeDesc]
				  ,[SubDesc]
				  ,[StatusDesc]
				  ,[CandSignDesc]
				  ,[InvSignDesc]
				  ,[OMRDesc]
				  ,[RegNoDesc]
				  ,[QPVCDesc]
				  ,[FinalDesc]
				  ,[EditFor]
				  ,[EditSkip]
				  ,[EditUserID]
				  ,[EditedOn]
             FROM NominalRoll1
             WHERE ID=@ID
            
             UPDATE NominalRoll1
             SET [center_code] =@CenterCode 
				  ,[subcenter_code] = @SubCenterCode
				  ,[subject_code] = @SubCode
				  ,[signature_present]= @CandSig, [invigilator_signed] = @InvSign
				  ,[omr_no] = @OMRNo
				  ,[registration_no] = @RegNo
				  ,[qpvc]= @QPVC
				  --,whitenerDesc = @WhitenerDesc
				  --,isBlackDesc = @isBlackDesc
				  --,[ThDesc] = @ThDesc
				  ,[EditFor] = @EditFor
				  ,[EditUserID]= @UserID
				  ,[EditedOn]=GETDATE()                 
             WHERE ID=@ID
			 update NominalRoll1 
			    set [center_code] = iif(len(Replace([center_code],' ',''))<1,1,0) , subcenter_code = iif(len(Replace([subcenter_code],' ',''))<1,1,0),RegNoDesc = iif(len(Replace([registration_no],' ',''))<9,'1',0),
				CandSignDesc = iif(signature_present = 1,0,1) ,InvSignDesc=iif( invigilator_signed = 1,0,1) , [SubDesc]= iif(len(Replace([subject_code],' ',''))<3,'1',0) , OMRDesc= iif(len(Replace([omr_no],' ',''))<7,'1',0),
				QPVCDesc =iif(len(Replace([qpvc],' ',''))<1,1,0) 
				--[whitenerflag] = whitenerDesc, [isblack] = isBlackDesc, [bubble_Th_status] = ThDesc
			WHERE ID=@ID
			Update NominalRoll1 Set FinalDesc = 1 where (CenterCodeDesc =1 or SubCenterCodeDesc =1 or SubDesc =1 or StatusDesc=1 or CandSignDesc =0 or InvSignDesc=0 or  OMRDesc=1 or  RegNoDesc=1 or QPVCDesc =1) and ID=@ID
			Update NominalRoll1 Set FinalDesc = 0 where (CenterCodeDesc =0 AND SubCenterCodeDesc =0 AND SubDesc =0 AND StatusDesc=0 AND CandSignDesc =1 AND InvSignDesc=1 AND OMRDesc=0 AND RegNoDesc=0 AND QPVCDesc =0) and ID=@ID
        END
        

    END TRY

    BEGIN CATCH

         INSERT INTO ErrorLog
         (
			[ErrorScreen],[ErrorModule],
             ErrorText,
             ErrorTime
         )
         VALUES
         (
             'NominalRoll1EditedData','usp_NominalRoll1EditUpdate',
			 ERROR_MESSAGE(),
             GETDATE()
         )

    END CATCH

END

go

Create or ALTER PROCEDURE [dbo].usp_NominalRoll2EditUpdate 
(
      @EditFor varchar(200), @UserID int, @ID int, @CenterCode varchar(20),
	  @SubCenterCode varchar(20),@SubCode varchar(10),@OMRNo varchar(20),@RegNo varchar(20),
	  @CandSig bit, @InvSign bit
)
AS
BEGIN

    SET NOCOUNT ON;
    
    BEGIN TRY

        BEGIN
		   INSERT INTO NominalRoll2EditLog ([id]
			  ,[filename]
			  ,[center_code]
			  ,[subcenter_code]
			  ,[subject_code]
			  ,[invigilator_signed]
			  ,[row_number]
			  ,[status]
			  ,[signature_present]
			  ,qcab_serial_no
			  ,[registration_no]
			  ,[created_at]
			  ,[CreatedBy]
			  ,[CenterCodeDesc]
			  ,[SubCenterCodeDesc]
			  ,[SubDesc]
			  ,[StatusDesc]
			  ,[CandSignDesc]
			  ,[InvSignDesc]
			  ,QCABDesc
			  ,[RegNoDesc]
			  ,[FinalDesc]
			  ,[EditFor]
			  ,[EditSkip]
			  ,[EditUserID]
			  ,[EditedOn])
             
             SELECT
				  [id]
				  ,[filename]
				  ,[center_code]
				  ,[subcenter_code]
				  ,[subject_code]
				  ,[invigilator_signed]
				  ,[row_number]
				  ,[status]
				  ,[signature_present]
				  ,qcab_serial_no
				  ,registration_no				 
				  ,[created_at]
				  ,[CreatedBy]
				  ,[CenterCodeDesc]
				  ,[SubCenterCodeDesc]
				  ,[SubDesc]
				  ,[StatusDesc]
				  ,[CandSignDesc]
				  ,[InvSignDesc]
				  ,QCABDesc
				  ,[RegNoDesc]
				  ,[FinalDesc]
				  ,[EditFor]
				  ,[EditSkip]
				  ,[EditUserID]
				  ,[EditedOn]
             FROM NominalRoll2
             WHERE ID=@ID
            
             UPDATE NominalRoll2
             SET [center_code] =@CenterCode 
				  ,[subcenter_code] = @SubCenterCode
				  ,[subject_code] = @SubCode
				  ,[signature_present]= @CandSig, [invigilator_signed] = @InvSign
				  ,qcab_serial_no = @OMRNo
				  ,[registration_no] = @RegNo
				  --,[qpvc]= @QPVC
				  --,whitenerDesc = @WhitenerDesc
				  --,isBlackDesc = @isBlackDesc
				  --,[ThDesc] = @ThDesc
				  ,[EditFor] = @EditFor
				  ,[EditUserID]= @UserID
				  ,[EditedOn]=GETDATE()                 
             WHERE ID=@ID
			 update NominalRoll2 
			    set [center_code] = iif(len(Replace([center_code],' ',''))<1,1,0) , subcenter_code = iif(len(Replace([subcenter_code],' ',''))<1,1,0),RegNoDesc = iif(len(Replace([registration_no],' ',''))<9,'1',0),
				CandSignDesc = iif([signature_present] = 1,0,1) ,InvSignDesc=iif( invigilator_signed = 1,0,1) , [SubDesc]= iif(len(Replace([subject_code],' ',''))<3,'1',0) , QCABDesc= iif(len(Replace(qcab_serial_no,' ',''))<7,'1',0)
				--QPVCDesc =iif(len(Replace(A.[qpvc],' ',''))<1,1,0) 
				--[whitenerflag] = whitenerDesc, [isblack] = isBlackDesc, [bubble_Th_status] = ThDesc
			WHERE ID=@ID
			Update NominalRoll2 Set FinalDesc = 1 where (CenterCodeDesc =1 or SubCenterCodeDesc =1 or SubDesc =1 or StatusDesc=1 or CandSignDesc =0 or InvSignDesc=0 or  QCABDesc=1 or  RegNoDesc=1 ) and ID=@ID
			Update NominalRoll2 Set FinalDesc = 0 where (CenterCodeDesc =0 AND SubCenterCodeDesc =0 AND SubDesc =0 AND StatusDesc=0 AND CandSignDesc =1 AND InvSignDesc=1 AND QCABDesc=0 AND RegNoDesc=0 ) and ID=@ID
        END
        

    END TRY

    BEGIN CATCH

         INSERT INTO ErrorLog
         (
			[ErrorScreen],[ErrorModule],
             ErrorText,
             ErrorTime
         )
         VALUES
         (
             'NominalRoll2Edited','usp_NominalRoll2EditUpdate',
			 ERROR_MESSAGE(),
             GETDATE()
         )

    END CATCH

END

go

Create or alter Procedure usp_CounterFoilRawData
as
begin
Select O.id,O.[filename], O.[barcode], O.[bubble_regno],O.[handwritten_regno],
				 O.[candidate_signed], O.[invigilator_signed],O.[subject_code], O.[BookletSlNo],
				   O.[whitenerflag],O.[isblack] [Non Standard sheet],
				iif(Replace(O.[barcode],' ','')='','Yes','No') BarcodeDesc, iif(len(Replace(O.[bubble_regno],' ',''))<9,'Yes','No') OMRRegNoDesc, iif(len(Replace(O.[handwritten_regno],' ',''))<9,'Yes','No') ICRRegNoDesc,
				iif(O.[candidate_signed]=1,'No','Yes') CandSigDesc, iif(O.[invigilator_signed]=1,'No','Yes') InvSignDesc, iif(len(Replace(O.[subject_code],' ',''))<3,'Yes','No') SubCodeDesc, iif(len(Replace(O.[BookletSlNo],' ',''))<7,'Yes','No') BSlNoDesc,
				O.[whitenerflag] whitenerDesc, O.[isblack] isBlackDesc, O.[bubble_Th_status] ThDesc ,O.[created_at] ScannedOn
			from [dbo].[omr_results] O 
end

Go
Create  or Alter Procedure NominalRoll1RawData
as
begin
	Select A.[ID],A.[FileName],A.[Center_Code]
			,A.[Subcenter_Code],A.[Subject_Code],A.[Invigilator_Signed],A.[Row_Number]
			,A.[status],A.[Signature_Present],A.[OMR_No],A.[Registration_no],A.[QPVC]
			,iif(len(Replace(A.[center_code],' ',''))<1,1,0) CenterCodeDesc,iif(len(Replace(A.[subcenter_code],' ',''))<1,1,0) [SubCenterCodeDesc],iif(len(Replace(A.[subject_code],' ',''))<3,1,0) [SubDesc]
			,iif(len(Replace(A.[status],' ',''))<1,1,0) StatusDesc, iif(A.[signature_present]=1,'No','Yes') CandSignDesc, iif(A.[invigilator_signed]=1,'No','Yes') [InvSignDesc],iif(len(Replace(A.[omr_no],' ',''))<7,'1',0) OMRoDesc
			,iif(len(Replace(A.[registration_no],' ',''))<9,'1',0) RegNoDesc ,iif(len(Replace(A.[qpvc],' ',''))<1,1,0)  QPVCDesc , created_at ScannedOn
			from [dbo].[attendance_sheet_data_1] A 
end
Go
Create  or Alter Procedure NominalRoll2RawData
as
begin
	Select A.[ID],A.[FileName],A.[Center_Code]
			,A.[Subcenter_Code],A.[Subject_Code],A.[Invigilator_Signed],A.[Row_Number]
			,A.[Status],A.[Signature_Present],A.[QCAB_Serial_No],A.[Registration_No]
			,iif(len(Replace(A.[center_code],' ',''))<1,1,0) CenterCodeDesc,iif(len(Replace(A.[subcenter_code],' ',''))<1,1,0) [SubCenterCodeDesc],iif(len(Replace(A.[subject_code],' ',''))<3,1,0) [SubDesc]
			,iif(len(Replace(A.[status],' ',''))<1,1,0) StatusDesc, iif(A.[signature_present]=1,'No','Yes') CandSignDesc, iif(A.[invigilator_signed]=1,'No','Yes') [InvSignDesc],iif(len(Replace(A.[omr_no],' ',''))<7,'1',0) OMRNoDesc
			,iif(len(Replace(A.[registration_no],' ',''))<9,'1',0) RegNoDesc  , created_at ScannedOn
			from [dbo].[attendance_sheet_data_2] A 
end


go

/*
Nominal Roll 1 (Descriptive Test)	Center Code discrepancy
Nominal Roll 1 (Descriptive Test)	Sub Center Code discrepancy
Nominal Roll 1 (Descriptive Test)	Subject Code discrepancy
Nominal Roll 1 (Descriptive Test)	Roll No discrepancy
Nominal Roll 1 (Descriptive Test)	OMR No discrepancy
Nominal Roll 1 (Descriptive Test)	QBVC discrepancy
Nominal Roll 2 (OMR Test)	Not signed by candidate in Nominal Roll 2 discrepancy
Nominal Roll 2 (OMR Test)	Not signed by Invigilator in Nominal Roll 2 discrepancy
Nominal Roll 2 (OMR Test)	Center Code discrepancy
Nominal Roll 2 (OMR Test)	Sub Center Code discrepancy
Nominal Roll 2 (OMR Test)	Subject Code discrepancy
Nominal Roll 2 (OMR Test)	Roll No discrepancy
Nominal Roll 2 (OMR Test)	OMR No discrepancy
*/
--SP_helptext NominalRoll1_inv_Sign_Desc
  
CREATE or Alter PROCEDURE [dbo].[NominalRoll1_CenterCode_Desc]  
 -- Add the parameters for the stored procedure here  
AS  
BEGIN  
 -- SET NOCOUNT ON added to prevent extra result sets from  
 -- interfering with SELECT statements.  
 SET NOCOUNT ON;  
  
    -- Insert statements for procedure here  
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[Row_Number],[filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], OMR_No,[Registration_No] ,[qpvc], [signature_present] CandSig, [Invigilator_Signed] InvSig,[Status], 
			 FinalDesc FinalStatus from NominalRoll1 where CenterCodeDesc =1 
end
go
CREATE or Alter PROCEDURE [dbo].[NominalRoll1_SubCenterCode_Desc]  
 -- Add the parameters for the stored procedure here  
AS  
BEGIN  
 -- SET NOCOUNT ON added to prevent extra result sets from  
 -- interfering with SELECT statements.  
 SET NOCOUNT ON;  
  
    -- Insert statements for procedure here  
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[Row_Number],[filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], OMR_No,[Registration_No] ,[qpvc], [signature_present] CandSig, [Invigilator_Signed] InvSig,[Status], 
			 FinalDesc FinalStatus from NominalRoll1 where SubCenterCodeDesc =1 
end
go
CREATE or Alter PROCEDURE [dbo].[NominalRoll1_SubjectCode_Desc]  
 -- Add the parameters for the stored procedure here  
AS  
BEGIN  
 -- SET NOCOUNT ON added to prevent extra result sets from  
 -- interfering with SELECT statements.  
 SET NOCOUNT ON;  
  
    -- Insert statements for procedure here  
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[Row_Number],[filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], OMR_No,[Registration_No] ,[qpvc], [signature_present] CandSig, [Invigilator_Signed] InvSig,[Status], 
			 FinalDesc FinalStatus from NominalRoll1 where SubDesc =1 
end
go
CREATE or Alter PROCEDURE [dbo].[NominalRoll1_OMRNo_Desc]  
 -- Add the parameters for the stored procedure here  
AS  
BEGIN  
 -- SET NOCOUNT ON added to prevent extra result sets from  
 -- interfering with SELECT statements.  
 SET NOCOUNT ON;  
  
    -- Insert statements for procedure here  
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[Row_Number],[filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], OMR_No,[Registration_No] ,[qpvc], [signature_present] CandSig, [Invigilator_Signed] InvSig,[Status], 
			 FinalDesc FinalStatus from NominalRoll1 where OMRDesc =1 
end
go
CREATE or Alter PROCEDURE [dbo].[NominalRoll1_RegNo_Desc]  
 -- Add the parameters for the stored procedure here  
AS  
BEGIN  
 -- SET NOCOUNT ON added to prevent extra result sets from  
 -- interfering with SELECT statements.  
 SET NOCOUNT ON;  
  
    -- Insert statements for procedure here  
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[Row_Number],[filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], OMR_No,[Registration_No] ,[qpvc], [signature_present] CandSig, [Invigilator_Signed] InvSig,[Status], 
			 FinalDesc FinalStatus from NominalRoll1 where RegNoDesc =1 
end
go
CREATE or Alter PROCEDURE [dbo].[NominalRoll1_QPVC_Desc]  
 -- Add the parameters for the stored procedure here  
AS  
BEGIN  
 -- SET NOCOUNT ON added to prevent extra result sets from  
 -- interfering with SELECT statements.  
 SET NOCOUNT ON;  
  
    -- Insert statements for procedure here  
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[Row_Number],[filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], OMR_No,[Registration_No] ,[qpvc], [signature_present] CandSig, [Invigilator_Signed] InvSig,[Status], 
			 FinalDesc FinalStatus from NominalRoll1 where QPVCDesc =1 
end
go
CREATE or Alter PROCEDURE [dbo].[NominalRoll1_Status_Desc]  
 -- Add the parameters for the stored procedure here  
AS  
BEGIN  
 -- SET NOCOUNT ON added to prevent extra result sets from  
 -- interfering with SELECT statements.  
 SET NOCOUNT ON;  
  
    -- Insert statements for procedure here  
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[Row_Number],[filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], OMR_No,[Registration_No] ,[qpvc], [signature_present] CandSig, [Invigilator_Signed] InvSig,[Status], 
			 FinalDesc FinalStatus from NominalRoll1 where StatusDesc =1 
end

CREATE or Alter PROCEDURE [dbo].[NominalRoll1_CandSign_Desc]  
 -- Add the parameters for the stored procedure here  
AS  
BEGIN  
 -- SET NOCOUNT ON added to prevent extra result sets from  
 -- interfering with SELECT statements.  
 SET NOCOUNT ON;  
  
    -- Insert statements for procedure here  
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[Row_Number],[filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], OMR_No,[Registration_No] ,[qpvc], [signature_present] CandSig, [Invigilator_Signed] InvSig,[Status], 
			 FinalDesc FinalStatus from NominalRoll1 where CandSignDesc =1 
end
go
CREATE or Alter PROCEDURE [dbo].[NominalRoll1_InvSign_Desc]  
 -- Add the parameters for the stored procedure here  
AS  
BEGIN  
 -- SET NOCOUNT ON added to prevent extra result sets from  
 -- interfering with SELECT statements.  
 SET NOCOUNT ON;  
  
    -- Insert statements for procedure here  
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[Row_Number],[filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], OMR_No,[Registration_No] ,[qpvc], [signature_present] CandSig, [Invigilator_Signed] InvSig,[Status], 
			 FinalDesc FinalStatus from NominalRoll1 where InvSignDesc =1 
end
go
go
CREATE or Alter PROCEDURE [dbo].[NominalRoll2_SubjectCode_Desc]  
 -- Add the parameters for the stored procedure here  
AS  
BEGIN  
 -- SET NOCOUNT ON added to prevent extra result sets from  
 -- interfering with SELECT statements.  
 SET NOCOUNT ON;  
  
    -- Insert statements for procedure here  
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[Row_Number],[filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], QCAB_Serial_No,[Registration_No] , [signature_present] CandSig, [Invigilator_Signed] InvSig, [Status],
			 FinalDesc FinalStatus from NominalRoll2 where SubDesc =1 
end
go
CREATE or Alter PROCEDURE [dbo].[NominalRoll2_CenterCode_Desc]  
 -- Add the parameters for the stored procedure here  
AS  
BEGIN  
 -- SET NOCOUNT ON added to prevent extra result sets from  
 -- interfering with SELECT statements.  
 SET NOCOUNT ON;  
  
    -- Insert statements for procedure here  
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[Row_Number],[filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], QCAB_Serial_No,[Registration_No] , [signature_present] CandSig, [Invigilator_Signed] InvSig, [Status],
			 FinalDesc FinalStatus from NominalRoll2 where CenterCodeDesc =1 
end
go
CREATE or Alter PROCEDURE [dbo].[NominalRoll2_SubCenterCode_Desc]  
 -- Add the parameters for the stored procedure here  
AS  
BEGIN  
 -- SET NOCOUNT ON added to prevent extra result sets from  
 -- interfering with SELECT statements.  
 SET NOCOUNT ON;  
  
    -- Insert statements for procedure here  
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[Row_Number],[filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], QCAB_Serial_No,[Registration_No] , [signature_present] CandSig, [Invigilator_Signed] InvSig, [Status],
			 FinalDesc FinalStatus from NominalRoll2 where SubCenterCodeDesc =1 
end
go
CREATE or Alter PROCEDURE [dbo].[NominalRoll2_QCAB_Desc]  
 -- Add the parameters for the stored procedure here  
AS  
BEGIN  
 -- SET NOCOUNT ON added to prevent extra result sets from  
 -- interfering with SELECT statements.  
 SET NOCOUNT ON;  
  
    -- Insert statements for procedure here  
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[Row_Number],[filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], QCAB_Serial_No,[Registration_No] , [signature_present] CandSig, [Invigilator_Signed] InvSig, [Status],
			 FinalDesc FinalStatus from NominalRoll2 where QCABDesc =1 
end
go
CREATE or Alter PROCEDURE [dbo].[NominalRoll2_RegNo_Desc]  
 -- Add the parameters for the stored procedure here  
AS  
BEGIN  
 -- SET NOCOUNT ON added to prevent extra result sets from  
 -- interfering with SELECT statements.  
 SET NOCOUNT ON;  
  
    -- Insert statements for procedure here  
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[Row_Number],[filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], QCAB_Serial_No,[Registration_No] , [signature_present] CandSig, [Invigilator_Signed] InvSig, [Status],
			 FinalDesc FinalStatus from NominalRoll2 where RegNoDesc =1 
end
go
CREATE or Alter PROCEDURE [dbo].[NominalRoll2_CandSign_Desc]  
 -- Add the parameters for the stored procedure here  
AS  
BEGIN  
 -- SET NOCOUNT ON added to prevent extra result sets from  
 -- interfering with SELECT statements.  
 SET NOCOUNT ON;  
  
    -- Insert statements for procedure here  
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[Row_Number],[filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], QCAB_Serial_No,[Registration_No] , [signature_present] CandSig, [Invigilator_Signed] InvSig, [Status],
			 FinalDesc FinalStatus from NominalRoll2 where CandSignDesc =1 
end
go
CREATE or Alter PROCEDURE [dbo].[NominalRoll2_InvSign_Desc]  
 -- Add the parameters for the stored procedure here  
AS  
BEGIN  
 -- SET NOCOUNT ON added to prevent extra result sets from  
 -- interfering with SELECT statements.  
 SET NOCOUNT ON;  
  
    -- Insert statements for procedure here  
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[Row_Number],[filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], QCAB_Serial_No,[Registration_No] , [signature_present] CandSig, [Invigilator_Signed] InvSig, [Status],
			 FinalDesc FinalStatus from NominalRoll2 where InvSignDesc =1 
end
go
-----------
go
CREATE or Alter PROCEDURE [dbo].[NominalRoll2_FinalData]  
 -- Add the parameters for the stored procedure here  
AS  
BEGIN  
 -- SET NOCOUNT ON added to prevent extra result sets from  
 -- interfering with SELECT statements.  
 SET NOCOUNT ON;  
  
    -- Insert statements for procedure here  
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[Row_Number],[Filename], Center_Code, Subcenter_Code, 
			 [Subject_Code], QCAB_Serial_No,[Registration_No] , [signature_present] CandSig, [Invigilator_Signed] InvSig, [Status]
			 ,iif(len(Replace([center_code],' ',''))<1,1,0) CenterCodeDesc,iif(len(Replace([subcenter_code],' ',''))<1,1,0) [SubCenterCodeDesc],iif(len(Replace([subject_code],' ',''))<3,1,0) [SubDesc]
			,iif(len(Replace([status],' ',''))<1,1,0) StatusDesc, iif([signature_present]=1 ,0,1) CandSignDesc,iif([invigilator_signed]=1 ,0,1) [InvSignDesc]
			,iif(len(Replace([registration_no],' ',''))<9,1,0) RegNoDesc,iif(len(Replace([qcab_serial_no],' ',''))<7,1,0)  QCABDesc
			,FinalDesc FinalStatus,[created_at] ScannedOn from NominalRoll2 
end
go
CREATE or Alter PROCEDURE [dbo].[NominalRoll1_FinalData]  
 -- Add the parameters for the stored procedure here  
AS  
BEGIN  
 -- SET NOCOUNT ON added to prevent extra result sets from  
 -- interfering with SELECT statements.  
 SET NOCOUNT ON;  
  
    -- Insert statements for procedure here  
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[Filename],[Row_number],[Center_Code]
			,[Subcenter_Code],[Subject_Code],[Invigilator_signed]
			,[Status],[Signature_present],[OMR_No],[Registration_No],[QPVC]
			,iif(len(Replace([center_code],' ',''))<1,1,0) CenterCodeDesc,iif(len(Replace([subcenter_code],' ',''))<1,1,0) [SubCenterCodeDesc],iif(len(Replace([subject_code],' ',''))<3,1,0) [SubjectDesc]
			,iif(len(Replace([status],' ',''))<1,1,0) StatusDesc, iif([signature_present]=1 ,0,1) CandSignDesc,iif([invigilator_signed]=1 ,0,1)  [InvSignDesc],iif(len(Replace([omr_no],' ',''))<7,'1',0) OMRNoDesc
			,iif(len(Replace([registration_no],' ',''))<9,'1',0) RegNoDesc ,iif(len(Replace([qpvc],' ',''))<1,1,0)  QPVCDesc
			,FinalDesc FinalStatus,[created_at] ScannedOn from NominalRoll1 where StatusDesc =1 
end
go
CREATE or Alter PROCEDURE [dbo].[CounterFoil_FinalData]  
 -- Add the parameters for the stored procedure here  
AS  
BEGIN  
 -- SET NOCOUNT ON added to prevent extra result sets from  
 -- interfering with SELECT statements.  
 SET NOCOUNT ON;  
  
    -- Insert statements for procedure here  
	Select ROW_NUMBER() OVER(ORDER BY ID ASC) AS SlNo,ID SheetNo,[Filename], [Barcode], [Bubble_Regno],[Handwritten_Regno], 
		[Candidate_Signed], [Invigilator_Signed],[Subject_Code], [BookletSlNo],[WhitenerFlag],
		iif(Replace([barcode],' ','')='','1',0) BarcodeDesc, iif(len(Replace([bubble_regno],' ',''))<9,'1',0) OMRRegNoDesc, iif(len(Replace([handwritten_regno],' ',''))<9,'1',0) ICRRegNoDesc,
		iif([candidate_signed]=1 ,0,1) CandSignDesc,iif([invigilator_signed]=1 ,0,1)  InvSignDesc, iif(len(Replace([subject_code],' ',''))<3,'1',0) SubCodeDesc, iif(len(Replace([BookletSlNo],' ',''))<7,'1',0) BSlNoDesc,
		[whitenerflag] WhitenerDesc, [isblack] NonStandardSheet, [bubble_Th_status] [Threshold<35%], 
		FinalDesc FinalStatus,[created_at] ScannedOn from CounterFoilData  
end

go
CREATE or Alter PROCEDURE [dbo].[CounterFoil_DiscCountSummary]  
 -- Add the parameters for the stored procedure here  
AS  
BEGIN  
 -- SET NOCOUNT ON added to prevent extra result sets from  
 -- interfering with SELECT statements.  
 SET NOCOUNT ON;  
      -- Insert statements for procedure here 
	  Select Distinct M.Subject_Code,Barcode.BarcodeDesc,OMR.OMRRegNoDesc,ICR.ICRRegNoDesc,BSlNo.BSlNoDesc,CandSig.NoCandSig,InvSign.NoInvSign,Whitener.WhitenerApplied,Black.NonStandardSheet,Th.[Threshold<35%]  from CounterFoilData M Left Join 
	  (Select Subject_Code,Count('A') BarcodeDesc  from CounterFoilData where BarcodeDesc = 1 group by subject_code) Barcode 
	  on M.subject_code = Barcode.subject_code left Join
	  (Select Subject_Code,Count('A') OMRRegNoDesc  from CounterFoilData where OMRRegNoDesc = 1 group by subject_code) OMR 
	  on M.subject_code = OMR.subject_code left Join
	  (Select Subject_Code,Count('A') ICRRegNoDesc  from CounterFoilData where ICRRegNoDesc = 1 group by subject_code) ICR 
	  on M.subject_code = ICR.subject_code left Join
	  (Select Subject_Code,Count('A') BSlNoDesc  from CounterFoilData where BSlNoDesc = 1 group by subject_code) BSLNo 
	  on M.subject_code = BSlNo.subject_code left Join
	  (Select Subject_Code,Count('A') NoCandSig  from CounterFoilData where CandSigDesc = 1 group by subject_code) CandSig 
	  on M.subject_code = CandSig.subject_code left Join
	  (Select Subject_Code,Count('A') NoInvSign  from CounterFoilData where InvSignDesc = 1 group by subject_code) InvSign 
	  on M.subject_code = InvSign.subject_code left Join
	  (Select Subject_Code,Count('A') WhitenerApplied  from CounterFoilData where WhitenerDesc = 1 group by subject_code) Whitener 
	  on M.subject_code = Whitener.subject_code left Join
	  (Select Subject_Code,Count('A') [NonStandardSheet]  from CounterFoilData where isBlackDesc = 1 group by subject_code) Black 
	  on M.subject_code = Black.subject_code left Join
	  (Select Subject_Code,Count('A') [Threshold<35%]   from CounterFoilData where ThDesc = 1 group by subject_code) Th 
	  on M.subject_code = Th.subject_code 

 
end
go
go
CREATE or Alter PROCEDURE [dbo].[NominalRol1_DiscCountSummary]  
 -- Add the parameters for the stored procedure here  
AS  
BEGIN  
 -- SET NOCOUNT ON added to prevent extra result sets from  
 -- interfering with SELECT statements.  
 SET NOCOUNT ON;  
      -- Insert statements for procedure here 
	  Select Distinct M.Subject_Code,Center.CenterCodeDesc,SubCenter.SubCenterCodeDesc,OMR.OMRNoDesc,RegNo.RegNoDesc,CandSig.NoCandSig,InvSign.NoInvSign  from NominalRoll1 M Left Join 
	  (Select Subject_Code,Count('A') CenterCodeDesc  from NominalRoll1 where CenterCodeDesc = 1 group by subject_code) Center 
	  on M.subject_code = Center.subject_code left Join
	  (Select Subject_Code,Count('A') SubCenterCodeDesc  from NominalRoll1 where SubCenterCodeDesc = 1 group by subject_code) SubCenter 
	  on M.subject_code = SubCenter.subject_code left Join
	  (Select Subject_Code,Count('A') OMRNoDesc  from NominalRoll1 where OMRDesc = 1 group by subject_code) OMR 
	  on M.subject_code = OMR.subject_code left Join
	  (Select Subject_Code,Count('A') RegNoDesc  from NominalRoll1 where RegNoDesc = 1 group by subject_code) RegNo 
	  on M.subject_code = RegNo.subject_code left Join
	  (Select Subject_Code,Count('A') NoCandSig  from NominalRoll1 where CandSignDesc = 1 group by subject_code) CandSig 
	  on M.subject_code = CandSig.subject_code left Join
	  (Select Subject_Code,Count('A') NoInvSign  from NominalRoll1 where InvSignDesc = 1 group by subject_code) InvSign 
	  on M.subject_code = InvSign.subject_code 
	   
end
go
CREATE or Alter PROCEDURE [dbo].[NominalRol2_DiscCountSummary]  
 -- Add the parameters for the stored procedure here  
AS  
BEGIN  
 -- SET NOCOUNT ON added to prevent extra result sets from  
 -- interfering with SELECT statements.  
 SET NOCOUNT ON;  
      -- Insert statements for procedure here 
	  Select Distinct M.Subject_Code,Center.CenterCodeDesc,SubCenter.SubCenterCodeDesc,RegNo.RegNoDesc,QCAB.QCABDesc,CandSig.NoCandSig,InvSign.NoInvSign  from NominalRoll2 M Left Join 
	  (Select Subject_Code,Count('A') CenterCodeDesc  from NominalRoll2 where CenterCodeDesc = 1 group by subject_code) Center 
	  on M.subject_code = Center.subject_code left Join
	  (Select Subject_Code,Count('A') SubCenterCodeDesc  from NominalRoll2 where SubCenterCodeDesc = 1 group by subject_code) SubCenter 
	  on M.subject_code = SubCenter.subject_code left Join
	  (Select Subject_Code,Count('A') QCABDesc  from NominalRoll2 where QCABDesc = 1 group by subject_code) QCAB 
	  on M.subject_code = QCAB.subject_code left Join
	  (Select Subject_Code,Count('A') RegNoDesc  from NominalRoll2 where RegNoDesc = 1 group by subject_code) RegNo 
	  on M.subject_code = RegNo.subject_code left Join
	  (Select Subject_Code,Count('A') NoCandSig  from NominalRoll2 where CandSignDesc = 1 group by subject_code) CandSig 
	  on M.subject_code = CandSig.subject_code left Join
	  (Select Subject_Code,Count('A') NoInvSign  from NominalRoll2 where InvSignDesc = 1 group by subject_code) InvSign 
	  on M.subject_code = InvSign.subject_code 
	   
end

--usp_CounterFoilEditFor
--usp_LoadCounterfoilEditGrid @EditFor, @UserID
--usp_CounterFoilEditSkip @EditFor, @UserID
--usp_CounterFoilEditUpdate @EditFor, @UserID, @ID, @barcode,@bubble_regno,@handwritten_regno,@subject_code,@BookletSlNo,@CandSig, @InvSign, @WhitenerDesc, @isBlackDesc, @ThDesc

--Create usp_LoadCounterfoilEditGrid @EditFor, @UserID

--SlNo, ID, [filename], [barcode], [bubble_regno], [handwritten_regno], [subject_code], [BookletSlNo],  OMRRegNoDesc, ICRRegNoDesc, CandSigDesc, InvSignDesc, SubCodeDesc, BSlNoDesc,  WhitenerDesc [WhitenerApplied], isBlackDesc [Non Standard Sheet], ThDesc [Threshold < 35%]