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
            url = path #'http://guppy-service/download'
            headers = {'Content-Type': 'application/json'}
            body = json.dumps(queryBody, separators=(',', ':'))
            jwt = get_jwt_from_header()
            headers['Authorization'] = 'bearer ' + jwt
            sm = SignatureManager(key=config["RSA_PRIVATE_KEY"])
            headers['Signature'] = b'signature ' + sm.sign(body, config)
            headers['Gen3-Service'] = encode_str(config.get('SERVICE_NAME'))

            r = requests.post(
                url, data=body, headers=headers # , proxies=flask.current_app.config.get("EXTERNAL_PROXIES")
            )
        except NoKeyError as e:
            print(e.message)
        except requests.HTTPError as e:
            print(e.message)
    
        if r.status_code == 200:
            return r.json()
        return []

    