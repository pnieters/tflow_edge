import asyncio
import logging
loglevel = logging.INFO
logging.basicConfig(level=loglevel)
import numpy as np

from Traumschreiber import *
from twisted.internet import reactor, defer, task

SHOWPLOT = True

########################################
# ID of the traumschreiber you are using
ID = 3
########################################

GAIN = 32
TRAUMSCHREIBER_ADDR = "74:72:61:75:6D:{:02x}".format(ID)

# reference channel
REF_CHANNEL = 7

duration=2500
cnt = 0
data = np.zeros((duration,9), dtype='<i2')

def data_callback(data_in):
    global data
    global cnt

    data = np.roll(data, -1, axis=0)
    # data[-1,:] = data_in
    data[-1,:] = reref_channels(data_in, REF_CHANNEL)
    cnt += 1

if SHOWPLOT:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib import pyplot as pp
    def plot():
        try:
            for i,line in enumerate(lines):
                fig.canvas.restore_region(background[i])
                line.set_data(tt, data[:,i])
                ax[i].draw_artist(line)
                #fig.canvas.set_window_title("Data (received {} packages/second)".format(pkgs_per_second))
                fig.canvas.blit(ax[i].bbox)
        except Exception as e:
            print("Encountered exception in plot callback: {}".format(e))

async def run():
    async with Traumschreiber(addr=TRAUMSCHREIBER_ADDR) as t:
        await t.start_listening(data_callback)
        await async_sleep(1)
        await t.set(a_on=1,b_on=1,color=(255,0,0), gain=GAIN)
        await async_sleep(1)
        await t.set(a_on=0,color=(0,255,0))
        await async_sleep(1)
        await t.set(a_on=1,b_on=0,color=(0,255,0))
        await async_sleep(1)
        await t.set(color=(255,255,0))
        await async_sleep(1)
        await t.set(b_on=1,color=(255,255,0))
        await async_sleep(1)
        await t.set(a_on=1,color=(125,125,0))
        await async_sleep(1)
        await t.set(a_on=0,b_on=0,color=(0,0,0))
        await async_sleep(50)
        if SHOWPLOT:
            plot()

def main(reactor):
    d = defer.ensureDeferred(run())
    return d


if SHOWPLOT:
    # Plot lines
    fig, ax = pp.subplots(nrows=9, ncols=1, figsize=(15,10), sharex=True, sharey=True)
    fig.show()
    fig.canvas.draw()

    tt = np.arange(duration)
    lines = [ax[i].plot(tt, data[:,i])[0] for i in range(9)]
    hlines = [(ax[i].axhline(y=2**11, c="black"), ax[i].axhline(y=-2**11, c="black")) for i in range(9)]
    ax[0].set_ylim([-2**12, 2**12])
    background = [fig.canvas.copy_from_bbox(ax[i].bbox) for i in range(9)]
    task.LoopingCall(plot).start(0.5)

task.react(main)
