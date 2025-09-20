import { redirect } from '@sveltejs/kit';

export async function load() {
    // Always start on the login page; the login route will redirect to
    // /portfolio if the user is already authenticated.
    throw redirect(302, '/login');
}
