import { AfterViewChecked, Component, ElementRef, OnInit, ViewChild } from '@angular/core';

import {
  AuthResponse,
  AuthUser,
  ChatCard,
  ChatCitation,
  ChatMessage,
  ChatSession,
  Student,
} from './models/academic.models';
import { AcademicApiService } from './services/academic-api.service';

interface StoredAuth {
  accessToken: string;
  user: AuthUser;
}

@Component({
  selector: 'app-root',
  standalone: false,
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css'],
})
export class AppComponent implements OnInit, AfterViewChecked {
  @ViewChild('chatHistory') private chatHistory?: ElementRef<HTMLElement>;
  @ViewChild('promptInput') private promptInput?: ElementRef<HTMLTextAreaElement>;

  students: Student[] = [];
  selectedStudentId = '';
  selectedStudent?: Student;
  sessionId?: string;

  messages: ChatMessage[] = [];
  sessions: ChatSession[] = [];
  pendingUserMessage?: ChatMessage;
  citations: ChatCitation[] = [];
  cards: ChatCard[] = [];
  prompt = '';
  isSending = false;
  isLoadingStudent = false;
  isBackendAvailable = true;
  errorMessage = '';
  agentStatus = '';
  agentRoute = '';
  clarificationQuestions: string[] = [];

  isAuthenticated = false;
  authMode: 'login' | 'register' = 'login';
  authUser?: AuthUser;
  accessToken = '';
  authErrorMessage = '';
  isAuthSubmitting = false;
  showPassword = false;

  loginForm = {
    email: 'demo@nexus.ai',
    password: '123456',
    rememberMe: true,
  };

  registerForm = {
    fullName: '',
    email: '',
    password: '',
    studentId: '',
  };

  readonly quickPrompts = [
    'Đăng ký học phần',
    'Điểm và môn nợ',
    'Lịch học tuần này',
    'Xét tốt nghiệp',
    'Điểm A là từ mấy đến mấy?',
  ];

  private readonly storageKey = 'nexus-auth';
  private shouldScrollToBottom = false;

  private readonly fallbackStudent: Student = {
    id: 'SV001',
    fullName: 'Nguyễn Văn An',
    faculty: 'Công nghệ thông tin',
    major: 'Kỹ thuật phần mềm',
    classCode: '13DHTH01',
    intakeYear: 2023,
    email: 'an.nguyen@student.huit.edu.vn',
  };

  constructor(private readonly api: AcademicApiService) {}

  get isEmptyChat(): boolean {
    return !this.sessionId && this.messages.length === 0 && !this.pendingUserMessage && !this.isSending;
  }

  get currentAuthSubtitle(): string {
    return this.authMode === 'login'
      ? 'Đăng nhập để truy cập hệ thống tư vấn học vụ dùng AI Core, RAG và tool-use.'
      : 'Tạo tài khoản để lưu lịch sử chat và gắn với hồ sơ sinh viên mẫu.';
  }

  ngOnInit(): void {
    this.prefetchStudentsForRegister();
    const stored = this.restoreAuth();
    if (stored) {
      this.isAuthenticated = true;
      this.accessToken = stored.accessToken;
      this.authUser = stored.user;
      this.loadInitialData(stored.user.studentId);
    }
  }

  ngAfterViewChecked(): void {
    if (!this.shouldScrollToBottom) {
      return;
    }

    this.shouldScrollToBottom = false;
    this.scrollToBottom();
  }

  switchAuthMode(mode: 'login' | 'register'): void {
    this.authMode = mode;
    this.authErrorMessage = '';
  }

  submitLogin(): void {
    if (this.isAuthSubmitting) {
      return;
    }

    this.isAuthSubmitting = true;
    this.authErrorMessage = '';

    this.api.login(this.loginForm).subscribe({
      next: (response) => this.handleAuthSuccess(response, this.loginForm.rememberMe),
      error: (error) => this.handleAuthError(error, 'Không đăng nhập được. Hãy kiểm tra email, mật khẩu hoặc chạy backend.'),
    });
  }

