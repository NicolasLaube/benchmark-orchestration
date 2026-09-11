import Keycloack from "keycloak-js";

export const keycloak = new Keycloack(
    {
        "url": import.meta.env.VITE_KEYCLOAK_URL,
        "realm": "benchmark-orchestrator",
        "clientId": "frontend",

    }
)

export async function authenticatedFetch(
    input: RequestInfo | URL,
    init: RequestInit = {},
): Promise<Response> {
    try {
        await keycloak.updateToken(30);
    } catch {
        await keycloak.login({
            redirectUri: window.location.origin,
        });

        throw new Error("Authentication required");
    }

    const headers = new Headers(init.headers);

    if (keycloak.token) {
        headers.set("Authorization", `Bearer ${keycloak.token}`);
    }

    const response = await fetch(input, {
        ...init,
        headers,
    });

    if (response.status === 401) {
        await keycloak.login({
            redirectUri: window.location.origin,
        });
    }

    return response;
}

export default keycloak;

