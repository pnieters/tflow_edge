# small example that (hopefully) runs a graph on the compute stick

import sys
import numpy as np

from mvnc import mvncapi as mvnc

x_size = 8
y_size = 1
z_size = 1
T = 100


devices = mvnc.EnumerateDevices() # ...
if len(devices) == 0:
    print('No devices found')
    sys.exit()

device = mvnc.Device(devices[0])
device.OpenDevice()

with open('graph', 'rb') as f:
    graphfile = f.read()

graph = device.AllocateGraph(graphfile)

inp_ = np.random.rand(x_size,y_size,z_size)
inp_ = inp_.astype(np.float32)

# print('Start download to NCS...')
# graph.LoadTensor(inp_, 'user object')
# output, userobj = graph.GetResult()
#
# print('Input: {} \t \t Output: {}'.format(inp_, output))

def foo(input_, graph):
    graph.LoadTensor(input_, 'user object')
    output, userobj = graph.GetResult()
    return output
