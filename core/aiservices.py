import asyncio
import tornado.escape
import tornado.ioloop
import tornado.locks
import tornado.web
import os.path
import uuid
import json
import logging
import datetime
import sqlite3
import base64

from tornado.options import define, options, parse_command_line
import core.hub as  Hub
import core.settings as config

class TrainHandler(tornado.web.RequestHandler):
    def post(self):
        try:
            id = self.get_argument("id", default="anonymous")
            logging.info("TrainHandler: request id =  %s" % id)
            Hub.send_request(id, self.json_args)
            self.write('OK')
        except Exception as e:
            logging.error("Train Handler Error: %s" % str(e))
            raise tornado.web.HTTPError(500, "TrainHandler Error: %s" % repr(e))

    def prepare(self):
        if self.request.headers.get("Content-Type", "").startswith("application/json"):
            try:
                content = self.request.body.decode('utf-8')
                logging.debug("request content is :%s " % content)
                self.json_args = json.loads(content)
            except Exception as e:
                logging.error("Prepare json_args Error: %s" % str(e))
                raise tornado.web.HTTPError(400, "Invalid request parameters : %s" % repr(e))
        else:
            raise tornado.web.HTTPError(400, "Invalid request parameters : %s" % self.request.body.decode('utf-8'))

class CancelTrainHandler(tornado.web.RequestHandler):
    def get(self):
        try:
            id = self.get_argument("id", default="anonymous")
            logging.info("CancelTrainHandler: request id =  %s" % id)
            Hub.send_event(id, 'cancel')
            self.write('OK')
        except ValueError as v:
            raise tornado.web.HTTPError(400, repr(v))
        except Exception as e:
            logging.error("CancelTrainHandler Error: %s" % str(e))
            raise tornado.web.HTTPError(500, "CancelTrainHandler Error: %s" % repr(e))

class PredictHandler(tornado.web.RequestHandler):
    def get(self):
        try:
            id = self.get_argument("id", default="anonymous")
            logging.info("PredictHandler: request id =  %s" % id)
            self.write("OK")
        except Exception as e:
            logging.error("History Handler Error: %s" % repr(e))
            raise tornado.web.HTTPError(500, "History Handler Error")

class HistoryHandler(tornado.web.RequestHandler):
    def get(self):
        try:
            id = self.get_argument("id", default="anonymous")
            logging.info("HistoryHandler: request id =  %s" % id)
            Hub.send_event(id, 'predict')
            self.write(Hub.fetch_data(id))
        except ValueError as v:
            raise tornado.web.HTTPError(400, repr(v))
        except Exception as e:
            logging.error("History Handler Error: %s" % repr(e))
            raise tornado.web.HTTPError(500, "HistoryHandler Error: %s" % repr(e))

class ModelHandler(tornado.web.RequestHandler):
    def get(self):
        id = self.get_argument("id", default="anonymous")
        print(id)

class QueryRequestHandler(tornado.web.RequestHandler):
    def get(self):
        try:
            self.write(Hub.query_request())
        except Exception as e:
            raise tornado.web.HTTPError(500, repr(e))

class MockHandler(tornado.web.RequestHandler):
    def get(self):
        try:
            data = []
            for line in open(os.path.dirname(os.path.abspath(__file__))+r'\mock\monthly-sunspot-number-zurich-17.csv'):
                value = line.strip('\n').split(',')
                value[0] = value[0].strip('"')
                data.append({'name': value[0], 'value': value})

            self.write({'result': data[1:]})
        except Exception as e:
            print("Mock Handler Error: "+str(e))
            raise tornado.web.HTTPError(500, "Mock Handler Error")

def listFiles(dir):
    for root, dirs, files in os.walk(dir):
        return files

class PreviewHandler(tornado.web.RequestHandler):
    index = 0
    directory = os.path.dirname(os.path.abspath(__file__)) + '/preview/'
    files = listFiles(directory)
    def get(self):
        try:
            _files = PreviewHandler.files
            _dir = PreviewHandler.directory
            num = PreviewHandler.index%len(_files)
            PreviewHandler.index = num + 1
            data = []
            for line in open(_dir + _files[num]):
                value = line.strip('\n').split(',')
                try:
                    data.append(float(value[0]))
                except:
                    print("Float convert error: %s, %s" % (_files[num], value[0]))
            
            self.write({'values': data, 'name': _files[num]})
        except Exception as e:
            print("Preview Handler Error: "+str(e))
            raise tornado.web.HTTPError(500, "Preview Handler Error" + repr(e))


class ListModelsHandler(tornado.web.RequestHandler):
    directory = os.getcwd() + '/static/models/'
    def get(self):
        try:
            files = listFiles(ListModelsHandler.directory)
            self.write({'files': files})
        except Exception as e:
            print("ListModels Handler Error: "+str(e))
            raise tornado.web.HTTPError(500, "ListModels Handler Error")


def aiserver():
    define("port", default=8888, help="run on the given port", type=int)
    define("debug", default=True, help="run in debug mode")
    define("level", default="DEBUG", help="logging level: ERROR/INFO/DEBUG")

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    parse_command_line()

    # init log
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    LOG_DIR = os.path.join(BASE_DIR, "logs")
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    LOG_FILE = datetime.datetime.now().strftime("%Y-%m-%d") + ".log"
    file = os.path.join(LOG_DIR, LOG_FILE)
    config.init_log(options.level, file)

    # web application
    app = tornado.web.Application(
        [
            (r"/ai/train", TrainHandler),
            (r"/ai/history", HistoryHandler),
            (r"/ai/model", ModelHandler),
            (r"/ai/mock/data", MockHandler),
            (r"/ai/cancel", CancelTrainHandler),
            (r"/ai/query/request", QueryRequestHandler)
        ],
        template_path=os.path.join(os.path.dirname(__file__), "templates"),
        static_path=os.path.join(os.path.dirname(__file__), "static"),
    )

    # start Hub
    Hub.start()

    # start web application
    app.listen(options.port)
    logging.info("Web Server started !")
    tornado.ioloop.IOLoop.current().start()

    logging.info("Start over !")

if __name__ == "__main__":
    aiserver()