import flask

from lifelines import KaplanMeierFitter
from lifelines.statistics import multivariate_logrank_test
from PcdcAnalysisTools import utils
import numpy as np
import pandas as pd


def main():
    args = utils.parse.parse_request_json()
    data = fetch_fake_data(args)
    return flask.jsonify(get_survival_result(data, args))


def fetch_data(url, search_criteria):
    # TODO run guppy query towards ES
    return


def fetch_fake_data(args):
    efs_flag = args.get("efsFlag")
    factor_var = args.get("factorVariable")
    stratification_var = args.get("stratificationVariable")
    start_time = args.get("startTime")
    end_time = args.get("endTime")

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
            "data": parse_survival(kmf.survival_function_, time_range)
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
                "data": parse_survival(kmf.survival_function_, time_range)
            })

    return {"pval": pval, "risktable": risktable, "survival": survival}


def get_time_range(data, args):
    max_time = int(np.floor(data.time.max()))
    start_time = args.get("startTime")
    end_time = (
        min(args.get("endTime"), max_time)
        if args.get("endTime") > start_time
        else max_time
    )

    return range(start_time, end_time + 1)


def parse_survival(df, time_range):
    return (
        df.reset_index()
        .rename(columns={"KM_estimate": "prob", "timeline": "time"})
        .replace({'time': {0: min(time_range)}})
        .to_dict(orient="records")
    )


def get_pval(df, variables):
    groups = list(map(str, zip(*[df[f] for f in variables])))
    result = multivariate_logrank_test(df.time, groups, df.status)
    return result.p_value


def get_risktable(df, time_range):
    return (
        df.reset_index()
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
