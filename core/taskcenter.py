from multiprocessing import Process, Queue, Value
from enum import Enum
import numpy as np
import core.kai as kai
import logging
import time
import threading
import time
import datetime
import sys
import traceback

global SEND_DATA, SEND_STATUS, SEND_INFO

SIGNAL = Enum('SIGNAL', ('Started', 'Running', 'Stopped'))
STATUS = Enum('STATUS', ('Waiting', 'Binded', 'Trainning', 'Finished', 'Error', 'Done'))

def train(request, event, location):
    """ train main """
    values = request['values']
    model = kai.smart_model(request, len(values)-1) if type(values[0]) == list else kai.smart_model(request, request.get('time_step', 32))
    pred_type = request.get('pred_type', 'realtime')
    input_values, output_values, min_value, max_value = kai.normalize(values, degrees=request.get('time_step', 32))
    total_num = len(input_values)
    train_num = round(total_num * request['percent'])
    pred_num = total_num - train_num

    def _real_predict():
        out_pred_std = model.predict(np.array(input_values))
        return kai.renormalize(out_pred_std.reshape(out_pred_std.size).tolist(), min_value, max_value)

    def _recurse_predict():
        x = list(map(lambda v: v, input_values[-1]))
        x.append(output_values[-1])
        
        for i in range(pred_num):
            y = model.predict(np.array([x[i+1:]]))
            x.append(y[0][0])

        return kai.renormalize(x, min_value, max_value) # 多指标的时候呢？

    def predict_depend_event():
        # print('--------------------- event.value = %d' % event.value)
        value = event.value
        event.value = 0 # must set event value to 0

        if value > 0:
            if value == 1: # cancel
                model.stop_training = True
            elif value == 2: # predict
                # print('----------------- predict -----------------')
                return _recurse_predict() if pred_type == 'recurse' else _real_predict()
            elif value == 5:
                SEND_STATUS(SIGNAL.Stopped)
                sys.exit()
            else:
                pass
        
        return None
            
    def action(epoch, logs, last_time):
        duration = time.time() - last_time
        pred = predict_depend_event()
        SEND_DATA({
            'predict': pred,
            'loss': [epoch, duration, logs['loss']],
            'status': '2:Training:'+ str(epoch)
        })

    def do_train():
        callback = kai.EpochEndCallback(action)
        hist = model.fit(np.array(input_values[0:train_num]), np.array(output_values[0:train_num]), epochs=request['epochs'], batch_size=request['batch_size'],  verbose=0, callbacks=[callback])
        score = model.evaluate(np.array(input_values[train_num:]), np.array(output_values[train_num:]), batch_size=request['batch_size'])
        model.save("."+location) # relative directory
        pred = _recurse_predict() if pred_type == 'recurse' else _real_predict()
        SEND_DATA({
            'predict': pred,
            'loss': [],
            'status': '3:Finished:' + location,
            'evaluate': [np.mean(hist.history['loss']), score]
        })

    do_train()

# refator it next version
class Respose(object):
    def __init__(self, type, reqid, pname, content):
        self.type = type
        self.reqid = reqid
        self.pname = pname
        self.content = content

    def __str__(self):
        return ("Response: type = %s, pname = %s, reqid = %s" % (self.type, self.pname, self.reqid))

# refator it next version     
class Request(object):
    def __init__(self, id):
        self.id = id
        self.status = "STATUS.Waiting"
        self.data = {
            'predict': None,
            'loss': [],
            'status': "0:Waiting bind"
        }

    def __str__(self):
        return "Request: id = %s, status = %s" % (self.id, self.status)  

    def fetch_data(self):
        result = self.data
        if self.status == STATUS.Finished:
            self.status = STATUS.Done
        elif self.status == STATUS.Trainning:
            self.data = {
                'predict': None,
                'loss': [],
                'status': "1:Trainning fetched"
            }
        else:
            pass

        return result

class AiProcess(Process):
    def __init__(self, name, send, resv, event):
        Process.__init__(self)
        self.name = name
        self.send = send
        self.resv = resv
        self.event = event
        self.request_id = "None"

    def _prepare(self):
        def _send(**parms):
                self.send.put({
                'type': parms.get("type", 'info'), # info/status/data ,
                'request_id': self.request_id,
                'proc_name': self.name,
                'info': parms.get("info", ""),
                'data': parms.get("data", None),
                'status': parms.get("status")
            })

        def _send_status(status):
            _send(type='status', status=status)
        
        def _send_data(data):
            _send(type='data', data=data)

        def _send_info(info):
            _send(type='info', info=info)

        global SEND_DATA, SEND_STATUS, SEND_INFO
        SEND_STATUS, SEND_INFO, SEND_DATA = _send_status, _send_info , _send_data

    def run(self):
        self._prepare()

        # """ process main """
        print("Start a new process : %s " % self.name)
        SEND_INFO('started')
        while True:
            request = self.resv.get() # 

            try:
                if self.event.value == 5:
                    SEND_INFO('stoped')
                    SEND_INFO('Stop proecess %s' % name)
                    sys.exit()

                self.request_id = request['id']
                date = datetime.datetime.now().strftime('%Y-%m-%d-%H%M%S')
                location = "/static/models/"+ str(self.request_id) + "_" + date + '.h5'

                SEND_STATUS(STATUS.Binded)
                train(request['body'], self.event, location)
                SEND_STATUS(STATUS.Finished)
            except Exception as e:
                traceback.print_exc()
                SEND_INFO("Process %s meet some error: " % repr(e))

