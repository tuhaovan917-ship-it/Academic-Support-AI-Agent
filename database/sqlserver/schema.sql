IF DB_ID(N'AcademicSupportMock') IS NULL
BEGIN
    CREATE DATABASE AcademicSupportMock;
END;
GO

USE AcademicSupportMock;
GO

CREATE TABLE dbo.Students (
    StudentId NVARCHAR(20) NOT NULL PRIMARY KEY,
    FullName NVARCHAR(120) NOT NULL,
    Faculty NVARCHAR(120) NOT NULL,
    Major NVARCHAR(120) NOT NULL,
    ClassCode NVARCHAR(40) NOT NULL,
    IntakeYear INT NOT NULL,
    Email NVARCHAR(160) NOT NULL UNIQUE,
    CreatedAt DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET()
);
GO

CREATE TABLE dbo.Courses (
    CourseCode NVARCHAR(30) NOT NULL PRIMARY KEY,
    CourseName NVARCHAR(160) NOT NULL,
    Credits INT NOT NULL,
    Faculty NVARCHAR(120) NULL
);
GO

CREATE TABLE dbo.Enrollments (
    EnrollmentId UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID() PRIMARY KEY,
    StudentId NVARCHAR(20) NOT NULL,
    CourseCode NVARCHAR(30) NOT NULL,
    Semester NVARCHAR(30) NOT NULL,
    Status NVARCHAR(30) NOT NULL DEFAULT N'active',
    CreatedAt DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    CONSTRAINT FK_Enrollments_Students FOREIGN KEY (StudentId) REFERENCES dbo.Students(StudentId),
    CONSTRAINT FK_Enrollments_Courses FOREIGN KEY (CourseCode) REFERENCES dbo.Courses(CourseCode)
);
GO

CREATE TABLE dbo.Schedules (
    ScheduleId UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID() PRIMARY KEY,
    StudentId NVARCHAR(20) NOT NULL,
    CourseCode NVARCHAR(30) NOT NULL,
    Lecturer NVARCHAR(120) NOT NULL,
    DayOfWeek NVARCHAR(20) NOT NULL,
    StartPeriod INT NOT NULL,
    EndPeriod INT NOT NULL,
    Room NVARCHAR(40) NOT NULL,
    StartDate DATE NOT NULL,
    EndDate DATE NOT NULL,
    CONSTRAINT FK_Schedules_Students FOREIGN KEY (StudentId) REFERENCES dbo.Students(StudentId),
    CONSTRAINT FK_Schedules_Courses FOREIGN KEY (CourseCode) REFERENCES dbo.Courses(CourseCode)
);
GO

CREATE TABLE dbo.Grades (
    GradeId UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID() PRIMARY KEY,
    StudentId NVARCHAR(20) NOT NULL,
    CourseCode NVARCHAR(30) NOT NULL,
    Semester NVARCHAR(30) NOT NULL,
    ProcessScore DECIMAL(4,2) NOT NULL,
    FinalScore DECIMAL(4,2) NOT NULL,
    TotalScore DECIMAL(4,2) NOT NULL,
    LetterGrade NVARCHAR(5) NOT NULL,
    IsRetakeNeeded BIT NOT NULL DEFAULT 0,
    UpdatedAt DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    CONSTRAINT FK_Grades_Students FOREIGN KEY (StudentId) REFERENCES dbo.Students(StudentId),
    CONSTRAINT FK_Grades_Courses FOREIGN KEY (CourseCode) REFERENCES dbo.Courses(CourseCode)
);
GO

CREATE TABLE dbo.ChatSessions (
    SessionId UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID() PRIMARY KEY,
    StudentId NVARCHAR(20) NOT NULL,
    Title NVARCHAR(160) NOT NULL,
    CreatedAt DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    UpdatedAt DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    CONSTRAINT FK_ChatSessions_Students FOREIGN KEY (StudentId) REFERENCES dbo.Students(StudentId)
);
GO

CREATE TABLE dbo.ChatMessages (
    MessageId UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID() PRIMARY KEY,
    SessionId UNIQUEIDENTIFIER NOT NULL,
    Role NVARCHAR(30) NOT NULL,
    Content NVARCHAR(MAX) NOT NULL,
    CreatedAt DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    CONSTRAINT FK_ChatMessages_ChatSessions FOREIGN KEY (SessionId) REFERENCES dbo.ChatSessions(SessionId)
);
GO

CREATE TABLE dbo.ApiToolLogs (
    ToolLogId UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID() PRIMARY KEY,
    SessionId UNIQUEIDENTIFIER NULL,
    ToolName NVARCHAR(80) NOT NULL,
    RequestJson NVARCHAR(MAX) NOT NULL,
    ResponseJson NVARCHAR(MAX) NULL,
    Status NVARCHAR(30) NOT NULL,
    CreatedAt DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    CONSTRAINT FK_ApiToolLogs_ChatSessions FOREIGN KEY (SessionId) REFERENCES dbo.ChatSessions(SessionId)
);
GO

CREATE INDEX IX_Enrollments_Student_Semester ON dbo.Enrollments(StudentId, Semester);
CREATE INDEX IX_Schedules_Student ON dbo.Schedules(StudentId, DayOfWeek, StartPeriod);
CREATE INDEX IX_Grades_Student_Semester ON dbo.Grades(StudentId, Semester);
CREATE INDEX IX_ChatSessions_Student ON dbo.ChatSessions(StudentId, UpdatedAt DESC);
CREATE INDEX IX_ChatMessages_Session ON dbo.ChatMessages(SessionId, CreatedAt);
GO
