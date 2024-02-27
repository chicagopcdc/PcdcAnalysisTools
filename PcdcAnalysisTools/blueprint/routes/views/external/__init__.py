import json
import flask
import urllib.parse
from flask import current_app as capp
from flask import make_response

from PcdcAnalysisTools import utils
from PcdcAnalysisTools import auth


# Import and build configuration variables
DEFAULT_EXTERNAL_CONFIG = {"commons": [{"label": 'Genomic Data Commons', "value": 'gdc'}, {"label": 'Gabriella Miller Kids First', "value": 'gmkf'}], "commons_dict": {"gdc": "TARGET - GDC", "gmkf": "GMKF"}}
other = "other"



@auth.authorize_for_analysis("access")
def get_config():
    config = capp.config.get("EXTERNAL", DEFAULT_EXTERNAL_CONFIG)
    return flask.jsonify(config)

@auth.authorize_for_analysis("access")
def get_info(common):
    """Returns the GDC URL with a query string with case ids.

    If the URL is too long the GDC website will return a 414 error. The maximum length
    depends on their server as well as the client browser. When that happens this function
    will return a relative URL with a response header of 'Content-Disposition': 'attachment;
    and the payload will be a plain text file with UUIDs separated by comma. This Should allow
    the user to copy-paste the contents of the file directly onto the appropriate field in the
    GDC website. 
    
    2048 characters seems to be one of the lower limits. We are using that number,
    minus the URL size, as an approximation for when the text file should be returned.
    This ends up being around 40 UUIDs after encoding.
    """
    config = capp.config.get("EXTERNAL", DEFAULT_EXTERNAL_CONFIG)
    common_list = [common["value"] for common in config["commons"]]
    common_list.append(other)

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
    payload = {}
    csv_data = ','.join(d for d in data)
    payload["data"] = csv_data
    payload["type"] = "file"
    payload["link"] = get_link(common)

    # GDC 2.0 is not supporting query params anymore
    # payload["link"] = build_url(data, common)
    # payload["type"] = "redirect"
    return flask.jsonify(payload)


def fetch_data(args, common):

    config = capp.config.get("EXTERNAL", DEFAULT_EXTERNAL_CONFIG)
    commons_dict = config["commons_dict"]

    # TODO add json payload control
    # TODO add check on payload nulls and stuff
    # TODO add path in the config file or ENV variable
    _filter = args.get("filter", {})
    filters = json.loads(json.dumps(_filter))
    filters.setdefault("AND", [])

    if common == other:
        fields = ["subject_submitter_id"]
    elif common == 'gmkf':
        fields = ["external_references.external_subject_submitter_id", "external_references.external_resource_name"]
    elif common == 'cds':
        fields = ["external_references.external_subject_submitter_id", "external_references.external_resource_name"]
    else:
        fields = ["external_references.external_subject_id", "external_references.external_resource_name"]


    guppy_data = utils.guppy.downloadDataFromGuppy(
        path=capp.config['GUPPY_API'] + "/download",
        type="subject",
        totalCount=100000,
        fields=fields,
        filters=(
            {"AND": [
                {"nested":{"path":"external_references","AND":[{"IN":{"external_resource_name":[commons_dict[common]]}}]}},
                filters
            ]}
            if common
            else filters
        ),
        sort=[],
        accessibility="accessible",
        config=capp.config
    )

    if common == other:
        # return USI from our system since we don't have a connection to this specific external Commons
        return [item["subject_submitter_id"] for item in guppy_data if "subject_submitter_id" in item]
    elif common in ['gmkf','cds']:
        return [item["external_subject_submitter_id"] for ext_ref in guppy_data if ext_ref and "external_references" in ext_ref for item in ext_ref["external_references"] if item and "external_resource_name" in item and item["external_resource_name"] == commons_dict[common] and "external_subject_submitter_id" in item and item["external_subject_submitter_id"]]
    else:
        # TODO I can count how many are without that information and communicate that to the frontend (guppy data return empty objects when data is missing)
        # external_references = [item["external_subject_id"] for item in guppy_data if "external_references" in item and len(item["external_references"]) > 0]

        # return [item["external_subject_id"] for ext_ref in guppy_data if ext_ref and "external_references" in ext_ref for item in ext_ref["external_references"]]
        return [item["external_subject_id"] for ext_ref in guppy_data if ext_ref and "external_references" in ext_ref for item in ext_ref["external_references"] if item and "external_resource_name" in item and item["external_resource_name"] == commons_dict[common] and "external_subject_id" in item and item["external_subject_id"]]


def get_link(common):
    if common == 'gdc':
        return "https://portal.gdc.cancer.gov/analysis_page?app=CohortBuilder&tab=general"
    elif common == 'gmkf':
        return 'https://portal.kidsfirstdrc.org/explore'
    elif common == 'cds':
        return 'https://dataservice.datacommons.cancer.gov/#/data'
    else:
        return None


def build_url(data, common):
    if type(data) is list and len(data) > 1: 
        if common == "gdc":
            query = '{"op":"and","content":[{"op":"in","content":{"field":"cases.case_id","value":'
            query += json.dumps(data)
            query += '}}]}'
            encoded = urllib.parse.quote(query)
            link = get_link(common) + '?filters=' + encoded
            return link
        else:
            return None
    
    return None












