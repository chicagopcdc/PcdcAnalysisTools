import json
import flask
import math

from PcdcAnalysisTools import utils
from PcdcAnalysisTools import auth


@auth.authorize_for_analysis("access")
def get_result():
    args = utils.parse.parse_request_json()
    data = fetch_data(args)
    return flask.jsonify(data)


def fetch_data(args):
    fields = args.get("fields")
    return utils.guppy.downloadDataFromGuppy(
        path="http://guppy-service/download",
        type="subject",
        totalCount=100000,
        fields=fields,
        filters=[],
        sort=[],
        accessibility="accessible"
    )
