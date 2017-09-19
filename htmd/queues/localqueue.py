# (c) 2015-2017 Acellera Ltd http://www.acellera.com
# All Rights Reserved
# Distributed under HTMD Software License Agreement
# No redistribution in whole or part
#
from htmd.queues.simqueue import SimQueue
from protocolinterface import ProtocolInterface, val
import queue
import threading
from subprocess import check_output
import os
from glob import glob as glob
import abc
import logging
logger = logging.getLogger(__name__)


class _LocalQueue(SimQueue, ProtocolInterface):
    """ Local machine queue system

    Parameters
    ----------
    datadir : str, default=None
        The path in which to store completed trajectories.
    trajext : str, default='xtc'
        Extension of trajectory files. This is needed to copy them to datadir.


    .. rubric:: Methods
    .. autoautosummary:: htmd.queues.localqueue._LocalQueue
       :methods:
    .. rubric:: Attributes
    .. autoautosummary:: htmd.queues.localqueue._LocalQueue
       :attributes:
    """

    def __init__(self):
        super().__init__()
        self._arg('datadir', 'str', 'The path in which to store completed trajectories.', None, val.String())
        self._arg('trajext', 'str', 'Extension of trajectory files. This is needed to copy them to datadir.', 'xtc', val.String())
        self._arg('copy', 'list', 'A list of file names or globs for the files to copy to datadir', ('*.xtc'), val.String(), nargs='*')
        self._cmdDeprecated('trajext', 'copy')

        self._states = dict()
        self._queue = None
        self._shutdown = False

    def _setupQueue(self):
        if self._queue is None:
            self._queue = queue.Queue()

            devices = self._getdevices()

            self._threads = []
            for d in devices:
                t = threading.Thread(target=run_job, args=(self, d))
                t.daemon = True
                t.start()
                self._threads.append(t)

<<<<<<< HEAD
    def _createJobScript(self, fname, workdir, runsh, device):
        logger.info('Modified version of _createJobScript, prepend bash call to the run.sh script to avoid permission error')
=======
    def _createJobScript(self, fname, workdir, runsh, gpudevice=None):
>>>>>>> master
        with open(fname, 'w') as f:
            f.write('#!/bin/bash\n\n')
            if gpudevice is not None:
                f.write('export CUDA_VISIBLE_DEVICES={}\n'.format(gpudevice))
            f.write('cd {}\n'.format(os.path.abspath(workdir)))
            f.write('bash {}'.format(runsh))

            # Move completed trajectories
            if self.datadir is not None:
                datadir = os.path.abspath(self.datadir)
                if not os.path.isdir(datadir):
                    os.mkdir(datadir)
                simname = os.path.basename(os.path.normpath(workdir))
                # create directory for new file
                odir = os.path.join(datadir, simname)
                os.mkdir(odir)
                f.write('\nmv {} {}'.format(' '.join(self.copy), odir))

        os.chmod(fname, 0o700)

    def _setRunning(self, path):
        self._states[path] = 'R'

    def _setCompleted(self, path):
        self._states[path] = 'C'

    def retrieve(self):
        """ Retrieves a list of jobs that have completed since the last call

        Example
        -------
        >>> comp = app.retrieve()
        """
        ret = []
        xx = self._states.copy().keys()
        for i in xx:
            if self._states[i] == 'C':
                del self._states[i]
                ret.append(i)

        return ret

    def submit(self, mydirs):
        """ Queue for execution all of the jobs in the passed list of directories

        Queues all work units in a given directory list with the options given in the constructor opt.

        Parameters
        ----------
        mydirs : list of str
            A list or ndarray of directory paths

        Examples
        --------
        >>> app.submit(glob('input/e2*/'))
        """
        self._setupQueue()

        if isinstance(mydirs, str): mydirs = [mydirs]

        for d in mydirs:
            if not os.path.isdir(d):
                raise NameError('Submit: directory ' + d + ' does not exist.')

        # if all folders exist, submit
        for d in mydirs:
            dirname = os.path.abspath(d)
            logger.info('Queueing ' + dirname)
            self._states[dirname] = 'Q'
            self._queue.put(dirname)

    def inprogress(self):
        """ Get the number of simulations in progress

        Returns the sum of the number of running and queued workunits of the specific group in the engine.

        Example
        -------
        >>> app.inprogress()
        """
        output_run = sum(x == 'R' for x in self._states.values())
        output_queue = sum(x == 'Q' for x in self._states.values())

        return output_run + output_queue

    def stop(self):
        self._shutdown = True

    @abc.abstractmethod
    def _getdevices(self):
        pass


