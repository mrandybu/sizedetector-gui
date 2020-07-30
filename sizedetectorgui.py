from subprocess import Popen, PIPE
from subprocess import TimeoutExpired

from sizedetector_core import SizeDetectorCore
from sizedetector_core import APPLICATION_NAME, LOGGER_NAME

import sys
import os
import psutil

import logging

from PySide2.QtWidgets import (QApplication, QLabel, QPushButton,
                               QVBoxLayout, QWidget, QLineEdit, QTableWidget,
                               QTableWidgetItem, QHeaderView)
from PySide2.QtCore import Qt
from PySide2 import QtGui

WIDTH, HEIGHT = 400, 500


class SizeDetector:
    def __init__(self, directory):
        self.directory = directory

        self.struct = SizeDetectorCore().get_config_params()
        self.cmd_args = SizeDetectorCore.get_cmd_params()

        self.logger = logging.getLogger(LOGGER_NAME)

    def _kill_process(self, proc, name):
        timeout = int(self.struct['gentimeout'])
        pid = proc.pid

        proc.terminate()
        try:
            proc.wait(timeout)
        except TimeoutExpired:
            self.logger.debug("Termination process timeout (pid: {}; name: {})"
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
                self.logger.debug("Killing process timeout (pid: {}; name: {})"
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
            self.logger.debug("Command `{}` failed: {}".format(shell, e.strerror))
            return False, "Runtime error. For detailed information see log file."

        timeout = int(self.struct['dutimeout'])
        try:
            child.wait(timeout)
        except TimeoutExpired:
            self.logger.debug("Command execution timeout `{}`".format(shell))
            self._kill_process(child, du_bin)
            return False, "Timeout. Very large size. You can increase the " \
                          "timeout in the config file."

        out, err = child.communicate()
        if err:
            if os.getuid() != 0:
                message = "Please, try with root access.."
            else:
                self.logger.debug(
                    "Command `{}` failed: {}".format(shell, err.decode()))
                message = "Runtime error. For detailed information see log file."
            return False, message

        return True, out.decode().split('\n')


class SizeDetectorGUI(QWidget):
    EXIT_CODE_REBOOT = -123
    PREVIOUS_GEOMETRY = None

    def __init__(self):
        QWidget.__init__(self)

        self.app_initialize = False

        self.logger = logging.getLogger(LOGGER_NAME)

        self.struct = SizeDetectorCore().get_config_params()
        self.cmd_args = SizeDetectorCore.get_cmd_params()

        self.gs_button = QPushButton(text="Detect Size!")
        self.ref_button = QPushButton(text="Refresh")

        self.inf_label = QLabel("Enter directory for sizing:")
        self.inf_label.setAlignment(Qt.AlignLeft)

        self.inp_line = QLineEdit("/")

        self.res_table = QTableWidget()
        self.res_table.setColumnCount(2)
        self.res_table.setHorizontalHeaderItem(0, QTableWidgetItem("size"))
        self.res_table.setHorizontalHeaderItem(1, QTableWidgetItem("file"))

        header = self.res_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.inf_label)
        self.layout.addWidget(self.inp_line)
        self.layout.addWidget(self.gs_button)
        self.layout.addWidget(self.res_table)
        self.layout.addWidget(self.ref_button)

        self.setLayout(self.layout)

        self.gs_button.clicked.connect(self.run_detecting)
        self.ref_button.clicked.connect(self.__refresh)

        self.__initialize()

    def __initialize(self):
        if self.struct is None:
            self._disable_form()
            self._set_info_message("Invalid or missing config file.\n"
                                   "For detailed information see log file")
            return

        if self.struct['pmanager'] != 'rpm':
            self._disable_form()
            self._set_info_message("Unsupported package manager {}"
                                   "".format(self.struct['pmanager']))
            return

        shell = 'rpm -qa {}'.format(self.struct['dupackage'])
        try:
            proc = Popen(shell.split(), stdout=PIPE, stderr=PIPE)
        except FileNotFoundError as e:
            self.logger.debug("Command `{}` failed: {}".format(shell, e.strerror))
            self._set_info_message(
                "Runtime error. For detailed information see log file.")
            return

        out, err = proc.communicate()

        if err:
            self.logger.debug(
                "Command `{}` failed: {}".format(shell, err.decode()))
            self._set_info_message(
                "Runtime error. For detailed information see log file.")
            return

        if not out:
            self._disable_form()
            self._set_info_message("No package `{}` found on the system"
                                   .format(self.struct['dupackage']))
            return

        self.app_initialize = True

    def run_detecting(self):
        self.inf_label.setText("Enter directory for sizing:")
        dir_ = self.inp_line.text()
        if dir_[-1] != '/':
            dir_ += '/'

        sd = SizeDetector(dir_)
        status, retval = sd.detect_size()
        if status is False:
            self._set_info_message(retval)
            return

        self.res_table.setRowCount(len(retval) - 1)

        count = 0
        for line in retval:
            if line:
                line = line.split()
                self.res_table.setItem(count, 0, QTableWidgetItem(line[0]))
                dir_name = line[1].replace(dir_, '')
                if len(retval) - 2 == count:
                    dir_name = '* Summary size *'
                self.res_table.setItem(count, 1, QTableWidgetItem(dir_name))
                count += 1

    def _set_info_message(self, message):
        self.inf_label.setText(message)

    def _disable_form(self):
        self.inp_line.setDisabled(True)
        self.gs_button.setDisabled(True)
        self.ref_button.setFocus()

    def __refresh(self):
        SizeDetectorGUI.PREVIOUS_GEOMETRY = self.geometry()
        QtGui.qApp.exit(SizeDetectorGUI.EXIT_CODE_REBOOT)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setApplicationDisplayName(APPLICATION_NAME)

    SizeDetectorCore().create_logger()

    current_exit_code = SizeDetectorGUI.EXIT_CODE_REBOOT
    while current_exit_code == SizeDetectorGUI.EXIT_CODE_REBOOT:
        widget = SizeDetectorGUI()
        if widget.app_initialize:
            win_size = widget.struct['winsize'].split(',')
            WIDTH = int(win_size[0].replace(' ', ''))
            HEIGHT = int(win_size[1].replace(' ', ''))
        widget.resize(WIDTH, HEIGHT)
        if widget.PREVIOUS_GEOMETRY:
            widget.setGeometry(widget.PREVIOUS_GEOMETRY)

        widget.show()
        current_exit_code = app.exec_()
