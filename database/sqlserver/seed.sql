USE AcademicSupportDb;
GO

;WITH StudentSeed AS (
    SELECT *
    FROM (VALUES
        (N'SV001', N'Nguyễn Văn An', N'Công nghệ thông tin', N'Kỹ thuật phần mềm', N'13DHTH01', 2023, N'an.nguyen@student.huit.edu.vn'),
        (N'SV002', N'Trần Thị Bình', N'Quản trị kinh doanh', N'Marketing', N'13DHQT02', 2023, N'binh.tran@student.huit.edu.vn'),
        (N'SV003', N'Lê Minh Châu', N'Công nghệ thực phẩm', N'Đảm bảo chất lượng', N'12DHTP04', 2022, N'chau.le@student.huit.edu.vn'),
        (N'SV004', N'Phạm Quốc Dũng', N'Công nghệ thông tin', N'Hệ thống thông tin', N'12DHTH03', 2022, N'dung.pham@student.huit.edu.vn'),
        (N'SV005', N'Võ Hải Yến', N'Kế toán - Tài chính', N'Kế toán', N'13DHKT01', 2023, N'yen.vo@student.huit.edu.vn')
    ) AS v(StudentId, FullName, Faculty, Major, ClassCode, IntakeYear, Email)
)
MERGE dbo.Students AS target
USING StudentSeed AS source
    ON target.StudentId = source.StudentId
WHEN MATCHED THEN
    UPDATE SET
        FullName = source.FullName,
        Faculty = source.Faculty,
        Major = source.Major,
        ClassCode = source.ClassCode,
        IntakeYear = source.IntakeYear,
        Email = source.Email
WHEN NOT MATCHED THEN
    INSERT (StudentId, FullName, Faculty, Major, ClassCode, IntakeYear, Email)
    VALUES (source.StudentId, source.FullName, source.Faculty, source.Major, source.ClassCode, source.IntakeYear, source.Email);
GO

;WITH AccountSeed AS (
    SELECT *
    FROM (VALUES
        (N'SV001', N'Demo Student', N'demo@nexus.ai', N'8D969EEF6ECAD3C29A3A629280E686CF0C3F5D5A86AFF3CA12020C923ADC6C92')
    ) AS v(StudentId, FullName, Email, PasswordHash)
)
MERGE dbo.UserAccounts AS target
USING AccountSeed AS source
    ON target.Email = source.Email
WHEN MATCHED THEN
    UPDATE SET
        StudentId = source.StudentId,
        FullName = source.FullName,
        PasswordHash = source.PasswordHash
WHEN NOT MATCHED THEN
    INSERT (StudentId, FullName, Email, PasswordHash)
    VALUES (source.StudentId, source.FullName, source.Email, source.PasswordHash);
GO

;WITH CourseSeed AS (
    SELECT *
    FROM (VALUES
        (N'IT301', N'Lập trình Web', 3, N'Công nghệ thông tin'),
        (N'IT315', N'Cơ sở dữ liệu', 3, N'Công nghệ thông tin'),
        (N'ENG201', N'Tiếng Anh 3', 2, N'Ngoại ngữ'),
        (N'FT210', N'Hóa sinh thực phẩm', 3, N'Công nghệ thực phẩm'),
        (N'IT330', N'Phân tích dữ liệu', 3, N'Công nghệ thông tin'),
        (N'ACC201', N'Kế toán tài chính', 3, N'Kế toán - Tài chính'),
        (N'IT101', N'Nhập môn lập trình', 3, N'Công nghệ thông tin'),
        (N'MATH101', N'Giải tích', 3, N'Khoa học cơ bản'),
        (N'ENG102', N'Tiếng Anh 2', 2, N'Ngoại ngữ'),
        (N'MKT210', N'Hành vi khách hàng', 3, N'Quản trị kinh doanh'),
        (N'BUS220', N'Quản trị học', 3, N'Quản trị kinh doanh'),
        (N'BUS101', N'Kinh tế vi mô', 3, N'Quản trị kinh doanh'),
        (N'MKT101', N'Marketing căn bản', 3, N'Quản trị kinh doanh'),
        (N'FT101', N'Vi sinh thực phẩm', 3, N'Công nghệ thực phẩm'),
        (N'CHE101', N'Hóa đại cương', 3, N'Khoa học cơ bản'),
        (N'IT205', N'Cấu trúc dữ liệu', 3, N'Công nghệ thông tin'),
        (N'IT220', N'Mạng máy tính', 3, N'Công nghệ thông tin'),
        (N'ACC101', N'Nguyên lý kế toán', 3, N'Kế toán - Tài chính')
    ) AS v(CourseCode, CourseName, Credits, Faculty)
)
MERGE dbo.Courses AS target
USING CourseSeed AS source
    ON target.CourseCode = source.CourseCode
