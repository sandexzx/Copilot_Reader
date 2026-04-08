/** API client for Copilot Reader backend. */

import type { Session, SessionSummary, Event, SessionStats, TreeNode, DailyUsageResponse, DeleteResult, CopilotUserInfo } from './types';

function getBaseUrl(): string {
	if (typeof window === 'undefined') return 'http://localhost:8000';
	const { hostname, port } = window.location;
	if (port === '5173') return `http://${hostname}:8000`;
	return window.location.origin;
}

let baseUrl = getBaseUrl();

export function setBaseUrl(url: string): void {
	baseUrl = url;
}

export function getApiBaseUrl(): string {
	return baseUrl;
}

async function apiFetch<T>(path: string, options?: { method?: string; body?: unknown }): Promise<T> {
	const fetchOptions: RequestInit = {};
	if (options?.method) {
		fetchOptions.method = options.method;
	}
	if (options?.body !== undefined) {
		fetchOptions.headers = { 'Content-Type': 'application/json' };
		fetchOptions.body = JSON.stringify(options.body);
	}
	const res = await fetch(`${baseUrl}${path}`, fetchOptions);
	if (!res.ok) {
		throw new Error(`API error ${res.status}: ${res.statusText}`);
	}
	return res.json() as Promise<T>;
}

export function fetchSessions(): Promise<SessionSummary[]> {
	return apiFetch<SessionSummary[]>('/api/sessions');
}

export function fetchSession(id: string): Promise<Session> {
	return apiFetch<Session>(`/api/sessions/${id}`);
}

export function fetchSessionStats(id: string): Promise<SessionStats> {
	return apiFetch<SessionStats>(`/api/sessions/${id}/stats`);
}

export function fetchSessionEvents(id: string): Promise<Event[]> {
	return apiFetch<Event[]>(`/api/sessions/${id}/events`);
}

export function fetchSessionTree(id: string): Promise<TreeNode[]> {
	return apiFetch<TreeNode[]>(`/api/sessions/${id}/tree`);
}

export function fetchDailyUsage(): Promise<DailyUsageResponse> {
	return apiFetch<DailyUsageResponse>('/api/sessions/stats/daily');
}

export function deleteSession(id: string): Promise<DeleteResult> {
	return apiFetch<DeleteResult>(`/api/sessions/${id}`, { method: 'DELETE' });
}

export function deleteSessions(ids: string[]): Promise<DeleteResult> {
	return apiFetch<DeleteResult>('/api/sessions', {
		method: 'DELETE',
		body: { session_ids: ids }
	});
}

export function deleteSessionsByDateRange(dateFrom: string, dateTo: string): Promise<DeleteResult> {
	return apiFetch<DeleteResult>('/api/sessions/by-date', {
		method: 'DELETE',
		body: { date_from: dateFrom, date_to: dateTo }
	});
}

export function fetchCopilotUser(): Promise<CopilotUserInfo> {
	return apiFetch<CopilotUserInfo>('/api/sessions/copilot-user');
}
