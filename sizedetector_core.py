import configparser
from configparser import NoSectionError, NoOptionError

from argparse import ArgumentParser

import logging

logger = logging.getLogger()

CONFIG_FILE_PATH = './config'
STRUCTURE_TEMPLATE = {
    'System': ['PManager', 'duPackage', 'duTimeout', 'genTimeout'],
    'Application': ['WinSize'],
}


class SizeDetectorCore:
    def __init__(self):
        pass

    @staticmethod
    def get_cmd_params():
        parser = ArgumentParser("Size detector parameters")
        parser.add_argument('--config', required=True,
                            help='path to `Size detector` config file')

        subparsers = parser.add_subparsers()
        parser_shell = subparsers.add_parser('shell', help='run app without gui')
        parser_shell.add_argument('--path', required=True,
                                  help='path to directory for sizing')

        return parser.parse_args()

    @staticmethod
    def get_config_params():
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE_PATH)

        struct = {}
        for sec, opts in STRUCTURE_TEMPLATE.items():
            for opt in opts:
                try:
                    struct[opt.lower()] = config.get(sec, opt).lower()
                except (NoSectionError, NoOptionError) as err:
                    logger.debug(err.message)
                    return

        return struct
