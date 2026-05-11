"""Service-specific error types."""

from cdiserrors import *

from PcdcAnalysisTools.globals import SUPPORTED_FORMATS


class UnsupportedError(UserError):
    def __init__(self, file_format, code=400, json=None):
        if json is None:
            json = {}
        message = "Format {} is not supported; supported formats are: {}.".format(
            file_format, ",".join(SUPPORTED_FORMATS)
        )
        super(UnsupportedError, self).__init__(message, code, json)


class NoIndexForFileError(UserError):
    def __init__(self, file_id):
        message = "Existing index is required for file creation. File id {} has no indexd record.".format(
            file_id
        )
        super(NoIndexForFileError, self).__init__(message, 400, {})


class UpstreamServiceError(APIError):
    def __init__(self, upstream, message="upstream service request failed", code=502, json=None):
        if json is None:
            json = {}
        details = {"upstream": upstream}
        details.update(json)
        super(UpstreamServiceError, self).__init__(message, code, details)


class HandledIntegrityError(Exception):
    pass







