import { env } from '$env/dynamic/private';
import type { RequestHandler } from './$types';

const BACKEND_URL = env.BACKEND_URL || 'http://backend:8000/api';

function buildHeaders(request: Request, token?: string) {
    const headers = new Headers(request.headers);
    headers.delete('host');
    headers.delete('content-length');
    headers.delete('transfer-encoding');
    headers.delete('connection');
    if (token) headers.set('Authorization', `Bearer ${token}`);
    return headers;
}

function buildBackendUrl(request: Request): string {
    const u = new URL(request.url);
    // Preserve the exact trailing slash semantics of the incoming path
    const subpath = u.pathname.replace(/^\/?api\/?/, '');
    const qs = u.search ? u.search : '';
    return `${BACKEND_URL}/${subpath}${qs}`;
}

async function proxy({ request, token }: { request: Request; token?: string }) {
    const headers = buildHeaders(request, token);
    const method = request.method.toUpperCase();
    // If multipart/form-data, rebuild the FormData to ensure boundary and file parts are preserved
    const ct = request.headers.get('content-type') || '';
    if (method !== 'GET' && method !== 'HEAD' && ct.toLowerCase().includes('multipart/form-data')) {
        const incoming = await request.formData();
        const fd = new FormData();
        for (const [key, value] of incoming.entries()) {
            // value can be string or File
            fd.append(key, value as any);
        }
        headers.delete('content-type'); // let fetch set proper multipart boundary
        const url = buildBackendUrl(request);
        const response = await fetch(url, { method, headers, body: fd } as RequestInit);
        const resHeaders = new Headers(response.headers);
        return new Response(response.body, { status: response.status, headers: resHeaders });
    }

    const url = buildBackendUrl(request);
    let response: Response;
    let bufferedBody: BodyInit | null = null;
    if (method !== 'GET' && method !== 'HEAD') {
        const buf = await request.arrayBuffer();
        bufferedBody = buf.byteLength ? Buffer.from(buf) : null;
        response = await fetch(url, { method, headers, body: bufferedBody } as RequestInit);
    } else {
        response = await fetch(url, { method, headers } as RequestInit);
    }
    // Handle backend redirects explicitly for non-GET so we don't lose multipart bodies
    if (response.status >= 300 && response.status < 400) {
        const loc = response.headers.get('location');
        if (loc) {
            const target = new URL(loc, BACKEND_URL).toString();
            if (method !== 'GET' && method !== 'HEAD') {
                // Reuse the already-buffered body on redirect to avoid re-reading the stream
                response = await fetch(target, { method, headers, body: bufferedBody } as RequestInit);
            } else {
                response = await fetch(target, { method, headers } as RequestInit);
            }
        }
    }
    // Stream the response back to the client
    const resHeaders = new Headers(response.headers);
    return new Response(response.body, { status: response.status, headers: resHeaders });
}

export const GET: RequestHandler = async ({ request, cookies }) => {
    const token = cookies.get('accessToken');
    return proxy({ request, token });
};

export const POST: RequestHandler = async ({ request, cookies }) => {
    const token = cookies.get('accessToken');
    return proxy({ request, token });
};

export const PUT: RequestHandler = async ({ request, cookies }) => {
    const token = cookies.get('accessToken');
    return proxy({ request, token });
};

export const DELETE: RequestHandler = async ({ request, cookies }) => {
    const token = cookies.get('accessToken');
    return proxy({ request, token });
};
