import requests
import json

from PcdcAnalysisTools.auth import get_jwt_from_header

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
            body = json.dumps(queryBody)

            print("INSIDE GUPPY")
            print(body)
            jwt = get_jwt_from_header()
            headers['Authorization'] = 'bearer ' + jwt
            print(headers)
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