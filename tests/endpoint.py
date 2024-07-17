
import pytest
from PcdcAnalysisTools.blueprint.routes.views import counts, survival
from PcdcAnalysisTools.api import app
import flask
import os
import json
import sys
from PcdcAnalysisTools.errors import NotFoundError

valid_consortiums = {
  'consortiumList': [
    'INSTRuCT',
    'MaGIC',
    'INRG',
    'NODAL',
    'INTERACT',
    'HIBISCUS',
    'ALL'
  ]
}

survival = {
  "efsFlag": False,
  "filterSets": [
    {
      "filters": {},
      "id": -1,
      "name": "1. *** All Subjects ***"
    }
  ],
  "usedFilterSetIds": [
    -1
  ],
  "explorerId": 1,
  "result": {
    "pval": False,
    "risktable": True,
    "survival": True
  }
}

stats = {
  "filter": {
    "AND": [
      {
        "IN": {
          "sex": [
            "Male"
          ]
        }
      }
    ]
  }
}



@pytest.fixture()
def app_setup():
    app.config.update({
        'TESTING': True,
    })
    yield app

@pytest.fixture()
def client(app_setup):
    return app.test_client()
    
@pytest.fixture()
def set_args():
    def this_args(args, base_args):
        pass
    return this_args


@pytest.fixture()
def set_data():
    def this_data(PATH):
        dir = os.path.dirname(__file__)
        print(dir)
        filename = os.path.join(dir, os.environ[PATH])
        os.environ['DATA_Path'] = filename
    return this_data

@pytest.fixture()
def counts_no_data(set_data):
    set_data('NO_DATA_PATH')
    return valid_consortiums
    

@pytest.fixture()
def counts_correct_data(set_data):
    set_data('SHORT_DATA_PATH')
    return valid_consortiums

@pytest.fixture()
def counts_incorrect_data(set_data):
    set_data('Short_DATA_PATH')
    return {'consortiumList': ['None']}


@pytest.fixture()
def survival_correct_data(set_data):
    set_data('Short_DATA_SURVIVAL_PATH')
    return survival

@pytest.fixture()
def survival_no_data(set_data):
    set_data('NO_DATA_PATH')
    return survival

@pytest.fixture()
def survival_incorrect_data(set_data):
    set_data('Short_DATA_SURVIVAL_PATH')
    return {}

@pytest.fixture()
def stats_no_data(set_data):
    set_data('NO_DATA_PATH')
    return stats

@pytest.fixture()
def stats_incorrect_data(set_data):
    set_data('Short_DATA_STATS_PATH')
    return {}

@pytest.fixture()
def stats_correct_data(set_data):
    set_data('Short_DATA_STATS_PATH')
    return survival

@pytest.fixture()
def external_correct_data(set_data):
    set_data('SHORT_DATA_EXTERNAL_PATH')
    return survival

def test_enviorment():
    assert app.mock_data == 'True'


def test_tools_route(client):
    response = client.get('/tools/')
    assert {'links':['aa','bb']} == response.json
    assert response.status_code == 200


def test_tools_counts_no_data(client, counts_no_data):
    response = client.post('/tools/counts', json=counts_no_data)
    assert [{"consortium":"total","molecular_analysis":0,"study":0,"subject":0},
    {"consortium":"INSTRuCT","molecular_analysis":0,"study":0,"subject":0},
    {"consortium":"MaGIC","molecular_analysis":0,"study":0,"subject":0},
    {"consortium":"INRG","molecular_analysis":0,"study":0,"subject":0},
    {"consortium":"NODAL","molecular_analysis":0,"study":0,"subject":0},
    {"consortium":"INTERACT","molecular_analysis":0,"study":0,"subject":0},
    {"consortium":"HIBISCUS","molecular_analysis":0,"study":0,"subject":0},
    {"consortium":"ALL","molecular_analysis":0,"study":0,"subject":0},
    {"consortium":"missing","molecular_analysis":0,"study":0,"subject":0}]  == response.json