  submitRegister(): void {
    if (this.isAuthSubmitting) {
      return;
    }

    this.isAuthSubmitting = true;
    this.authErrorMessage = '';

    this.api.register({
      fullName: this.registerForm.fullName,
      email: this.registerForm.email,
      password: this.registerForm.password,
      studentId: this.registerForm.studentId || undefined,
    }).subscribe({
      next: (response) => this.handleAuthSuccess(response, true),
      error: (error) => this.handleAuthError(error, 'Không tạo được tài khoản. Hãy kiểm tra thông tin và thử lại.'),
    });
  }

  logout(): void {
    window.localStorage.removeItem(this.storageKey);
    this.isAuthenticated = false;
    this.authUser = undefined;
    this.accessToken = '';
    this.sessionId = undefined;
    this.messages = [];
    this.sessions = [];
    this.clearAgentArtifacts();
    this.prompt = '';
    this.errorMessage = '';
    this.authMode = 'login';
  }

  selectStudent(studentId: string): void {
    this.selectedStudentId = studentId;
    this.selectedStudent = this.students.find((student) => student.id === studentId);
    this.startNewChat();
    this.sessions = [];
    this.errorMessage = '';

    if (!this.isBackendAvailable) {
      return;
    }

    this.loadSessions();
    this.isLoadingStudent = true;
    this.isLoadingStudent = false;
  }

  startNewChat(): void {
    this.sessionId = undefined;
    this.messages = [];
    this.pendingUserMessage = undefined;
    this.clearAgentArtifacts();
    this.prompt = '';
    this.errorMessage = '';
    this.queueScrollToBottom();
  }

  openSession(session: ChatSession): void {
    this.sessionId = session.id;
    this.pendingUserMessage = undefined;
    this.clearAgentArtifacts();
    this.errorMessage = '';

    if (!this.isBackendAvailable) {
      return;
    }

    this.api.getChatMessages(session.id).subscribe({
      next: (messages) => {
        this.messages = messages;
        this.queueScrollToBottom();
      },
      error: () => this.handleBackendLost('Không tải được lịch sử hội thoại.'),
    });
  }

  usePrompt(value: string): void {
    this.prompt = value;
    this.sendMessage();
  }

  focusPromptInput(): void {
    this.promptInput?.nativeElement.focus();
  }

