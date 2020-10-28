import json
import flask
import math

from lifelines import KaplanMeierFitter
from lifelines.statistics import multivariate_logrank_test
from PcdcAnalysisTools import utils
from PcdcAnalysisTools import auth

import numpy as np
import pandas as pd


@auth.authorize_for_analysis("access")
def get_result():
    args = utils.parse.parse_request_json()
    data = (
        fetch_data(args)
        if flask.current_app.config.get("IS_SURVIVAL_USING_GUPPY", True)
        else fetch_fake_data(args)
    )
    return flask.jsonify(get_survival_result(data, args))


def fetch_data(args):
    # TODO add json payload control 
    # TODO add check on payload nulls and stuff
    # TODO add path in the config file or ENV variable
    _filter = args.get("filter")
    factor_var = args.get("factorVariable")
    stratification_var = args.get("stratificationVariable")

    # NOT USED FOR NOW
    # args.get("efsFlag")

    status_var, time_var = ("lkss", "age_at_lkss")

    fields = [f for f in [status_var, time_var,
                          factor_var, stratification_var] if f != ""]

    filters = json.loads(json.dumps(_filter))
    filters.setdefault("AND", [])
    filters["AND"].append({">=": {time_var: 0}})

    guppy_data = utils.guppy.downloadDataFromGuppy(
        path="http://guppy-service/download",
        type="subject",
        totalCount=100000,
        fields=fields,
        filters=filters,
        sort=[],
        accessibility="accessible"
    )

    return (
        pd.DataFrame.from_records(guppy_data)
        .assign(status=lambda x: x[status_var] == "Dead",
                time=lambda x: x[time_var] / 365.25)
        .filter(items=[factor_var, stratification_var, "status", "time"])
    )


def fetch_fake_data(args):
    """Fetches the mocked source data (pandas.DataFrame) based on request body

    Args:
        args(dict): Request body parameters and values
    """
    efs_flag = args.get("efsFlag")
    factor_var = args.get("factorVariable")
    stratification_var = args.get("stratificationVariable")

    status_col, time_col = (
        ("EFSCENS", "EFSTIME")
        if efs_flag
        else ("SCENS", "STIME")
    )

    return (
        pd.read_json("./data/fake.json", orient="records")
        .query(f"{time_col} >= 0")
        .assign(status=lambda x: x[status_col] == 1,
                time=lambda x: x[time_col] / 365.25)
        .filter(items=[factor_var, stratification_var, "status", "time"])
    )


def get_survival_result(data, args):
    """Returns the survival results (dict) based on data and request body

    Args:
        data(pandas.DataFrame): Source data
        args(dict): Request body parameters and values

    Returns:
        A dict of survival result consisting of "pval", "risktable", and "survival" data
        example:

        {"pval": 0.1,
         "risktable": [{ "nrisk": 30, "time": 0}],
         "survival": [{"prob": 1.0, "time": 0.0}]}
    """
    kmf = KaplanMeierFitter()
    variables = [x for x in [args.get("factorVariable"),
                             args.get("stratificationVariable")] if x != ""]
    time_range = range(int(np.ceil(data.time.max())) + 1)

    if len(variables) == 0:
        pval = None

        kmf.fit(data.time, data.status)
        risktable = [{
            "name": "All",
            "data": get_risktable(kmf.event_table.at_risk, time_range)
        }]
        survival = [{
            "name": "All",
            "data": get_survival(kmf.survival_function_)
        }]
    else:
        pval = get_pval(data, variables)
        risktable = []
        survival = []
        for name, grouped_df in data.groupby(variables):
            name = map(str, name if isinstance(name, tuple) else (name,))
            label = ",".join(map(lambda x: "=".join(x), zip(variables, name)))

            kmf.fit(grouped_df.time, grouped_df.status)
            risktable.append({
                "name": label,
                "data": get_risktable(kmf.event_table.at_risk, time_range)
            })
            survival.append({
                "name": label,
                "data": get_survival(kmf.survival_function_)
            })

    return {"pval": pval, "risktable": risktable, "survival": survival}


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


def get_risktable(at_risk, time_range):
    """Returns the number-at-risk table data (dict) for the response API

    Args:
        at_risk(pandas.Series): Number-at-risk data from a fitted lifelines.KaplanMeierFitter instance
        time_range(range): A range of min and max time values
    """
    return (
        at_risk
        .reset_index()
        .assign(time=lambda x: x.event_at.apply(np.ceil))
        .groupby("time")
        .at_risk.min()
        .reset_index()
        .merge(pd.DataFrame(data={"time": time_range}), how="outer")
        .sort_values(by="time")
        .fillna(method="ffill")
        .rename(columns={"at_risk": "nrisk"})
        .astype({"nrisk": "int32"})
        .query(f"time >= {min(time_range)} and time <= {max(time_range)}")
        .to_dict(orient="records")
    )