class LocalGPUQueue(_LocalQueue):
    """ Local machine queue system

    Parameters
    ----------
    datadir : str, default=None
        The path in which to store completed trajectories.
    copy : list, default='*.xtc'
        A list of file names or globs for the files to copy to datadir
    ngpu : int, default=None
        Number of GPU devices that the queue will use. Each simulation will be run on a different GPU. The queue will use the first `ngpus` devices of the machine.
    devices : list, default=None
        A list of GPU device indexes on which the queue is allowed to run simulations. Mutually exclusive with `ngpus`


    .. rubric:: Methods
    .. autoautosummary:: htmd.queues.localqueue.LocalGPUQueue
       :methods:
    .. rubric:: Attributes
    .. autoautosummary:: htmd.queues.localqueue.LocalGPUQueue
       :attributes:

    """

    def __init__(self):
        super().__init__()
        self._arg('ngpu', 'int', 'Number of GPU devices that the queue will use. Each simulation will be run on '
                                  'a different GPU. The queue will use the first `ngpus` devices of the machine.',
                       None, val.Number(int, '0POS'))
        self._arg('devices', 'list', 'A list of GPU device indexes on which the queue is allowed to run '
                                     'simulations. Mutually exclusive with `ngpus`', None, val.Number(int, '0POS'), nargs='*')

    def _getdevices(self):
        ngpu = self.ngpu
        devices = self.devices
        if ngpu is not None and devices is not None:
            raise ValueError('Parameters `ngpu` and `devices` are mutually exclusive.')

        if ngpu is None and devices is None:
            try:
                check_output("nvidia-smi -L", shell=True)
                devices = range(int(check_output("nvidia-smi -L | wc -l", shell=True).decode("ascii")))
            except:
                raise
        elif ngpu is not None:
            devices = range(ngpu)

        if devices is None:
            raise NameError("Could not determine which GPUs to use. "
                            "Specify the GPUs with the `ngpu=` or `devices=` parameters")
        else:
            logger.info("Using GPU devices {}".format(','.join(map(str, devices))))
        return devices


class LocalCPUQueue(_LocalQueue):
    """ Local CPU machine queue system

    Parameters
    ----------
    datadir : str, default=None
        The path in which to store completed trajectories.
    copy : list, default='*.xtc'
        A list of file names or globs for the files to copy to datadir
    ncpu : int, default=None
        Number of CPU threads that the queue will use. If None it will use the `ncpu` configured for HTMD in htmd.configure()


    .. rubric:: Methods
    .. autoautosummary:: htmd.queues.localqueue.LocalCPUQueue
       :methods:
    .. rubric:: Attributes
    .. autoautosummary:: htmd.queues.localqueue.LocalCPUQueue
       :attributes:

    """

    def __init__(self):
        super().__init__()
        self._arg('ncpu', 'int', 'Number of CPU threads that the queue will use. If None it will use the `ncpu` '
                                 'configured for HTMD in htmd.configure()', None, val.Number(int, 'POS'))

    def _getdevices(self):
        import multiprocessing
        ncpu = self.ncpu
        totalcpus = multiprocessing.cpu_count()
        if ncpu is None:
            from htmd.config import _config
            ncpu = totalcpus + _config['ncpus'] + 1
        if ncpu > totalcpus:
            raise RuntimeError('You can only use up to {} threads on this machine'.format(totalcpus))
        return [None] * ncpu


def run_job(self, gpuid):
    queue = self._queue
    while not self._shutdown:
        path = None
        try:
            path = queue.get(timeout=1)
        except:
            pass

        if path:
            if gpuid is None:
                logger.info('Running ' + path)
            else:
                logger.info("Running " + path + " on GPU device " + str(gpuid))
            self._setRunning(path)

            runsh = os.path.join(path, 'run.sh')
            jobsh = os.path.join(path, 'job.sh')
            self._createJobScript(jobsh, path, runsh, gpuid)

            try:
                ret = check_output(jobsh)
                logger.debug(ret)
            except Exception as e:
                logger.info('Error in simulation {}. {}'.format(path, e))
                self._setCompleted(path)
                queue.task_done()
                continue

            logger.info("Completed " + path)
            self._setCompleted(path)
            queue.task_done()

    logger.info("Shutting down worker thread")


if __name__ == "__main__":
    from htmd.home import home
    import os

    lo = LocalCPUQueue()
    lo.ncpu = 1
    folder = os.path.join(home(dataDir='test-localqueue'), 'test_cpu')
    lo.submit([folder] * 2)
    lo.wait()

    lo = LocalGPUQueue()
    try:
        lo._getdevices()
        folders = glob(os.path.join(home(dataDir='test-localqueue'), 'test_gpu*'))
        lo.submit(folders)
        lo.wait()
        for f in folders:
            torem = glob(os.path.join(f, 'output.*')) + glob(os.path.join(f, 'restart.*')) + glob(os.path.join(f, 'log.txt'))
            for r in torem:
                os.remove(r)
    except:
        print('No GPUs detected on this machine')


