import json
import flask

from flask import current_app as capp

from lifelines import KaplanMeierFitter
from lifelines.statistics import multivariate_logrank_test
from PcdcAnalysisTools import utils
from PcdcAnalysisTools import auth
from PcdcAnalysisTools.errors import AuthError

import numpy as np
import pandas as pd


@auth.authorize_for_analysis("access")
def get_result():
    args = utils.parse.parse_request_json()

    # TODO add json payload control
    # TODO add check on payload nulls and stuff
    # TODO add path in the config file or ENV variable
    filter_sets = json.loads(json.dumps(args.get("filterSets")))
    # NOT USED FOR NOW
    # efs_flag = args.get("efsFlag")
    risktable_flag = args.get("result").get("risktable")
    survival_flag = args.get("result").get("survival")

    log_obj = {}
    log_obj["explorer_id"] = filter_sets[0].get("explorerId")
    log_obj["filter_set_ids"] = args.get("usedFilterSetIds")
    try:
        user = auth.get_current_user()
        log_obj["user_id"] = user.id
    except AuthError:
        logger.warning(
            "Unable to load or find the user, check your token"
        )
    capp.logger.info(log_obj)

    survival_results = {}
    if len(filter_sets) > 0:
        for filter_set in filter_sets:
            data = fetch_data(filter_set.get("filters"))
            result = get_survival_result(data, risktable_flag, survival_flag)
            survival_results[filter_set.get("id")] = result
    else:
        data = fetch_data({})
        result = get_survival_result(data, risktable_flag, survival_flag)
        survival_results[""] = result
    
    return flask.jsonify(survival_results)


def fetch_data(filters):
    status_var, time_var = ("survival_characteristics.lkss",
                            "survival_characteristics.age_at_lkss")

    filters.setdefault("AND", [])
    filters["AND"].append({
        "nested": {
            "path": "survival_characteristics",
            "AND": [{"GTE": {"age_at_lkss": 0}}]
        }
    })

    guppy_data = utils.guppy.downloadDataFromGuppy(
        path=capp.config['GUPPY_API'] + "/download",
        type="subject",
        totalCount=100000,
        fields=[status_var, time_var],
        filters=filters,
        sort=[],
        accessibility="accessible",
        config=capp.config
    )

    for each in guppy_data:
        survival_dict = each.get("survival_characteristics")[0]
        del each["survival_characteristics"]

        each[status_var] = survival_dict.get("lkss")
        each[time_var] = survival_dict.get("age_at_lkss")

    return (
        pd.DataFrame.from_records(guppy_data)
        .assign(status=lambda x: x[status_var] == "Dead",
                time=lambda x: x[time_var] / 365.25)
        .filter(items=["status", "time"])
    )


def get_survival_result(data, risktable_flag, survival_flag):
    """Returns the survival results (dict) based on data and request body

    Args:
        data(pandas.DataFrame): Source data
        risktable_flag(bool): Include risk table in result?
        survival_flag(bool): Include survival probability in result?

    Returns:
        A dict of survival result consisting of "risktable", and "survival" data
        example:

        {"risktable": [{ "nrisk": 30, "time": 0}],
         "survival": [{"prob": 1.0, "time": 0.0}]}
    """
    kmf = KaplanMeierFitter()
    kmf.fit(data.time, data.status)
    
    result = {}
    if risktable_flag:
        time_range = range(int(np.ceil(data.time.max())) + 1)
        result["risktable"] = get_risktable(kmf.event_table, time_range)

    if survival_flag:
        result["survival"] = get_survival(kmf.survival_function_)

    return result


def get_survival(survival_function):
    """Returns the survival probabilities data (dict) for the response API

    Args:
        survival_function(pandas.DataFrame): The estimated survival function from a fitted lifelines.KaplanMeierFitter instance
    """
    return (
        survival_function
        .reset_index()
        .rename(columns={"KM_estimate": "prob", "timeline": "time"})
        .to_dict(orient="records")
    )


def get_risktable(event_table, time_range):
    """Returns the number-at-risk table data (dict) for the response API

    Args:
        event_table(pandas.DataFrame): A summary of the life table from a fitted lifelines.KaplanMeierFitter instance
        time_range(range): A range of min and max time values
    """
    return (
        event_table
        .assign(nrisk=lambda x: x.at_risk - x.removed)
        .reset_index()
        .assign(time=lambda x: x.event_at.apply(np.ceil))
        .groupby("time")
        .nrisk.min()
        .reset_index()
        .merge(pd.DataFrame(data={"time": time_range}), how="outer")
        .sort_values(by="time")
        .fillna(method="ffill")
        .astype({"nrisk": "int32"})
        .to_dict(orient="records")
    )
