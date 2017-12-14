import itertools
import random
import datetime
import pandas

from .experiment import state, experiment
from Traumschreiber import *
from twisted.internet import reactor, defer, task
#from twisted.enterprise import adbapi
from utils import *


db_ready = False
dbpool = None

#3600s*250 = 900000 samples
MAX_SAMPLES = 100000

data_store = []
data_idx = 0

########################################
# ID of the traumschreiber you are using
ID = 2
GAIN = 32
########################################

TRAUMSCHREIBER_ADDR = "74:72:61:75:6D:{:02x}".format(ID)


def data_callback(data_in):
    global data_idx
    inrow =  np.hstack((datetime.datetime.now(), data_in.ravel(), state["highlighted"].ravel(), state["interval"], state["target"]))
    data_store.append(inrow)
    data_idx += 1

def data_save(ex):
    df = pandas.DataFrame(data_store, columns=
        ["timestamp"] +
        ["channel{}".format(i) for i in range(8)] +
        ["highlighted{}".format(i) for i in range(30)]+
        ["interval"] +
        ["target"]).set_index("timestamp")

    df.to_pickle("recording.pkl")

async def run_experiment(addr, training_text="", **kwargs):
    global db_ready
    async with Traumschreiber(addr=addr) as t:
        await t.start_listening(data_callback)
        await t.set(gain=GAIN)
        await t.set(gain=GAIN)
        await t.set(gain=GAIN)
        await experiment(**kwargs)
        db_ready = False

def main(reactor):
    ex = defer.ensureDeferred(run_experiment(TRAUMSCHREIBER_ADDR, targets="HALLO WELT"))
    ex.addCallback(data_save)
    return ex

task.react(main)
