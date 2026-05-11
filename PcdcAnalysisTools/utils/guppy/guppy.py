import requests
import json
from cdislogging import get_logger

from PcdcAnalysisTools.auth import get_jwt_from_header
from PcdcAnalysisTools.errors import InternalError, UpstreamServiceError
from pcdcutils.gen3 import Gen3RequestManager, SignaturePayload
from pcdcutils.errors import NoKeyError


logger = get_logger(__name__)
REQUEST_TIMEOUT_SECS = 30


def downloadDataFromGuppy(
    path, type, totalCount, fields, filters, sort, accessibility, config
):
    SCROLL_SIZE = 10000
    totalCount = 100000
    if totalCount <= SCROLL_SIZE:
        raise InternalError("Guppy download is only configured for large export requests")

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

        if not config.get("RSA_PRIVATE_KEY"):
            raise NoKeyError("Missing RSA_PRIVATE_KEY - cannot sign request")

        payload = SignaturePayload(
            method="POST",
            path=url,
            headers=headers,
            body=body,
        )

        g3rm = Gen3RequestManager(headers=headers)
        signature = g3rm.make_gen3_signature(payload, config=config)

        headers["Content-Type"] = "application/json"
        headers["Authorization"] = "bearer " + jwt
        headers["Signature"] = "signature " + signature

        response = requests.post(
            url,
            data=body,
            headers=headers,
            timeout=REQUEST_TIMEOUT_SECS,
        )
        response.raise_for_status()
        return response.json()
    except NoKeyError as e:
        logger.exception("Guppy request signing failed")
        raise InternalError("Service signing configuration is missing") from e
    except requests.Timeout as e:
        logger.exception("Guppy request timed out")
        raise UpstreamServiceError("guppy", "upstream service timed out", code=504) from e
    except requests.HTTPError as e:
        status_code = e.response.status_code if e.response is not None else None
        logger.exception("Guppy request failed with HTTP status %s", status_code)
        raise UpstreamServiceError(
            "guppy",
            "upstream service request failed",
            code=502,
            json={"upstream_status": status_code},
        ) from e
    except requests.ConnectionError as e:
        logger.exception("Guppy service unavailable")
        raise UpstreamServiceError("guppy", "upstream service unavailable", code=503) from e
    except requests.RequestException as e:
        logger.exception("Unexpected Guppy request failure")
        raise UpstreamServiceError("guppy") from e
