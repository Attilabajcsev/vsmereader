import type { RequestHandler } from './$types';

export const GET: RequestHandler = async () => {
    // Return empty 204 to satisfy browsers without shipping an asset
    return new Response(null, { status: 204 });
};


