/** Sessions store — Svelte 5 runes. */

import { fetchSessions } from '$lib/api';
import type { SessionSummary } from '$lib/types';

class SessionsStore {
	sessions = $state<SessionSummary[]>([]);
	selectedSessionId = $state<string | null>(null);
	isLoading = $state(false);
	error = $state<string | null>(null);

	async loadSessions(background = false): Promise<void> {
		if (!background) {
			this.isLoading = true;
		}
		this.error = null;
		try {
			const fresh = await fetchSessions();
			// Only replace if data actually changed to avoid unnecessary re-renders
			if (JSON.stringify(fresh) !== JSON.stringify(this.sessions)) {
				this.sessions = fresh;
			}
		} catch (e) {
			this.error = e instanceof Error ? e.message : 'Failed to load sessions';
		} finally {
			if (!background) {
				this.isLoading = false;
			}
		}
	}

	selectSession(id: string): void {
		this.selectedSessionId = id;
	}
}

export const sessionsStore = new SessionsStore();
