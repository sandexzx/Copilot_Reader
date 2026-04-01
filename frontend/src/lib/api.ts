/** API client for Copilot Reader backend. */

import type { Session, SessionSummary, Event, SessionStats, TreeNode, DailyUsageResponse } from './types';

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

async function apiFetch<T>(path: string): Promise<T> {
	const res = await fetch(`${baseUrl}${path}`);
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
