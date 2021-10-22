import json
import flask

from flask import current_app as capp

from lifelines import KaplanMeierFitter
from lifelines.statistics import multivariate_logrank_test
from PcdcAnalysisTools import utils
from PcdcAnalysisTools import auth

import numpy as np
import pandas as pd


@auth.authorize_for_analysis("access")
def get_result():
    args = utils.parse.parse_request_json()

    # TODO add json payload control
    # TODO add check on payload nulls and stuff
    # TODO add path in the config file or ENV variable
    _filter = args.get("filter")
    filters = json.loads(json.dumps(_filter))
    factor_var = args.get("parameter").get("factorVariable")
    stratification_var = args.get("parameter").get("stratificationVariable")
    # NOT USED FOR NOW
    # efs_flag = args.get("efsFlag")
    risktable_flag = args.get("result").get("risktable")
    survival_flag = args.get("result").get("survival")
    pval_flag = args.get("result").get("pval")

    log_obj = {}
    log_obj["filters"] = filters
    log_obj["factor_variable"] = factor_var
    log_obj["stratification_variable"] = stratification_var
    try:
        user = auth.get_current_user()
        log_obj["user_id"] = user.id
    except AuthError:
        logger.warning(
            "Unable to load or find the user, check your token"
        )
    capp.logger.info(log_obj)

    data = (
        fetch_data(filters, factor_var, stratification_var)
        if flask.current_app.config.get("IS_SURVIVAL_USING_GUPPY", True)
        else fetch_fake_data(args)
    )
    return flask.jsonify(get_survival_result(data, factor_var, stratification_var, risktable_flag, survival_flag, pval_flag))


def fetch_data(filters, factor_var, stratification_var):
    status_var, time_var = ("survival_characteristics.lkss",
                            "survival_characteristics.age_at_lkss")

    fields = [f for f in [status_var, time_var,
                          factor_var, stratification_var] if f != ""]

    filters.setdefault("AND", [])
    filters["AND"].append({
        "nested": {
            "path": "survival_characteristics",
            "AND": [{"GTE": {"age_at_lkss": 0}}]
        }
    })

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

    for each in guppy_data:
        survival_dict = each.get("survival_characteristics")[0]
        del each["survival_characteristics"]

        each[status_var] = survival_dict.get("lkss")
        each[time_var] = survival_dict.get("age_at_lkss")

    return (
        pd.DataFrame.from_records(guppy_data)
        .assign(status=lambda x: x[status_var] == "Dead",
                time=lambda x: x[time_var] / 365.25)
        .filter(items=[factor_var, stratification_var, "status", "time"])
    )


def fetch_fake_data(factor_var, stratification_var):
    """Fetches the mocked source data (pandas.DataFrame) based on request body

    Args:
        args(dict): Request body parameters and values
    """

    status_col, time_col = ("EFSCENS", "EFSTIME")
    # (
    # ("EFSCENS", "EFSTIME")
    # if efs_flag
    # else ("SCENS", "STIME")
    # )

    return (
        pd.read_json("./data/fake.json", orient="records")
        .query(f"{time_col} >= 0")
        .assign(status=lambda x: x[status_col] == 1,
                time=lambda x: x[time_col] / 365.25)
        .filter(items=[factor_var, stratification_var, "status", "time"])
    )


def get_survival_result(data, factor_var, stratification_var, risktable_flag, survival_flag, pval_flag):
    """Returns the survival results (dict) based on data and request body

    Args:
        data(pandas.DataFrame): Source data
        factor_var(str): Factor variable for survival results
        stratification_var(str): Stratification variable for survival results
        risktable_flag(bool): Include risk table in result?
        survival_flag(bool): Include survival probability in result?
        pval_flag(bool): Include p-value in result?

    Returns:
        A dict of survival result consisting of "pval", "risktable", and "survival" data
        example:

        {"pval": 0.1,
         "risktable": [{ "nrisk": 30, "time": 0}],
         "survival": [{"prob": 1.0, "time": 0.0}]}
    """
    kmf = KaplanMeierFitter()
    variables = [x for x in [factor_var,
                             stratification_var] if x != ""]
    time_range = range(int(np.ceil(data.time.max())) + 1)

    pval = None
    risktable = []
    survival = []
    if len(variables) == 0:
        kmf.fit(data.time, data.status)
        if risktable_flag:
            risktable.append({
                "group": [],
                "data": get_risktable(kmf.event_table, time_range)
            })

        if survival_flag:
            survival.append({
                "group": [],
                "data": get_survival(kmf.survival_function_)
            })
    else:
        if pval_flag:
            pval = get_pval(data, variables)

        for name, grouped_df in data.groupby(variables):
            name = map(str, name if isinstance(name, tuple) else (name,))
            group = list(map(
                lambda x: {"variable": x[0], "value": x[1]},
                zip(variables, name)
            ))

            kmf.fit(grouped_df.time, grouped_df.status)
            if risktable_flag:
                risktable.append({
                    "group": group,
                    "data": get_risktable(kmf.event_table, time_range)
                })

            if survival_flag:
                survival.append({
                    "group": group,
                    "data": get_survival(kmf.survival_function_)
                })

    result = {}
    if pval_flag:
        result["pval"] = pval

    if risktable_flag:
        result["risktable"] = risktable

    if survival_flag:
        result["survival"] = survival

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


def get_pval(data, variables):
    """Returns the log-rank test p-value (float) for the data and variables

    Args:
        data(pandas.DataFrame): Source data
        variables(list): Variables to use in the log-rank test
    """
    groups = list(map(str, zip(*[data[f] for f in variables])))
    result = multivariate_logrank_test(data.time, groups, data.status)
    return result.p_value if not np.isnan(result.p_value) else None


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