def test_tools_counts_correct_data(client, counts_correct_data):
    response = client.post('/tools/counts', json=counts_correct_data)
    assert [{"consortium":"total","molecular_analysis":1,"study":0,"subject":3},
    {"consortium":"INSTRuCT","molecular_analysis":1,"study":0,"subject":1},
    {"consortium":"MaGIC","molecular_analysis":0,"study":0,"subject":1},
    {"consortium":"INRG","molecular_analysis":0,"study":0,"subject":0},
    {"consortium":"NODAL","molecular_analysis":0,"study":0,"subject":1},
    {"consortium":"INTERACT","molecular_analysis":0,"study":0,"subject":0},
    {"consortium":"HIBISCUS","molecular_analysis":0,"study":0,"subject":0},
    {"consortium":"ALL","molecular_analysis":0,"study":0,"subject":0},
    {"consortium":"missing","molecular_analysis":0,"study":0,"subject":0}] == response.json


def test_tools_counts_incorrect_data(client, counts_incorrect_data):
    response = client.post('/tools/counts', json=counts_incorrect_data)
    assert [{"consortium":"total","molecular_analysis":1,"study":0,"subject":3},
            {'consortium': 'None', 'molecular_analysis': 0, 'study': 0, 'subject': 0},
            {"consortium":"missing","molecular_analysis":0,"study":0,"subject":0}] == response.json


def test_tools_survival_no_data(client, survival_no_data):
    response = client.post('/tools/survival', json=survival_no_data)
    assert {
            "message": "The cohort selected has no survival_characteristics.lkss and/or no survival_characteristics.age_at_lkss. The curve can't be built without these necessary data points."
           } == response.json

def test_tools_survival_incorrect_data(client, survival_incorrect_data):
    with pytest.raises(TypeError) as ex:
        client.post('/tools/survival', json=survival_incorrect_data)
    assert '\'NoneType\' object is not iterable' in str(ex.value)


def test_tools_survival_correct_data(client, survival_correct_data):
    response = client.post('/tools/survival', json=survival_correct_data)
    assert {
            "-1": {
                "count": {
                    "fitted": 2,
                    "total": 2
                },
                "name": "1. *** All Subjects ***",
                "risktable": [
                    {
                        "nrisk": 2,
                        "time": 0.0
                    },
                    {
                        "nrisk": 0,
                        "time": 1.0
                    }
                    ],
                "survival": [
                    {
                        "prob": 1.0,
                        "time": 0.0
                    },
                    {
                        "prob": 1.0,
                        "time": 0.07939767282683094
                    },
                    {
                        "prob": 1.0,
                        "time": 0.24914442162902123
                    }
                    ]
                }
            } == response.json

def test_tools_stats_correct_data(client, stats_correct_data):
    response = client.post('/tools/stats/consortiums', json=stats_correct_data)
    assert ["NODAL"] == response.json

def test_tools_stats_no_data(client, stats_no_data):
    response = response = client.post('/tools/stats/consortiums', json=stats_no_data)
    assert [] == response.json

def test_tools_stats_incorrect_data(client, stats_no_data):
    response = client.post('/tools/stats/consortiums', json=stats_no_data)
    assert [] == response.json


def test_tools_external_correct_data(client, external_correct_data):
    response = client.post('/tools/external/other', json=external_correct_data)
    assert 'file' == response.json['type']
    assert None == response.json['link']
    assert 'subject_domestic_flickery,subject_fiscally_Godfrey,subject_ejection_perfrication,subject_leucosphere_prepenetrate,subject_misconstitutional_uprouse,subject_proreption_dermoskeleton,subject_lymphocystosis_ornithoscopist,subject_scrimmage_retroflexion,subject_mirthfulness_persecution,subject_pedatilobate_trebuchet' == response.json['data']

                         
