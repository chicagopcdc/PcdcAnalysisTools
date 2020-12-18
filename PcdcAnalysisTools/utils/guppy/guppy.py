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
from PcdcAnalysisTools.errors import NoPrivateKeyError

def loadkey(current_app):
    """
    Load private key
    """
    with open(PRIVATE_KEY_PATH, "r") as f:
        current_app.config["RSA_PRIVATE_KEY"] = RSA.import_key(f.read())


def sign(body, config):
    """
    Create signature for payload
    """
    if config["RSA_PRIVATE_KEY"] is None:
        raise NoPrivateKeyError("ERROR - Can't sign the message, no private key has been found.")

    data = str.encode(body)
    hash_sign = SHA256.new(data)
    signer = pkcs1_15.new(config["RSA_PRIVATE_KEY"])
    msg_signature = signer.sign(hash_sign)

    hexify = codecs.getencoder('hex')
    m = hexify(msg_signature)[0]
    return m


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
            headers['Signature'] = b'signature ' + sign(body, config)

            r = requests.post(
                url, data=body, headers=headers # , proxies=flask.current_app.config.get("EXTERNAL_PROXIES")
            )
        except NoPrivateKeyError as e:
            print(e.message)
        except requests.HTTPError as e:
            print(e.message)
    
        if r.status_code == 200:
            return r.json()
        return []

    