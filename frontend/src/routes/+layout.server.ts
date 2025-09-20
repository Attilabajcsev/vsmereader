import { redirect } from '@sveltejs/kit';

export function load({ locals, url }) {
    const publicRoutes = ['/', '/login', '/register', '/login-oauth', '/oauth-google'];
    const isPublicRoute = publicRoutes.includes(url.pathname);
    if (!locals.authed && !isPublicRoute) {
        throw redirect(302, '/login');
    }
    return {
        user: locals.UserData,
        authed: locals.authed
    };
}
