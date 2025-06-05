import requests
import json

from PcdcAnalysisTools.auth import get_jwt_from_header
from pcdcutils.gen3 import Gen3RequestManager, SignaturePayload
from pcdcutils.errors import NoKeyError
from pcdcutils.helpers import encode_str




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
            headers = {
                "Gen3-Service": config.get("SERVICE_NAME").upper(),
            }
            body = json.dumps(queryBody, separators=(",", ":"))

            # --- RSA guard ---
            if not config.get("RSA_PRIVATE_KEY"):
                print("No RSA_PRIVATE_KEY configured — cannot sign request")
                raise NoKeyError("Missing RSA_PRIVATE_KEY — cannot sign request")
    
            payload = SignaturePayload(
                method="POST",
                path=url,
                headers=headers,
                body=body
            )

            g3rm = Gen3RequestManager(headers=headers)

            signature = g3rm.make_gen3_signature(payload, config=config)

            headers["Content-Type"] = "application/json"
            headers["Authorization"] = "bearer " + jwt
            headers["Signature"] = "signature " + signature
          
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
