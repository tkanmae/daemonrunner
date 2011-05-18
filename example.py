#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import time
from daemonrunner import DaemonRunner


class MyApp(object):
    def run(self):
        while True:
            logging.info('hello world!')
            time.sleep(10)


def main():
    def callback():
        try:
            app = MyApp()
            app.run()
        except Exception as exc:
            logging.error(exc)

    logging.basicConfig(filename='/tmp/myapp.log',
                        level=logging.INFO)

    runner = DaemonRunner(callback, '/tmp/myapp.pid')
    runner.register_logger(logging.getLogger())
    runner.parse_args_and_run()


if __name__ == '__main__':
    main()
