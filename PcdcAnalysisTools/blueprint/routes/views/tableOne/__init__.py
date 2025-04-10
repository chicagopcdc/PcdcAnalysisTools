import json
import flask
import os

from flask import current_app as capp

from lifelines import KaplanMeierFitter
from PcdcAnalysisTools import utils
from PcdcAnalysisTools import auth
from PcdcAnalysisTools.errors import AuthError, NotFoundError, UnsupportedError, UserError

import pandas as pd


# @auth.authorize_for_analysis("access")
# def get_config():
#     config = capp.config.get("SURVIVAL", DEFAULT_SURVIVAL_CONFIG)
#     return flask.jsonify(config)
covarname = {
    "sex":"sex",
    "race":"race",
    "survival_characteristics.lkss":"lkss"
}

config = {};
allFilter = {
        'AND': 
        [{'IN': {'consortium': ['INSTRuCT']}}, {'AND': []}]
    }
def get_result():
    try:
        args = utils.parse.parse_request_json()
        if not args or not args.get("filterSets") or not args.get("covarFields"):
            return {
            "message": "No filter or variable selected."
           }

        filter_sets = json.loads(json.dumps(args.get("filterSets")))
        fields = json.loads(json.dumps(args.get("covarFields")))
        groupFilter = filter_sets[0].get("filters")

        alldata = fetch_data(config, allFilter, fields)  # 注意：你这里 allFilter 没定义
        truedata = fetch_data(config, groupFilter, fields)

        dfb = pd.DataFrame(alldata)
        dfs = pd.DataFrame(truedata)

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
        # print("Error in get_result:", e)
        return {
            "message": "Error in selected filters or variables."
           }




def fetch_data(config, filters, fields):
    guppy_data = utils.guppy.downloadDataFromGuppy(
        path=capp.config['GUPPY_API'] + "/download",
        type="subject",
        totalCount=100000,
        fields=fields,
        filters=filters,
        sort=[],
        accessibility="accessible",
        config=capp.config
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