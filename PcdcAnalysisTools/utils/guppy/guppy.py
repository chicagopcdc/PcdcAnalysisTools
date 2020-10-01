import requests
import json

import Crypto
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
from Crypto import Random
import base64
import codecs


from PcdcAnalysisTools.auth import get_jwt_from_header
from PcdcAnalysisTools.globals import PRIVATE_KEY_PATH



def downloadDataFromGuppy(path, type, totalCount, fields, filters, sort, accessibility):
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

            with open(PRIVATE_KEY_PATH, "r") as f:
                private_key = RSA.import_key(f.read())

                data = body
                data = str.encode(data)

                hash_sign = SHA256.new(data)
                signer = pkcs1_15.new(private_key)
                msg_signature = signer.sign(hash_sign)

                hexify = codecs.getencoder('hex')
                m = hexify(msg_signature)[0]
                headers['Signature'] = b'signature ' + m

            r = requests.post(
                url, data=body, headers=headers # , proxies=flask.current_app.config.get("EXTERNAL_PROXIES")
            )
        except requests.HTTPError as e:
            print(e.message)
    
        if r.status_code == 200:
            print(r.json())
            return r.json()
        return []

    