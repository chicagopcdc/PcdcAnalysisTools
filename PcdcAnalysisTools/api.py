import os
import sys

from flask import Flask, jsonify

# from authutils.oauth2 import client as oauth2_client
from authutils.oauth2.client import blueprint as oauth2_blueprint
from authutils import AuthError
from cdispyutils.log import get_handler
from cdispyutils.uwsgi import setup_user_harakiri
from indexclient.client import IndexClient
from gen3authz.client.arborist.client import ArboristClient


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

    tools_blueprint = PcdcAnalysisTools.create_blueprint("tools")

    v0 = "/v0"
    app.register_blueprint(tools_blueprint, url_prefix=v0 + "/tools")
    app.register_blueprint(tools_blueprint, url_prefix="/tools")
    app.register_blueprint(oauth2_blueprint.blueprint,
                           url_prefix=v0 + "/oauth2")
    app.register_blueprint(oauth2_blueprint.blueprint, url_prefix="/oauth2")


def app_init(app):
    # Register duplicates only at runtime
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

    app_register_blueprints(app)

    # exclude es init as it's not used yet
    # es_init(app)
    try:
        app.secret_key = app.config["FLASK_SECRET_KEY"]
    except KeyError:
        app.logger.error(
            "Secret key not set in config! Authentication will not work")

    # ARBORIST deprecated, replaced by ARBORIST_URL
    arborist_url = os.environ.get("ARBORIST_URL", os.environ.get("ARBORIST"))
    if arborist_url:
        app.auth = ArboristClient(arborist_base_url=arborist_url)
    else:
        app.logger.info("Using default Arborist base URL")
        app.auth = ArboristClient()


app = Flask(__name__)


# Setup logger
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


@app.errorhandler(404)
def page_not_found(e):
    return jsonify(message=e.description), e.code


@app.errorhandler(500)
def server_error(e):
    app.logger.exception(e)
    return jsonify(message="internal server error"), 500


def _log_and_jsonify_exception(e):
    """
    Log an exception and return the jsonified version along with the code.

    This is the error handling mechanism for ``APIErrors`` and
    ``AuthError``.
    """
    app.logger.exception(e)
    if hasattr(e, "json") and e.json:
        return jsonify(**e.json), e.code
    else:
        return jsonify(message=e.message), e.code


app.register_error_handler(APIError, _log_and_jsonify_exception)

app.register_error_handler(
    PcdcAnalysisTools.errors.APIError, _log_and_jsonify_exception)
app.register_error_handler(AuthError, _log_and_jsonify_exception)


def run_for_development(**kwargs):
    # app.logger.setLevel(logging.INFO)

    for key in ["http_proxy", "https_proxy"]:
        if os.environ.get(key):
            del os.environ[key]
    app.config.from_object("PcdcAnalysisTools.dev_settings")

    kwargs["port"] = app.config["SHEEPDOG_PORT"]
    kwargs["host"] = app.config["SHEEPDOG_HOST"]

    try:
        app_init(app)
    except Exception:
        app.logger.exception(
            "Couldn't initialize application, continuing anyway")
    app.run(**kwargs)
