"""
View functions for routes in the blueprint for '/<program>' paths.
"""

import json
import uuid

import flask

from PcdcAnalysisTools import auth
from PcdcAnalysisTools import utils
from PcdcAnalysisTools.blueprint.routes.views.program import project
from PcdcAnalysisTools.errors import APINotImplemented, AuthError, NotFoundError, UserError
from PcdcAnalysisTools.globals import PERMISSIONS, PROJECT_SEED, ROLES, STATES_COMITTABLE_DRY_RUN


