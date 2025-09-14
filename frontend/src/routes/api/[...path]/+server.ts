import { env } from '$env/dynamic/private';
import type { RequestHandler } from './$types';

const BACKEND_URL = env.BACKEND_URL;

function buildHeaders(request: Request, token?: string) {
	const headers = new Headers(request.headers);
	headers.delete('host');
	headers.delete('content-length');
	headers.delete('transfer-encoding');
	if (token) headers.set('Authorization', `Bearer ${token}`);
	return headers;
}

async function proxy({ request, url, token }: { request: Request; url: string; token?: string }) {
	const headers = buildHeaders(request, token);
	const method = request.method.toUpperCase();
	let body: BodyInit | null = null;
	if (method !== 'GET' && method !== 'HEAD') {
		// Buffer the body so Node sets Content-Length instead of chunked TE
		const buf = await request.arrayBuffer();
		body = buf.byteLength ? Buffer.from(buf) : null;
	}
	const init: RequestInit = {
		method,
		headers,
		body
	};

	const response = await fetch(url, init);
	const respBuf = await response.arrayBuffer();
	const resHeaders = new Headers(response.headers);
	return new Response(respBuf, { status: response.status, headers: resHeaders });
}

export const GET: RequestHandler = async ({ request, cookies, params }) => {
	const token = cookies.get('accessToken');
	const url = `${BACKEND_URL}/${params.path}${request.url.endsWith('/') ? '/' : ''}`;
	return proxy({ request, url, token });
};

export const POST: RequestHandler = async ({ request, cookies, params }) => {
	const token = cookies.get('accessToken');
	const url = `${BACKEND_URL}/${params.path}${request.url.endsWith('/') ? '/' : ''}`;
	return proxy({ request, url, token });
};

export const PUT: RequestHandler = async ({ request, cookies, params }) => {
	const token = cookies.get('accessToken');
	const url = `${BACKEND_URL}/${params.path}${request.url.endsWith('/') ? '/' : ''}`;
	return proxy({ request, url, token });
};

export const DELETE: RequestHandler = async ({ request, cookies, params }) => {
	const token = cookies.get('accessToken');
	const url = `${BACKEND_URL}/${params.path}${request.url.endsWith('/') ? '/' : ''}`;
	return proxy({ request, url, token });
};
