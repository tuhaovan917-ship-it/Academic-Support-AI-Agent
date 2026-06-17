export interface Student {
  id: string;
  fullName: string;
  faculty: string;
  major: string;
  classCode: string;
  intakeYear: number;
  email: string;
}

export interface ScheduleItem {
  id: string;
  studentId: string;
  courseCode: string;
  courseName: string;
  lecturer: string;
  dayOfWeek: string;
  startPeriod: number;
  endPeriod: number;
  room: string;
  startDate: string;
  endDate: string;
}

export interface GradeRecord {
  id: string;
  studentId: string;
  courseCode: string;
  courseName: string;
  credits: number;
  processScore: number;
  finalScore: number;
  totalScore: number;
  letterGrade: string;
  semester: string;
  isRetakeNeeded: boolean;
}

export interface AcademicSummary {
  studentId: string;
  gpa10: number;
  gpa4: number;
  completedCredits: number;
  debtCredits: number;
  warningFlags: string[];
  retakeCourses: GradeRecord[];
}

export interface ChatMessage {
  id: string;
  sessionId: string;
  role: 'user' | 'assistant';
  content: string;
  createdAt: string;
}

export interface AuthUser {
  id: string;
  fullName: string;
  email: string;
  studentId: string;
}

export interface AuthResponse {
  accessToken: string;
  user: AuthUser;
  student: Student;
}

export interface RegisterRequest {
  fullName: string;
  email: string;
  password: string;
  studentId?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
  rememberMe: boolean;
}

export interface ChatSession {
  id: string;
  studentId: string;
  title: string;
  createdAt: string;
  updatedAt: string;
}

export interface ChatCitation {
  source: string;
  title: string;
  excerpt: string;
}

export interface ChatCard {
  type: 'schedule' | 'grades' | 'student' | 'tool_results' | 'retrieval_results' | string;
  title: string;
  data: unknown;
}

export interface ChatResponse {
  sessionId: string;
  userMessage: ChatMessage;
  assistantMessage: ChatMessage;
  citations: ChatCitation[];
  cards: ChatCard[];
  status: string;
  route: string;
  needsClarification: boolean;
  clarificationQuestions?: string[];
  error?: unknown;
  agent?: unknown;
}

export interface ChatRequest {
  studentId: string;
  sessionId?: string;
  message: string;
}
