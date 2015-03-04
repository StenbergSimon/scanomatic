__version__ = "0.9991"

import scanomatic.generics.model as model

class ScanningModel(model.Model):

    def __init__(self, number_of_scans=217, time_between_scans=20,
                 project_name="", directory_containing_project="",
                 project_tag="", scanner_tag="",
                 description="", email="", pinning_formats=tuple(),
                 fixture="", scanner=1, mode="TPU", version=__version__):

        super(ScanningModel, self).__init__(
            number_of_scans=number_of_scans, time_between_scans=time_between_scans,
            project_name=project_name,
            directory_containing_project=directory_containing_project,
            project_tag=project_tag, scanner_tag=scanner_tag,
            description=description, email=email,
            pinning_formats=pinning_formats,
            fixture=fixture, scanner=scanner, mode=mode, version=__version__)