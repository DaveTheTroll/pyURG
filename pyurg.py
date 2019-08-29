#!/usr/bin/env python
# -*- coding:utf-8 -*-

# The MIT License
#
# Copyright (c) 2010 Yota Ichino
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import serial
import re
import math
import time

class UrgDevice(serial.Serial):
    def __init__(self):
        super(serial.Serial, self).__init__()

    def __del__(self):
        self.laser_off()

    def connect(self, port = '/dev/ttyACM0', baudrate = 115200, timeout = 0.1):
        '''
        Connect to URG device
        port      : Port or device name. ex:/dev/ttyACM0, COM1, etc...
        baudrate  : Set baudrate. ex: 9600, 38400, etc...
        timeout   : Set timeout[sec]
        '''
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        try:
            self.open()
        except:
            return False
        
        if not self.isOpen():
            return False

        self.set_scip2()
        self.get_parameter()
        return True

    def flush_input_buf(self):
        '''Clear input buffer.'''
        self.flushInput()

    def send_command(self, cmd):
        '''Send command to device.'''
        self.write(cmd)

    def __receive_data(self):
        #return self.readlines()
        get = []
        line = (0,0)
        while len(line) > 1:
            line = self.readline()
            get.append(line)

        return get
    
    def set_scip2(self):
        '''Set SCIP2.0 protcol'''
        self.flush_input_buf()
        self.send_command(b'SCIP2.0\n')
        return self.__receive_data()

    def get_version(self):
        '''Get version information.'''
        if not self.isOpen():
            return False

        self.flush_input_buf()
        self.send_command(b'VV\n')
        get = self.__receive_data()
        return get

    def get_parameter(self):
        '''Get device parameter'''
        if not self.isOpen():
            return False
        
        self.send_command(b'PP\n')
        
        get = self.__receive_data()
        
        # check expected value
        if not (get[:2] == [b'PP\n', b'00P\n']):
            return False
        
        # pick received data out of parameters
        self.pp_params = {}
        for item in get[2:10]:
            tmp = re.split(r':|;', item.decode('utf-8'))[:2]
            self.pp_params[tmp[0]] = tmp[1]
        return self.pp_params

    def laser_on(self):
        '''Turn on the laser.'''
        if not self.isOpen():
            return False
        
        self.send_command(b'BM\n')
        
        get = self.__receive_data()
        
        if not(get == [b'BM\n', b'00P\n', b'\n']) and not(get == [b'BM\n', b'02R\n', b'\n']):
            return False
        return True
        
    def laser_off(self):
        '''Turn off the laser.'''
        if not self.isOpen():
            return False

        self.flush_input_buf()
        self.send_command(b'QT\n')
        get = self.__receive_data()
        
        if not(get == [b'QT\n', b'00P\n', b'\n']):
            return False
        return True
    
    def __decode(self, encode_str):
        '''Return a numeric which converted encoded string from numeric'''
        decode = 0
        
        for c in encode_str:
            decode <<= 6
            decode &= ~0x3f
            decode |= ord(c) - 0x30
            
        return decode

    def __decode_length(self, encode_str, byte):
        '''Return leght data as list'''
        data = []
        
        for i in range(0, len(encode_str), byte):
            split_str = encode_str[i : i+byte]
            data.append(self.__decode(split_str))
            
        return data

    def index2rad(self, index):
        '''Convert index to radian and reurun.'''
        rad = (2.0 * math.pi) * (index - int(self.pp_params['AFRT'])) / int(self.pp_params['ARES'])
        return rad

    def create_capture_command(self, start=-1, stop=-1):
        '''create capture command.'''
        if start == -1:
            start = self.pp_params['AMIN']
        if stop == -1:
            stop = self.pp_params['AMAX']
        cmd = ('GD' + str(start).zfill(4) + str(stop).zfill(4) + '01\n').encode('utf-8')
        return cmd

    def scan_sec(self):
        '''Return time of a cycle.'''
        rpm = float(self.pp_params['SCAN'])
        return (60.0 / rpm)

    def prep_fast_capture(self, start=-1, stop=-1):
        self.capture_command = self.create_capture_command(start, stop)
        if not self.laser_on():
            raise "Laser On Failure"
    
    def fast_capture(self):
        self.send_command(self.capture_command)
        return self.__retreive_capture(self.capture_command)

    def __retreive_capture(self, cmd):
        get = self.__receive_data()

        # checking the answer
        if not (get[:2] == [cmd, b'00P\n']):
            return [], -1
        
        # decode the timestamp
        tm_str = get[2][:-1] # timestamp
        timestamp = self.__decode(tm_str.decode('utf-8'))
        
        # decode length data
        length_byte = 0
        line_decode_str = ''
        if cmd[:2] == (b'GS' or b'MS'):
            length_byte = 2
        elif cmd[:2] == (b'GD' or b'MD'):
            length_byte = 3
        # Combine different lines which mean length data
        NUM_OF_CHECKSUM = -2
        for line in get[3:]:
            line_decode_str += line[:NUM_OF_CHECKSUM].decode('utf-8')

        # Set dummy data by begin index.
        length_data = [-1 for i in range(int(self.pp_params['AMIN']))]
        length_data += self.__decode_length(line_decode_str, length_byte)
        return (length_data, timestamp)
        
    def capture(self, start=-1, stop=-1):
        if not self.laser_on():
            return [], -1

        # Receive length data
        cmd = self.create_capture_command(start, stop)
        self.flush_input_buf()
        self.send_command(cmd)
        #time.sleep(0.1)

        return self.__retreive_capture(cmd)

if __name__ == '__main__':
    from datetime import datetime

    urg = UrgDevice()
    if not urg.connect('COM18'):
        print('Connect error')
        exit()

    for key, val in urg.pp_params.items():
        print(key, val)

    urg.prep_fast_capture(200, 210)

    for j in range(100):
        start = datetime.now()
        for i in range(100):
            data, tm = urg.fast_capture()
            if data == 0:
                continue
        end = datetime.now()
        print("100 Readings (s): ", (end-start).total_seconds())
