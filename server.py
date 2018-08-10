# -*- coding:utf-8 -*-
import os
import sys
import logging
import datetime
import core.settings as config

import tornado.ioloop
import tornado.options
import tornado.httpserver
import core.hub as Hub
from tornado.options import define, options, parse_command_line
from application import app

define("port", default=8888, help="Server listening on the given ports", type=int)
define("debug", default=True, help="run in debug mode")
define("level", default="DEBUG", help="logging level: ERROR/INFO/DEBUG")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def main():
    options.parse_command_line()
    print("HTTP Server running on {0} port ...".format(options.port))
    print("Stop the server, press Ctrl + C")


    # init log
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    LOG_DIR = os.path.join(BASE_DIR, "logs")
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    LOG_FILE = datetime.datetime.now().strftime("%Y-%m-%d") + ".log"
    file = os.path.join(LOG_DIR, LOG_FILE)
    config.init_log(options.level, file)


    # start Hub
    Hub.start()

    # start tornado server
    httpServer = tornado.httpserver.HTTPServer(app)
    if sys.platform.startswith("linux"):
        httpServer.bind(options.port, reuse_port=True)
    else:
        httpServer.bind(options.port, reuse_port=False)
    httpServer.start()
    tornado.ioloop.IOLoop.current().start()

if __name__ == "__main__":
    main()
