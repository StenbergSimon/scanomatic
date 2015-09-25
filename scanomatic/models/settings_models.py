__author__ = 'martin'

import scanomatic.generics.model as model
from scanomatic.io.power_manager import POWER_MANAGER_TYPE, POWER_MODES
import os


class VersionChangesModel(model.Model):

    def __init__(self, **kwargs):

        self.first_pass_change_1 = 0.997
        self.fixture_grid_history_change_1 = 0.998
        self.oldest_allow_fixture = 0.9991

        super(VersionChangesModel, self).__init__()


class PowerManagerModel(model.Model):

    def __init__(self, type=POWER_MANAGER_TYPE.notInstalled, number_of_sockets=4,
                 host="192.168.0.100", password="", verify_name=False, mac=None,
                 name="Server 1", power_mode=POWER_MODES.Toggle):

        self.type = type
        self.number_of_sockets = number_of_sockets
        self.host = host
        self.password = password
        self.name = name
        self.verify_name = verify_name
        self.mac = mac
        self.power_mode = power_mode

        super(PowerManagerModel, self).__init__()


class RPCServerModel(model.Model):

    def __init__(self, port=None, host=None, admin=None, config=None):

        self.port = port
        self.host = host
        self.admin = admin
        self.config = config

        super(RPCServerModel, self).__init__()


class UIServerModel(model.Model):

    def __init__(self, port=5000, local=None, host=None):

        self.port = port

        self.local = local if local is not None else (
            True if host is None or host in ['127.0.0.1', 'localhost'] else False)

        self.host = host

        super(UIServerModel, self).__init__()


class SMTPModel(model.Model):

    def __init__(self, host=None, port=0, user=None, password=""):

        self.host = host
        self.port = port
        self.user = user
        self.password = password

        super(SMTPModel, self).__init__()


class HardwareResourceLimitsModel(model.Model):

    def __init__(self, memory_minimum_percent=30, cpu_total_percent_free=30, cpu_single_free=75, cpu_free_count=1,
                 checks_pass_needed=3):

        self.memory_minimum_percent = memory_minimum_percent
        self.cpu_total_percent_free = cpu_total_percent_free
        self.cpu_single_free = cpu_single_free
        self.cpu_free_count = cpu_free_count
        self.checks_pass_needed = checks_pass_needed

        super(HardwareResourceLimitsModel, self).__init__()


class PathsModel(model.Model):

    def __init__(self, projects_root=os.path.join(os.path.expanduser("~"), "Documents")):

        self.projects_root = projects_root

        super(PathsModel, self).__init__()


class PipelineModel(model.Model):

    def __init__(self, mail_scanning_done_minutes_before=30):

        self.mail_scanning_done_minutes_before = mail_scanning_done_minutes_before

        super(PipelineModel, self).__init__()


class ApplicationSettingsModel(model.Model):

    def __init__(self,
                 number_of_scanners=3,
                 scanner_name_pattern="Scanner {0}",
                 scan_program="scanimage",
                 scan_program_version_flag="-V",
                 scanner_models=tuple(),
                 power_manager=None,
                 rpc_server=None,
                 ui_server=None,
                 smtp_model=None,
                 hardware_resource_limits=None,
                 pipeline=None,
                 paths=None):

        self.versions = VersionChangesModel()
        self.power_manager = power_manager if power_manager is not None else PowerManagerModel()
        self.rpc_server = rpc_server if rpc_server is not None else RPCServerModel()
        self.ui_server = ui_server if ui_server is not None else UIServerModel()
        self.smtp_model = smtp_model if smtp_model is not None else SMTPModel()
        self.hardware_resource_limits = hardware_resource_limits if hardware_resource_limits is not None else \
            HardwareResourceLimitsModel()
        self.pipeline = pipeline if pipeline is not None else PipelineModel()
        self.paths = paths

        self.number_of_scanners = number_of_scanners
        self.scanner_name_pattern = scanner_name_pattern

        if power_manager is not None:
            self.scanner_names = [self.scanner_name_pattern.format(i + 1) for i
                                  in range(self.power_manager.number_of_sockets)]
        else:
            self.scanner_names = []

        self.scan_program = scan_program
        self.scan_program_version_flag = scan_program_version_flag

        scanner_models += tuple('EPSON V700' for _ in range(len(self.scanner_names) - len(scanner_models)))

        self.scanner_models = {name: scanner_model for name, scanner_model in
                               zip(self.scanner_names, scanner_models)}

        self.scanner_sockets = {name: socket for name, socket in
                                zip(self.scanner_names, range(len(self.scanner_models)))}

        super(ApplicationSettingsModel, self).__init__()