#!/usr/bin/env python3
# -*- coding: iso8859-15 -*-
import os
import sys

appdir = os.path.abspath(os.path.dirname(__file__))
projdir = os.path.abspath(os.path.join(appdir, "../src"))
if projdir not in sys.path:
    sys.path.append(appdir)
    sys.path.append(projdir)

from src.mails.helpers.mail import generate_email_token_clients
import asyncio

if __name__ == "__main__":
        asyncio.run(generate_email_token_clients())
