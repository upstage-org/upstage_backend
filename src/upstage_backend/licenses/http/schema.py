# -*- coding: iso8859-15 -*-
import os
import sys

from ariadne import MutationType, QueryType, make_executable_schema
from upstage_backend.studio_management.http.graphql import type_defs
from ariadne.asgi import GraphQL
from upstage_backend.licenses.http.validation import LicenseInput
from upstage_backend.licenses.services.license import LicenseService

mutation = MutationType()
query = QueryType()


@mutation.field("createLicense")
def create_license(_, __, input):
    return LicenseService().create_license(LicenseInput(**input))


@mutation.field("revokeLicense")
def revoke_license(_, __, id: int):
    return LicenseService().revoke_license(id)


schema = make_executable_schema(type_defs, query, mutation)
license_graphql_app = GraphQL(schema, debug=True)
