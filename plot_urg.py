from pyurg import UrgDevice
import matplotlib.pyplot as plt
import matplotlib.animation as anim
import threading
import numpy as np

def start_map():
    fig = plt.figure()
    map, = plt.plot((-10000, 10000),(-10000, 10000),'x')
    plt.axis('equal')
    plt.grid()
    ani = anim.FuncAnimation(fig, update_map, fargs=(map, ), blit=True)
    plt.show()

def update_map(n, map):
    global data, new_data

    if new_data:
        new_data = False
        d = np.array(data)
        print(n)
        theta = np.pi/4 + np.arange(417) * 2 * np.pi / 554    # TODO: Parameterise
        x = np.multiply(d, np.cos(theta)) 
        y = np.multiply(d, np.sin(theta))
        map.set_data(x, y)

    return map,

def start_urg():
    global data, new_data, run
    urg = UrgDevice()
    if not urg.connect('COM18'):
        print('Connect error')
        exit()

    while run:
        data, tm = urg.capture()
        if len(data) > 0:
            new_data = True

#############################################################################
new_data = False
run = True
thread = threading.Thread(target=start_urg)
thread.start()
start_map()
run = False
