import { Component, OnInit } from '@angular/core';

import {
  AcademicSummary,
  ChatCard,
  ChatCitation,
  ChatMessage,
  GradeRecord,
  ScheduleItem,
  Student,
} from './models/academic.models';
import { AcademicApiService } from './services/academic-api.service';

interface GradesCardData {
  summary: AcademicSummary | null;
  grades: GradeRecord[];
}

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css'],
})
export class AppComponent implements OnInit {
  students: Student[] = [];
  selectedStudentId = '';
  selectedStudent?: Student;
  sessionId?: string;

  schedule: ScheduleItem[] = [];
  grades: GradeRecord[] = [];
  summary?: AcademicSummary;

  messages: ChatMessage[] = [];
  citations: ChatCitation[] = [];
  cards: ChatCard[] = [];
  prompt = '';
  isSending = false;
  isLoadingStudent = false;
  errorMessage = '';

  readonly quickPrompts = [
    'Tóm tắt câu trả lời này',
    'Giải thích dễ hiểu hơn',
    'Cần gặp phòng đào tạo khi nào?',
  ];

  readonly recentTopics = [
    'Đăng ký học phần',
    'Điểm và môn nợ',
    'Lịch học tuần này',
  ];

  constructor(private readonly api: AcademicApiService) {}

  ngOnInit(): void {
    this.api.getStudents().subscribe({
      next: (students) => {
        this.students = students;
        if (students.length > 0) {
          this.selectedStudentId = students[0].id;
          this.selectStudent(students[0].id);
        }
      },
      error: () => {
        this.errorMessage = 'Không kết nối được backend. Hãy chạy AcademicSupport.Api trước.';
      },
    });
  }

  selectStudent(studentId: string): void {
    this.selectedStudentId = studentId;
    this.selectedStudent = this.students.find((student) => student.id === studentId);
    this.startNewChat();
    this.errorMessage = '';
    this.isLoadingStudent = true;

    this.api.getSchedule(studentId).subscribe({
      next: (schedule) => (this.schedule = schedule),
      error: () => (this.errorMessage = 'Không tải được thời khóa biểu.'),
    });
    this.api.getGrades(studentId).subscribe({
      next: (grades) => (this.grades = grades),
      error: () => (this.errorMessage = 'Không tải được bảng điểm.'),
    });
    this.api.getAcademicSummary(studentId).subscribe({
      next: (summary) => {
        this.summary = summary;
        this.isLoadingStudent = false;
      },
      error: () => {
        this.errorMessage = 'Không tải được tóm tắt học tập.';
        this.isLoadingStudent = false;
      },
    });
  }

  startNewChat(): void {
    this.sessionId = undefined;
    this.messages = [];
    this.cards = [];
    this.citations = [];
    this.prompt = '';
  }

  askSchedule(): void {
    this.usePrompt('Cho em xem lịch học tuần này');
  }

  askGrades(): void {
    this.usePrompt('Điểm GPA và môn nợ của em thế nào?');
  }

  askRegistration(): void {
    this.usePrompt('Em đăng ký học phần như thế nào?');
  }

  usePrompt(value: string): void {
    this.prompt = value;
    this.sendMessage();
  }

  sendMessage(): void {
    const message = this.prompt.trim();
    if (!message || !this.selectedStudentId || this.isSending) {
      return;
    }

    this.isSending = true;
    this.errorMessage = '';
    this.prompt = '';

    this.api
      .sendChat({
        studentId: this.selectedStudentId,
        sessionId: this.sessionId,
        message,
      })
      .subscribe({
        next: (response) => {
          this.sessionId = response.sessionId;
          this.messages = [...this.messages, response.userMessage, response.assistantMessage];
          this.citations = response.citations;
          this.cards = response.cards;
          this.isSending = false;
        },
        error: () => {
          this.errorMessage = 'Gửi câu hỏi thất bại. Kiểm tra backend rồi thử lại.';
          this.isSending = false;
        },
      });
  }

  scheduleFromCard(card: ChatCard): ScheduleItem[] {
    return Array.isArray(card.data) ? (card.data as ScheduleItem[]) : [];
  }

  gradesFromCard(card: ChatCard): GradeRecord[] {
    const data = card.data as Partial<GradesCardData>;
    return Array.isArray(data.grades) ? data.grades : [];
  }

  summaryFromCard(card: ChatCard): AcademicSummary | null {
    const data = card.data as Partial<GradesCardData>;
    return data.summary ?? null;
  }

  trackByMessageId(_: number, message: ChatMessage): string {
    return message.id;
  }
}
