from utils import *
from Traumschreiber import *
from twisted.internet import reactor, defer, task
import itertools
import random


# This module-level variable (buh!) keeps track of the current state of the experiment
state = {"interval": 0, "highlighted": False}

# This is an asynchroneous co-routine for running the experiment itself
async def experiment(flashes=100, on_duration=1.0, off_duration=1.0, mode="fixed"):
    """ ERP test stimulus

    Shows flashes of bright stimuli alternating with a black screen.

    Args:
        flashes (int):        Number of flashes to show
        on_duration (float):  Duration of the flashes if mode == "fixed", else mean duration of flashes
        off_duration (float): Interval between flashes if mode == "fixed", else mean interval between flashes
        mode (str):           Either "fixed" (default) or "random"; if "random", intervals are randomly drawn
    """
    global state

    width,height = boilerplate()

    # Little helper function to do the actual rendering
    def render(color=(0,0,0,1)):
        glClearColor(*color)
        glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
        glFlush()
        pygame.display.flip()

    # Little helper function to poll & parse the events triggered
    def poll_events():
        events = []
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                pygame.quit()
                events.append("QUIT")
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    events.append("PAUSE")
        return events

    # start repetitions
    for i in range(flashes):
        # Poll event queue
        events = poll_events()
        if "QUIT" in events:
            return
        if "PAUSE" in events:
            await async_sleep(1)
            continue


        # bright screen
        render((1,1,1,1))
        state["highlighted"] = True
        on = on_duration if mode == "fixed" else np.random.exponential(on_duration)
        await async_sleep(on)

        # black screen
        render()
        state["highlighted"] = False
        off = off_duration if mode == "fixed" else np.random.exponential(off_duration)
        await async_sleep(off)
        state["interval"] += 1

    # The experiment is done!
    pygame.quit()
