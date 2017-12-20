import itertools
import random
import datetime
import pandas

from .experiment import state, experiment
from Traumschreiber import *
from twisted.internet import reactor, defer, task
#from twisted.enterprise import adbapi
from utils import *

# reference channel
REF_CHANNEL = 7
data_store = []

########################################
# ID of the traumschreiber you are using
ID = 4
GAIN = 32
########################################

TRAUMSCHREIBER_ADDR = "74:72:61:75:6D:{:02x}".format(ID)

def data_callback(data_in):
    inrow =  np.hstack((datetime.datetime.now(), reref_channels(data_in, REF_CHANNEL).ravel(), state["highlighted"], state["interval"]))
    data_store.append(inrow)

def data_save(ex):
    df = pandas.DataFrame(data_store, columns=
        ["timestamp"] +
        ["channel{}".format(i) for i in range(9)] +
        ["highlighted"]+
        ["interval"]).set_index("timestamp")

    df.to_pickle("erp_test/recording.pkl")

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
    ex = defer.ensureDeferred(run_experiment(TRAUMSCHREIBER_ADDR, flashes=100, on_duration=0.1, off_duration=0.5))
    ex.addCallback(data_save)
    return ex

task.react(main)
