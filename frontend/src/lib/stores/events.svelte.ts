/** Events store — Svelte 5 runes. */

import { fetchSessionEvents, fetchSessionStats, fetchSessionTree } from '$lib/api';
import type { Event, SessionStats, TreeNode } from '$lib/types';

class EventsStore {
	events = $state<Event[]>([]);
	stats = $state<SessionStats | null>(null);
	tree = $state<TreeNode[]>([]);
	isLoading = $state(false);
	error = $state<string | null>(null);

	async loadEvents(sessionId: string): Promise<void> {
		this.isLoading = true;
		this.error = null;
		try {
			const [events, stats, tree] = await Promise.all([
				fetchSessionEvents(sessionId),
				fetchSessionStats(sessionId),
				fetchSessionTree(sessionId)
			]);
			this.events = events;
			this.stats = stats;
			this.tree = tree;
		} catch (e) {
			this.error = e instanceof Error ? e.message : 'Failed to load events';
		} finally {
			this.isLoading = false;
		}
	}

	appendEvent(event: Event): void {
		this.events = [...this.events, event];
	}
}

export const eventsStore = new EventsStore();