  handlePromptKeydown(event: KeyboardEvent): void {
    if (event.key !== 'Enter' || event.shiftKey) {
      return;
    }

    event.preventDefault();
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
    this.clearAgentArtifacts();
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
          this.agentStatus = response.status;
          this.agentRoute = response.route;
          this.clarificationQuestions = response.clarificationQuestions ?? [];
          this.isSending = false;
          this.loadSessions();
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

  jsonFromCard(card: ChatCard): string {
    return JSON.stringify(card.data, null, 2);
  }

  retrievalRowsFromCard(card: ChatCard): unknown[] {
    return Array.isArray(card.data) ? card.data : [];
  }

  trackByMessageId(_: number, message: ChatMessage): string {
    return message.id;
  }

  trackBySessionId(_: number, session: ChatSession): string {
    return session.id;
  }

  trackByStudentId(_: number, student: Student): string {
    return student.id;
  }

  trackByIndex(index: number): number {
    return index;
  }

  private handleAuthSuccess(response: AuthResponse, persist: boolean): void {
    this.isAuthSubmitting = false;
    this.isAuthenticated = true;
    this.accessToken = response.accessToken;
    this.authUser = response.user;
    this.authErrorMessage = '';

    if (persist) {
      window.localStorage.setItem(
        this.storageKey,
        JSON.stringify({ accessToken: response.accessToken, user: response.user } satisfies StoredAuth)
      );
    } else {
      window.localStorage.removeItem(this.storageKey);
    }

    this.loadInitialData(response.user.studentId);
  }

  private handleAuthError(error: unknown, fallbackMessage: string): void {
    this.isAuthSubmitting = false;
    const apiMessage = this.extractApiMessage(error);
    this.authErrorMessage = apiMessage || fallbackMessage;
  }

  private extractApiMessage(error: unknown): string {
    if (typeof error === 'object' && error && 'error' in error) {
      const payload = (error as { error?: { message?: string } }).error;
      return payload?.message ?? '';
    }

    return '';
  }

  private loadInitialData(preferredStudentId?: string): void {
    this.api.getStudents().subscribe({
      next: (students) => {
        this.isBackendAvailable = true;
        this.errorMessage = '';
        this.students = students;
        const selected = students.find((student) => student.id === preferredStudentId) ?? students[0];
        if (selected) {
          this.selectedStudentId = selected.id;
          this.selectStudent(selected.id);
        }
      },
      error: () => this.useOfflinePreview(),
    });
  }

  private loadSessions(): void {
    if (!this.selectedStudentId || !this.isBackendAvailable) {
      return;
    }

    this.api.getChatSessions(this.selectedStudentId).subscribe({
      next: (sessions) => (this.sessions = sessions),
      error: () => this.handleBackendLost('Không tải được danh sách hội thoại.'),
    });
  }

  private prefetchStudentsForRegister(): void {
    this.api.getStudents().subscribe({
      next: (students) => {
        this.students = students;
        if (!this.registerForm.studentId && students.length > 0) {
          this.registerForm.studentId = students[0].id;
        }
      },
      error: () => {
        this.students = [this.fallbackStudent];
        this.registerForm.studentId = this.fallbackStudent.id;
      },
    });
  }

  private restoreAuth(): StoredAuth | null {
    const raw = window.localStorage.getItem(this.storageKey);
    if (!raw) {
      return null;
    }

    try {
      return JSON.parse(raw) as StoredAuth;
    } catch {
      window.localStorage.removeItem(this.storageKey);
      return null;
    }
  }

  private useOfflinePreview(): void {
    this.isBackendAvailable = false;
    this.isLoadingStudent = false;
    this.errorMessage = '';
    this.students = [this.fallbackStudent];
    this.selectedStudentId = this.fallbackStudent.id;
    this.selectedStudent = this.fallbackStudent;
    this.sessions = [];
  }

  private handleBackendLost(message: string): void {
    this.isBackendAvailable = false;
    this.errorMessage = message;
  }

  private addLocalOfflineReply(message: string): void {
    const sessionId = this.sessionId ?? crypto.randomUUID();
    const isNewSession = !this.sessionId;
    this.sessionId = sessionId;
    const now = new Date().toISOString();
    if (isNewSession) {
      this.sessions = [
        {
          id: sessionId,
          studentId: this.selectedStudentId,
          title: this.toSessionTitle(message),
          createdAt: now,
          updatedAt: now,
        },
        ...this.sessions,
      ];
    } else {
      this.sessions = this.sessions.map((session) =>
        session.id === sessionId ? { ...session, updatedAt: now } : session
      );
    }
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
          'Backend hiện chưa kết nối nên mình chỉ hiển thị bản xem trước giao diện. Hãy chạy AcademicSupport.Api để chatbot trả lời bằng AI Core/RAG.',
        createdAt: now,
      },
    ];
    this.clearAgentArtifacts();
    this.queueScrollToBottom();
  }

  private clearAgentArtifacts(): void {
    this.cards = [];
    this.citations = [];
    this.agentStatus = '';
    this.agentRoute = '';
    this.clarificationQuestions = [];
  }

  private queueScrollToBottom(): void {
    this.shouldScrollToBottom = true;
    setTimeout(() => this.scrollToBottom(), 0);
  }

  private toSessionTitle(message: string): string {
    const title = message.trim().replace(/\s+/g, ' ');
    return title.length <= 60 ? title : `${title.slice(0, 60).trimEnd()}...`;
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
