"""
Defines the PcdcAnalysisTools blueprint.
"""

import flask

from PcdcAnalysisTools import sanity_checks


def create_blueprint(name):
    """
    Create the blueprint.

    Args:
        name: blueprint name

    Return:
        flask.Blueprint: the PcdcAnalysisTools blueprint
    """
    sanity_checks.validate()

    blueprint = flask.Blueprint(name, __name__)

    # Add all the routes defined in PcdcAnalysisTools.blueprint.routes to the new
    # blueprint.
    from PcdcAnalysisTools.blueprint.routes import routes

    for route in routes:
        blueprint.add_url_rule(
            route["rule"],
            endpoint=route["endpoint"],
            view_func=route["view_func"],
            **route["options"]
        )

    return blueprint
