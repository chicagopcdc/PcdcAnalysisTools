import json
import flask
import urllib.parse
from flask import current_app as capp


from PcdcAnalysisTools import utils
from PcdcAnalysisTools import auth

other = "other"
common_list = ["gdc", other]
commons_dict = {}
commons_dict["gdc"] = "TARGET-GDC"
# "GDC", "PDC", "GMKF", "Other". 

### TODO TODO
#return a link in case it is short enough and supported
# otherwise return a link to the file and a link to the other common if any


@auth.authorize_for_analysis("access")
def get_info(common):
    args = utils.parse.parse_request_json()

    if not common or common not in common_list:
        common = other

    data = fetch_data(args, common)
    # data = [value for value in data if value]
    
    # return_type = args.get("return_type")
    # if not return_type or return_type not in ["url", "manifest"]:
    #     return_type = "url"
    # if return_type == "manifest":
    #     return flask.jsonify({"manifest": data})

    ret_obj = {}
    if common == other:
        # TODO complete
        ret_obj["link"] = None
        #TODO build file, store in S3, return URL instead of string
        ret_obj["download_link"] = None
        # ret_obj["type"] = "download"
        ret_obj["type"] = "string"
        ret_obj["data"] = data
    else:
        link = build_url(data, common)
        ret_obj["link"] = link
        ret_obj["type"] = "redirect"
        
    return flask.jsonify(ret_obj)



def fetch_data(args, common):
    # TODO add json payload control
    # TODO add check on payload nulls and stuff
    # TODO add path in the config file or ENV variable
    _filter = args.get("filter")
    filters = json.loads(json.dumps(_filter))

    if common == other:
        fields = ["subject_submitter_id"]
    else:
        fields = ["external_references.external_subject_id", "external_references.external_resource_name"]

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

    if common == other:
        # return USI from our system since we don't have a connection to this specific external Commons
        return [item["subject_submitter_id"] for item in guppy_data if "subject_submitter_id" in item]
    else:
        # TODO I can count how many are without that information and communicate that to the frontend (guppy data return empty objects when data is missing)
        # external_references = [item["external_subject_id"] for item in guppy_data if "external_references" in item and len(item["external_references"]) > 0]

        # return [item["external_subject_id"] for ext_ref in guppy_data if ext_ref and "external_references" in ext_ref for item in ext_ref["external_references"]]
        return [item["external_subject_id"] for ext_ref in guppy_data if ext_ref and "external_references" in ext_ref for item in ext_ref["external_references"] if item and "external_resource_name" in item and item["external_resource_name"] == commons_dict[common] and "external_subject_id" in item and item["external_subject_id"]]

def build_url(data, common):
    if commons_dict[common] == "TARGET-GDC":
        query = '{"op":"and","content":[{"op":"in","content":{"field":"cases.case_id","value":'
        query += json.dumps(data)
        query += '}}]}'

        encoded = urllib.parse.quote(query)
        link = 'https://portal.gdc.cancer.gov/exploration?filters=' + encoded
        return link
    else:
        return None



