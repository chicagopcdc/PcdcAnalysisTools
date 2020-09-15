POST http://localhost/analysis/tools/survival_curve

Authorization Bearer ...

Template for payload:

`
{
	"patientSearchCriteria": {
		"query":"query ($filter: JSON) {\n    subject (accessibility: accessible, offset: 0, first: 20, filter: $filter) { \n      \n    _subject_id\n    \n\n    age_at_enrolment\n    \n\n    auth_resource_path\n    \n\n    enrolled_status\n    \n\n    node_id\n    \n\n    person_submitter_id\n    \n\n    project_id\n    \n\n    study_phase\n    \n\n    study_type\n    \n\n    submitter_id\n    \n\n    year_at_enrolment\n    \n    }\n    _aggregation {\n      subject (filter: $filter, accessibility: accessible) { \n        _totalCount\n      }\n    }\n  }",
        "variables":{
            "filter":{
                "AND":[
                    {
                        "IN":{
                            "submitter_id":["sub_id_1"]
                        }
                    }
                ]
            }
        }
	},
    "fields": ["person_submitter_id", "submitter_id"],
	"factorVariable": ["sex"],
	"stratificationVariable": ["ethnicity"],
	"efsFlag": false,
	"start_time": 0,
	"end_time": 10,
	"time_unit": "year",
	"userName": null
}
`