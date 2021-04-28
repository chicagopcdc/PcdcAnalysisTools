import json
import flask
from flask import current_app as capp

from PcdcAnalysisTools import utils
from PcdcAnalysisTools import auth


@auth.authorize_for_analysis("access")
def get_result():
    args = utils.parse.parse_request_json()
    data = utils.guppy.downloadDataFromGuppy(
        path="http://guppy-service/download",
        type="subject",
        totalCount=100000,
        fields=["consortium", "study_id", "_molecular_analysis_count"],
        filters=[],
        sort=[],
        accessibility="accessible",
        config=capp.config
    )
    return flask.jsonify(get_counts_list(data, args))


def get_counts_list(data, args):
    consortium_list = args.get("consortiumList")
    counts_list = []
    counts_list.append(get_counts_per_consortium(data))
    for consortium in consortium_list:
        counts_list.append(get_counts_per_consortium(data, consortium))

    return counts_list


def get_counts_per_consortium(data, consortium=None):
    molecular_analysis_count = 0
    study_set = set()
    subject_count = len(data) if consortium is None else 0

    for d in data:
        if consortium is None:
            molecular_analysis_count += d.get("_molecular_analysis_count")
            for id in d.get("study_id", []):
                study_set.add(id)
        elif consortium == d.get("consortium"):
            molecular_analysis_count += d.get("_molecular_analysis_count")
            for id in d.get("study_id", []):
                study_set.add(id)
            subject_count += 1

    return {
        "consortium": "total" if consortium is None else consortium,
        "molecular_analysis": molecular_analysis_count,
        "study": len(study_set),
        "subject": subject_count
    }
