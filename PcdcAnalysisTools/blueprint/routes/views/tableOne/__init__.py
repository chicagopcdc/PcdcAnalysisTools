import flask
from flask import current_app as capp

from PcdcAnalysisTools import utils
from PcdcAnalysisTools import auth
from PcdcAnalysisTools.errors import (
    AuthError,
    UserError,
    InternalError,
)
from cdislogging import get_logger
import pandas as pd
from PcdcAnalysisTools.blueprint.routes.views.survival import check_allowed_filter
from PcdcAnalysisTools.blueprint.routes.views.stats import get_consortium_list


logger = get_logger(logger_name=__name__, log_level="info")

DEFAULT_TABLE_ONE_CONFIG = {"consortium": [], "excluded_variables": [], "enabled": True}


@auth.authorize_for_analysis("access")
def get_config():
    config = capp.config.get("TABLE_ONE", DEFAULT_TABLE_ONE_CONFIG)
    # change the name of the key from excluded_variables to excludedVariables
    config = dict(config)  # make a shallow copy so we don't modify the original
    if "excluded_variables" in config:
        config["excludedVariables"] = config.pop("excluded_variables")
    return flask.jsonify(config)


# TODO - this is not used anywhere so I am not sure?? maybe it is the format expected for the `covariates` arg in the request
covarname = {"sex": "sex", "race": "race", "survival_characteristics.lkss": "lkss"}


# TODO - add mock options to run it locally for dev / testing
@auth.authorize_for_analysis("access")
def get_result():
    config = capp.config.get("TABLE_ONE", DEFAULT_TABLE_ONE_CONFIG)
    args = utils.parse.parse_request_json()
    _check_user_input(args)

    filter_set = args.get("filterSets")[0]
    covariates = args.get("covariates")

    fields = ["subject_submitter_id"]

    for covariate in covariates.values():
        if covariate["label"] == "subject_submitter_id":
            # subject_submitter_id is a special case, it is always included
            continue
        fields.append(covariate["label"])

    user_filter_set_df = _get_table_one_df(filter_set["filter"], fields)
    total_filter_set_df = _get_table_one_df(
        {"AND": [{"IN": {"consortium": config["consortium"]}}]}, fields
    )
    total_fs_df_less_user_fs_df = _find_inverse_user_df(
        total_filter_set_df, user_filter_set_df
    )

    res = _get_table_result(
        user_filter_set_df, total_fs_df_less_user_fs_df, total_filter_set_df, covariates
    )
    return flask.jsonify(res)


def _get_table_one_df(filterset, fields):

    try:
        data = _fetch_data(filterset, fields)
        df = pd.DataFrame(data)
    except Exception as e:
        logger.error(f"Error fetching data from Guppy: {e}")
        raise InternalError(
            "There was an error fetching data from the data source. Please try again later."
        )

    if len(df) == 0:
        raise UserError(
            "The filter set returned no data. Please check the filter set and try again."
        )

    for field in fields:
        if "." in field:
            # Split the field by '.' to get the nested fields
            nested_fields = field.split(".")
            base_field = nested_fields[
                0
            ]  # The column name (e.g., 'survival_characteristics')
            target_field = nested_fields[
                -1
            ]  # The field to extract (e.g., 'lkss_obfuscated')
            # Check if the column exists
            if base_field in df.columns:
                # Handle lists of dictionaries - extract the first value that matches
                df[field] = df[base_field].apply(
                    lambda x: (
                        x[0].get(target_field)
                        if isinstance(x, list) and len(x) > 0 and isinstance(x[0], dict)
                        else None
                    )
                )

                # Drop the original column if requested
                df = df.drop(base_field, axis="columns")

    return df


