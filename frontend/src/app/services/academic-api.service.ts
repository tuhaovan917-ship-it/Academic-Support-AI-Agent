import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../environments/environment';
import {
  AcademicSummary,
  ChatMessage,
  ChatRequest,
  ChatResponse,
  ChatSession,
  GradeRecord,
  ScheduleItem,
  Student,
} from '../models/academic.models';

@Injectable({ providedIn: 'root' })
export class AcademicApiService {
  private readonly apiBaseUrl = environment.apiBaseUrl;

  constructor(private readonly http: HttpClient) {}

  getStudents(): Observable<Student[]> {
    return this.http.get<Student[]>(`${this.apiBaseUrl}/students`);
  }

  getSchedule(studentId: string): Observable<ScheduleItem[]> {
    return this.http.get<ScheduleItem[]>(`${this.apiBaseUrl}/students/${studentId}/schedule`);
  }

  getGrades(studentId: string): Observable<GradeRecord[]> {
    return this.http.get<GradeRecord[]>(`${this.apiBaseUrl}/students/${studentId}/grades`);
  }

  getAcademicSummary(studentId: string): Observable<AcademicSummary> {
    return this.http.get<AcademicSummary>(`${this.apiBaseUrl}/students/${studentId}/academic-summary`);
  }

  getChatSessions(studentId?: string): Observable<ChatSession[]> {
    const suffix = studentId ? `?studentId=${encodeURIComponent(studentId)}` : '';
    return this.http.get<ChatSession[]>(`${this.apiBaseUrl}/chat/sessions${suffix}`);
  }

  getChatMessages(sessionId: string): Observable<ChatMessage[]> {
    return this.http.get<ChatMessage[]>(`${this.apiBaseUrl}/chat/sessions/${sessionId}/messages`);
  }

  sendChat(request: ChatRequest): Observable<ChatResponse> {
    return this.http.post<ChatResponse>(`${this.apiBaseUrl}/chat`, request);
  }
}
