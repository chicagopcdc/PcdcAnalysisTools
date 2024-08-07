"""
This module will depend on the downstream authutils dependency.

eg:
``pip install git+https://git@github.com/NCI-GDC/authutils.git@1.2.3#egg=authutils``
or
``pip install git+https://git@github.com/uc-cdis/authutils.git@1.2.3#egg=authutils``
"""

import functools

from authutils.user import current_user
from authutils.token.validate import current_token
from cdislogging import get_logger
import flask

from PcdcAnalysisTools.errors import AuthNError, AuthZError


logger = get_logger(__name__)

try:
    from authutils.token.validate import validate_request
except ImportError:
    logger.warning(
        "Unable to import authutils validate_request. PcdcAnalysisTools will error if config AUTH_SUBMISSION_LIST is set to "
        "True (note that it is True by default) "
    )

def get_current_user():
    return current_user

def get_jwt_from_header():
    jwt = None
    auth_header = flask.request.headers.get("Authorization")
    if auth_header:
        items = auth_header.split(" ")
        if len(items) == 2 and items[0].lower() == "bearer":
            jwt = items[1]
    if not jwt:
        raise AuthNError("Didn't receive JWT correctly")
    return jwt


def authorize_for_analysis(*required_roles):
    """
    Wrap a function to allow access to the handler iff the user has at least
    one of the roles requested on the given project.
    """

    def wrapper(func):
        @functools.wraps(func)
        def authorize_and_call(*args, **kwargs):
            resource = "/analysis"
            if flask.current_app.mock_data == 'True':
                return func(*args, **kwargs)
            else:
                jwt = get_jwt_from_header()
                authz = flask.current_app.auth.auth_request(
                    jwt=jwt,
                    service="analysis",
                    methods="access",
                    resources=[resource],
                )
                if not authz:
                    raise AuthZError("user is unauthorized")
                return func(*args, **kwargs)

        return authorize_and_call

    return wrapper


def authorize_for(resource, method):
    """
    Wrap a function to allow access to the handler iff the user has at least
    one of the roles requested on the given project.
    """

    def wrapper(func):
        @functools.wraps(func)
        def authorize_and_call(*args, **kwargs):
            jwt = get_jwt_from_header()
            authz = flask.current_app.auth.auth_request(
                jwt=jwt,
                service="analysis",
                methods=method,
                resources=[resource],
            )
            if not authz:
                raise AuthZError("user is unauthorized")
            return func(*args, **kwargs)

        return authorize_and_call

    return wrapper




def authorize_for_project(*required_roles):
    """
    Wrap a function to allow access to the handler iff the user has at least
    one of the roles requested on the given project.
    """

    def wrapper(func):
        @functools.wraps(func)
        def authorize_and_call(program, project, *args, **kwargs):
            resource = "/programs/{}/projects/{}".format(program, project)
            jwt = get_jwt_from_header()
            authz = flask.current_app.auth.auth_request(
                jwt=jwt,
                service="PcdcAnalysisTools",
                methods=required_roles,
                resources=[resource],
            )
            if not authz:
                raise AuthZError("user is unauthorized")
            return func(program, project, *args, **kwargs)

        return authorize_and_call

    return wrapper


def require_sheepdog_program_admin(func):
    """
    Wrap a function to allow access to the handler if the user has access to
    the resource /services/sheepdog/submission/program (Sheepdog program admin)
    """

    @functools.wraps(func)
    def authorize_and_call(*args, **kwargs):
        jwt = get_jwt_from_header()
        authz = flask.current_app.auth.auth_request(
            jwt=jwt,
            service="PcdcAnalysisTools",
            methods="*",
            resources=["/services/sheepdog/submission/program"],
        )
        if not authz:
            raise AuthZError("Unauthorized: User must be Sheepdog program admin")
        return func(*args, **kwargs)

    return authorize_and_call


def require_sheepdog_project_admin(func):
    """
    Wrap a function to allow access to the handler if the user has access to
    the resource /services/sheepdog/submission/project (Sheepdog project admin)
    """

    @functools.wraps(func)
    def authorize_and_call(*args, **kwargs):
        jwt = get_jwt_from_header()
        authz = flask.current_app.auth.auth_request(
            jwt=jwt,
            service="PcdcAnalysisTools",
            methods="*",
            resources=["/services/sheepdog/submission/project"],
        )
        if not authz:
            raise AuthZError("Unauthorized: User must be Sheepdog project admin")
        return func(*args, **kwargs)

    return authorize_and_call


def authorize(program, project, roles):
    resource = "/programs/{}/projects/{}".format(program, project)
    jwt = get_jwt_from_header()
    authz = flask.current_app.auth.auth_request(
        jwt=jwt, service="sheepdog", methods=roles, resources=[resource]
    )
    if not authz:
        raise AuthZError("user is unauthorized")


def create_resource(program, project=None):
    resource = "/programs/{}".format(program)
    if project:
        resource += "/projects/{}".format(project)
    logger.info("Creating arborist resource {}".format(resource))

    json_data = {
        "name": resource,
        "description": "Created by sheepdog",  # TODO use authz provider field
    }
    resp = flask.current_app.auth.create_resource(
        parent_path="", resource_json=json_data, create_parents=True
    )
    if resp and resp.get("error"):
        logger.error(
            "Unable to create resource: code {} - {}".format(
                resp.error.code, resp.error.message
            )
        )