class TaskManager(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.running = True
        self.send = Queue()
        self.resv = Queue()
        self.request = {}
        self.process = {}
    
    def fork(self, proc_name):
        event = Value('i')
        p = AiProcess(proc_name, self.resv, self.send, event)
        p.start()
        self.process[proc_name] = [p, event]

    def run(self):      
        def handle_status_response(request, status, process):
            request['status'] = status
            if status == STATUS.Binded:
                request['process'] = process # bind process to request
            elif status == STATUS.Error:
                request['data'] = None # Delete request for error from process
            else:
                pass

        def handle_data_response(request, response):
            request['status'] = STATUS.Trainning
            req_data = request['data']
            rsp_data = response['data']

            req_data['loss'].append(rsp_data['loss'])
            req_data['status'] = rsp_data['status']

            if rsp_data['predict']: # 防止 None 冲掉有效的 predict 
                req_data['predict'] = rsp_data['predict']

            if 'evaluate' in rsp_data:
                req_data['evaluate'] = rsp_data['evaluate']

        # ............... Main Loop ................ 
        while self.running:
            try:
                response = self.resv.get()
                resp_type = response['type']
                if resp_type == 'info':
                    print("Info from process %s： %s" % (response['proc_name'], response['info']))
                    logging.debug("Info from process %s： %s" % (response['proc_name'], response['info']))
                    continue

                request = self.request[response['request_id']] # may raise KeyError 
                if resp_type == 'data':
                    handle_data_response(request, response)
                elif resp_type == 'status':
                    handle_status_response(request, response['status'], self.process[response['proc_name']])
                else:
                    pass
            except Exception as e:
                logging.error("TaskManager Error: %s" % repr(e))
            
    def send_request(self, raw_data):
        request_id = raw_data['id']
        if request_id in self.request:
            old_request = self.request[request_id]
            old_status = old_request['status']

            if old_status == STATUS.Waiting:
                logging.error("%s is waiting for training, do not request repeatedly!" % str(request_id))
                raise ValueError("%s is waiting for training, do not request repeatedly!" % str(request_id))
            elif old_status == STATUS.Trainning:
                logging.warn("%s will be canceled for a new request was received!" % str(request_id))
                event = old_request['process'][1]
                event.value = 1
                del self.request[request_id]
            elif old_status == STATUS.Finished:
                pass # train it again
            else:
                pass # Todo design this logic later

        self.request[request_id] = {
            'status': STATUS.Waiting,
            'data': {
                'predict': None,
                'loss': [],
                'status': "0:Waiting bind"
            },
        }
        self.send.put(raw_data)

    def send_event(self, request_id, value):
        # print('------------ set event 1------------- %s' % value)
        if request_id in self.request:
            if self.request[request_id]['status'] == STATUS.Waiting:
                logging.info('Request not binded already')
                return
                
            event = self.request[request_id]['process'][1]
            # print('--------------------- set event 2 : %s' % str(self.request[request_id]))
            if value == 'cancel':
                event.value = 1
                del self.request[request_id]
            elif value == 'predict':
                event.value = 2
            elif value == 'test':
                event.value = 3
            elif value == 'stop':
                event.value = 5
            else:
                event.value = 6
        else:
            raise ValueError("Request_id is not found : %s" % request_id)

    def fetch_data(self, request_id):
        if request_id in self.request:
            try:
                result = self.request[request_id]['data']
                
                if self.request[request_id]['status'] == STATUS.Finished:
                    del self.request[request_id]
                else:
                    self.request[request_id]['data'] = {
                        'predict': None,
                        'loss': [],
                        'status': "1:Training:Fetched"
                    }

                return result
            except Exception as e:
                logging.error("fetch data error: %s, %s, %s" % (request_id, str(self.request[request_id]), repr(e)))
                return {
                    'predict': None,
                    'loss': [],
                    'status': "6:Internal Error"
                }
        else:
            raise ValueError("request %s is not found" % request_id)

    
    def finish_request(self, request_id):
        if request_id in self.request:
            del self.request[request_id]

    def close(self):
        for proc in self.process.values():
            proc[1].value = 5 
        
        self.request = {}
        self.process = {}

        self.running = False

def test_01():
    manager = TaskManager()
    manager.start()
    manager.fork("DEMO")

    manager.send_request({
        'id': 1001,
        'body': "Hello world!"
    })

    manager.send_event(1001, 'cancel')

    print(manager.fetch_data(1001))

if __name__ == '__main__':
    test_01()
    



