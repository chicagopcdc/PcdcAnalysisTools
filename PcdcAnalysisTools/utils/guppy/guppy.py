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
            url = "https://portal-dev.pedscommons.org/guppy/download" #'http://guppy-service/download'
            headers = {'Content-Type': 'application/json'}
            body = json.dumps(queryBody, separators=(',', ':'))
            #jwt = get_jwt_from_header()
            
            jwt = "eyJhbGciOiJSUzI1NiIsImtpZCI6ImZlbmNlX2tleV8yMDIyLTA5LTE1VDE2OjE5OjUwWiIsInR5cCI6IkpXVCJ9.eyJwdXIiOiJhY2Nlc3MiLCJpc3MiOiJodHRwczovL3BvcnRhbC1kZXYucGVkc2NvbW1vbnMub3JnL3VzZXIiLCJhdWQiOlsiaHR0cHM6Ly9wb3J0YWwtZGV2LnBlZHNjb21tb25zLm9yZy91c2VyIiwib3BlbmlkIiwidXNlciIsImNyZWRlbnRpYWxzIiwiZGF0YSIsImFkbWluIiwiZ29vZ2xlX2NyZWRlbnRpYWxzIiwiZ29vZ2xlX3NlcnZpY2VfYWNjb3VudCIsImdvb2dsZV9saW5rIiwiZ2E0Z2hfcGFzc3BvcnRfdjEiXSwiaWF0IjoxNzI1ODk4OTQwLCJleHAiOjE3MjU5MDAxNDAsImp0aSI6ImEzMzA5YjExLTdjMzctNDcwYi1iNThmLTk0ODkwNTJhMzIxNCIsInNjb3BlIjpbIm9wZW5pZCIsInVzZXIiLCJjcmVkZW50aWFscyIsImRhdGEiLCJhZG1pbiIsImdvb2dsZV9jcmVkZW50aWFscyIsImdvb2dsZV9zZXJ2aWNlX2FjY291bnQiLCJnb29nbGVfbGluayIsImdhNGdoX3Bhc3Nwb3J0X3YxIl0sImNvbnRleHQiOnsidXNlciI6eyJuYW1lIjoibHczNTExQG55dS5lZHUiLCJpc19hZG1pbiI6dHJ1ZSwiZ29vZ2xlIjp7InByb3h5X2dyb3VwIjpudWxsfX19LCJhenAiOiIiLCJzdWIiOiIzMiJ9.TpbooHDOp8simw4NgCSW4WDzXD5gX7__-llSg9XzsORF7PRYKlcp_cLRQJR8KPqyT1VxB9cqpbF_wwBmp56dIDQw1yXRo8EHQHWuncuXfu4Q3_pVNiCGRW-P80C02o5UA_C-IqjrzJcVyDz3CVboKlX0zh1-7biaY0oRGtEgpBMx_uafIyWDRuUWR37eT0csaTEwX5pmfLnuYxyZ2E1DCmtkRW1GT9GZwFVaJaQJ1SCzmg44IehzLI-QBV7_BzbhuxRXleuzB6cHmIj0Q1nwiqGzDF8SJCgamGPtfn82PICnaACBvcaRTsLgtxDLvXZhIgWctlHHYrro30Jas-2w-w"
            headers['Authorization'] = 'bearer ' + jwt
            #sm = SignatureManager(key=config["RSA_PRIVATE_KEY"])
            #headers['Signature'] = b'signature ' + sm.sign(body)
            #headers['Gen3-Service'] = encode_str(config.get('SERVICE_NAME'))

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

    