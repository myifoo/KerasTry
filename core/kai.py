from keras.models import Sequential
from keras.layers import Dense
from keras import optimizers
from keras.callbacks import Callback
from time import time
import keras.backend as kb
import numpy as np
import pandas as pd

def normalize(values, degrees):
    # 多维数据的归一化
    if type(values[0]) == list:
        len_1 = len(values)
        len_2 = len(values[0])

        valuess_std = []
        for _values in values:
            v_max = max(_values)
            v_min = min(_values)
            valuess_std.append(list(map(lambda v: (v-v_min)/(v_max-v_min), _values)))

        X = []
        Y = valuess_std[0]
        for i in range(len_2):
            tmp_x = []
            for j in range(1, len_1):
                tmp_x.append(valuess_std[j][i])

            X.append(tmp_x)

        return X, Y, min(values[0]), max(values[0]) # values[0] 制定为 output 数据


    length = len(values)
    v_min = min(values)
    v_max = max(values)

    values_std = list(map(lambda v: (v-v_min)/(v_max-v_min), values))# normalization
    # 一维数据，归一化处理，并转换为多维数据
    if degrees > length:
        raise ValueError('relation degrees is greater than the length of values: degrees = %d, length = %d' % degrees, length)

    X = []
    Y = []
    for i in range(degrees, length):
        X.append(values_std[i-degrees:i])
        Y.append(values_std[i])
    
    return X, Y, v_min, v_max

    



def multi_normalize(valuess):
    len_1 = len(valuess)
    len_2 = len(valuess[0])

    valuess_std = []
    for values in valuess:
        v_max = max(values)
        v_min = min(values)
        valuess_std.append(list(map(lambda v: (v-v_min)/(v_max-v_min), values)))

    X = []
    Y = valuess_std[0]
    for i in range(len_2):
        tmp_x = []
        for j in range(1, len_1):
            tmp_x.append(valuess_std[j][i])

        X.append(tmp_x)

    return X, Y

def multi_renormalize():
    pass


def _normalize(values, percent):
    "normalize values to [0, 1]"
    v_min = values.min()
    v_max = values.max()

    values_std = (values - v_min)/(v_max - v_min) # normalization

    X = []
    Y = []
    for i in range(32, len(values_std)):
        X.append(values_std[i-32:i])
        Y.append(values_std[i])

    num = round(values.size * percent)
    return np.array(X[:num]), np.array(Y[:num]), np.array(X[num:])

def renormalize(values_std, min, max):
    "renormalize values_std to [min, max]"
    return list(map(lambda v: v*(max - min) + min, values_std))


def simple_model(request):
    optimizer=request['optimizer'] 
    step=request['step']
    nnum=request['nnum']
    loss='mean_squared_error'
    _optimizer = None

    kb.clear_session()

    if optimizer == "adma":
        _optimizer = optimizers.Adam(lr=step)
    else:
        _optimizer = optimizers.Adam(lr=step)

    model = Sequential()
    model.add(Dense(nnum, input_dim=32, init='normal', activation='relu'))
    model.add(Dense(1, init='normal'))
    model.compile(loss=loss, optimizer=_optimizer)
    return model

def smart_model(request, degrees):
    step = request.get('step', 0.01)
    layers = request.get('layers', [degrees, 10, 1])
    activation = request.get('activation', 'relu')

    def get_optimizer():
        _optimizer =  request.get('optimizer', "adam")
        if _optimizer == "adma":
            return optimizers.Adam(lr=step)
        else:
            return optimizers.Adam(lr=step)

    if len(layers) < 3:
        raise ValueError("lentgh of layers must >= 3")

    kb.clear_session() # clear cached model in process
    model = Sequential()
    model.add(Dense(layers[1], input_dim=layers[0], init='normal', activation=activation))

    for i in range(3, len(layers)):
        model.add(Dense(layers[i], init='normal', activation=activation))

    model.add(Dense(layers[-1], init='normal'))
    model.compile(loss=request.get('loss','mean_squared_error'), optimizer=get_optimizer())
    return model
        
class EpochEndCallback(Callback):
    def __init__(self, action):
        self.last_time = time()
        self.action = action

    def on_epoch_end(self, epoch, logs=None):
        try:
            self.action(epoch, logs, self.last_time)
            self.last_time = time()
        except Exception as e:
            print("EpochEndCallback error: %s" % str(e))
        
if __name__ == "__main__":
    print("keras ai module")