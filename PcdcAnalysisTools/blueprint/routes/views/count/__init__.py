import json
import flask
import math

from PcdcAnalysisTools import utils
from PcdcAnalysisTools import auth

import numpy as np
import pandas as pd


@auth.authorize_for_analysis("access")
def get_result():
    #  http://localhost/guppy/download
    # {"type":"subject","fields":["consortium","study_id","_molecular_analysis_count"]}
    args = utils.parse.parse_request_json()
    print("IN COUNT")
    print(args)
    # data = (
    #     fetch_data(args)
    #     if flask.current_app.config.get("IS_SURVIVAL_USING_GUPPY", True)
    #     else fetch_fake_data(args)
    # )
    data = fetch_data(args)
    return flask.jsonify(get_survival_result(data, args))


def fetch_data(args):
    # TODO add json payload control 
    # TODO add check on payload nulls and stuff
    # TODO add path in the config file or ENV variable
    fields = args.get("fields")
    index_type = args.get("type")

    guppy_data = utils.guppy.downloadDataFromGuppy(
        path="http://guppy-service/download",
        type="subject",
        totalCount=100000,
        fields=fields,
        filters=[],
        sort=[],
        accessibility="accessible"
    )

    print(guppy_data)

    return (
        pd.DataFrame.from_records(guppy_data)
    )


def fetch_fake_data(args):
    """Fetches the mocked source data (pandas.DataFrame) based on request body

    Args:
        args(dict): Request body parameters and values
    """

    return (
        pd.read_json("./data/analysis_count_fake.json", orient="records")
    )


def get_survival_result(data, args):
    """Returns the counts for the overview components and index page chart

    Args:
        data(pandas.DataFrame): Source data
        args(dict): Request body parameters and values

    Returns:
        A dict of count result consisting of "consortium", "study_id", and "_molecular_analysis_count" data
        example:

        {"consortium": 0.1,
         "study_id": [{ "nrisk": 30, "time": 0}],
         "_molecular_analysis_count": [{"prob": 1.0, "time": 0.0}]}
    """


    return {"consortium": pval, "study_id": risktable, "_molecular_analysis_count": survival}
