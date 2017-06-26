import os.path as path
from os import makedirs
import subprocess
import logging
logger = logging.getLogger(__name__)


def simfiltercpptraj(sims, outfolder, cpptraj_file):
    """

    :rtype: object
    """
    if not path.exists(outfolder):
        makedirs(outfolder)
    logger.info('Stripping with cpptraj')
    for sim in sims:
        sim_name = sim.input.split('/')[1]
        logger.info('sim_name is {}'.format(sim_name))
        bashCommand = "cpptraj -p {} -y {} -i {} -x {}/{}_filtered.nc".format(sim.molfile,
                                                                                  sim.trajectory[0],
                                                                                  cpptraj_file,
                                                                                  outfolder,
                                                                                  sim_name)
        process = subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
        _, error = process.communicate()
        logger.info('Process ended with error {}'.format(error))
