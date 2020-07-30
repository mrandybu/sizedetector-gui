import configparser
from configparser import NoSectionError, NoOptionError

from argparse import ArgumentParser

import logging
import os

APPLICATION_NAME = 'Size Detector GUI'
LOGGER_NAME = ''.join(APPLICATION_NAME.split())

CONFIG_FILE_PATH = './config'
STRUCTURE_TEMPLATE = {
    'System': ['PManager', 'duPackage', 'duTimeout', 'genTimeout'],
    'Application': ['WinSize'],
}


class SizeDetectorCore:
    def __init__(self):
        self.logger = logging.getLogger(LOGGER_NAME)

    @staticmethod
    def get_cmd_params():
        parser = ArgumentParser("Size detector parameters")
        parser.add_argument('--config', required=True,
                            help='path to `Size detector` config file')
        parser.add_argument('--logging-path', help='write logs in specified path')

        subparsers = parser.add_subparsers()
        parser_shell = subparsers.add_parser('shell', help='run app without gui')
        parser_shell.add_argument('--path', required=True,
                                  help='path to directory for sizing')

        return parser.parse_args()

    def get_config_params(self):
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE_PATH)

        struct = {}
        for sec, opts in STRUCTURE_TEMPLATE.items():
            for opt in opts:
                try:
                    struct[opt.lower()] = config.get(sec, opt).lower()
                except (NoSectionError, NoOptionError) as err:
                    self.logger.debug(err.message)
                    return

        return struct

    def create_logger(self):
        app_logger = logging.getLogger(LOGGER_NAME)
        app_logger.setLevel(logging.DEBUG)

        log_path = None or self.get_cmd_params().logging_path
        if log_path is not None:
            fn = logging.FileHandler(
                os.path.join(log_path, LOGGER_NAME.lower() + '.log'))
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            fn.setFormatter(formatter)
            app_logger.addHandler(fn)