WHEN MATCHED THEN
    UPDATE SET
        CourseName = source.CourseName,
        Credits = source.Credits,
        Faculty = source.Faculty
WHEN NOT MATCHED THEN
    INSERT (CourseCode, CourseName, Credits, Faculty)
    VALUES (source.CourseCode, source.CourseName, source.Credits, source.Faculty);
GO

;WITH ScheduleSeed AS (
    SELECT *
    FROM (VALUES
        (N'SV001', N'IT301', N'ThS. Lê Minh', N'Thứ 2', 1, 3, N'B.09.02', CONVERT(date, '2026-06-01'), CONVERT(date, '2026-08-30')),
        (N'SV001', N'IT315', N'TS. Phạm Hoa', N'Thứ 4', 4, 6, N'C.05.01', CONVERT(date, '2026-06-01'), CONVERT(date, '2026-08-30')),
        (N'SV001', N'ENG201', N'ThS. Nguyễn Lan', N'Thứ 6', 7, 9, N'A.03.04', CONVERT(date, '2026-06-01'), CONVERT(date, '2026-08-30')),
        (N'SV002', N'MKT210', N'ThS. Võ Khánh', N'Thứ 3', 1, 3, N'D.02.06', CONVERT(date, '2026-06-01'), CONVERT(date, '2026-08-30')),
        (N'SV002', N'BUS220', N'TS. Đỗ Mỹ', N'Thứ 5', 4, 6, N'B.04.03', CONVERT(date, '2026-06-01'), CONVERT(date, '2026-08-30')),
        (N'SV003', N'FT210', N'TS. Nguyễn Hạnh', N'Thứ 2', 7, 9, N'A.06.01', CONVERT(date, '2026-06-01'), CONVERT(date, '2026-08-30')),
        (N'SV004', N'IT330', N'ThS. Trần Nam', N'Thứ 4', 1, 3, N'B.08.05', CONVERT(date, '2026-06-01'), CONVERT(date, '2026-08-30')),
        (N'SV005', N'ACC201', N'TS. Bùi Mai', N'Thứ 6', 4, 6, N'C.02.02', CONVERT(date, '2026-06-01'), CONVERT(date, '2026-08-30'))
    ) AS v(StudentId, CourseCode, Lecturer, DayOfWeek, StartPeriod, EndPeriod, Room, StartDate, EndDate)
)
DELETE target
FROM dbo.Schedules AS target
WHERE EXISTS (
    SELECT 1
    FROM ScheduleSeed AS source
    WHERE source.StudentId = target.StudentId
      AND source.CourseCode = target.CourseCode
);

