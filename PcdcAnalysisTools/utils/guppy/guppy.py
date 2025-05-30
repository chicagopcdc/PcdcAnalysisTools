import json
import logging
import requests

from PcdcAnalysisTools.auth import get_jwt_from_header
from pcdcutils.errors import NoKeyError
from pcdcutils.helpers import encode_str
from pcdcutils.gen3 import Gen3RequestManager
from types import SimpleNamespace


# Compatibility helper to wrap a string body in an async function.
# This allows synchronous Flask code to provide a payload compatible with
# async signature generation logic (used by FastAPI-based services).
def wrap_async_body(data):
    async def _wrapped():
        return data.encode()

    return _wrapped


def downloadDataFromGuppy(
    path, type, totalCount, fields, filters, sort, accessibility, config
):
    SCROLL_SIZE = 10000
    totalCount = 100000
    if totalCount > SCROLL_SIZE:
        queryBody = {"type": type}
        if fields:
            queryBody["fields"] = fields
        if filters:
            queryBody["filter"] = filters
        if sort:
            queryBody["sort"] = []  # sort
        if accessibility:
            queryBody["accessibility"] = "accessible"

        try:
            url = path
            path_only = path.split("/", 3)[-1] if "/" in path else path
            method = "POST"
            service_name = config.get("SERVICE_NAME", "").upper()

            key = config.get(f"{service_name}_PRIVATE_KEY")

            # Try to find the specific private key for this service (e.g., PCDCANALYSISTOOLS_PRIVATE_KEY).
            # If it's not found, fall back to a shared RSA_PRIVATE_KEY. This supports legacy behavior.
            if not key:
                key = config.get("RSA_PRIVATE_KEY")

            if not key:
                raise NoKeyError(
                    f"No signing key found for service {service_name} or fallback RSA_PRIVATE_KEY."
                )

            jwt = get_jwt_from_header()

            # Empty body for GET request, but still needs to be encoded for signature
            body = json.dumps(queryBody, separators=(",", ":"))

            # Make a copy of the config and plug in the private key we found
            signing_config = config.copy()
            signing_config[f"{service_name}_PRIVATE_KEY"] = key

            g3rm = Gen3RequestManager(headers={"Gen3-Service": service_name})
            signature = g3rm.make_gen3_signature(
                # Prepare a namespace object containing method, path, and encoded body — this will be signed.
                SimpleNamespace(
                    method=method,
                    url=SimpleNamespace(path=path),
                    body=wrap_async_body(body),
                ),
                signing_config,
            )

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"bearer {jwt}",
                "Signature": "signature "
                + (signature.decode() if isinstance(signature, bytes) else signature),
                "Gen3-Service": encode_str(service_name or ""),
            }

            r = requests.post(url, data=body, headers=headers)
            if r.status_code == 200:
                return r.json()

        except NoKeyError as e:
            print(f"[ERROR] {e}")
        except requests.HTTPError as e:
            print(f"[HTTP ERROR] {e}")

    return {}
