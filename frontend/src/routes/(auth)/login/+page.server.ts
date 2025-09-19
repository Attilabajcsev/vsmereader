import { error, redirect } from '@sveltejs/kit';
import type { Actions, RequestEvent } from '@sveltejs/kit';
import * as api from '$lib/api.js';

export async function load({ locals }) {
	if (locals.authed) {
        throw redirect(303, '/portfolio');
	}
}

export const actions: Actions = {
    login: async ({ cookies, request }: RequestEvent) => {
		const loginFormData = await request.formData();
		const username = loginFormData.get('username')?.toString() ?? '';
		const password = loginFormData.get('password')?.toString() ?? '';

        let data: { access: string; refresh: string };
        try {
            data = await api.post('login/', { username, password });
        } catch (e) {
            return { message: 'Login failed. Check credentials.' };
        }
		const accessToken = data.access;
		const refreshToken = data.refresh;

        const isSecure = (() => { try { return new URL(request.url).protocol === 'https:'; } catch { return false; } })();

        cookies.set('accessToken', accessToken, {
			httpOnly: true,
			path: '/',
			maxAge: 60 * 60,
            sameSite: 'lax',
            secure: isSecure
		}); //expires in 1h

        cookies.set('refreshToken', refreshToken, {
			httpOnly: true,
			path: '/',
			maxAge: 60 * 60 * 24 * 7,
            sameSite: 'lax',
            secure: isSecure
		}); // expires in 1 week

        console.log('login successful. Redirecting..');
        throw redirect(303, '/portfolio');
	}
};
