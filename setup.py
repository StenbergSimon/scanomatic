#!/usr/bin/env python
__version__ = "v1.4"

#
# DEPENDENCIES
#

import os
import sys
from subprocess import Popen, PIPE, call
import json

#
# Parsing and removing argument for accepting all questions as default
#

silent_install = any(arg.lower() == '--default' for arg in sys.argv)
if silent_install:
    sys.argv = [arg for arg in sys.argv if arg.lower() != '--default']

#
# Parsing and removing arguments for branch information
#

branch = None
branch_info = tuple(i for i, arg in enumerate(sys.argv) if arg.lower() == '--branch')

if branch_info:
    branch_info = branch_info[0]
    branch = sys.argv[branch_info + 1] if len(sys.argv) > branch_info + 1 else None
    sys.argv = sys.argv[:branch_info] + sys.argv[branch_info + 2:]

#
# Python-setup
#

from setup_tools import MiniLogger, patch_bashrc_if_not_reachable, test_executable_is_reachable

if sys.argv[1] == 'uninstall':
    call('python -c"from setup_tools import uninstall;uninstall()"', shell=True)
    sys.exit()

_logger = MiniLogger()
_logger.info("Checking non-python dependencies")

#
# INSTALLING NON-PYTHONIC PROGRAMS
#

program_dependencies = ('nmap',)
PROGRAM_NOT_FOUND = 32512
install_dependencies = []

for dep in program_dependencies:
    try:
        p = Popen(dep, stdout=PIPE, stderr=PIPE)
        p.communicate()
    except OSError:
        install_dependencies.append(dep)

if len(install_dependencies) > 0:

    if os.name == 'posix':

        if os.system("gksu apt-get install {0}".format(
                " ".join(install_dependencies))) != 0:

            _logger.warning("Could not install: {0}".format(
                install_dependencies))

    else:

        _logger.warning(
            "Scan-o-Matic is only designed to be run on Linux. "
            "Setup will try to continue but you are on your own from now on. "
            "The following programs were not found: {0}".format(
                install_dependencies))


_logger.info("Non python dependencies done")
_logger.info("Preparing setup parameters")

#
# PREPARING INSTALLATION
#

package_dependencies = [
    'argparse', 'matplotlib', 'multiprocessing', 'odfpy',
    'numpy', 'sh', 'nmap', 'configparse', 'skimage',
    'uuid', 'PIL', 'scipy', 'setproctitle', 'psutil', 'flask', 'requests']

data_files = []

scripts = [
    os.path.join("scripts", p) for p in [
        "scan-o-matic",
        'scan-o-matic_as_service_check',
        "scan-o-matic_server",
        "scan-o-matic_experiment",
        "scan-o-matic_analysis",
        "scan-o-matic_analysis_move_plate",
        "scan-o-matic_analysis_patch_times",
        "scan-o-matic_compile_project",
        "scan-o-matic_analysis_skip_gs_norm",
        "scan-o-matic_analysis_xml_upgrade",
        "scan-o-matic_xml2image_data",
        "scan-o-matic_inspect_compilation"
    ]
]

#
# INSTALLING SCAN-O-MATIC
#

from distutils.core import setup

_logger.info("Setting up Scan-o-Matic on the system")

setup(
    name="Scan-o-Matic",
    version=__version__,
    description="High Throughput Solid Media Image Phenotyping Platform",
    long_description="""Scan-o-Matic is a high precision phenotyping platform
    that uses scanners to obtain images of yeast colonies growing on solid
    substrate.

    The package contains a user interface as well as an extensive package
    for yeast colony analysis from scanned images.
    """,
    author="Martin Zackrisson",
    author_email="martin.zackrisson@gu.se",
    url="www.gitorious.org/scannomatic",
    packages=[
        "scanomatic",
        "scanomatic.generics",
        "scanomatic.models",
        "scanomatic.models.factories",
        "scanomatic.io",
        "scanomatic.io.xml",
        "scanomatic.qc",
        "scanomatic.server",
        "scanomatic.image_analysis",
        "scanomatic.data_processing",
        "scanomatic.data_processing.phases",
        "scanomatic.util",
        "scanomatic.ui_server"],

    package_data={"scanomatic": data_files},
    scripts=scripts,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: X11 Application :: GTK',
        'Environment :: Console',
        'Intended Autdience :: Science/Research',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2.7',
        'Topic :: Scientific/Engineering :: Bio-Informatics'
    ],
    requires=package_dependencies
)

if os.name == "nt":

    _logger.info(
        "The files in the script folder can be copied to wherever you"
        " want to try to run Scan-o-Matic. Good luck!")

_logger.info("Scan-o-Matic is setup on system")

#
# POST-INSTALL
#

from setup_tools import install_data_files, install_launcher
_logger.info("Copying data and configuration files")
install_data_files(silent=silent_install)
install_launcher()
patch_bashrc_if_not_reachable(silent=silent_install)
_logger.info("Post Setup Complete")

if not test_executable_is_reachable():
    print """

    INFORMATION ABOUT LOCAL / USER INSTALL
    --------------------------------------

    The scripts for launching the Scan-o-Matic
    programs should be directly accessible from
    the commandline by e.g. writing:

        scan-o-matic

    If this is not the case you will have to
    modify your PATH-variable in bash as follows:

        export PATH=$PATH:$HOME/.local/bin/

    If above gives you direct access to Scan-o-Matic
    then you should put that line at the end of your
    .bashrc file, usually located in your $HOME.

    If it doesn't work, you need to check the setup
    output above to see where the files were copied and
    extend the path accordingly.

    Alternatively, if you install Scan-o-Matic for all
    users then the launch scripts should be copied
    into a folder that is already in path.

    If you use a USB-connected PowerManager, make sure
    sispmctl is installed.

"""

from scanomatic.io.paths import Paths

try:
    with open(Paths().source_location_file, mode='w') as fh:
        directory = os.path.dirname(os.path.join(os.path.abspath(os.path.expanduser(os.path.curdir)), sys.argv[0]))
        json.dump({'location': directory, 'branch': branch}, fh)

except IOError:
    _logger.warning("Could not write info for future upgrades. You should stick to manual upgrades")

# postSetup.CheckDependencies(package_dependencies)

_logger.info("Install Complete")
