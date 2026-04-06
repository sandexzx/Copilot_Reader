/** Daily usage store — Svelte 5 runes, singleton. */

import { fetchDailyUsage } from '$lib/api';
import { eventsStore } from '$lib/stores/events.svelte';
import type { DailyUsageResponse } from '$lib/types';

const POLL_INTERVAL_MS = 30_000;
const DEBOUNCE_MS = 5_000;

class DailyUsageStore {
	data = $state<DailyUsageResponse | null>(null);
	loading = $state(false);

	private initialized = false;
	private pollInterval: ReturnType<typeof setInterval> | null = null;
	private refreshTimer: ReturnType<typeof setTimeout> | null = null;

	/** Start polling. Idempotent — safe to call multiple times. */
	init(): void {
		if (this.initialized) return;
		this.initialized = true;

		this.load();
		this.pollInterval = setInterval(() => this.load(), POLL_INTERVAL_MS);

		// Debounced refresh on new WS events
		$effect(() => {
			const len = eventsStore.events.length;
			if (len === 0) return;
			if (this.refreshTimer) clearTimeout(this.refreshTimer);
			this.refreshTimer = setTimeout(() => this.load(), DEBOUNCE_MS);
			return () => {
				if (this.refreshTimer) {
					clearTimeout(this.refreshTimer);
					this.refreshTimer = null;
				}
			};
		});
	}

	private async load(): Promise<void> {
		this.loading = true;
		try {
			this.data = await fetchDailyUsage();
		} catch {
			// Silently fail — don't break UI
		} finally {
			this.loading = false;
		}
	}
}

export const dailyUsageStore = new DailyUsageStore();
