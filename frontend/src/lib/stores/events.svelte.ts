/** Events store — Svelte 5 runes. */

import { fetchSessionEvents, fetchSessionStats, fetchSessionTree } from '$lib/api';
import type { Event, SessionStats, TreeNode } from '$lib/types';

class EventsStore {
	events = $state<Event[]>([]);
	stats = $state<SessionStats | null>(null);
	tree = $state<TreeNode[]>([]);
	isLoading = $state(false);
	error = $state<string | null>(null);
	private eventIds = new Set<string>();

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
		this.events = [...this.events, event];
	}
}

export const eventsStore = new EventsStore();
