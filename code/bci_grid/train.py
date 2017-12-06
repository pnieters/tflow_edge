from utils import *
from Traumschreiber import *
from twisted.internet import reactor, defer, task
import itertools
import random
from .experiment import experiment

# This global variable (buh!) keeps track of the current state of the experiment
experiment_state = {}

def data_callback(data_in):
    print(experiment_state, data_in)


async def run_experiment(addr, training_text="", **kwargs):
    async with Traumschreiber(addr=addr) as t:
        await t.start_listening(data_callback)
        await experiment(**kwargs)

def main(reactor):
    #d = defer.ensureDeferred(experiment("HALLO WELT"))
    d = defer.ensureDeferred(run_experiment(None, targets="HALLO WELT"))
    return d

task.react(main)
