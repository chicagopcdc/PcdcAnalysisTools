import json
import flask
import os

from flask import current_app as capp

from lifelines import KaplanMeierFitter
from PcdcAnalysisTools import utils
from PcdcAnalysisTools import auth
from PcdcAnalysisTools.errors import AuthError, NotFoundError, UnsupportedError, UserError

import pandas as pd


DEFAULT_TABLE_ONE_CONFIG = {"consortium": [], "excluded_variables": [], "result": {}}
# @auth.authorize_for_analysis("access")
# def get_config():
#     config = capp.config.get("TABLE_ONE", DEFAULT_TABLE_ONE_CONFIG)
#     return flask.jsonify(config)


# TODO - this is not used anywhere so I am not sure?? maybe it is the format expected for the `covariates` arg in the request 
covarname = {
    "sex":"sex",
    "race":"race",
    "survival_characteristics.lkss":"lkss"
}


 # TODO - add mock options to run it locally for dev / testing 
@auth.authorize_for_analysis("access")
def get_result():
    try:
        args = utils.parse.parse_request_json()
        config = capp.config.get("TABLE_ONE", DEFAULT_TABLE_ONE_CONFIG)

        if not args or not args.get("filterSets") or not args.get("covarFields"):
            # TODO replace this with a meaningful PcdcAnalysisTools.errors error 
            return {
            "message": "No filter or variable selected."
           }

        filter_sets = json.loads(json.dumps(args.get("filterSets")))
        fields = json.loads(json.dumps(args.get("covarFields")))
        groupFilter = filter_sets[0].get("filters")

        # TODO - we want to add custom logs for tracking usage and abse like in the survival

       

        # TODO I assume we don't need a filter for all data aside from {} We will need to support consortiums limitations like for the survival.
        # I guess this is the reason of this allFilter variable?
        # we will also in addition to this need to check if the selected filters is allowed, like in the survival 
        allFilter = {
            'AND': 
            [{'IN': {'consortium': ['INSTRuCT']}}, {'AND': []}]
        }
        alldata = fetch_data(config, allFilter, fields) 
        truedata = fetch_data(config, groupFilter, fields)

        dfb = pd.DataFrame(alldata)
        dfs = pd.DataFrame(truedata)

        # this IF statement is supposed to execute for every nested object in the data, not just survival_characteristics
        # tries to expand each col of the nested object in its own col. subject.survival_characteristics is a list of object of survival_characteristics type
        # so in short it flattens the nested object in the dataframe
        if 'survival_characteristics' in dfb.columns:
            df_c = dfb['survival_characteristics'].apply(pd.Series)
            df_c = df_c[0].apply(pd.Series)
            dfb = dfb.drop('survival_characteristics', axis='columns')
            dfb = pd.concat([dfb, df_c], axis=1)

            df_c = dfs['survival_characteristics'].apply(pd.Series)
            df_c = df_c[0].apply(pd.Series)
            dfs = dfs.drop('survival_characteristics', axis='columns')
            dfs = pd.concat([dfs, df_c], axis=1)

        res = get_table_result(dfs, dfb, args.get("covariates"), filter_sets[0])
        return res

    except Exception as e:
        # TODO replace this with a meaningful PcdcAnalysisTools.errors error 
        return {
            "message": "Error in selected filters or variables."
           }




def fetch_data(config, filters, fields):
    guppy_data = utils.guppy.downloadDataFromGuppy(
        path=config['GUPPY_API'] + "/download",
        type="subject",
        totalCount=100000,
        fields=fields,     # TODO - check it is a list
        filters=filters,
        sort=[],
        accessibility="accessible",
        config=config
    )

    
    return(guppy_data);

def get_table_result(query_data_true, dfb, fields, filterset):
    total = dfb.index.max()
    #response_headers = [{"size": 'Sample size (' + filterset.get("id")+ ')'}]
    true_number = int(query_data_true.index.nunique())
    varis = {}
    response_variables=[]

    for cov in fields:
        print(cov)
        varis[cov['name']] = []

    print(query_data_true.head())
    
    #  for each covariate, so for each row / variables it computes 
    # for continous should bucketize the response, and the buckets shoud come from the user input, not sure it is doing this
    for covariate in fields:
        if covariate["type"] == "continuous":
            true_mean = format((query_data_true[covariate['name']].mean())/int(covariate['unit']), '0.0f' )
            if len(varis[covariate['name']]) == 0:
                key = {"name" : "" , "data" : {f"true": true_mean}}
                varis[covariate['name']].append(key)
            else:
                varis[covariate['name']][0]['data'][f"true"] = true_mean

        if covariate["type"] == "categorical":
            cats = dict(zip(covariate["keys"], covariate["values"]))
            if len(varis[covariate['name']]) == 0:
                for k, v in cats.items():
                    cat_true = '{:.1%}'.format(
                        int(query_data_true.query(f"{covariate['name']} == '{v}' ").index.nunique()) / true_number)
                    key = {"name": k, "data": {f"true": cat_true}}
                    varis[covariate['name']].append(key)
            else:
                count = 0
                for k, v in cats.items():
                    cat_true = '{:.1%}'.format(
                        int(query_data_true.query(f"{covariate['name']} == '{v}' ").index.nunique()) / true_number)

                    varis[covariate['name']][count]['data'][f"true"] = cat_true
                    count += 1

    for k,v in varis.items():
        variable = {
                "name": k,
                "size": { "total": total ,"true" : true_number},
                "keys": v
        }
        response_variables.append(variable)
    
    res = {
        "variables": response_variables,
    }

    return res