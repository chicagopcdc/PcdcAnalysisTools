import requests
import json

from PcdcAnalysisTools.auth import get_jwt_from_header
from pcdcutils.signature import SignatureManager
from pcdcutils.errors import NoKeyError
from pcdcutils.helpers import encode_str
from pcdcutils.gen3 import Gen3RequestManager
from types import SimpleNamespace


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
            url = path  # path should be assigned properly
            headers = {'Content-Type': 'application/json'}
            body = json.dumps(queryBody, separators=(',', ':'))
            jwt = get_jwt_from_header()

            # Instance with the req Gen3 headers
            mgr = Gen3RequestManager({
                'Signature': None,
                'Gen3-Service': config['SERVICE_NAME']
            })

            # Using pcdcutils gen3 make_gen3_signature
            signature = mgr.make_gen3_signature(
                payload=SimpleNamespace(
                    method='POST',  # or any method you're using
                    path=url,
                    get_data=lambda as_text=True: body  # Pass body as text
                ),
                config=config
            )

            # headers
            headers['Signature'] = 'signature ' + signature.decode()  # Ensure it's decoded if needed
            headers['Gen3-Service'] = encode_str(config['SERVICE_NAME'])

            if jwt:
                headers['Authorization'] = 'bearer ' + jwt

            r = requests.post(url, data=body, headers=headers)
                
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

    