import json
import flask
from flask import current_app as capp

from PcdcAnalysisTools import utils
from PcdcAnalysisTools import auth

import os


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
    if capp.mock_data == 'True': 
        f = open(os.environ.get('DATA_PATH'))
        data = json.load(f)
    else:
        data = utils.guppy.downloadDataFromGuppy(
            path=capp.config['GUPPY_API'] + "/download",
            type="subject",
            totalCount=100000,
            fields=["consortium"],
            filters=filters,
            sort=[],
            accessibility="accessible",
            config=capp.config
        )    

    ret = list(set([d['consortium'] for d in data if 'consortium' in d]))
    return ret

