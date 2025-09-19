import { redirect } from '@sveltejs/kit';

export function load({ locals, url }) {
    if (!locals.authed && url.pathname.startsWith('/(app)')) {
        throw redirect(302, '/login');
    }
    return {
        user: locals.UserData,
        authed: locals.authed
    };
}
