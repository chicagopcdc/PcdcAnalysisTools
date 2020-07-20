"""
View functions for routes in the blueprint for '/<program>' paths.
"""

import json
import uuid

import flask

from sheepdog import auth
from sheepdog import utils
from sheepdog.blueprint.routes.views.program import project
from sheepdog.errors import APINotImplemented, AuthError, NotFoundError, UserError
from sheepdog.globals import PERMISSIONS, PROJECT_SEED, ROLES, STATES_COMITTABLE_DRY_RUN


