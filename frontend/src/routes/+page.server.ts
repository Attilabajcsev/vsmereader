import { redirect } from '@sveltejs/kit';

export async function load({ locals }) {
    if (locals.authed) {
        throw redirect(303, '/portfolio');
    }
    throw redirect(302, '/login');
}
