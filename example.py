#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import logging
import time
from daemonrunner import DaemonRunner


logger = logging.getLogger('myapp')


class MyApp(object):
    def run(self):
        while True:
            logger.info('hello, world!')
            time.sleep(10)


def init_logger():
    logger = logging.getLogger('myapp')
    logger.setLevel(logging.INFO)

    lh = logging.FileHandler('/tmp/myapp.log')
    formatter = logging.Formatter(
        '%(asctime)s:%(process)d:%(levelname)s:%(message)s')
    lh.setFormatter(formatter)
    lh.setLevel(logging.INFO)

    logger.addHandler(lh)

    return logger


def init_argparser(parser):
    subparser = parser.add_subparsers(help="sub-command help")

    help = 'start daemon'
    p = subparser.add_parser('start', help=help)
    p.set_defaults(action='start')

    help = 'stop daemon'
    p = subparser.add_parser('stop', help=help)
    p.set_defaults(action='stop')

    help = 'restart daemon'
    p = subparser.add_parser('restart', help=help)
    p.set_defaults(action='restart')

    help = 'show status'
    p = subparser.add_parser('status', help=help)
    p.set_defaults(action='status')

    return parser


def main(args):
    def callback():
        try:
            app = MyApp()
            app.run()
        except Exception as exc:
            logger.error(exc)

    logger = init_logger()

    runner = DaemonRunner(callback, '/tmp/myapp.pid')
    runner.register_logger(logger)
    runner.actions[args.action]()


if __name__ == '__main__':
    parser = init_argparser(argparse.ArgumentParser())

    args = parser.parse_args()
    main(args)
