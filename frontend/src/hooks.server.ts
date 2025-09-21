import { redirect } from '@sveltejs/kit';
import { error } from '@sveltejs/kit';
import * as api from '$lib/api';
import type { RequestEvent } from './routes/$types';
import type { UserData } from '$lib/types';

const VERIFY_URL = 'token/verify/';
const REFRESH_URL = 'token/refresh/';
const userCache = new Map();
const TTL = 6 * 60 * 60 * 1000;

export async function handle({ event, resolve }) {
    let accessToken = event.cookies.get('accessToken');
    const refreshToken = event.cookies.get('refreshToken');

    // Do not verify on every request to avoid 429s; trust cookie presence
    if (accessToken) {
        event.locals.authed = true;
    } else {
        clearCookies(<RequestEvent>event);
    }

	// Protect routes that require authentication

	const publicRoutes = ['/', '/login', '/register', '/login-oauth', '/oauth-google'];
	const isPublicRoute = publicRoutes.includes(event.url.pathname);

    if (!isPublicRoute) {
        if (!event.locals.authed) throw redirect(302, '/login');

        try {
            if (!accessToken) throw error(401, 'Unauthorized');
            event.locals.UserData = await getUserData(accessToken);
        } catch (err) {
            // If profile fails (likely expired access), try a single refresh
            if (refreshToken) {
                try {
                    const refreshResponse = await api.post(REFRESH_URL, { refresh: refreshToken });
                    if (refreshResponse?.access) {
                        accessToken = refreshResponse.access;
                        event.cookies.set('accessToken', accessToken, {
                            httpOnly: true,
                            path: '/',
                            maxAge: 60 * 60,
                            sameSite: 'lax',
                            secure: event.url.protocol === 'https:'
                        });
                        event.locals.authed = true;
                        // retry profile once
                        event.locals.UserData = await getUserData(accessToken);
                    } else {
                        clearCookies(<RequestEvent>event);
                        throw redirect(302, '/login');
                    }
                } catch (refreshError) {
                    // On refresh errors (incl. 429), don't thrash: keep current page and require explicit login
                    clearCookies(<RequestEvent>event);
                    throw redirect(302, '/login');
                }
            } else {
                clearCookies(<RequestEvent>event);
                throw redirect(302, '/login');
            }
        }
    }

	return await resolve(event);
}

// Supporting functions
function clearCookies(event: RequestEvent): void {
	const token = event.cookies.get('accessToken');
	if (token) userCache.delete(token);
	event.cookies.delete('accessToken', { path: '/' });
	event.cookies.delete('refreshToken', { path: '/' });
}

async function getUserData(accessToken: string): Promise<UserData> {
	const cachedUser: { data: UserData; timestamp: number } = userCache.get(accessToken);

	console.log('looking for user cache');
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
        throw error(500, `Failed to fetch user ${err}`);
	}
}
