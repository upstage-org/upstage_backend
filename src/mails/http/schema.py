# -*- coding: iso8859-15 -*-
import os
import sys

appdir = os.path.abspath(os.path.dirname(__file__))
projdir = os.path.abspath(os.path.join(appdir, ".."))
projdir2 = os.path.abspath(os.path.join(appdir, "../.."))
if projdir not in sys.path:
    sys.path.append(appdir)
    sys.path.append(projdir)
    sys.path.append(projdir2)

from ariadne import MutationType, QueryType, make_executable_schema
from graphql import GraphQLError
from studio_management.http.graphql import type_defs
from ariadne.asgi import GraphQL

from mails.helpers.mail import create_email, send_async, valid_token

query = QueryType()
mutation = MutationType()


@mutation.field("sendEmailExternal")
async def send_email_external(_, info, emailInfo):
    request = info.context["request"]
    token = request.headers.get("X-Email-Token")
    if not token:
        raise GraphQLError("Missing X-Email-Token header")

    try:
        if not valid_token(token):
            raise GraphQLError("Invalid X-Email-Token")
    except:
        raise GraphQLError("Invalid X-Email-Token")

    msg = create_email(
        to=emailInfo["recipients"],
        subject=emailInfo["subject"],
        html=emailInfo["body"],
        cc=emailInfo["cc"],
        bcc=emailInfo["bcc"],
        filenames=emailInfo["filenames"],
        external=True,
    )

    await send_async(msg=msg)
    return {"success": True}


schema = make_executable_schema(type_defs, query, mutation)
mail_graphql_app = GraphQL(schema, debug=True)
