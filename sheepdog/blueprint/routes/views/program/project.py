# pylint: disable=protected-access
# pylint: disable=unsubscriptable-object
# pylint: disable=unsupported-membership-test
"""
View functions for routes in the blueprint for '/<program>/<project>' paths.
"""

import json

import flask
import yaml

from sheepdog import auth
from sheepdog import utils
from sheepdog.errors import AuthError, NotFoundError, UserError
from sheepdog.globals import PERMISSIONS, ROLES, STATES_COMITTABLE_DRY_RUN


def create_viewer(method, bulk=False, dry_run=False):
    """
    Provide view functions for the following endpoints:

        /<program>/<project>
        /<program>/<project>/_dry_run
        /<program>/<project>/bulk
        /<program>/<project>/bulk/_dry_run

    for POST and PUT methods.

    The view function returned is for handling either a POST or PUT method and
    with ``dry_run`` being either True or False.
    """
    if method == "POST":
        auth_roles = [ROLES["CREATE"]]
        transaction_role = ROLES["CREATE"]
    elif method == "PUT":
        auth_roles = [ROLES["CREATE"], ROLES["UPDATE"]]
        transaction_role = ROLES["UPDATE"]
    else:
        # HCF
        raise RuntimeError("create_bulk_viewer: given invalid method")

    # @utils.assert_project_exists
    # @auth.authorize_for_project(*auth_roles)
    

# @utils.assert_project_exists


# @utils.assert_program_exists
# @auth.authorize_for_project(ROLES["READ"])


@auth.authorize_for_project(ROLES["READ"])
def export_entities(program, project):
    """
    Return a file with the requested entities as an attachment.

    Either ``ids`` or ``node_label`` must be provided in the parameters. When both are
    provided, ``node_label`` is ignored and ``ids`` is used.

    If ``ids`` is provided, all entities matching given ``ids`` will be exported. If
    there is only one entity type in the output, it will return a ``{node_type}.tsv`` or
    ``{node_type}.json`` file, e.g.: ``aliquot.tsv``. If there are multiple entity
    types, it returns ``gdc_export_{one_time_sha}.tar.gz`` for TSV format, or
    ``gdc_export_{one_time_sha}.json`` for JSON format. CSV is similar to TSV.

    If ``node_label`` is provided, it will export all entities of type with name
    ``node_label`` to a TSV file or JSON file. CSV is not supported yet in this case.

    Summary:
        Export entities

    Tags:
        export

    Args:
        program (str): |program_id|
        project (str): |project_id|

    Query Args:
        ids (str): one or a list of node IDs seperated by commas.
        node_label (str): type of nodes to look up, for example ``'case'``
        format (str): output format, ``json`` or ``tsv`` or ``csv``; default is ``tsv``
        with_children (str): whether to recursively find children or not; default is False
        category (str): category of node to filter on children. Example: ``clinical``
        without_id (bool): whether to include the ids in the export file; default is False

    Responses:
        200: Success
        400: Bad Request
        404: No id is found
        403: Unauthorized request.
    """
    try:
        import uwsgi
    except ImportError:
        # not in uWSGI, skip
        pass
    else:
        if hasattr(uwsgi, "set_user_harakiri"):
            # disable HARAKIRI because export is meant to take a long time
            uwsgi.set_user_harakiri(0)

    if flask.request.method == "GET":
        # Unpack multidict, or values will unnecessarily be lists.
        kwargs = {k: v for k, v in flask.request.args.items()}
    else:
        kwargs = utils.parse.parse_request_json()

    # Convert `format` argument to `file_format`.
    if "format" in kwargs:
        kwargs["file_format"] = kwargs["format"]
        del kwargs["format"]

    without_id = kwargs.get("without_id", "false").lower() == "true"

    node_label = kwargs.get("node_label")
    project_id = "{}-{}".format(program, project)
    file_format = kwargs.get("file_format") or "tsv"

    mimetype = (
        "application/json"
        if file_format.lower() == "json"
        else "application/octet-stream"
    )
    if not kwargs.get("ids"):
        if not node_label:
            raise UserError("expected either `ids` or `node_label` parameter")
        filename = "{}.{}".format(node_label, file_format)
        content_disp = "attachment; filename={}".format(filename)
        headers = {"Content-Disposition": content_disp}
        utils.transforms.graph_to_doc.validate_export_node(node_label)
        return flask.Response(
            flask.stream_with_context(
                utils.transforms.graph_to_doc.export_all(
                    node_label,
                    project_id,
                    file_format,
                    flask.current_app.db,
                    without_id,
                )
            ),
            mimetype=mimetype,
            headers=headers,
        )
    else:
        output = utils.transforms.graph_to_doc.ExportFile(
            program=program, project=project, **kwargs
        )
        content_disp = "attachment; filename={}".format(output.filename)
        headers = {"Content-Disposition": content_disp}
        return flask.Response(
            flask.stream_with_context(output.get_response()),
            mimetype=mimetype,
            headers=headers,
        )