def _check_user_input(args):

    config = capp.config.get("TABLE_ONE", DEFAULT_TABLE_ONE_CONFIG)

    filter_sets = args.get("filterSets")
    covariates = args.get("covariates")
    # for first version only allow one filter set
    if not filter_sets:
        raise UserError("You must submit a filter set")
    if len(filter_sets) != 1:
        raise UserError("You must submit exactly one filter set")

    if not covariates:
        raise UserError("You must submit at least one covariate")

    for name, covariate in covariates.items():
        if covariate["type"] not in ["continuous", "categorical"]:
            raise UserError(
                f"Unsupported covariate type: {covariate['type']}. Supported types are 'continuous' and 'categorical'."
            )
        if covariate["type"] == "categorical":
            if "selectedKeys" not in covariate or not covariate["selectedKeys"]:
                raise UserError(
                    f"You must provide selectedKeys for categorical covariate: {name}"
                )
        if covariate["type"] == "continuous":
            # add this in later
            # if "unit" not in covariate or not isinstance(covariate["unit"], (int, float)):
            #     raise UserError(
            #         f"You must provide a numeric unit for continuous covariate: {name}"
            #     )
            if "selectedKeys" in covariate:
                raise UserError(
                    f"You cannot provide selectedKeys for continuous covariate: {name}"
                )
            if "buckets" in covariate:
                if (
                    not isinstance(covariate["buckets"], list)
                    or len(covariate["buckets"]) == 0
                ):
                    raise UserError(
                        f"Buckets for continuous covariate: {name} must be a non-empty list"
                    )

                for i in range(len(covariate["buckets"])):
                    bucket = covariate["buckets"][i]
                    if "splitValue" not in bucket or not isinstance(
                        bucket["splitValue"], (int, float)
                    ):
                        raise UserError(
                            f"Each bucket for continuous covariate: {name} must have a 'splitValue' numerical value"
                        )
                    if "inclusiveLower" not in bucket or not isinstance(
                        bucket["inclusiveLower"], bool
                    ):
                        raise UserError(
                            f"Each bucket for continuous covariate: {name} must have an 'inclusiveLower' boolean value"
                        )
                    if i > 0:
                        prev_bucket = covariate["buckets"][i - 1]
                        if bucket["splitValue"] < prev_bucket["splitValue"]:
                            raise UserError(
                                f"Buckets for continuous covariate: {name} must not overlap"
                            )

    # TODO - we want to add custom logs for tracking usage and abse like in the survival

    log_obj = {}
    if not capp.mock_data:
        try:
            user = auth.get_current_user()
            log_obj["user_id"] = user.id
        except AuthError:
            logger.warning("Unable to load or find the user, check your token")
    for filter_set in filter_sets:
        try:

            log_obj["filter"] = filter_set["filter"]
            # log_obj["explorer_id"] = filter_set["explorerId"]
            log_obj["filter_name"] = filter_set["name"]
            log_obj["filter_set_id"] = filter_set["id"]
            logger.info(f"TABLE ONE - {log_obj}")
        except KeyError as e:
            raise UserError(f"Missing required field in filter set: {e}")

    # TODO I assume we don't need a filter for all data aside from {} We will need to support consortiums limitations like for the survival.
    # I guess this is the reason of this allFilter variable?
    # we will also in addition to this need to check if the selected filters is allowed, like in the survival
    # doesnt the sumbited filter need to be within this filter

    if_filterset_allowed = check_allowed_filter(
        config, filter_sets[0]["filter"]
    ) and set(get_consortium_list(filter_sets[0]["filter"])).issubset(
        set(config.get("consortium"))
    )

    disallowed_variables = [
        variable["field"] for variable in config.get("excluded_variables", [])
    ]
    for label, covariate in covariates.items():
        if covariate["label"] in disallowed_variables:
            raise UserError(f"Covariate '{label}' is not allowed in this analysis.")

    if not if_filterset_allowed:
        raise UserError(
            "The filter set is not allowed for this analysis. Please check the filter set and try again."
        )


def _find_inverse_user_df(total_filter_set_df, user_filter_set_df):
    ### compare the two pandas dataframes and create a new dataframe of the rows from total_filter_set_df whose values in subject_submitter_id are not in user_filter_set_df
    if (
        "subject_submitter_id" not in total_filter_set_df.columns
        or "subject_submitter_id" not in user_filter_set_df.columns
    ):
        raise InternalError(
            "Both dataframes must contain the 'subject_submitter_id' column to find the inverse."
        )
    # Find the subject_submitter_id values in user_filter_set_df
    user_subject_submitter_ids = set(user_filter_set_df["subject_submitter_id"])
    # Filter total_filter_set_df to get rows where subject_submitter_id is not in user_ids
    inverse_df = total_filter_set_df[
        ~total_filter_set_df["subject_submitter_id"].isin(user_subject_submitter_ids)
    ]
    # Reset the index of the resulting dataframe
    inverse_df.reset_index(drop=True, inplace=True)
    return inverse_df


def _fetch_data(filters, fields):
    guppy_data = utils.guppy.downloadDataFromGuppy(
        path=capp.config.get("GUPPY_API") + "/download",
        type="subject",
        totalCount=100000,
        fields=fields,  # TODO - check it is a list
        filters=filters,
        sort=[],
        accessibility="accessible",
        config=capp.config,
    )

    return guppy_data


