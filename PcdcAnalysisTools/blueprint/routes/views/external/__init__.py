import json
import flask
import urllib.parse
from flask import current_app as capp


from PcdcAnalysisTools import utils
from PcdcAnalysisTools import auth


@auth.authorize_for_analysis("access")
def get_gdc():
    print("IN GDC - LUCA")

    args = utils.parse.parse_request_json()
    return_type = args.get("return_type")

    if not return_type or return_type is not in ["url", "manifest"]:
        return_type = "url"

    data = (
        fetch_data(args)
        if flask.current_app.config.get("IS_SURVIVAL_USING_GUPPY", True)
        else fetch_fake_data(args)
    )

    data = [value for value in data if value]

    if return_type == "manifest":
        return flask.jsonify({"manifest": data})

    query = '{"op":"and","content":[{"op":"in","content":{"field":"cases.case_id","value":'
    query += json.dumps(data)
    query += '}}]}'

    encoded = urllib.parse.quote(query)
    link = 'https://portal.gdc.cancer.gov/exploration?filters=' + encoded

    return flask.jsonify({"link": link})



def fetch_data(args):
    # TODO add json payload control
    # TODO add check on payload nulls and stuff
    # TODO add path in the config file or ENV variable
    _filter = args.get("filter")
    filters = json.loads(json.dumps(_filter))

    fields = ["external_subject_id"]

    guppy_data = utils.guppy.downloadDataFromGuppy(
        path="http://guppy-service/download",
        type="subject",
        totalCount=100000,
        fields=fields,
        filters=filters,
        sort=[],
        accessibility="accessible",
        config=capp.config
    )

    # TODO I can count how many are without that information and communicate that to the frontend (guppy data return empty objects when data is missing)
    ids = [item["external_subject_id"] for item in guppy_data if "external_subject_id" in item]

    return ids

