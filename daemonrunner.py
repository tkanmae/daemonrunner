#!/usr/bin/env python
# -*- coding: utf-8 -*-
# A wrapper for daemon.DaemonContext based on daemon.runner.DaemonRunner in
# python-daemon package.
#
# daemon/runner.py
# Part of python-daemon, an implementation of PEP 3143.
#
# Copyright © 2009–2010 Ben Finney <ben+python@benfinney.id.au>
# Copyright © 2007–2008 Robert Niederreiter, Jens Klein
# Copyright © 2003 Clark Evans
# Copyright © 2002 Noah Spurrier
# Copyright © 2001 Jürgen Hermann
#
# This is free software: you may copy, modify, and/or distribute this work
# under the terms of the Python Software Foundation License, version 2 or
# later as published by the Python Software Foundation.
# No warranty expressed or implied. See the file LICENSE.PSF-2 for details.
import argparse
import errno
import inspect
import logging
import os
import signal
import sys

import daemon.pidfile
from daemon import DaemonContext


__all__ = ['DaemonRunner', 'DaemonRunnerError',
           'DaemonRunnerStartError', 'DaemonRunnerStopError']


class DaemonRunnerError(Exception):
    pass


class DaemonRunnerStartError(RuntimeError, Exception):
    pass


class DaemonRunnerStopError(RuntimeError, Exception):
    pass


class DaemonRunner(object):

    def __init__(self, callback, pidpath, timeout=1, parser=None):
        """
        Parameters
        ----------
        callback : function
            A callback function called when a daemon process starts.  It is
            called without arguments.
        pidpath : str
            Absolute path of the PID file.
        """
        argspec = inspect.getargspec(callback)
        if len(argspec.args) != 0:
            msg = ('callback is called without arguments: {0}'.format(argspec))
            raise DaemonRunnerError(msg)

        self.callback = callback
        self.pidfile = self._make_pidlockfile(pidpath, timeout)

        self.daemon_context = DaemonContext()
        self.daemon_context.pidfile = self.pidfile

        self._parser = self._init_argparser(parser)
        self._logger = None

    def parse_args_and_run(self):
        args = self._parser.parse_args()
        args.func()

    def register_logger(self, logger):
        """Register a logger.

        Parameters
        ----------
        logger : logging.Logger
            A logger object.
        """
        if not isinstance(logger, logging.Logger):
            raise ValueError('logger must be a logging.Logger object')
        self._logger = logger

    def _start(self):
        """Open the daemon context and run the application."""
        if self._is_pidfile_stale():
            self.pidfile.break_lock()

        if self.pidfile.is_locked():
            pid = self.pidfile.read_pid()
            msg = 'Already running with pid: {0}\n'.format(pid)
            self._emit_message(msg)
        else:
            if self._logger is not None:
                self._preserve_logging_file_handler()

            msg = 'Starting\n'.format(os.getpid())
            self._emit_message(msg, sys.stdout)

            self.daemon_context.open()
            self.callback()

    def _stop(self):
        """Exit the daemon process specified in the current PID file."""
        # If the current PID is stale, then breaks the lock and removes
        # the PID file.
        if self.pidfile.read_pid() is None:
            self._emit_message('Not running\n')
            return

        if self._is_pidfile_stale():
            self.pidfile.break_lock()
        else:
            self._terminate_daemon_process()
            self._emit_message('Stopped\n', sys.stdout)

    def _restart(self):
        """Stop, and then start."""
        self._stop()
        self.pidfile.break_lock()
        self._start()

    def _show_status(self):
        if self.pidfile.read_pid() is None:
            self._emit_message('Not running\n', sys.stdout)
        elif self.pidfile.is_locked():
            pid = self.pidfile.read_pid()
            self._emit_message('Running with pid: {0}\n'.format(pid), sys.stdout)
        else:
            self._emit_message('Unknown\n', sys.stdout)

    def _terminate_daemon_process(self):
        """Terminate the daemon process specified in the current PID file."""
        pid = self.pidfile.read_pid()
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            msg = 'Failed to terminate: {0}'.format(pid)
            raise DaemonRunnerStopError(msg)

    def _preserve_logging_file_handler(self):
        # Ensure there is no duplicate in the files_preserve.
        current = self.daemon_context.files_preserve
        current = set(current) if current is not None else set()

        handlers = set(lh.stream for lh in self._logger.handlers
                       if isinstance(lh, logging.FileHandler))

        self.daemon_context.files_preserve = list(current.union(handlers))

    def _is_pidfile_stale(self):
        """Return True if the current PID file is stale."""
        result = False
        pid = self.pidfile.read_pid()
        # Send SIGDFL signal to the PID specified in the current PID
        # file.  If no such PID is found, then the current PID file is
        # stale.
        if pid is not None:
            try:
                os.kill(pid, signal.SIG_DFL)
            except OSError as exc:
                if exc.errno == errno.ESRCH:
                    result = True
        return result

    def _emit_message(self, msg, stream=sys.stderr):
        stream.write(msg)
        stream.flush()

    def _init_argparser(self, parser=None):
        if parser is None:
            parser = argparse.ArgumentParser()
        subparser = parser.add_subparsers()

        p = subparser.add_parser('start', help='start')
        p.set_defaults(func=self._start)
        p = subparser.add_parser('stop', help= 'stop')
        p.set_defaults(func=self._stop)
        p = subparser.add_parser('restart', help='restart')
        p.set_defaults(func=self._restart)
        p = subparser.add_parser('status', help='show status')
        p.set_defaults(func=self._show_status)

        return parser

    @classmethod
    def _make_pidlockfile(cls, path, acquire_timeout):
        """Make a PIDLockFile object with the given filesystem path.

        Parameters
        ----------
        path : str
            Absolute path of a PIDLockFile.
        acquire_timeout : int
            Timeout for acquireing the PIDLockFile.

        Returns
        -------
        lockfile : TimeoutPIDLockFile
            TimeoutPIDLockFile object

        See Also
        --------
        daemon.pidlockfile.TimeoutPIDLockFile
        """
        if not isinstance(path, basestring):
            raise ValueError('Not a file path: {0}'.format(path))
        if not os.path.isabs(path):
            raise ValueError('Not a absolute path: {0}'.path)
        lockfile = daemon.pidfile.TimeoutPIDLockFile(path, acquire_timeout)
        return lockfile
