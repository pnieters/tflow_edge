# small example that (hopefully) runs a graph on the compute stick

import sys
import numpy as np

from mvnc import mvncapi as mvnc

# params
N_CHANNELS = 1
N_WINDOWWIDTH = 1
T_TIMESTEPS = 100

def random_data():
    """ Generate random input with some non-linear transform as the
    target variable
    """
    input_ = np.random.rand(N_CHANNELS, N_WINDOWWIDTH, T_TIMESTEPS)
    output = - input_**3 + input_**2 + input_

    return input_.astype(np.float32), output.astype(np.float32)

def eval_on_usb(input_, graph):
    """ Load input onto the USB-Device graph and evaluate.
    """
    graph.LoadTensor(input_, 'user object')
    output, _ = graph.GetResult()
    return output

"""
mvnc.EnumerateDevices() returns a list of usb devices with
the Intel(r) Movidius Neural Compute Stick as the first element
"""
devices = mvnc.EnumerateDevices()
if len(devices) == 0:
    print('No devices found')
    sys.exit()

# Open the first neural compute stick device
device = mvnc.Device(devices[0])
device.OpenDevice()

# The graphfile contains the tensorflow graph compiled for the NCS
# via mvNCCompile
with open('graph', 'rb') as f:
    graphfile = f.read()

# Load the graph on the USB-Device
graph = device.AllocateGraph(graphfile)

# get T_TIMESTEPS examples.
inp_, target = random_data()

print("Eval on the NCS...")

err = 0
for t in range(T_TIMESTEPS):
    yhat = eval_on_usb(inp_[:,:,t], graph)
    print("Input: {} \t \t Target: {} \t \t Result: {}".format(inp_[:,:,t], target[:,:,t], yhat))
    err += (yhat - target[:,:,t]) ** 2

RMSE = np.sqrt( 1/T_TIMESTEPS * err )
print("Average RMSE: {}".format(RMSE))

