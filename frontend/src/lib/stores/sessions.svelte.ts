/** Sessions store — Svelte 5 runes. */

import { fetchSessions } from '$lib/api';
import type { SessionSummary } from '$lib/types';

class SessionsStore {
	sessions = $state<SessionSummary[]>([]);
	selectedSessionId = $state<string | null>(null);
	isLoading = $state(false);
	error = $state<string | null>(null);

	async loadSessions(): Promise<void> {
		this.isLoading = true;
		this.error = null;
		try {
			this.sessions = await fetchSessions();
		} catch (e) {
			this.error = e instanceof Error ? e.message : 'Failed to load sessions';
		} finally {
			this.isLoading = false;
		}
	}

	selectSession(id: string): void {
		this.selectedSessionId = id;
	}
}

export const sessionsStore = new SessionsStore();
