import json
import flask

from flask import current_app as capp

from lifelines import KaplanMeierFitter
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
    efs_flag = args.get('efsFlag', False)

    log_obj = {}
    log_obj["explorer_id"] = args.get("explorerId")
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
    for filter_set in filter_sets:
        # the default "All Subjects" option has filter set id of -1
        filter_set_id = filter_set.get("id")
        data = fetch_data(filter_set.get("filters"), efs_flag)
        result = get_survival_result(data, risktable_flag, survival_flag)

        survival_results[filter_set_id] = result
        survival_results[filter_set_id]["name"] = filter_set.get("name")

    return flask.jsonify(survival_results)


EVENT_FREE_STATUS_STR = "Subject has had one or more events"
EVENT_FREE_STATUS_VAR = "censor_status"
EVENT_FREE_TIME_VAR = "age_at_censor_status"

OVERALL_STATUS_STR = "Dead"
OVERALL_STATUS_VAR = "survival_characteristics.lkss"
OVERALL_TIME_VAR = "survival_characteristics.age_at_lkss"


def fetch_data(filters, efs_flag):
    status_str, status_var, time_var = (
        (EVENT_FREE_STATUS_STR, EVENT_FREE_STATUS_VAR, EVENT_FREE_TIME_VAR)
        if efs_flag
        else (OVERALL_STATUS_STR, OVERALL_STATUS_VAR, OVERALL_TIME_VAR)
    )

    filters.setdefault("AND", [])

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

    if not efs_flag:
        for each in guppy_data:
            survival_dict = each.get("survival_characteristics")[0]
            del each["survival_characteristics"]

            each[status_var] = survival_dict.get("lkss")
            each[time_var] = survival_dict.get("age_at_lkss")

    return (
        pd.DataFrame.from_records(guppy_data)
        .assign(
            omitted=lambda x:
                ((x[status_var].isna()) | (x[time_var].isna()) | (x[time_var] < 0)),
            status=lambda x:
                np.where(x["omitted"], None, x[status_var] == status_str),
            time=lambda x:
                np.where(x["omitted"], None, x[time_var] / 365.25)
        )
        .filter(items=["omitted", "status", "time"])
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

        {"count": {"fitted": 30, "total": 30},
         "risktable": [{ "nrisk": 30, "time": 0}],
         "survival": [{"prob": 1.0, "time": 0.0}]}
    """
    data_kmf = data.loc[data["omitted"] == False]
    result = {
        "count": {
            "fitted": data_kmf.shape[0],
            "total": data.shape[0]
        }
    }

    if result["count"]["fitted"] == 0:
        if risktable_flag:
            result["risktable"] = [{"nrisk": 0, "time": 0}]

        if survival_flag:
            result["survival"] = [{"prob": 0, "time": 0}]

        return result

    kmf = KaplanMeierFitter()
    kmf.fit(data_kmf.time, data_kmf.status)

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
