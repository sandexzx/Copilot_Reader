/** WebSocket store — Svelte 5 runes. */

import { getApiBaseUrl } from '$lib/api';
import { eventsStore } from '$lib/stores/events.svelte';
import type { WebSocketMessage } from '$lib/types';

const MAX_RETRIES = 5;
const BACKOFF_BASE_MS = 1000;

class WebSocketStore {
	isConnected = $state(false);
	error = $state<string | null>(null);

	private ws: WebSocket | null = null;
	private retryCount = 0;
	private retryTimer: ReturnType<typeof setTimeout> | null = null;
	private sessionId: string | null = null;
	private intentionalClose = false;

	connect(sessionId: string): void {
		this.disconnect();
		this.sessionId = sessionId;
		this.retryCount = 0;
		this.intentionalClose = false;
		this.open();
	}

	disconnect(): void {
		this.intentionalClose = true;
		if (this.retryTimer !== null) {
			clearTimeout(this.retryTimer);
			this.retryTimer = null;
		}
		if (this.ws) {
			this.ws.close();
			this.ws = null;
		}
		this.isConnected = false;
		this.sessionId = null;
	}

	private open(): void {
		if (!this.sessionId) return;

		const base = getApiBaseUrl().replace(/^http/, 'ws');
		const url = `${base}/ws/sessions/${this.sessionId}/events`;

		this.ws = new WebSocket(url);

		this.ws.onopen = () => {
			this.isConnected = true;
			this.error = null;
			this.retryCount = 0;
		};

		this.ws.onmessage = (ev: MessageEvent) => {
			try {
				const msg: WebSocketMessage = JSON.parse(ev.data as string);
				if (msg.type === 'event' && msg.data) {
					eventsStore.appendEvent(msg.data as unknown as import('$lib/types').Event);
				}
			} catch {
				// ignore malformed messages
			}
		};

		this.ws.onclose = () => {
			this.isConnected = false;
			this.ws = null;
			if (!this.intentionalClose) {
				this.scheduleReconnect();
			}
		};

		this.ws.onerror = () => {
			this.error = 'WebSocket connection error';
		};
	}

	private scheduleReconnect(): void {
		if (this.retryCount >= MAX_RETRIES) {
			this.error = `Failed to reconnect after ${MAX_RETRIES} attempts`;
			return;
		}
		const delay = BACKOFF_BASE_MS * Math.pow(2, this.retryCount);
		this.retryCount++;
		this.retryTimer = setTimeout(() => {
			this.retryTimer = null;
			this.open();
		}, delay);
	}
}

export const websocketStore = new WebSocketStore();