def create_files_viewer(dry_run=False, reassign=False):
    """
    Create a view function for handling file operations.
    """
    auth_roles = [
        ROLES["CREATE"],
        ROLES["UPDATE"],
        ROLES["DELETE"],
        ROLES["DOWNLOAD"],
        ROLES["READ"],
    ]

    @utils.assert_project_exists
    @auth.authorize_for_project(*auth_roles)
    # admin only
    # TODO: check if we need these (pauline)
    @auth.require_sheepdog_program_admin
    @auth.require_sheepdog_project_admin
    def file_operations(program, project, file_uuid):
        """
        Handle molecular file operations.  This will only be available once the
        user has created a file entity with GDC id ``uuid`` via the
        ``/<program>/<project>/`` endppoint.

        This endpoint is an S3 compatible endpoint as described here:
        http://docs.aws.amazon.com/AmazonS3/latest/API/RESTObjectOps.html

        Supported operations:

        PUT /<program>/<project>/files/<uuid>
            Upload data using single PUT. The request body should contain
            binary data of the file

        PUT /internal/<program>/<project>/files/<uuid>/reassign
            Manually (re)assign the S3 url for a given node

        DELETE /<program>/<project>/files/<uuid>
            Delete molecular data from object storage.

        POST /<program>/<project>/files/<uuid>?uploads
            Initiate Multipart Upload.

        PUT /<program>/<project>/files/<uuid>?partNumber=PartNumber&uploadId=UploadId
            Upload Part.

        POST /<program>/<project>/files/<uuid>?uploadId=UploadId
            Complete Multipart Upload

        DELETE /<program>/<project>/files/<uuid>?uploadId=UploadId
            Abort Multipart Upload

        GET /<program>/<project>/files/<uuid>?uploadId=UploadId
            List Parts

        Tags:
            file

        Args:
            program (str): |program_id|
            project (str): |project_id|
            uuid (str): The GDC id of the file to upload.

        Responses:
            200: Success.
            400: Bad Request
            404: File not found.
            405: Method Not Allowed.
            403: Unauthorized request.

        :reqheader Content-Type: |reqheader_Content-Type|
        :reqheader Accept: |reqheader_Accept|
        :reqheader X-Auth-Token: |reqheader_X-Auth-Token|
        :resheader Content-Type: |resheader_Content-Type|
        """

        headers = {
            k: v for k, v in flask.request.headers.items() if v and k != "X-Auth-Token"
        }
        url = flask.request.url.split("?")
        args = url[-1] if len(url) > 1 else ""
        if flask.request.method == "GET":
            if flask.request.args.get("uploadId"):
                action = "list_parts"
            else:
                raise UserError("Method GET not allowed on file", code=405)
        elif flask.request.method == "POST":
            if flask.request.args.get("uploadId"):
                action = "complete_multipart"
            elif flask.request.args.get("uploads") is not None:
                action = "initiate_multipart"
            else:
                action = "upload"
        elif flask.request.method == "PUT":
            if reassign:
                action = "reassign"
            elif flask.request.args.get("partNumber"):
                action = "upload_part"
            else:
                action = "upload"
        elif flask.request.method == "DELETE":
            if flask.request.args.get("uploadId"):
                action = "abort_multipart"
            else:
                action = "delete"
        else:
            raise UserError("Unsupported file operation", code=405)

        project_id = program + "-" + project
        resp = utils.proxy_request(
            project_id,
            file_uuid,
            flask.request.stream,
            args,
            headers,
            flask.request.method,
            action,
            dry_run,
        )

        if dry_run or action == "reassign":
            return resp

        return flask.Response(
            resp.read(),
            status=resp.status,
            headers=resp.getheaders(),
            mimetype="text/xml",
        )

    return file_operations


@auth.authorize_for_project(ROLES["READ"])
def get_manifest(program, project):
    """
    Create a json manifest of the files.

    Summary:
        Get a manifest of data files

    Tags:
        file

    Args:
        program (str): |program_id|
        project (str): |project_id|

    Responses:
        200: Success
        400: User error.
        404: Resource not found.
        403: Unauthorized request.
    """
    id_string = flask.request.args.get("ids", "").strip()
    if not id_string:
        raise UserError(
            "No ids specified. Use query parameter 'ids', e.g." " 'ids=id1,id2'."
        )
    requested_ids = id_string.split(",")
    docs = utils.manifest.get_manifest(program, project, requested_ids)
    response = flask.make_response(
        yaml.safe_dump({"files": docs}, default_flow_style=False)
    )
    filename = "submission_manifest.yaml"
    response.headers["Content-Disposition"] = "attachment; filename={}".format(filename)
    return response
