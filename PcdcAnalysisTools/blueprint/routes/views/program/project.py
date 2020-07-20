# pylint: disable=protected-access
# pylint: disable=unsubscriptable-object
# pylint: disable=unsupported-membership-test
"""
View functions for routes in the blueprint for '/<program>/<project>' paths.
"""

import json

import flask
import yaml

from PcdcAnalysisTools import auth
from PcdcAnalysisTools import utils
from PcdcAnalysisTools.errors import AuthError, NotFoundError, UserError
from PcdcAnalysisTools.globals import PERMISSIONS, ROLES, STATES_COMITTABLE_DRY_RUN


# @utils.assert_project_exists


# @utils.assert_program_exists
# @auth.authorize_for_project(ROLES["READ"])

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