;WITH ScheduleSeed AS (
    SELECT *
    FROM (VALUES
        (N'SV001', N'IT301', N'ThS. Lê Minh', N'Thứ 2', 1, 3, N'B.09.02', CONVERT(date, '2026-06-01'), CONVERT(date, '2026-08-30')),
        (N'SV001', N'IT315', N'TS. Phạm Hoa', N'Thứ 4', 4, 6, N'C.05.01', CONVERT(date, '2026-06-01'), CONVERT(date, '2026-08-30')),
        (N'SV001', N'ENG201', N'ThS. Nguyễn Lan', N'Thứ 6', 7, 9, N'A.03.04', CONVERT(date, '2026-06-01'), CONVERT(date, '2026-08-30')),
        (N'SV002', N'MKT210', N'ThS. Võ Khánh', N'Thứ 3', 1, 3, N'D.02.06', CONVERT(date, '2026-06-01'), CONVERT(date, '2026-08-30')),
        (N'SV002', N'BUS220', N'TS. Đỗ Mỹ', N'Thứ 5', 4, 6, N'B.04.03', CONVERT(date, '2026-06-01'), CONVERT(date, '2026-08-30')),
        (N'SV003', N'FT210', N'TS. Nguyễn Hạnh', N'Thứ 2', 7, 9, N'A.06.01', CONVERT(date, '2026-06-01'), CONVERT(date, '2026-08-30')),
        (N'SV004', N'IT330', N'ThS. Trần Nam', N'Thứ 4', 1, 3, N'B.08.05', CONVERT(date, '2026-06-01'), CONVERT(date, '2026-08-30')),
        (N'SV005', N'ACC201', N'TS. Bùi Mai', N'Thứ 6', 4, 6, N'C.02.02', CONVERT(date, '2026-06-01'), CONVERT(date, '2026-08-30'))
    ) AS v(StudentId, CourseCode, Lecturer, DayOfWeek, StartPeriod, EndPeriod, Room, StartDate, EndDate)
)
INSERT INTO dbo.Schedules (StudentId, CourseCode, Lecturer, DayOfWeek, StartPeriod, EndPeriod, Room, StartDate, EndDate)
SELECT StudentId, CourseCode, Lecturer, DayOfWeek, StartPeriod, EndPeriod, Room, StartDate, EndDate
FROM ScheduleSeed;
GO

;WITH GradeSeed AS (
    SELECT *
    FROM (VALUES
        (N'SV001', N'IT101', N'2025-2026-HK1', 7.50, 8.00, 7.80, N'B+', CONVERT(bit, 0)),
        (N'SV001', N'MATH101', N'2025-2026-HK1', 4.50, 3.80, 4.10, N'F', CONVERT(bit, 1)),
        (N'SV001', N'ENG102', N'2025-2026-HK1', 6.50, 6.00, 6.20, N'C+', CONVERT(bit, 0)),
        (N'SV002', N'BUS101', N'2025-2026-HK1', 8.00, 7.00, 7.40, N'B', CONVERT(bit, 0)),
        (N'SV002', N'MKT101', N'2025-2026-HK1', 8.50, 8.20, 8.30, N'A', CONVERT(bit, 0)),
        (N'SV003', N'FT101', N'2025-2026-HK1', 4.00, 4.20, 4.10, N'F', CONVERT(bit, 1)),
        (N'SV003', N'CHE101', N'2025-2026-HK1', 5.00, 4.50, 4.70, N'D', CONVERT(bit, 1)),
        (N'SV004', N'IT205', N'2025-2026-HK1', 8.00, 8.50, 8.30, N'A', CONVERT(bit, 0)),
        (N'SV004', N'IT220', N'2025-2026-HK1', 5.00, 4.80, 4.90, N'D', CONVERT(bit, 1)),
        (N'SV005', N'ACC101', N'2025-2026-HK1', 6.50, 6.80, 6.70, N'C+', CONVERT(bit, 0))
    ) AS v(StudentId, CourseCode, Semester, ProcessScore, FinalScore, TotalScore, LetterGrade, IsRetakeNeeded)
)
MERGE dbo.Grades AS target
USING GradeSeed AS source
    ON target.StudentId = source.StudentId
    AND target.CourseCode = source.CourseCode
    AND target.Semester = source.Semester
WHEN MATCHED THEN
    UPDATE SET
        ProcessScore = source.ProcessScore,
        FinalScore = source.FinalScore,
        TotalScore = source.TotalScore,
        LetterGrade = source.LetterGrade,
        IsRetakeNeeded = source.IsRetakeNeeded,
        UpdatedAt = SYSDATETIMEOFFSET()
WHEN NOT MATCHED THEN
    INSERT (StudentId, CourseCode, Semester, ProcessScore, FinalScore, TotalScore, LetterGrade, IsRetakeNeeded)
    VALUES (source.StudentId, source.CourseCode, source.Semester, source.ProcessScore, source.FinalScore, source.TotalScore, source.LetterGrade, source.IsRetakeNeeded);
GO
