from utils import *
from Traumschreiber import *
from twisted.internet import reactor, defer, task
#from twisted.enterprise import adbapi
import itertools
import random
from .experiment import state, experiment
import datetime
import pandas

db_ready = False
dbpool = None

#3600s*250 = 900000 samples
MAX_SAMPLES = 100000

data_store = []
data_idx = 0

def data_callback(data_in):
    global data_idx

    new_data = np.frombuffer(np.array(data_in, dtype=np.int8), dtype=np.dtype('<i2')).reshape((8,))
    inrow =  np.hstack((datetime.datetime.now(), new_data, state["highlighted"].ravel(), state["target"]))
    data_store.append(inrow)
    data_idx += 1

def data_save(ex):
    print(data_store)
    df = pandas.DataFrame(data_store, columns=
        ["timestamp"] +
        ["channel{}".format(i) for i in range(8)] +
        ["highlighted{}".format(i) for i in range(30)]+
        ["target"]).set_index("timestamp")

    df.to_pickle("recording.pkl")

async def run_experiment(addr, training_text="", **kwargs):
    global db_ready
    async with Traumschreiber(addr=addr) as t:
        await t.start_listening(data_callback)
        await experiment(**kwargs)
        db_ready = False

def main(reactor):
    ex = defer.ensureDeferred(run_experiment(None, targets="HALLO WELT"))
    ex.addCallback(data_save)
    return ex

task.react(main)
