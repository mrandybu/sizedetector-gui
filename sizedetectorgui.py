from subprocess import Popen, PIPE
from subprocess import TimeoutExpired

from sizedetector_core import SizeDetectorCore

import os
import psutil

import logging

logger = logging.getLogger()

APPLICATION_NAME = 'Size Detector GUI'
WIDTH, HEIGHT = 400, 500


class SizeDetector:
    def __init__(self, directory):
        self.directory = directory
        self.struct = SizeDetectorCore.get_config_params()

    def _kill_process(self, proc, name):
        timeout = int(self.struct['gentimeout'])
        pid = proc.pid

        proc.terminate()
        try:
            proc.wait(timeout)
        except TimeoutExpired:
            logger.debug("Termination process timeout (pid: {}; name: {})"
                         .format(pid, name))

        if not psutil.pid_exists(pid):
            return

        p = psutil.Process(pid)
        p.terminate()
        if psutil.pid_exists(pid):
            proc = Popen(['pkill', name], stderr=PIPE, stdout=PIPE)
            try:
                proc.wait(timeout)
            except TimeoutExpired:
                logger.debug("Killing process timeout (pid: {}; name: {})"
                             .format(pid, name))
                return

    def detect_size(self):
        if not os.path.exists(self.directory):
            return False, "`{}` directory does not exist!".format(self.directory)

        du_bin, du_params = 'du', '-h --max-depth=1'

        shell = [du_bin] + du_params.split() + [self.directory]
        try:
            child = Popen(shell, stderr=PIPE, stdout=PIPE)
        except FileNotFoundError as e:
            logger.debug("Command `{}` failed: {}".format(shell, e.strerror))
            return False, "Runtime error. For detailed information see log file."

        timeout = int(self.struct['dutimeout'])
        try:
            child.wait(timeout)
        except TimeoutExpired:
            logger.debug("Command execution timeout `{}`".format(shell))
            self._kill_process(child, du_bin)
            return False, "Timeout. Very large size. You can increase the " \
                          "timeout in the config file."

        out, err = child.communicate()
        if err:
            if os.getuid() != 0:
                message = "Please, try with root access.."
            else:
                logger.debug(
                    "Command `{}` failed: {}".format(shell, err.decode()))
                message = "Runtime error. For detailed information see log file."
            return False, message

        return True, out.decode().split('\n')
