import { redirect } from '@sveltejs/kit';

export function load({ locals }) {
    if (!locals.authed) {
        throw redirect(302, '/login');
    }
    return {};
}