def _get_table_result(
    user_filter_set_df, everything_else_df, total_filter_set_df, covariates
):
    true_number = len(user_filter_set_df)
    everything_else_number = len(everything_else_df)

    return_table = {
        "variables": [],
        "trueCount": true_number,
        "everythingElseCount": everything_else_number,
    }

    #  for each covariate, so for each row / variables it computes
    # for continous should bucketize the response, and the buckets shoud come from the user input, not sure it is doing this
    for name, covariate in covariates.items():

        covariate_return_value = {"name": name}
        keys = []
        # calcuate the total number of row values which are empty / data is missing for this column covariate['label']
        if covariate["label"] not in user_filter_set_df.columns:
            raise InternalError(
                f"Covariate label '{covariate['label']}' not found in the data."
            )

        missing_count_from_true = user_filter_set_df[covariate["label"]].isnull().sum()
        missing_count_from_everything_else = (
            everything_else_df[covariate["label"]].isnull().sum()
        )

        covariate_return_value["missingFromTruePercent"] = "{:.1%}".format(
            missing_count_from_true / true_number
        )
        covariate_return_value["missingFromTrueCount"] = int(missing_count_from_true)
        covariate_return_value["missingFromEverythingElsePercent"] = "{:.1%}".format(
            missing_count_from_everything_else / everything_else_number
        )
        covariate_return_value["missingFromEverythingElseCount"] = int(
            missing_count_from_everything_else
        )

        if covariate["type"] == "continuous":
            # need to figure out how to find unit in data-portal
            # removed unit for now/int(covariate['unit']
            # this is rounding
            # if
            covariate_return_value["type"] = "continuous"
            if "buckets" in covariate:
                # determine min/max from total dataset for this covariate column
                col = covariate["label"]
                col_series = total_filter_set_df[col].dropna()
                col_min = float(col_series.min())
                col_max = float(col_series.max())

                for i in range(-1, len(covariate["buckets"])):
                    # "buckets": [
                    #     {"splitValue": 25.140827870369, "inclusiveLower": True},
                    #     {"splitValue": 73.62612608075142, "inclusiveLower": True}
                    # ],
                    if i == -1:
                        start = col_min
                        start_op = ">="
                    else:
                        start = covariate["buckets"][i]["splitValue"]
                        start_op = (
                            ">" if covariate["buckets"][i]["inclusiveLower"] else ">="
                        )

                    if i == len(covariate["buckets"]) - 1:
                        end = col_max
                        end_op = "<="
                    else:
                        end = covariate["buckets"][i + 1]["splitValue"]
                        end_op = (
                            "<="
                            if covariate["buckets"][i + 1]["inclusiveLower"]
                            else "<"
                        )

                    # Filter data for this bucket
                    true_bucket_data = user_filter_set_df.query(
                        f"`{covariate['label']}` {start_op} @start and `{covariate['label']}` {end_op} @end"
                    )
                    everything_else_bucket_data = everything_else_df.query(
                        f"`{covariate['label']}` {start_op} @start and `{covariate['label']}` {end_op} @end"
                    )

                    # Calculate means for this bucket
                    true_mean = (
                        true_bucket_data[covariate["label"]].mean()
                        if len(true_bucket_data) > 0
                        else 0
                    )
                    everything_else_mean = (
                        everything_else_bucket_data[covariate["label"]].mean()
                        if len(everything_else_bucket_data) > 0
                        else 0
                    )

                    keys.append(
                        {
                            "name": f"{round(start, 2)} - {round(end, 2)}",
                            "data": {
                                "trueMean": round(true_mean, 2),
                                "trueCount": int(len(true_bucket_data)),
                                "everythingElseMean": round(everything_else_mean, 2),
                                "everythingElseCount": int(
                                    len(everything_else_bucket_data)
                                ),
                            },
                        }
                    )

                covariate_return_value["buckets"] = keys
            else:
                true_mean = format(user_filter_set_df[covariate["label"]].mean(), ".1f")
                everything_else_mean = format(
                    everything_else_df[covariate["label"]].mean(), ".1f"
                )
                covariate_return_value["mean"] = {
                    f"trueMean": true_mean,
                    "everythingElseMean": everything_else_mean,
                }

        elif covariate["type"] == "categorical":

            for selected_key in covariate["selectedKeys"]:

                true_count = (
                    user_filter_set_df[covariate["label"]] == selected_key
                ).sum()
                true_percentage = "{:.1%}".format(true_count / true_number)

                everything_else_count = (
                    everything_else_df[covariate["label"]] == selected_key
                ).sum()
                everything_else_percentage = "{:.1%}".format(
                    everything_else_count / everything_else_number
                )

                keys.append(
                    {
                        "name": selected_key,
                        "data": {
                            f"truePercent": true_percentage,
                            "trueCount": int(true_count),
                            "everythingElsePercent": everything_else_percentage,
                            "everythingElseCount": int(everything_else_count),
                        },
                    }
                )

            covariate_return_value["keys"] = keys
            covariate_return_value["type"] = "categorical"

        else:

            raise UserError(
                f"Unsupported covariate type: {covariate}. Supported types are 'continuous' and 'categorical'."
            )

        return_table["variables"].append(covariate_return_value)

    return return_table
