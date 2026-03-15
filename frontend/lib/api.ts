import { fetchAuthSession } from 'aws-amplify/auth';

/**
 * Authenticated fetch wrapper. Retrieves the current Cognito idToken and
 * injects it as `Authorization: Bearer <token>` on every request.
 * Drop-in replacement for `fetch` — returns the raw Response.
 */
export async function authFetch(
    input: RequestInfo | URL,
    init: RequestInit = {}
): Promise<Response> {
    const session = await fetchAuthSession();
    const idToken = session.tokens?.idToken?.toString();
    if (!idToken) {
        throw new Error('Not authenticated — no Cognito idToken available.');
    }

    const headers = new Headers(init.headers);
    headers.set('Authorization', `Bearer ${idToken}`);

    return fetch(input, { ...init, headers });
}
