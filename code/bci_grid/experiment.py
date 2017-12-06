from utils import *
from Traumschreiber import *
from twisted.internet import reactor, defer, task
import itertools
import random

# This module-level variable (buh!) keeps track of the current state of the experiment
state = {}

def char2idx(char, grid_shape):
    """ Finds a symbol in the symbol list and converts its position to grid coordinates"""
    symbols = "ABCDEFGHIJKLMNOPQRSTUVWXYZ !?."
    idx = symbols.index(char.upper())
    assert idx >= 0, "Character '{}' not in the list of allowed symbols ({})".format(char, symbols)
    return np.unravel_index(idx, grid_shape), idx


# This is an asynchroneous co-routine for running the experiment itself
async def experiment(targets=None, max_runs=None, repetitions=1, flash_time=0.4):
    """ BCI - EEG decoding - Grid stimulus (COROUTINE)

    A grid of symbols is shown on screen, rows and columns of which are randomly
    highlighted (once each).

    Args:
        targets (str):      String of symbols to use as targets during stimulation. Defaults to no targets.
                            When no targets are given, this can be used for testing predictions
        max_runs (int):     Maximum number of runs to use. Defaults to no limit.
        repetitions (int):  Number of repetitions to use per symbol. Defaults to 1 (no additional repetitions).
                            For each repetition, each column and row of the grid will be highlighted exactly once.
        flash_time (float): Time in seconds of each flashing each row/column. Defaults to 0,4s.
    """
    global state
    width,height = boilerplate()

    # Create 5x6 grid of symbols
    grid_shape = (5,6)
    g = Grid(*grid_shape, "bci_grid/symbols.png", img_rows=5, img_cols=6, coords=((-0.75,0.5), (0.75, -0.5)), space=0.5)

    if targets is None:
        targets = itertools.repeat(None)

    # Flash each row/column exactly once (per repetition)
    combinations = [("row", x) for x in range(grid_shape[0])] \
                 + [("col", x) for x in range(grid_shape[1])]

    # Little helper function to do the actual rendering
    def render(draw_grid=True):
        glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
        if draw_grid:
            g.draw()
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

    pause = False
    for target in itertools.islice(targets, max_runs):

        # Reset highlights and clear screen before each trial
        flashed=g.flash([],[])
        render(False)

        # right now, there is neither a stimulus nor targets
        state["highlighted"] = flashed
        state["target"] = None
        await async_sleep(2)

        # Set symbol to focus, if any
        if target is not None:
            char_idx2d, char_idx = char2idx(target, grid_shape)
            # Show the desired character
            g.symbols[char_idx2d[0], char_idx2d[1]].color=np.array([1.0,0.0,0.0,1.0])

        # draw grid w/o any highlights
        render()
        await async_sleep(2)

        # start repetitions
        repeat = repetitions
        while repeat>0:
            # If it's currently paused, poll for events
            if pause:
                # Poll event queue
                events = poll_events()
                if "QUIT" in events:
                    return
                if "PAUSE" in events:
                    pause = False
                    await async_sleep(1)
                    continue

            random.shuffle(combinations)
            for rowcol,num in combinations:
                # Poll event queue
                events = poll_events()
                if "QUIT" in events:
                    return
                if "PAUSE" in events:
                    pause = True
                    break

                # Flash appropriate symbols
                flashed = g.flash(rows=num) if rowcol=="row" else g.flash(cols=num)
                # draw the grid
                render()

                # record stimulus and target
                state["highlighted"] = flashed
                state["target"] = None if not target else char_idx

                # sleep a while
                await async_sleep(flash_time)
            else:
                repeat-=1

        # Release focused symbol, if any
        if target is not None:
            g.symbols[char_idx2d[0], char_idx2d[1]].color=np.array([1.0,1.0,1.0,0.25])

    # The experiment is done!
    pygame.quit()
