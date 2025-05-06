import requests
import json

from PcdcAnalysisTools.auth import get_jwt_from_header
from pcdcutils.signature import SignatureManager
from pcdcutils.errors import NoKeyError
from pcdcutils.helpers import encode_str


def downloadDataFromGuppy(path, type, totalCount, fields, filters, sort, accessibility, config):
    SCROLL_SIZE = 10000
    totalCount = 100000
    print(config.get('SERVICE_NAME'))
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
            
            #jwt = "eyJhbGciOiJSUzI1NiIsImtpZCI6ImZlbmNlX2tleV8yMDIyLTA5LTE1VDE2OjE5OjUwWiIsInR5cCI6IkpXVCJ9.eyJwdXIiOiJhY2Nlc3MiLCJpc3MiOiJodHRwczovL3BvcnRhbC1kZXYucGVkc2NvbW1vbnMub3JnL3VzZXIiLCJhdWQiOlsiaHR0cHM6Ly9wb3J0YWwtZGV2LnBlZHNjb21tb25zLm9yZy91c2VyIiwib3BlbmlkIiwidXNlciIsImNyZWRlbnRpYWxzIiwiZGF0YSIsImFkbWluIiwiZ29vZ2xlX2NyZWRlbnRpYWxzIiwiZ29vZ2xlX3NlcnZpY2VfYWNjb3VudCIsImdvb2dsZV9saW5rIiwiZ2E0Z2hfcGFzc3BvcnRfdjEiXSwiaWF0IjoxNzQxMjkxODg0LCJleHAiOjE3NDEyOTMwODQsImp0aSI6IjkzOGQ1NDUyLTBlZTEtNDRmNC04ODE2LWExNDgxYjcyNjU2ZSIsInNjb3BlIjpbIm9wZW5pZCIsInVzZXIiLCJjcmVkZW50aWFscyIsImRhdGEiLCJhZG1pbiIsImdvb2dsZV9jcmVkZW50aWFscyIsImdvb2dsZV9zZXJ2aWNlX2FjY291bnQiLCJnb29nbGVfbGluayIsImdhNGdoX3Bhc3Nwb3J0X3YxIl0sImNvbnRleHQiOnsidXNlciI6eyJuYW1lIjoibHczNTExQG55dS5lZHUiLCJpc19hZG1pbiI6dHJ1ZSwiZ29vZ2xlIjp7InByb3h5X2dyb3VwIjpudWxsfX19LCJhenAiOiIiLCJzdWIiOiIzMiJ9.RBIdKjpScXd8b4W-l9L41dVACf8Sppww241Ju7IMWwGeC-KscE2IUs6Vr892N_eX2og9vR8OkdEPh33U2pBnJWCGudDxOzcmVK8jN-HYTAVO1IpV8rtghPn48PvNfUudcT3k-A_VxLocmfZ5saPIe6JuwTdR8NGhJ6D0Td81tYyQhpxJcDASI2XnDU-yzeT6NXSrky7peAfDwMl-i1mKSptm3pt_CC_j20HE4ZRRmcChHl2yXg1NDXMFvZJYkS2yhDf6iRCyUf21PbajYlfqI5Dj8iPZljFNPbt-_uYs4SZkd5YsVkDz0j1o2fDTItnDQ4OhZ4czDq3zusrbdWsoCQ"
            headers['Authorization'] = 'bearer ' + jwt
            sm = SignatureManager(key=config["RSA_PRIVATE_KEY"])
            headers['Signature'] = 'signature ' + sm.sign(body_signature)
            headers['Gen3-Service'] = encode_str(config.get('SERVICE_NAME'))

            r = requests.request(
                "POST",
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

    