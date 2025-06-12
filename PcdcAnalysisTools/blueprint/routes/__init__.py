"""
List routes to be added to the blueprint in ``PcdcAnalysisTools.blueprint``. Each
route is constructed with the ``new_route`` function from
``PcdcAnalysisTools.blueprint.routes.route_utils``.
"""

from PcdcAnalysisTools.blueprint.routes import views


def new_route(
    rule,
    view_func,
    endpoint=None,
    methods=None,
    options=None,
    swagger=None,
    schema=None,
):
    """
    Construct a dictionary representation of a URL rule to be added to the
    blueprint.

    The 'swagger' and 'schema' parameters are only used for generating the Swagger documentation.

    Args:
        rule (str): the path for the URL
        view_func (callable): function to render the page

    Keyword Args:
        endpoint (str): endpoint name (internal Flask usage)
        methods (list[str]): list of methods the rule should handle (GET, etc.)
        options (dict): options to pass as keyword args to ``add_url_rule``

    Return:
        dict: dictionary containing the above information for the route
    """
    if options is None:
        options = {}
    if methods is not None:
        options["methods"] = methods
    return {
        "rule": rule,
        "view_func": view_func,
        "endpoint": endpoint,
        "options": options,
        "swagger": swagger,
        # Swagger schema definitions (defined in openapi/definitions)
        "schema": schema,
    }


routes = [
    new_route("/", views.get_programs, methods=["GET"]),
    new_route(
        "/survival",
        views.survival.get_result,
        endpoint="survival",
        methods=["POST"],
    ),
    new_route(
        "/survival/config",
        views.survival.get_config,
        endpoint="survival/config",
        methods=["GET"],
    ),
    new_route(
        "/counts",
        views.counts.get_result,
        endpoint="counts",
        methods=["POST"],
    ),
    new_route(
        "/counts/invalidate",
        views.counts.reset_count_cache,
        endpoint="/counts/invalidate",
        methods=["GET"],
    ),
    new_route(
        "/external/<common>",
        views.external.get_info,
        # endpoint="external",
        methods=["POST"],
    ),
    new_route(
        "/external/config",
        views.external.get_config,
        endpoint="external/config",
        methods=["GET"],
    ),
    new_route(
        "/stats/consortiums",
        views.stats.get_consortiums,
        endpoint="stats/consortiums",
        methods=["POST"],
    ),
    new_route(
        "/tableone",
        views.tableOne.get_result,
        endpoint="tableone",
        methods=["POST"],
    ),
    new_route(
        "/tableone/config",
        views.tableOne.get_config,
        endpoint="tableone/config",
        methods=["GET"],
    ),


    # new_route("/<program>", views.program.delete_program, methods=["DELETE"]),
    # new_route(
    #     "/<program>/<project>/manifest",
    #     views.program.project.get_manifest,
    #     methods=["GET"],
    # ),
    # new_route(
    #     "/<program>/<project>/review",
    #     views.program.project.create_review_project_viewer(),
    #     endpoint="review_project",
    #     methods=["PUT", "POST"],
    # ),
]
