# -*- coding: iso8859-15 -*-
import os
import sys

from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
import re
import ssl
import aiosmtplib

from upstage_backend.global_config import ScopedSession
from upstage_backend.global_config.env import (
    DOMAIN,
    EMAIL_HOST,
    EMAIL_HOST_DISPLAY_NAME,
    EMAIL_HOST_PASSWORD,
    EMAIL_HOST_FROM,
    EMAIL_HOST_LOGIN,
    EMAIL_PORT,
    EMAIL_USE_TLS,
    SUPPORT_EMAILS,
)
from upstage_backend.upstage_options.db_models.config import ConfigModel


async def send(to, subject, content, bcc=[], cc=[], filenames=[]):
    msg = create_email(
        to=to, subject=subject, html=content, cc=cc, bcc=bcc, filenames=filenames
    )
    await send_async(msg=msg)


async def send_async(msg, user=EMAIL_HOST_LOGIN, password=EMAIL_HOST_PASSWORD):
    """
    Send via SMTP. Port 465 uses implicit TLS; other ports use STARTTLS when
    EMAIL_USE_TLS is true (typical for 587 + external providers).
    """
    if not EMAIL_HOST:
        raise RuntimeError("EMAIL_HOST is not configured")

    host = EMAIL_HOST
    port = int(EMAIL_PORT)
    tls_context = ssl.create_default_context()
    implicit_tls = port == 465

    smtp = aiosmtplib.SMTP(
        hostname=host,
        port=port,
        use_tls=implicit_tls,
        tls_context=tls_context if implicit_tls else None,
    )
    await smtp.connect()
    if not implicit_tls and EMAIL_USE_TLS:
        await smtp.starttls(tls_context)
    if user:
        await smtp.login(user, password)
    await smtp.send_message(msg)
    await smtp.quit()


def create_email(
    to,
    subject,
    html,
    filenames=[],
    cc=[],
    bcc=[],
    sender=EMAIL_HOST_FROM,
):
    """
    Create an email
    """
    msg = MIMEMultipart("fixed")
    with ScopedSession() as local_db_session:
        subject_prefix = (
            local_db_session.query(ConfigModel)
            .filter(ConfigModel.name == "EMAIL_SUBJECT_PREFIX")
            .first()
        )
        if subject_prefix:
            subject = f"{subject_prefix.value}: {subject}"
    msg.preamble = subject

    # Remove empty strings. Not sure how they get here.
    # Remove support admins if they've been listed as recipients.
    # They are implicitly added to all emails. No need to add them again.

    if type(to) != list:
        to = [to]

    if type(cc) != list:
        cc = [cc]

    if type(bcc) != list:
        bcc = [bcc]

    if len(to) == 1:
        if to[0] in ("", None):
            to = []
    else:
        to = [x for x in to if x not in ("", None) and len(to) > 1]

    if len(cc) == 1:
        if cc[0] in ("", None):
            cc = []
    else:
        cc = [x for x in cc if x not in ("", None) and len(cc) > 1]

    if len(bcc) == 1:
        if bcc[0] in ("", None):
            bcc = []
    else:
        bcc = [x for x in bcc if x not in ("", None) and len(bcc) > 1]

    if subject != "Welcome to UpStage!":
        if to and SUPPORT_EMAILS:
            to = list(set(to).difference(set(SUPPORT_EMAILS)))
        if cc and SUPPORT_EMAILS:
            cc = list(set(cc).difference(set(SUPPORT_EMAILS)))
        if bcc and SUPPORT_EMAILS:
            bcc = list(set(bcc).difference(set(SUPPORT_EMAILS)))

        if bcc:
            if SUPPORT_EMAILS:
                msg["Bcc"] = ", ".join(SUPPORT_EMAILS) + "," + ", ".join(bcc)
        else:
            if SUPPORT_EMAILS:
                msg["Bcc"] = ", ".join(SUPPORT_EMAILS)

    else:
        cc = []
        bcc = []

    msg["Subject"] = subject
    msg["message-id"] = make_msgid(domain=DOMAIN)
    msg["Date"] = formatdate(localtime=True)
    msg["From"] = f"{EMAIL_HOST_DISPLAY_NAME} <{sender}>"
    msg["To"] = ", ".join(to) if to else ""
    msg["Cc"] = ", ".join(cc) if cc else ""
    """
    Multipart message prep. Send both plain text and html, to ensure
    that it can be read.
    """
    msg_alternative = MIMEMultipart("alternative")
    msg_alternative.attach(MIMEText(remove_html(html), "plain", "latin-1"))
    msg_alternative.attach(MIMEText(html, "html", "latin-1"))
    """
    Attach plain and HTML variations of the body to main message content.
    """
    msg.attach(msg_alternative)
    """
    If files exists, attach them to the main message content.
    """
    for filename in filenames:
        with open(filename, "rb") as fp:
            part3 = MIMEApplication(fp.read())
            part3["Content-ID"] = "<{}>".format(os.path.basename(filename))
            part3["Content-Description"] = os.path.basename(filename)
            part3["Content-Disposition"] = 'attachment; filename = "{}"'.format(
                os.path.basename(filename)
            )
            msg.attach(part3)
            msg["X-MS-Has-Attach"] = "Yes"

    return msg


def remove_html(raw_html):
    cleanr = re.compile("<.*?>")
    cleantext = re.sub(cleanr, "", raw_html)
    return cleantext

'''
if __name__ == '__main__':
    import asyncio
    asyncio.run(send(to='some_email_address', subject='testing smtp', content='test', bcc=[], cc=[], filenames=[]))
'''
