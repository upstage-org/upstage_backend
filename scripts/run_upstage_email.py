#!/usr/bin/env python3
# -*- coding: iso8859-15 -*-
import os
import sys

from upstage_backend.mails.helpers.mail import generate_email_token_clients
import asyncio

if __name__ == "__main__":
        asyncio.run(generate_email_token_clients())
