/** Events store — Svelte 5 runes. */

import { fetchSessionEvents, fetchSessionStats, fetchSessionTree } from '$lib/api';
import type { Event, SessionStats, TreeNode } from '$lib/types';

const REFRESH_DEBOUNCE_MS = 5000;

class EventsStore {
	events = $state<Event[]>([]);
	stats = $state<SessionStats | null>(null);
	tree = $state<TreeNode[]>([]);
	isLoading = $state(false);
	error = $state<string | null>(null);
	private eventIds = new Set<string>();
	private currentSessionId: string | null = null;
	private refreshTimer: ReturnType<typeof setTimeout> | null = null;

	async loadEvents(sessionId: string): Promise<void> {
		this.isLoading = true;
		this.error = null;
		this.currentSessionId = sessionId;
		this.cancelRefreshTimer();
		try {
			const [events, stats, tree] = await Promise.all([
				fetchSessionEvents(sessionId),
				fetchSessionStats(sessionId),
				fetchSessionTree(sessionId)
			]);
			this.events = events.map(e => ({ ...e, isNew: false }));
			this.stats = stats;
			this.tree = tree;
			this.eventIds = new Set(events.map(e => e.id));
		} catch (e) {
			this.error = e instanceof Error ? e.message : 'Failed to load events';
		} finally {
			this.isLoading = false;
		}
	}

	appendEvent(event: Event): void {
		if (this.eventIds.has(event.id)) return;
		this.eventIds.add(event.id);
		this.events = [...this.events, { ...event, isNew: true }];
		this.scheduleRefresh();
	}

	private scheduleRefresh(): void {
		this.cancelRefreshTimer();
		this.refreshTimer = setTimeout(() => {
			this.refreshTimer = null;
			this.refreshStatsAndTree();
		}, REFRESH_DEBOUNCE_MS);
	}

	private cancelRefreshTimer(): void {
		if (this.refreshTimer !== null) {
			clearTimeout(this.refreshTimer);
			this.refreshTimer = null;
		}
	}

	private async refreshStatsAndTree(): Promise<void> {
		if (!this.currentSessionId) return;
		const sessionId = this.currentSessionId;
		try {
			const [stats, tree] = await Promise.all([
				fetchSessionStats(sessionId),
				fetchSessionTree(sessionId)
			]);
			if (this.currentSessionId === sessionId) {
				this.stats = stats;
				this.tree = tree;
			}
		} catch {
			// Silently ignore refresh errors — stale data is acceptable
		}
	}
}

export const eventsStore = new EventsStore();
