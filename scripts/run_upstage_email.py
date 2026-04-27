#!/usr/bin/env python3
# -*- coding: iso8859-15 -*-
import os
import sys

import loguru  # noqa: F401  # entrypoint: load loguru before upstage (see app_containers compose)
import asyncio

from upstage_backend.mails.helpers.mail import generate_email_token_clients

if __name__ == "__main__":
        asyncio.run(generate_email_token_clients())
