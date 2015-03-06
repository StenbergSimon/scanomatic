from argparse import ArgumentParser
from scanomatic.io.first_pass_results import FirstPassResults
from scanomatic.models.factories.analysis_factories import AnalysisModelFactory
import scanomatic.io.rpc_client as rpc_client

__author__ = 'martin'

if __name__ == "__main__":

    parser = ArgumentParser(description="""Runs Scan-o-Matic image analyses""")

    parser.add_argument(
        '-p', '--p', type=str, dest="path",
        help='Path to first pass file')

    args = parser.parse_args()

    first_pass_file = FirstPassResults(args.path)

    analysis_model = first_pass_file.analysis_model

    if AnalysisModelFactory.validate(analysis_model):

        client = rpc_client.get_client(admin=True)
        client.create_analysis_job(analysis_model)
        print "Job requested."