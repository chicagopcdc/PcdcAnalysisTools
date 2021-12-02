#!/usr/bin/env python

from authutils import ROLES as all_roles
from collections import defaultdict
from mock import patch, PropertyMock
from os import environ

import requests

from flask import current_app
# from psqlgraph import PolyNode as Node
from pcdcutils.environment import is_env_enabled
from PcdcAnalysisTools.api import run_for_development


requests.packages.urllib3.disable_warnings()

all_role_values = list(all_roles.values())
roles = defaultdict(lambda: all_role_values)


class FakeBotoKey(object):
    def __init__(self, name):
        self.name = name

    def close(self):
        pass

    def open_read(self, *args, **kwargs):
        pass

    @property
    def size(self):
        return len("fake data for {}".format(self.name))

    def __iter__(self):
        for string in ["fake ", "data ", "for ", self.name]:
            yield string


def fake_get_nodes(dids):
    nodes = []
    for did in dids:
        try:
            file_name = files.get(did, {})["data"]["file_name"]
        except ValueError:
            file_name = did
        nodes.append({}
            # Node(
            #     node_id=did,
            #     label="file",
            #     acl=["open"],
            #     properties={
            #         "file_name": file_name,
            #         "file_size": len("fake data for {}".format(did)),
            #         "md5sum": "fake_md5sum",
            #         "state": "live",
            #     },
            # )
        )
    return nodes


def fake_urls_from_index_client(did):
    return ["s3://fake-host/fake_bucket/{}".format(did)]


def fake_key_for(parsed):
    return FakeBotoKey(parsed.netloc.split("/")[-1])


def fake_key_for_node(node):
    return FakeBotoKey(node.node_id)


class FakeUser(object):
    username = "test"
    roles = roles


def set_user(*args, **kwargs):
    from flask import g

    g.user = FakeUser()


def run_with_fake_auth():
    def get_project_ids(role="_member_", project_ids=None):
        from gdcdatamodel import models as md

        if project_ids is None:
            project_ids = []
        if not project_ids:
            with current_app.db.session_scope():
                project_ids += [
                    "{}-{}".format(p.programs[0].name, p.code)
                    for p in current_app.db.nodes(md.Project).all()
                ]
        return project_ids

    with patch(
        "PcdcAnalysisTools.auth.FederatedUser.roles",
        new_callable=PropertyMock,
        return_value=roles,
    ), patch(
        "PcdcAnalysisTools.auth.FederatedUser.logged_in",
        new_callable=PropertyMock,
        return_value=lambda: True,
    ), patch(
        "PcdcAnalysisTools.auth.FederatedUser.get_project_ids",
        new_callable=PropertyMock,
        return_value=get_project_ids,
    ), patch(
        "PcdcAnalysisTools.auth.verify_hmac", new=set_user
    ):

        run_for_development(debug=debug, threaded=True)


def run_with_fake_authz():
    """
    Mocks arborist calls.
    """
    authorized = True  # modify this to mock authorized/unauthorized
    with patch(
        "gen3authz.client.arborist.client.ArboristClient.create_resource",
        new_callable=PropertyMock,
    ), patch(
        "gen3authz.client.arborist.client.ArboristClient.auth_request",
        new_callable=PropertyMock,
        return_value=lambda jwt, service, methods, resources: authorized,
    ):
        run_for_development(debug=debug, threaded=True)


def run_with_fake_download():
    with patch("PcdcAnalysisTools.download.get_nodes", fake_get_nodes):
        with patch.multiple(
            "PcdcAnalysisTools.download",
            key_for=fake_key_for,
            key_for_node=fake_key_for_node,
            urls_from_index_client=fake_urls_from_index_client,
        ):
            if is_env_enabled("GDC_FAKE_AUTH"):
                run_with_fake_auth()
            else:
                run_for_development(debug=debug, threaded=True)


if __name__ == "__main__":
    environ["GDC_FAKE_AUTH"] = "false"
    environ["GDC_FAKE_DOWNLOAD"] = "false"
    debug = is_env_enabled('SHEEPDOG_DEBUG')
    if is_env_enabled("GDC_FAKE_DOWNLOAD"):
        run_with_fake_download()
    else:
        if is_env_enabled("GDC_FAKE_AUTH"):
            run_with_fake_auth()
        else:
            run_with_fake_authz()
