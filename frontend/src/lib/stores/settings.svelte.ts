/**
 * Settings store — persists AI translation config in localStorage.
 */

const STORAGE_KEY = 'copilot-reader-settings';

interface Settings {
	apiKey: string;
	model: string;
}

function loadFromStorage(): Settings {
	try {
		const raw = localStorage.getItem(STORAGE_KEY);
		if (raw) {
			const parsed = JSON.parse(raw);
			return {
				apiKey: parsed.apiKey || '',
				model: parsed.model || 'gpt-4.1',
			};
		}
	} catch {
		// ignore
	}
	return { apiKey: '', model: 'gpt-4.1' };
}

function saveToStorage(s: Settings) {
	localStorage.setItem(STORAGE_KEY, JSON.stringify(s));
}

const initial = loadFromStorage();

let apiKey = $state(initial.apiKey);
let model = $state(initial.model);
let showSettings = $state(false);

export const settingsStore = {
	get apiKey() { return apiKey; },
	set apiKey(v: string) { apiKey = v; saveToStorage({ apiKey: v, model }); },

	get model() { return model; },
	set model(v: string) { model = v; saveToStorage({ apiKey, model: v }); },

	get showSettings() { return showSettings; },
	set showSettings(v: boolean) { showSettings = v; },

	get isConfigured() { return apiKey.length > 0; },
};
