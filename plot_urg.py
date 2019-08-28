from pyurg import UrgDevice
import matplotlib.pyplot as plt
import matplotlib.animation as anim
import threading
import numpy as np
import sys

def start_map():
    fig = plt.figure()
    map, pnt = plt.plot((-10000, 10000),(-10000, 10000),'x', 0,0,'rp')
    text = plt.text(0,0,'TARGET')
    plt.axis('equal')
    plt.grid()
    ani = anim.FuncAnimation(fig, update_map, fargs=(map, pnt, text), blit=True)
    plt.show()

def update_map(n, map, pnt, text):
    global data, new_data
    global target_selected, target
    global min_target, max_target

    if new_data:
        new_data = False
        d = np.array(data)
        print(n)
        theta = np.pi/4 + np.arange(417) * 2 * np.pi / 554    # TODO: Parameterise
        x = np.multiply(d, np.cos(theta)) 
        y = np.multiply(d, np.sin(theta))
        map.set_data(x, y)
        pnt.set_data(x[target], y[target])
        text.set_position((x[target], y[target]))
        text.set_text(str(target))

        if not target_selected:
            target += 1
            if target > max_target:
                target = min_target

    return map, pnt, text

def start_urg():
    global data, new_data, run
    urg = UrgDevice()
    if not urg.connect('COM12'):
        print('Connect error')
        exit()

    while run:
        data, tm = urg.capture()
        if len(data) > 0:
            new_data = True

#############################################################################
new_data = False
run = True
if len(sys.argv) == 2:
    target_selected = True
    target = int(sys.argv[1])
elif len(sys.argv) == 3:
    target_selected = False
    min_target = int(sys.argv[1])
    max_target = int(sys.argv[2])
    target = min_target
else:
    target_selected = False
    target = 0
    min_target = 0
    max_target = 416
thread = threading.Thread(target=start_urg)
thread.start()
start_map()
run = False
