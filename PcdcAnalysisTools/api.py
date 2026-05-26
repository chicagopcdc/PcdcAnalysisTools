import os
import sys
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv
from uuid import uuid4

from flask import Flask, jsonify, request

# from authutils.oauth2 import client as oauth2_client
from authutils.oauth2.client import blueprint as oauth2_blueprint
from authutils import AuthError
from cdispyutils.log import get_handler
from cdispyutils.uwsgi import setup_user_harakiri
from gen3authz.client.arborist.client import ArboristClient
from pcdcutils.environment import is_env_enabled
from pcdcutils.signature import SignatureManager

import PcdcAnalysisTools
from PcdcAnalysisTools.errors import (
    APIError,
    setup_default_handlers,
    UnhealthyCheck,
    NotFoundError,
    InternalError,
)
from PcdcAnalysisTools.version_data import VERSION, COMMIT

# recursion depth is increased for complex graph traversals
sys.setrecursionlimit(10000)
DEFAULT_ASYNC_WORKERS = 8


def app_register_blueprints(app):
    # TODO: (jsm) deprecate the index endpoints on the root path,
    # these are currently duplicated under /index (the ultimate
    # path) for migration

    app.url_map.strict_slashes = False

    v0 = "/v0"
    tools_blueprint = PcdcAnalysisTools.create_blueprint("tools")
    app.register_blueprint(tools_blueprint, url_prefix=v0 + "/tools")
    tools_blueprint.name += "_legacy"
    app.register_blueprint(tools_blueprint, url_prefix="/tools")
    app.register_blueprint(oauth2_blueprint.blueprint,
                           url_prefix=v0 + "/oauth2")
    oauth2_blueprint.blueprint.name += "_legacy"
    app.register_blueprint(oauth2_blueprint.blueprint, url_prefix="/oauth2")


def app_init(app):
    # Register duplicates only at runtime
    app.logger.setLevel(logging.INFO)
    app.logger.info("Initializing app")

    # explicit options set for compatibility with gdc's api
    app.config["AUTH_SUBMISSION_LIST"] = True
    app.config["USE_DBGAP"] = False
    app.config["IS_GDC"] = False

    # default settings
    app.config["REQUIRE_FILE_INDEX_EXISTS"] = (
        # If True, enforce indexd record exists before file node registration
        app.config.get("REQUIRE_FILE_INDEX_EXISTS", False)
    )
    if app.config.get("USE_USER_HARAKIRI", True):
        setup_user_harakiri(app)

    app.config["AUTH_NAMESPACE"] = "/" + \
        os.getenv("AUTH_NAMESPACE", "").strip("/")

    # data source for survival analysis
    app.config["IS_SURVIVAL_USING_GUPPY"] = True

    key_path = app.config.get("PRIVATE_KEY_PATH", None)
    app.config["RSA_PRIVATE_KEY"] = SignatureManager(key_path=key_path).get_key()
    if app.config["RSA_PRIVATE_KEY"] is None:
        app.logger.error(f"ERROR - PRIVATE KEY NOT LOADED! ('{key_path}')")
    # else:
    #     app.logger.info(f"Private key loaded. ('{key_path}')")

    # gapi = app.config['GUPPY_API']
    # app.logger.info(f"GUPPY_API hostname {gapi}")
    # sn = app.config['SERVICE_NAME']
    # app.logger.info(f"SERVICE_NAME: {sn}")
    app_register_blueprints(app)

    # exclude es init as it's not used yet
    # es_init(app)
    try:
        app.secret_key = app.config["FLASK_SECRET_KEY"]
    except KeyError:
        app.logger.error(
            "Secret key not set in config! Authentication will not work")

    app.config["cache"] = {}

    # ARBORIST deprecated, replaced by ARBORIST_URL
    arborist_url = os.environ.get("ARBORIST_URL", os.environ.get("ARBORIST"))
    if arborist_url:
        app.auth = ArboristClient(arborist_base_url=arborist_url)
    else:
        app.logger.info("Using default Arborist base URL")
        app.auth = ArboristClient()


app = Flask(__name__)
load_dotenv()
app.mock_data = os.environ.get("MOCK_DATA", False)
if app.mock_data == 'True':
    app_register_blueprints(app)
    app.config["cache"] = {}
# Setup logger
app.logger.setLevel(
    logging.DEBUG if is_env_enabled('GEN3_DEBUG') else logging.WARNING
)
app.logger.propagate = False
while app.logger.handlers:
    app.logger.removeHandler(app.logger.handlers[0])
app.logger.addHandler(get_handler())

setup_default_handlers(app)

@app.route("/_status", methods=["GET"])
def health_check():
    """
    Health check endpoint
    ---
    tags:
      - system
    responses:
      200:
        description: Healthy
      default:
        description: Unhealthy
    """

    return "Healthy", 200


@app.route("/_version", methods=["GET"])
def version():
    """
    Returns the version of PcdcAnalysisTools
    ---
    tags:
      - system
    responses:
      200:
        description: successful operation
    """
    base = {"version": VERSION, "commit": COMMIT}

    return jsonify(base), 200


def _get_request_id():
    request_id = request.headers.get("X-Request-Id")
    return request_id or str(uuid4())


def _error_response(status_code, message, error_type=None, details=None):
    payload = {
        "code": status_code,
        "message": message,
        "details": details or {},
        "request_id": _get_request_id(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if error_type:
        payload["error"] = error_type
    return jsonify(payload), status_code


@app.errorhandler(404)
def page_not_found(e):
    message = getattr(e, "description", "resource not found")
    return _error_response(
        404,
        message,
        error_type="NotFound",
        details={"path": request.path},
    )


@app.errorhandler(500)
def server_error(e):
    app.logger.exception("Unhandled server error")
    return _error_response(500, "internal server error", error_type="InternalServerError")


def _log_and_jsonify_exception(e):
    """
    Log an exception and return the jsonified version along with the code.

    This is the error handling mechanism for ``APIErrors`` and
    ``AuthError``.
    """
    app.logger.exception(
        "Handled API error (%s) request_id=%s",
        e.__class__.__name__,
        _get_request_id(),
    )
    status_code = int(getattr(e, "code", 500))
    message = getattr(e, "message", str(e))
    details = {}
    if hasattr(e, "json") and isinstance(e.json, dict):
        details = e.json

    return _error_response(
        status_code,
        message,
        error_type=e.__class__.__name__,
        details=details,
    )


def _log_and_jsonify_unhandled_exception(e):
    app.logger.exception(
        "Unhandled exception (%s) request_id=%s",
        e.__class__.__name__,
        _get_request_id(),
    )
    return _error_response(500, "internal server error", error_type="InternalServerError")


app.register_error_handler(APIError, _log_and_jsonify_exception)
app.register_error_handler(AuthError, _log_and_jsonify_exception)
app.register_error_handler(Exception, _log_and_jsonify_unhandled_exception)


def run_for_development(**kwargs):
    # app.logger.setLevel(logging.INFO)

    for key in ["http_proxy", "https_proxy"]:
        if os.environ.get(key):
            del os.environ[key]
    app.config.from_object("PcdcAnalysisTools.dev_settings")

    kwargs["port"] = app.config["SHEEPDOG_PORT"]
    kwargs["host"] = app.config["SHEEPDOG_HOST"]

    app_init(app)
    app.run(**kwargs)
