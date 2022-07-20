import json
import flask
from flask import current_app as capp

from PcdcAnalysisTools import utils
from PcdcAnalysisTools import auth

from pcdcutils.environment import is_env_enabled
import json
import os 

from dotenv import load_dotenv

load_dotenv()

@auth.authorize_for_analysis("access")
def get_result():
    args = utils.parse.parse_request_json()
    if os.environ.get('MOCK_DATA') == 'True': 
        f = open(os.environ.get('DATA_PATH'))
        data = json.load(f)
    else:
        data = utils.guppy.downloadDataFromGuppy(
            path=capp.config['GUPPY_API'] + "/download",
            type="subject",
            totalCount=100000,
            fields=["consortium", "studies.study_id", "molecular_analysis.molecular_abnormality"],
            filters=[],
            sort=[],
            accessibility="accessible",
            config=capp.config
        )
    return flask.jsonify(get_counts_list(data, args))


def get_counts_list(data, args):
    consortium_list = args.get("consortiumList", [])
    counts_list = []
    counts_list.append(get_counts_per_consortium(data))
    for consortium in consortium_list:
        counts_list.append(get_counts_per_consortium(data, consortium))
    counts_list.append(get_counts_per_consortium(data, "missing"))

    return counts_list


def get_counts_per_consortium(data, consortium=None):
    molecular_analysis_count = 0
    study_set = set()
    subject_count = 0

    for d in data:
        if (consortium is None) or (consortium and "consortium" in d and d["consortium"] == consortium):
            if "molecular_analysis" in d:
                molecular_analysis_count += len(d["molecular_analysis"])
            if "studies" in d:
                for study in d["studies"]:
                    if "study_id" in study:
                        study_set.add(study["study_id"])
            subject_count += 1
        elif consortium == "missing":
            if "consortium" not in d:
                subject_count += 1


    return {
        "consortium": "total" if consortium is None else consortium,
        "molecular_analysis": molecular_analysis_count,
        "study": len(study_set),
        "subject": subject_count
    }
