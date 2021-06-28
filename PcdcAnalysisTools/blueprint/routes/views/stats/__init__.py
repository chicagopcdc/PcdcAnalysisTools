import json
import flask
from flask import current_app as capp

from PcdcAnalysisTools import utils
from PcdcAnalysisTools import auth


@auth.authorize_for_analysis("access")
def get_consortiums():
    args = utils.parse.parse_request_json()
    #TODO add some check on the payload to make sure it has the correct information
    # print(args)

    # Extract the filters
    _filter = args.get("filter")
    filters = json.loads(json.dumps(_filter))

    return flask.jsonify(get_consortium_list(filters))


def get_consortium_list(filters):
    # consortium_list = args.get("consortiumList")
    # consortium_list = []
    # counts_list.append(get_counts_per_consortium(data))
    # for consortium in consortium_list:
    #     counts_list.append(get_counts_per_consortium(data, consortium))

    data = utils.guppy.downloadDataFromGuppy(
        path="http://guppy-service/download",
        type="subject",
        totalCount=100000,
        fields=["consortium"],
        filters=filters, #[],                 #TODO add filter
        sort=[],
        accessibility="accessible",
        config=capp.config
    )    
    # print(data)

    ret = list(set([d['consortium'] for d in data if 'consortium' in d]))
    # ret = list(set(val for dic in data for val in dic.values())) 
    return ret

