#!/usr/bin/env python
from os import listdir
import sys
import devtools.wipe_dev
from src.global_config import logger


class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


if __name__ == "__main__":
    if not len(sys.argv) == 2:
        logger.info("Usage: run_script.py <script_name>")
        logger.info("Available scripts:")
        for script in listdir("scripts"):
            if script.endswith(".py"):
                logger.info("\t" + script[:-3])
        sys.exit(1)
    script_name = sys.argv[1]
    if script_name == "wipe_dev":
        devtools.wipe_dev.run()
    else:
        logger.info("Unknown script: {}".format(script_name))
        sys.exit(1)
