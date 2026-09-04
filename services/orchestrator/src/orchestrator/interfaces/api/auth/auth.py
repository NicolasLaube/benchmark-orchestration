import os
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

KEYCLOAK_URL = os.getenv(
    "KEYCLOAK_URL",
    "http://localhost:8081",
)

ISSUER_BASE_URL = os.getenv(
    "ISSUER_BASE_URL",
    "http://localhost:8081",
)

REALM = os.getenv(
    "REALM",
    "benchmark-orchestrator",
)


ISSUER = f"{ISSUER_BASE_URL}/realms/{REALM}"

JWKS_URL = f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/certs"

jwks_client = jwt.PyJWKClient(JWKS_URL)

# security is able to read the header "Authorization: Bearer dksZqa..."
security = HTTPBearer()

Credentials = Annotated[
    HTTPAuthorizationCredentials,
    Depends(security),
]


def get_signing_key(token: str):
    """
    Get the public key corresponding to the json web token (JWT):
    1. reads the header of the jwt token
    2. extracts the kid of the header
    3. gets the public keys of keycloak
    4. finds the public key corresponding to the token (thanks to kid)
    """
    signing_key = jwks_client.get_signing_key_from_jwt(token=token)

    return signing_key


def verify_access_token(
    credentials: Credentials,
):
    """This function verifies the Json web token and returns the information on the user
    1. gets the jwt signing key (from the kid in the header)
    2. verify cryptographically the jwt
    3. verifies its main claims
    4. returns the payload

    Among the other claims verified are:
    - exp → did the jwt expire
    - iss → is the issuer correct
    - aud → is the audience correct
    - nbf → is it already valid
    """

    token = credentials.credentials

    try:
        signing_key = get_signing_key(token=token)

        payload = jwt.decode(
            jwt=token,
            issuer=ISSUER,
            key=signing_key.key,
            algorithms=["RS256"],
            options={
                "verify_aud": False,
            },
        )

        return payload

    except jwt.PyJWKError as exc:
        # error sent if header, payload and signature combination
        # wasn't verified cryptographically
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token",
        ) from exc
