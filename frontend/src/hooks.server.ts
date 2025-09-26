import { redirect } from '@sveltejs/kit';
import { error } from '@sveltejs/kit';
import * as api from '$lib/api';
import type { RequestEvent } from './routes/$types';
import type { UserData } from '$lib/types';

const VERIFY_URL = 'token/verify/';
const userCache = new Map();
const tokenCache = new Map();
const TTL = 6 * 60 * 60 * 1000;
const TTL_TOKEN_CACHE = 15 * 60 * 1000

export async function handle({ event, resolve }) {

	// Protect routes that require authentication
	const publicRoutes = ['/', '/login'];
	const isPublicRoute = publicRoutes.includes(event.url.pathname);
	if (isPublicRoute) return resolve(event);

	let accessToken = event.cookies.get('accessToken');
	if (accessToken) {
		const cached = tokenCache.get(accessToken);
		if (!cached || Date.now() - cached > TTL_TOKEN_CACHE) {
			try {
				await api.post(VERIFY_URL, { token: accessToken });
				tokenCache.set(accessToken, Date.now());
				event.locals.authed = true;
			} catch (error) {
				if (error.status === 429 && cached) {
					console.log('Rate limited on token verification, using cached validation');
					event.locals.authed = true;
				} else {
					clearCookies(event);
					console.log(`Failed to verify token ${error}`);
				}
			}
		} else event.locals.authed = true;
	} else redirect(302, '/');


	if (!event.locals.authed) redirect(302, '/');

	try {
		event.locals.UserData = await getUserData(accessToken);
	} catch (err) {
		clearCookies(<RequestEvent>event);
		error(500, `Unable to load user profile ${err}`);
	}

	return await resolve(event);
}

// Supporting functions
function clearCookies(event: RequestEvent): void {
	const token = event.cookies.get('accessToken');
	if (token) {
		userCache.delete(token);
		tokenCache.delete(token);
	}
	event.cookies.delete('accessToken', { path: '/' });
}

async function getUserData(accessToken: string): Promise<UserData> {
	const cachedUser: { data: UserData; timestamp: number } = userCache.get(accessToken);
	if (cachedUser && Date.now() - cachedUser.timestamp < TTL) return cachedUser.data;

	console.log('no cache, fetching new data');
	try {
		const data: UserData = await api.get('user/profile/', accessToken);
		userCache.set(accessToken, {
			data,
			timestamp: Date.now()
		});

		return data;
	} catch (err) {
		console.log(`Failed to fetch user ${err}`);
		error(500, `Failed to fetch user ${err}`);
	}
}