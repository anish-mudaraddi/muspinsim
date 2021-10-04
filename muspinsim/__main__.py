import os
import logging
import numpy as np
import argparse as ap
from datetime import datetime

from muspinsim.mpi import mpi_controller as mpi
from muspinsim.input import MuSpinInput
from muspinsim.simconfig import MuSpinConfig
from muspinsim.experiment import ExperimentRunner


def main(use_mpi=False):

    if use_mpi:
        mpi.connect()

    if mpi.is_root:
        # Entry point for script
        parser = ap.ArgumentParser()
        parser.add_argument('input_file', type=str, default=None, help="""YAML
                            formatted file with input parameters.""")
        args = parser.parse_args()

        fs = open(args.input_file)
        infile = MuSpinInput(fs)
        is_fitting = len(infile.variables) > 0

        # Open logfile
        logfile = '{0}.log'.format(os.path.splitext(args.input_file)[0])
        logformat = '[%(levelname)s] [%(threadName)s] [%(asctime)s] %(message)s'
        logging.basicConfig(filename=logfile,
                            filemode='w',
                            level=logging.INFO,
                            format=logformat,
                            datefmt='%Y-%m-%d %H:%M:%S')

        logging.info('Launching MuSpinSim calculation '
                     'from file: {0}'.format(args.input_file))

        if is_fitting:
            logging.info('Performing fitting in variables: '
                         '{0}'.format(', '.join(infile.variables)))

        tstart = datetime.now()        
    else:
        infile = MuSpinInput()
        is_fitting = False

    is_fitting = mpi.broadcast(is_fitting)

    if not is_fitting:
        # No fitting
        runner = ExperimentRunner(infile, {})
        results = runner.run_all()

        if mpi.is_root:
            # Output
            runner.config.save_output()
    else:
        raise NotImplementedError('Fitting still not implemented')

    if mpi.is_root:
        tend = datetime.now()
        simtime = (tend-tstart).total_seconds()
        logging.info('Simulation completed in '
                     '{0:.3f} seconds'.format(simtime))



def main_mpi():
    main(use_mpi=True)


if __name__ == '__main__':
    main()
