import requests
import json

from PcdcAnalysisTools.auth import get_jwt_from_header
from pcdcutils.signature import SignatureManager
from pcdcutils.errors import NoKeyError
from pcdcutils.helpers import encode_str


def downloadDataFromGuppy(path, type, totalCount, fields, filters, sort, accessibility, config):
    SCROLL_SIZE = 10000
    totalCount = 100000
    if (totalCount > SCROLL_SIZE):
        queryBody = { "type": type }
        if fields:
            queryBody["fields"] = fields
        if filters:
            queryBody["filter"] = filters # getGQLFilter(filter);
        if sort:
            queryBody["sort"] = [] # sort
        if accessibility:
            queryBody["accessibility"] = 'accessible' # accessibility

        try:
            # TODO in the future use the makesignature in the gen3Manager in pcdcutils to make this
            url = path #'http://guppy-service/download'
            headers = {'Content-Type': 'application/json'}
            body = json.dumps(queryBody, separators=(',', ':'))
            # Use this only for the signature because json.dumps will transform special char in \u encoding which will make a signature javascript won't be able to verify it.
            # For instance `β` is translated to `\u03b2`
            body_signature = json.dumps(queryBody, separators=(',', ':'), ensure_ascii=False)
            jwt = get_jwt_from_header()
            headers['Authorization'] = 'bearer ' + jwt
            sm = SignatureManager(key=config["RSA_PRIVATE_KEY"])
            headers['Signature'] = 'signature ' + sm.sign(body_signature)
            headers['Gen3-Service'] = encode_str(config.get('SERVICE_NAME'))

            r = requests.post(
                url, data=body, headers=headers # , proxies=flask.current_app.config.get("EXTERNAL_PROXIES")
            )
        except NoKeyError as e:
            print(e.message)
            return []
        except requests.HTTPError as e:
            print(e.message)
            return []
        except requests.ConnectionError as e:
            print(e)
            print("An error connecting with Guppy.")
            return []
    
        if r.status_code == 200:
            return r.json()
        return []

    