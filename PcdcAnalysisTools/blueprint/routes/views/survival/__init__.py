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
    start_time = args.get("startTime", 0) * 365.25
    end_time = args.get("endTime", 0) * 365.25

    # NOT USED FOR NOW
    # args.get("efsFlag")


    # This is to avoid doible as 5.0 to be translated in 5 in the JSON call which would break the body decoding
    start_time_int = math.floor(start_time)
    differential = start_time - start_time_int
    start_time = start_time_int if differential == 0 else start_time
    end_time_int = math.floor(end_time)
    differential = end_time - end_time_int
    end_time = end_time_int if differential == 0 else end_time



    status_var, time_var = ("lkss", "age_at_lkss")

    fields = [f for f in [status_var, time_var,
                          factor_var, stratification_var] if f != ""]

    filters = json.loads(json.dumps(_filter))
    filters.setdefault("AND", [])
    time_filters = [{">=": {time_var: start_time}}]
    if end_time > 0 and end_time > start_time:
        time_filters.append({"<=": {time_var: end_time}})
    filters["AND"].append({"AND": time_filters})

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
    start_time = args.get("startTime", 0)
    end_time = args.get("endTime", 0)

    status_col, time_col = (
        ("EFSCENS", "EFSTIME")
        if efs_flag
        else ("SCENS", "STIME")
    )
    time_range_query = (
        f"time >= {start_time} and time <= {end_time}"
        if end_time > 0
        else f"time >= {start_time}"
    )

    return (
        pd.read_json("./data/fake.json", orient="records")
        .query(f"{time_col} >= 0")
        .assign(status=lambda x: x[status_col] == 1,
                time=lambda x: x[time_col] / 365.25)
        .filter(items=[factor_var, stratification_var, "status", "time"])
        .query(time_range_query)
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
    time_range = get_time_range(data, args)

    if len(variables) == 0:
        pval = None

        kmf.fit(data.time, data.status)
        risktable = [{
            "name": "All",
            "data": get_risktable(kmf.event_table.at_risk, time_range)
        }]
        survival = [{
            "name": "All",
            "data": get_survival(kmf.survival_function_, time_range)
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
                "data": get_survival(kmf.survival_function_, time_range)
            })

    return {"pval": pval, "risktable": risktable, "survival": survival}


def get_time_range(data, args):
    """Returns a (min, max) time range based on the data and request body

    Args:
        data(pandas.DataFrame): Source data
        request_body(dict): Request body parameters and values
    """
    max_time = int(np.ceil(data.time.max()))
    start_time = args.get("startTime", 0)
    end_time = (
        min(args.get("endTime", 0), max_time)
        if args.get("endTime", 0) > start_time
        else max_time
    )

    return range(start_time, end_time + 1)


def get_survival(survival_function, time_range):
    """Returns the survival probabilities data (dict) for the response API

    Args:
        survival_function(pandas.DataFrame): The estimated survival function from a fitted lifelines.KaplanMeierFitter instance
        time_range(range): A range of min and max time values
    """
    return (
        survival_function
        .reset_index()
        .rename(columns={"KM_estimate": "prob", "timeline": "time"})
        .replace({"time": {0: min(time_range)}})
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
