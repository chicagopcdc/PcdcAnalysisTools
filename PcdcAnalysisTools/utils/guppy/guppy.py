import requests
import json

from PcdcAnalysisTools.auth import get_jwt_from_header
from pcdcutils.gen3 import Gen3RequestManager
from pcdcutils.errors import NoKeyError
from pcdcutils.helpers import encode_str


class SignaturePayload:
    def __init__(self, method, path, headers=None):
        self.method = method.upper()
        self.path = path
        self.headers = headers or {}

    def get_data(self, as_text=True):
        header_str = "\n".join(f"{k}: {v}" for k, v in sorted(self.headers.items()))
        payload_str = f"{self.method} {self.path}\n{header_str}"
        return payload_str if as_text else payload_str.encode("utf-8")


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
            queryBody["sort"] = []
        if accessibility:
            queryBody["accessibility"] = "accessible"

        try:
            url = path
            jwt = get_jwt_from_header()

            # --- RSA guard ---
            if not config.get("RSA_PRIVATE_KEY"):
                print("No RSA_PRIVATE_KEY configured — cannot sign request")
                raise NoKeyError("Missing RSA_PRIVATE_KEY — cannot sign request")

            g3rm = Gen3RequestManager()

            # --- Prepare body ---
            body = json.dumps(queryBody, separators=(",", ":"))
            body_signature = json.dumps(
                queryBody, separators=(",", ":"), ensure_ascii=False
            )

            # --- Prepare SignaturePayload ---
            from urllib.parse import urlparse
            from types import SimpleNamespace

            parsed_url = urlparse(url)
            path_only = parsed_url.path

            payload = SimpleNamespace(
                method="POST",
                path=path_only,
                get_data=lambda as_text=True: body_signature,  # Sign the BODY
            )

            signature = g3rm.make_gen3_signature(payload, config=config)

            # --- Headers ---
            headers = {
                "Content-Type": "application/json",
                "Authorization": "bearer " + jwt,
                "Signature": "signature " + signature.decode(),
                "Gen3-Service": encode_str(config.get("SERVICE_NAME")),
            }

            # --- POST ---
            r = requests.post(
                url,
                data=body,
                headers=headers,
            )

        except NoKeyError as e:
            print(e)
            return []
        except requests.HTTPError as e:
            print(e)
            return []
        except requests.ConnectionError as e:
            print(e)
            print("An error connecting with Guppy.")
            return []

        if r.status_code == 200:
            return r.json()
        return []
