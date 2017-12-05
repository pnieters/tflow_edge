from utils import *
from Traumschreiber import *
from twisted.internet import reactor, defer, task
import itertools
import random


experiment_state = {}

def char2idx(char, grid_shape):
    symbols = "ABCDEFGHIJKLMNOPQRSTUVWXYZ !?."
    idx = symbols.index(char.upper())
    assert idx >= 0, "Character '{}' not in the list of allowed symbols ({})".format(char, symbols)
    return np.unravel_index(idx, grid_shape)

async def experiment(targets=None, max_runs=None, repetitions=1, flash_time=0.4):
    global experiment_state
    width,height = boilerplate()

    # Create 5x6 grid of symbols
    grid_shape = (5,6)
    g = Grid(*grid_shape, "bci/symbols.png", img_rows=5, img_cols=6, coords=((-0.75,0.5), (0.75, -0.5)), space=0.5)

    if targets is None:
        targets = itertools.repeat(None)

    combinations = [("row", x) for x in range(grid_shape[0])] \
                 + [("col", x) for x in range(grid_shape[1])]

    def render(draw_grid=True):
        #<rendering/>
        glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
        if draw_grid:
            g.draw()
        glFlush()
        pygame.display.flip()
        #</rendering>

    pause = False
    for target in itertools.islice(targets, max_runs):

        flashed=g.flash([],[])
        # Clear screen before each trial
        render(False)

        # right now, there is neither a stimulus nor targets
        experiment_state["flashed"] = flashed
        experiment_state["target"] = None

        await async_sleep(2)

        # Set symbol to focus, if any
        if target is not None:
            char_idx = char2idx(target, grid_shape)
            # Show the desired character
            g.symbols[char_idx[0], char_idx[1]].color=np.array([1.0,0.0,0.0,1.0])

        render()
        await async_sleep(2)

        repeat = repetitions
        while repeat>0:
            if pause:
                # Poll event queue
                for event in pygame.event.get():
                    if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                        pygame.quit()
                        return
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_SPACE:
                            pause = not pause
                            print("paused" if pause else "unpaused")
                await async_sleep(1)
                if pause:
                    continue

            random.shuffle(combinations)
            for rowcol,num in combinations:
                # Poll event queue
                for event in pygame.event.get():
                    if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                        pygame.quit()
                        return
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_SPACE:
                            pause = not pause
                            print("paused" if pause else "unpaused")
                if pause:
                    break

                # Flash appropriate symbols
                flashed = g.flash(rows=num) if rowcol=="row" else g.flash(cols=num)
                # draw the grid
                render()

                # record stimulus and target
                experiment_state["flashed"] = flashed
                experiment_state["target"] = None if not target else char_idx 

                # sleep a while
                await async_sleep(flash_time)
            else:
                repeat-=1

        # Release focused symbol, if any
        if target is not None:
            g.symbols[char_idx[0], char_idx[1]].color=np.array([1.0,1.0,1.0,0.25])

    clock = pygame.time.Clock()
    pygame.quit()

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
