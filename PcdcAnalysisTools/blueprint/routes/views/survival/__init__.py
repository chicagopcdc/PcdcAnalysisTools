import json
import flask
import os

from flask import current_app as capp

from lifelines import KaplanMeierFitter
from PcdcAnalysisTools import utils
from PcdcAnalysisTools import auth
from PcdcAnalysisTools.errors import AuthError, NotFoundError

import numpy as np
import pandas as pd




DEFAULT_SURVIVAL_CONFIG = {"consortium": [], "result": {}}


@auth.authorize_for_analysis("access")
def get_config():
    config = capp.config.get("SURVIVAL", DEFAULT_SURVIVAL_CONFIG)
    return flask.jsonify(config)


@auth.authorize_for_analysis("access")
def get_result():
    args = utils.parse.parse_request_json()
    config = capp.config.get("SURVIVAL", DEFAULT_SURVIVAL_CONFIG)

    # TODO add json payload control
    # TODO add check on payload nulls and stuff
    # TODO add path in the config file or ENV variable
    filter_sets = json.loads(json.dumps(args.get("filterSets")))
    risktable_flag = config.get("result").get("risktable", False)
    survival_flag = config.get("result").get("survival", False)
    efs_flag = args.get('efsFlag', False)

    log_obj = {}
    log_obj["explorer_id"] = args.get("explorerId")
    log_obj["filter_set_ids"] = args.get("usedFilterSetIds")
    log_obj["efs_flag"] = efs_flag
    if not capp.mock_data:
        try:
            user = auth.get_current_user()
            log_obj["user_id"] = user.id
        except AuthError:
            logger.warning(
                "Unable to load or find the user, check your token"
            )
    capp.logger.info("SURVIVAL TOOL - " + json.dumps(log_obj))

    survival_results = {}
    for filter_set in filter_sets:
        # the default "All Subjects" option has filter set id of -1
        filter_set_id = filter_set.get("id")
        data = fetch_data(config, filter_set.get("filters"), efs_flag)
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

AGE_AT_DISEASE_PHASE = "timings.age_at_disease_phase"
DISEASE_PHASE = "timings.disease_phase"

def fetch_data(config, filters, efs_flag):
    status_str, status_var, time_var = (
        (EVENT_FREE_STATUS_STR, EVENT_FREE_STATUS_VAR, EVENT_FREE_TIME_VAR)
        if efs_flag
        else (OVERALL_STATUS_STR, OVERALL_STATUS_VAR, OVERALL_TIME_VAR)
    )

    filters.setdefault("AND", [])

    if capp.mock_data == 'True': 
        f = open(os.environ.get('DATA_PATH'))
        guppy_data = json.load(f)
    else:
        guppy_data = utils.guppy.downloadDataFromGuppy(
        path=capp.config['GUPPY_API'] + "/download",
        type="subject",
        totalCount=100000,
        fields=[status_var, time_var, DISEASE_PHASE, AGE_AT_DISEASE_PHASE],
        filters=(
            {"AND": [
                {"IN": {"consortium": config.get('consortium')}},
                filters
            ]}
            if config.get('consortium')
            else filters
        ),
        sort=[],
        accessibility="accessible",
        config=capp.config
    )


    node, age_at_disease_phase = AGE_AT_DISEASE_PHASE.split('.')
    node, disease_phase = DISEASE_PHASE.split('.')

    MISSING_STATUS_VAR = True
    MISSING_TIME_VAR = True
    for each in guppy_data:
        # Get the age at initial diagnosis
        dict_tmp = each.get(node)
        if dict_tmp:
            for n in dict_tmp:
                if n.get(disease_phase) == "Initial Diagnosis" and n.get(age_at_disease_phase):
                    if age_at_disease_phase not in each or n.get(age_at_disease_phase) < each[age_at_disease_phase]:
                        each[age_at_disease_phase] = n.get(age_at_disease_phase)

        if efs_flag:
            if MISSING_STATUS_VAR and each.get(EVENT_FREE_STATUS_VAR) is not None:
                MISSING_STATUS_VAR = False

            if MISSING_TIME_VAR and each.get(EVENT_FREE_TIME_VAR) is not None:
                MISSING_TIME_VAR = False

            if not MISSING_STATUS_VAR and not MISSING_TIME_VAR:
                break
        elif not efs_flag:
            survival_dict_tmp = each.get("survival_characteristics")
            survival_dict = None
            for surv in survival_dict_tmp:
                if not survival_dict or surv["age_at_lkss"] > survival_dict["age_at_lkss"]:
                    survival_dict = surv

            if survival_dict:
                del each["survival_characteristics"]

                each[status_var] = survival_dict.get("lkss")
                if each[status_var] is not None:
                    MISSING_STATUS_VAR = False

                each[time_var] = survival_dict.get("age_at_lkss")
                if each[time_var] is not None:
                    MISSING_TIME_VAR = False

    if MISSING_STATUS_VAR or MISSING_TIME_VAR:
        raise NotFoundError("The cohort selected has no {} and/or no {}. The curve can't be built without these necessary data points.".format(
            EVENT_FREE_STATUS_VAR if efs_flag else OVERALL_STATUS_VAR, EVENT_FREE_TIME_VAR if efs_flag else OVERALL_TIME_VAR))
   

    return (
        pd.DataFrame.from_records(guppy_data)
        .assign(
            omitted=lambda x:
                ((x[status_var].isna()) | (x[status_var] == 'Unknown') |
                 (x[time_var].isna()) | (x[time_var] < 0)),
            status=lambda x:
                np.where(x["omitted"], None, x[status_var] == status_str),
            time=lambda x:
                np.where(x["omitted"], None, (x[time_var] - x[age_at_disease_phase]) / 365.25)        
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
