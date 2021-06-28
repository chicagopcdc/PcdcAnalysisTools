"""
Provide view functions for routes in the blueprint.
"""

import uuid

import flask
from flask import current_app
import requests

from PcdcAnalysisTools import auth, utils
from PcdcAnalysisTools.utils import parse
from PcdcAnalysisTools.blueprint.routes.views import program, survival, counts, external, stats
from PcdcAnalysisTools.errors import AuthError, NotFoundError, UserError
from PcdcAnalysisTools.globals import PROGRAM_SEED, ROLES

# @auth.require_sheepdog_program_admin


def get_programs():
    """
    Return the available resources at the top level above programs i.e.
    registered programs.

    Summary:
        Get the programs

    Tags:
        program

    Responses:
        200 (schema_links): Success
        403: Unauthorized request.

    :reqheader Content-Type: |reqheader_Content-Type|
    :reqheader Accept: |reqheader_Accept|
    :reqheader X-Auth-Token: |reqheader_X-Auth-Token|
    :resheader Content-Type: |resheader_Content-Type|

    **Example**

    .. code-block:: http

           GET /v0/submission/ HTTP/1.1
           Host: example.com
           Content-Type: application/json
           X-Auth-Token: MIIDKgYJKoZIhvcNAQcC...
           Accept: application/json

    .. code-block:: JavaScript

        {
            "links": [
                "/v0/sumission/CGCI/",
                "/v0/sumission/TARGET/",
                "/v0/sumission/TCGA/"
            ]
        }
    """
    # if flask.current_app.config.get("AUTH_SUBMISSION_LIST", True) is True:
    #     auth.validate_request(aud={"openid"}, purpose=None)

    return flask.jsonify({"links": ["aa", "bb"]})
