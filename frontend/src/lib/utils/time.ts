/** Relative time formatting for session timestamps. */

export function relativeTime(iso: string): string {
	const now = Date.now();
	const then = new Date(iso).getTime();
	const diffMs = now - then;

	if (diffMs < 0) return 'just now';

	const seconds = Math.floor(diffMs / 1000);
	const minutes = Math.floor(seconds / 60);
	const hours = Math.floor(minutes / 60);
	const days = Math.floor(hours / 24);

	if (seconds < 60) return 'just now';
	if (minutes < 60) return `${minutes} min ago`;
	if (hours < 24) return `${hours}h ago`;
	if (days === 1) return 'yesterday';
	if (days < 7) return `${days}d ago`;

	const date = new Date(iso);
	const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
	return `${months[date.getMonth()]} ${date.getDate()}`;
}

/** Shorten a cwd path for display. */
export function shortenPath(cwd: string): string {
	const home = cwd.replace(/^\/home\/[^/]+/, '~').replace(/^\/Users\/[^/]+/, '~');
	const parts = home.split('/');
	if (parts.length <= 3) return home;
	return `${parts[0]}/…/${parts[parts.length - 1]}`;
}
