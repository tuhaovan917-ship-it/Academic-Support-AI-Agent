import { AfterViewChecked, Component, ElementRef, OnInit, ViewChild } from '@angular/core';

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
export class AppComponent implements OnInit, AfterViewChecked {
  @ViewChild('chatHistory') private chatHistory?: ElementRef<HTMLElement>;

  students: Student[] = [];
  selectedStudentId = '';
  selectedStudent?: Student;
  sessionId?: string;

  schedule: ScheduleItem[] = [];
  grades: GradeRecord[] = [];
  summary?: AcademicSummary;

  messages: ChatMessage[] = [];
  pendingUserMessage?: ChatMessage;
  citations: ChatCitation[] = [];
  cards: ChatCard[] = [];
  prompt = '';
  isSending = false;
  isLoadingStudent = false;
  isBackendAvailable = true;
  errorMessage = '';
  private shouldScrollToBottom = false;

  readonly quickPrompts = [
    'Tóm tắt câu trả lời này',
    'Giải thích dễ hiểu hơn',
    'Cần gặp phòng đào tạo khi nào?',
  ];

  private readonly fallbackStudent: Student = {
    id: 'SV001',
    fullName: 'Nguyen Van An',
    faculty: 'Công nghệ thông tin',
    major: 'Kỹ thuật phần mềm',
    classCode: '13DHTH01',
    intakeYear: 2023,
    email: 'an.nguyen@student.huit.edu.vn',
  };

  constructor(private readonly api: AcademicApiService) {}

  ngOnInit(): void {
    this.api.getStudents().subscribe({
      next: (students) => {
        this.isBackendAvailable = true;
        this.errorMessage = '';
        this.students = students;
        if (students.length > 0) {
          this.selectedStudentId = students[0].id;
          this.selectStudent(students[0].id);
        }
      },
      error: () => {
        this.useOfflinePreview();
      },
    });
  }

  ngAfterViewChecked(): void {
    if (!this.shouldScrollToBottom) {
      return;
    }

    this.shouldScrollToBottom = false;
    this.scrollToBottom();
  }

  selectStudent(studentId: string): void {
    this.selectedStudentId = studentId;
    this.selectedStudent = this.students.find((student) => student.id === studentId);
    this.startNewChat();
    this.errorMessage = '';

    if (!this.isBackendAvailable) {
      return;
    }

    this.isLoadingStudent = true;
    this.api.getSchedule(studentId).subscribe({
      next: (schedule) => (this.schedule = schedule),
      error: () => this.handleBackendLost('Không tải được thời khóa biểu.'),
    });
    this.api.getGrades(studentId).subscribe({
      next: (grades) => (this.grades = grades),
      error: () => this.handleBackendLost('Không tải được bảng điểm.'),
    });
    this.api.getAcademicSummary(studentId).subscribe({
      next: (summary) => {
        this.summary = summary;
        this.isLoadingStudent = false;
      },
      error: () => {
        this.isLoadingStudent = false;
        this.handleBackendLost('Không tải được tóm tắt học tập.');
      },
    });
  }

  startNewChat(): void {
    this.sessionId = undefined;
    this.messages = [];
    this.pendingUserMessage = undefined;
    this.cards = [];
    this.citations = [];
    this.prompt = '';
    this.errorMessage = '';
    this.queueScrollToBottom();
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

    if (!this.isBackendAvailable) {
      this.addLocalOfflineReply(message);
      this.prompt = '';
      this.queueScrollToBottom();
      return;
    }

    this.isSending = true;
    this.errorMessage = '';
    this.prompt = '';
    this.cards = [];
    this.citations = [];
    this.pendingUserMessage = {
      id: crypto.randomUUID(),
      sessionId: this.sessionId ?? 'pending',
      role: 'user',
      content: message,
      createdAt: new Date().toISOString(),
    };
    this.queueScrollToBottom();

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
          this.pendingUserMessage = undefined;
          this.citations = response.citations;
          this.cards = response.cards;
          this.isSending = false;
          this.queueScrollToBottom();
        },
        error: () => {
          this.isSending = false;
          this.pendingUserMessage = undefined;
          this.handleBackendLost('Gửi câu hỏi thất bại. Kiểm tra backend rồi thử lại.');
          this.addLocalOfflineReply(message);
          this.queueScrollToBottom();
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

  private useOfflinePreview(): void {
    this.isBackendAvailable = false;
    this.isLoadingStudent = false;
    this.errorMessage = '';
    this.students = [this.fallbackStudent];
    this.selectedStudentId = this.fallbackStudent.id;
    this.selectedStudent = this.fallbackStudent;
    this.schedule = [];
    this.grades = [];
    this.summary = undefined;
  }

  private handleBackendLost(message: string): void {
    this.isBackendAvailable = false;
    this.errorMessage = message;
  }

  private addLocalOfflineReply(message: string): void {
    const sessionId = this.sessionId ?? crypto.randomUUID();
    this.sessionId = sessionId;
    const now = new Date().toISOString();
    this.messages = [
      ...this.messages,
      {
        id: crypto.randomUUID(),
        sessionId,
        role: 'user',
        content: message,
        createdAt: now,
      },
      {
        id: crypto.randomUUID(),
        sessionId,
        role: 'assistant',
        content:
          'Backend hiện chưa kết nối nên mình chỉ hiển thị bản xem trước giao diện. Hãy chạy AcademicSupport.Api ở http://localhost:5098 để chatbot trả lời bằng dữ liệu thật.',
        createdAt: now,
      },
    ];
    this.cards = [];
    this.citations = [];
    this.queueScrollToBottom();
  }

  private queueScrollToBottom(): void {
    this.shouldScrollToBottom = true;
    setTimeout(() => this.scrollToBottom(), 0);
  }

  private scrollToBottom(): void {
    const element = this.chatHistory?.nativeElement;
    if (!element) {
      return;
    }

    element.scrollTo({
      top: element.scrollHeight,
      behavior: 'smooth',
    });
  }
}
