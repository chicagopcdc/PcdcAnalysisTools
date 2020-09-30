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



# fields = []
# sort = []
# filter = {}
# ACCESSIBLE: 'accessible',
#   UNACCESSIBLE: 'unaccessible',
#   ALL: 'all',

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

            print("INSIDE GUPPY")
            print(body)
            jwt = get_jwt_from_header()
            headers['Authorization'] = 'bearer ' + jwt
            print(headers)



            #####################
            with open(PRIVATE_KEY_PATH, "r") as f:
                private_key = RSA.import_key(f.read())
                print("PRIVATE KEY")
                print(private_key)

                # data = b'test message'
                data = body
                print(data)
                data = str.encode(data)
                print(data)
                print(body)
                # data = b'test message'
                # hash_sign = SHA256.new(data.encode('utf-8'))
                hash_sign = SHA256.new(data)
                signer = pkcs1_15.new(private_key)
                msg_signature = signer.sign(hash_sign)
                print("signed message")
                print(msg_signature)
                print(data)
                hexify = codecs.getencoder('hex')
                m = hexify(msg_signature)[0]
                print(m)

                # try:
                #         res = pkcs1_15.new(public_key).verify(hash_sign, msg_signature)
                #         print(res)
                #         print("valid")
                # except (ValueError, TypeError):
                #         print("not valid")
            ###################

                headers['Signature'] = b'signature ' + m
                print("HERE")
                print(data)
                print(body)
                # print(data.encode('utf-8'))


            r = requests.post(
                url, data=body, headers=headers # , proxies=flask.current_app.config.get("EXTERNAL_PROXIES")
            )
        except requests.HTTPError as e:
            print(e.message)
        #   self.record_error(
        #     "Failed to download data from Guppy: {}".format(
        #         e.message
        #     )
        # )
    
        if r.status_code == 200:
            print(r.json())
            return r.json()
        return []

    
  

  # return askGuppyForRawData(path, type, fields, filter, sort, 0, totalCount, accessibility)
  #   .then((res) => {
  #     if (res && res.data && res.data[type]) {
  #       return res.data[type];
  #     }
  #     throw Error('Error downloading data from Guppy');
  #   })



# # /**
# #    * Get raw data from other es type, with filter
# #    * @param {string} type
# #    * @param {object} filter
# #    * @param {string[]} fields
# #    */
# def handleDownloadRawDataByTypeAndFilter(type, filter, fields):

#     count = askGuppyForTotalCounts(
#       this.props.guppyConfig.path,
#       type,
#       filter,
#       this.state.accessibility,
#     )





#     return askGuppyForTotalCounts(
#       this.props.guppyConfig.path,
#       type,
#       filter,
#       this.state.accessibility,
#     )
#       .then((count) => downloadDataFromGuppy(
#         this.props.guppyConfig.path,
#         type,
#         count,
#         {
#           fields,
#           filter,
#         },
#       ));
#   }