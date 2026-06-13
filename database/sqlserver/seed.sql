USE AcademicSupportMock;
GO

INSERT INTO dbo.Students (StudentId, FullName, Faculty, Major, ClassCode, IntakeYear, Email)
VALUES
    (N'SV001', N'Nguyen Van An', N'Cong nghe thong tin', N'Ky thuat phan mem', N'13DHTH01', 2023, N'an.nguyen@student.huit.edu.vn'),
    (N'SV002', N'Tran Thi Binh', N'Quan tri kinh doanh', N'Marketing', N'13DHQT02', 2023, N'binh.tran@student.huit.edu.vn');
GO

INSERT INTO dbo.Courses (CourseCode, CourseName, Credits, Faculty)
VALUES
    (N'IT301', N'Lap trinh Web', 3, N'Cong nghe thong tin'),
    (N'IT315', N'Co so du lieu', 3, N'Cong nghe thong tin'),
    (N'ENG201', N'Tieng Anh 3', 2, N'Ngoai ngu'),
    (N'IT101', N'Nhap mon lap trinh', 3, N'Cong nghe thong tin'),
    (N'MATH101', N'Giai tich', 3, N'Khoa hoc co ban'),
    (N'ENG102', N'Tieng Anh 2', 2, N'Ngoai ngu'),
    (N'MKT210', N'Hanh vi khach hang', 3, N'Quan tri kinh doanh'),
    (N'BUS220', N'Quan tri hoc', 3, N'Quan tri kinh doanh'),
    (N'BUS101', N'Kinh te vi mo', 3, N'Quan tri kinh doanh'),
    (N'MKT101', N'Marketing can ban', 3, N'Quan tri kinh doanh');
GO

INSERT INTO dbo.Schedules (StudentId, CourseCode, Lecturer, DayOfWeek, StartPeriod, EndPeriod, Room, StartDate, EndDate)
VALUES
    (N'SV001', N'IT301', N'ThS. Le Minh', N'Thu 2', 1, 3, N'B.09.02', '2026-06-01', '2026-08-30'),
    (N'SV001', N'IT315', N'TS. Pham Hoa', N'Thu 4', 4, 6, N'C.05.01', '2026-06-01', '2026-08-30'),
    (N'SV001', N'ENG201', N'ThS. Nguyen Lan', N'Thu 6', 7, 9, N'A.03.04', '2026-06-01', '2026-08-30'),
    (N'SV002', N'MKT210', N'ThS. Vo Khanh', N'Thu 3', 1, 3, N'D.02.06', '2026-06-01', '2026-08-30'),
    (N'SV002', N'BUS220', N'TS. Do My', N'Thu 5', 4, 6, N'B.04.03', '2026-06-01', '2026-08-30');
GO

INSERT INTO dbo.Grades (StudentId, CourseCode, Semester, ProcessScore, FinalScore, TotalScore, LetterGrade, IsRetakeNeeded)
VALUES
    (N'SV001', N'IT101', N'2025-2026-HK1', 7.50, 8.00, 7.80, N'B+', 0),
    (N'SV001', N'MATH101', N'2025-2026-HK1', 4.50, 3.80, 4.10, N'F', 1),
    (N'SV001', N'ENG102', N'2025-2026-HK1', 6.50, 6.00, 6.20, N'C+', 0),
    (N'SV002', N'BUS101', N'2025-2026-HK1', 8.00, 7.00, 7.40, N'B', 0),
    (N'SV002', N'MKT101', N'2025-2026-HK1', 8.50, 8.20, 8.30, N'A', 0);
GO
