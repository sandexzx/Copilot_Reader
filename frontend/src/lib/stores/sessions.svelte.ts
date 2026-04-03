/** Sessions store — Svelte 5 runes. */

import { fetchSessions, deleteSessions, deleteSessionsByDateRange } from '$lib/api';
import type { SessionSummary, DeleteResult } from '$lib/types';

class SessionsStore {
	sessions = $state<SessionSummary[]>([]);
	selectedSessionId = $state<string | null>(null);
	isLoading = $state(false);
	error = $state<string | null>(null);

	selectedForDeletion = $state<Set<string>>(new Set());
	isDeleting = $state(false);
	deleteError = $state<string | null>(null);
	lastDeleteResult = $state<DeleteResult | null>(null);
	manageMode = $state(false);

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

	toggleManageMode(): void {
		this.manageMode = !this.manageMode;
		if (!this.manageMode) {
			this.clearDeleteSelection();
		}
	}

	toggleDeleteSelection(id: string): void {
		const next = new Set(this.selectedForDeletion);
		if (next.has(id)) {
			next.delete(id);
		} else {
			next.add(id);
		}
		this.selectedForDeletion = next;
	}

	selectAllInactive(): void {
		const inactiveIds = this.sessions
			.filter((s) => !s.is_active)
			.map((s) => s.id);
		this.selectedForDeletion = new Set(inactiveIds);
	}

	clearDeleteSelection(): void {
		this.selectedForDeletion = new Set();
	}

	isSelectedForDeletion(id: string): boolean {
		return this.selectedForDeletion.has(id);
	}

	get selectedCount(): number {
		return this.selectedForDeletion.size;
	}

	async deleteSelected(): Promise<void> {
		if (this.selectedForDeletion.size === 0) return;
		this.isDeleting = true;
		this.deleteError = null;
		try {
			const ids = Array.from(this.selectedForDeletion);
			const result = await deleteSessions(ids);
			this.lastDeleteResult = result;
			if (this.selectedSessionId && result.deleted.includes(this.selectedSessionId)) {
				this.selectedSessionId = null;
			}
			this.clearDeleteSelection();
			await this.loadSessions();
		} catch (e) {
			this.deleteError = e instanceof Error ? e.message : 'Failed to delete sessions';
		} finally {
			this.isDeleting = false;
		}
	}

	async deleteByDateRange(dateFrom: string, dateTo: string): Promise<void> {
		this.isDeleting = true;
		this.deleteError = null;
		try {
			const result = await deleteSessionsByDateRange(dateFrom, dateTo);
			this.lastDeleteResult = result;
			if (this.selectedSessionId && result.deleted.includes(this.selectedSessionId)) {
				this.selectedSessionId = null;
			}
			this.clearDeleteSelection();
			await this.loadSessions();
		} catch (e) {
			this.deleteError = e instanceof Error ? e.message : 'Failed to delete sessions';
		} finally {
			this.isDeleting = false;
		}
	}

	dismissDeleteResult(): void {
		this.lastDeleteResult = null;
		this.deleteError = null;
	}
}

export const sessionsStore = new SessionsStore();
