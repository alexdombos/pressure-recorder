#!/usr/bin/env python3

from collections import namedtuple
from datetime import datetime
from datetime import timedelta
from threading import Thread
import numpy as np
import os
import ROOT
import socket
import subprocess
import time

class Baratron:
    def __init__(self):
        self.sock = socket.socket(family = socket.AF_INET, type = socket.SOCK_STREAM)
        self.sockfile = self.sock.makefile()
        host = 'redacted for github'
        port = 10005
        server_address = (host, port)
        self.sock.connect(server_address)
        print(f'Baratron connecting to host {self.sock.getpeername()[0]} '
              f'({socket.gethostbyaddr(self.sock.getpeername()[0])[0]}) '
              f'port {self.sock.getpeername()[1]}')
    def read(self):
        message = b'p\r\n'
        self.sock.sendall(message)
        #buffer_size = 1024
        #data = self.sock.recv(buffer_size).decode()
        data = self.sockfile.readline()
        # Since only one sensor is being used, the second reading will be "Off"
        # Therefore, examples of received data are:
        # "973.1e+0 Off"
        # "-10.8e+0 Off"
        # "- 9.1e+0 Off" (note the space between minus sign and number!)
        entries = data.strip().split()
        if len(entries) not in (2, 3):
            raise RuntimeError(f'Baratron entries: Expected 2 or 3, got {len(entries)}\n'
                               f"{'':14}Anomalous entries were {entries}")
        reading_1 = entries[:-1]
        reading_2 = entries[-1]
        if reading_2 != 'Off':
            raise TypeError(f'Baratron entries: Expected second sensor to be "Off"\n'
                            f"{'':11}Anomalous entries were {entries}")
        if len(reading_1) == 1:
            return float(reading_1[0])
        else:
            if reading_1[0] != '-':
                raise TypeError(f'Baratron entries: Expected "-", got {reading_1[0]}\n'
                                f"{'':11}Anomalous entries were {entries}")
            return -1.0 * float(reading_1[1])

VacuumGauge = namedtuple(typename = 'VacuumGauge',
                         field_names = ['ionization_gauge',
                                        'convection_gauge_1',
                                        'convection_gauge_2'])

class HIPPO:
    def __init__(self):
        self.sock = socket.socket(family = socket.AF_INET, type = socket.SOCK_DGRAM)
        host = '<broadcast>'
        port = 56123
        server_address = (host, port)
        self.sock.bind(server_address)
        print(f'HIPPO starting up on host {self.sock.getsockname()[0]} '
              f'port {self.sock.getsockname()[1]}')
    def read(self):
        vacuum_gauges = [None for _ in range(4)]
        while any(vacuum_gauge is None for vacuum_gauge in vacuum_gauges):
            buffer_size = 1024
            data = self.sock.recv(buffer_size).decode()
            # Refer to operating instructions, "Pumping Operations With DCU" by Pfeiffer Vacuum
            if data in (
                    # parameter number = 010
                    # text designation = 'Pumping station ON/OFF'
                    # data = 'turbo {0,1,2,3,4} 010 {000000,111111}'
                    # OFF
                    'turbo 0 010 000000',
                    'turbo 1 010 000000',
                    'turbo 2 010 000000',
                    'turbo 3 010 000000',
                    'turbo 4 010 000000',
                    # ON
                    'turbo 0 010 111111',
                    'turbo 1 010 111111',
                    'turbo 2 010 111111',
                    'turbo 3 010 111111',
                    'turbo 4 010 111111',
                    # roots blower pump
                    # data = 'pumpStatus {6,7,8,10,11} {0,1}'
                    # OFF
                    'pumpStatus 6 0',
                    'pumpStatus 7 0',
                    'pumpStatus 8 0',
                    'pumpStatus 10 0',
                    'pumpStatus 11 0',
                    # ON
                    'pumpStatus 6 1',
                    'pumpStatus 7 1',
                    'pumpStatus 8 1',
                    'pumpStatus 10 1',
                    'pumpStatus 11 1'):
                #entries = data.strip().split()
                #if entries[-1] in ('000000', '0'):
                #    print('========================================\a')
                #    print(f"Pumping status: OFF for '{data}'")
                #    print('========================================\a')
                continue
            elif data[:11] in (
                    # parameter number = 309
                    # text designation = 'Actual rotation speed TMP in Hz'
                    # data = 'turbo {0,1,2,3,4} 309 (speed)'
                    'turbo 0 309',
                    'turbo 1 309',
                    'turbo 2 309',
                    'turbo 3 309',
                    'turbo 4 309'):
                continue
            elif data[:7] in ('m vac_1',
                              'm vac_2',
                              'm vac_3',
                              'm vac_4') :
                entries = data.strip().split()
                if len(entries) != 5:
                    raise RuntimeError(f'HIPPO entries: Expected 5, got {len(entries)}\n'
                                       f"{'':14}Anomalous entries were {entries}")
                gauge_number = int(entries[1][-1])
                pressure_readings = [float(entry) for entry in entries[2:]]
                vacuum_gauges[gauge_number - 1] = VacuumGauge(*pressure_readings)
            else:
                raise RuntimeError(f"Unexpected data from HIPPO: '{data}'")
        return vacuum_gauges

class ReadoutListener:
    def __init__(self):
        self.sock = socket.socket(family = socket.AF_INET, type = socket.SOCK_STREAM)
        host = ''
        port = 56125
        server_address = (host, port)
        self.sock.bind(server_address)
        print(f'Readout listener starting up on host {self.sock.getsockname()[0]} '
              f'port {self.sock.getsockname()[1]}')
        backlog = 1
        self.sock.listen(backlog)

class ROOTRecorder(Thread):
    def __init__(self, run_number):
        Thread.__init__(self)
        self.running = True
        self.run_number = run_number
    def run(self):
        daq_machine_info, local_machine_info = get_date_time()

        baratron = Baratron()
        hippo = HIPPO()

        output = ROOT.TFile(f'pressures_run-{int(self.run_number):04}.root', 'RECREATE')
        output.WriteObject(ROOT.std.string(f'run {self.run_number}'), f'run {self.run_number}')
        output.WriteObject(ROOT.std.string(daq_machine_info), daq_machine_info)
        output.WriteObject(ROOT.std.string(local_machine_info), local_machine_info)
        tree = ROOT.TTree('tree', '')
        date_time = ROOT.TDatime()
        tree.Branch('date_time', date_time)
        baratron_pressure = np.zeros(shape = 1, dtype = np.float64)
        tree.Branch('baratron_pressure', baratron_pressure, 'baratron_pressure/D')
        hippo_pressures = np.zeros(shape = (5, 3), dtype = np.float64)
        tree.Branch('hippo_pressures', hippo_pressures, f'hippo_pressures[{hippo_pressures.shape[0]}][{hippo_pressures.shape[1]}]/D')

        while self.running:
            date_time.Set()
            baratron_pressure[0] = baratron.read()
            hippo_pressures[1:] = [list(vacuum_gauge) for vacuum_gauge in hippo.read()]
            tree.Fill()
            time.sleep(1)

        baratron.sock.close()
        hippo.sock.close()
        tree.Write()
        output.Close()

    def stop(self):
        self.running = False

def get_date_time():

    daq_machine = 'redacted for github'
    daq_machine_time_stamp = subprocess.run(f'ssh {daq_machine} date +%s'.split(),
                                           stdout = subprocess.PIPE,
                                           encoding = 'utf-8',
                                           check = True)
    daq_machine_date_time = datetime.fromtimestamp(int(daq_machine_time_stamp.stdout))

    local_machine = f'{os.getlogin()}@{os.uname().nodename}'
    local_machine_date_time = datetime.now()

    time_difference = abs(daq_machine_date_time - local_machine_date_time)

    print(f'Date/time on DAQ machine ({daq_machine}):', daq_machine_date_time)
    print(f'Date/time on local machine ({local_machine}):', local_machine_date_time)
    print('Time difference:', time_difference)

    #if time_difference > timedelta(seconds = 10):
    #    raise RuntimeError(f'Unacceptable time difference: {time_difference}')

    daq_machine_info = f'{daq_machine} {daq_machine_date_time}'
    local_machine_info = f'{local_machine} {local_machine_date_time}'

    return daq_machine_info, local_machine_info

def main():

    readout_listener = ReadoutListener()
    root_recorder = None

    while True:
        connection = None
        try:
            print('Waiting for a connection')
            connection, client_address = readout_listener.sock.accept()
            print(f'Connection from {socket.gethostbyaddr(client_address[0])[0]} {client_address}')
            buffer_size = 1024
            data = connection.recv(buffer_size).decode().rstrip()
            print(f'Received "{data}"')
            readout_command, run_number = data.strip().split()
            if readout_command == 'Begin':
                root_recorder = ROOTRecorder(run_number)
                root_recorder.start()
            elif readout_command == 'End':
                root_recorder.stop()
                print('\n', end = '')
                assert(run_number == root_recorder.run_number)
        except KeyboardInterrupt as exception:
            print('\n')
            print(type(exception).__name__)
            if root_recorder:
                root_recorder.stop()
            break
        finally:
            if connection:
                connection.close()

if __name__ == '__main__':
    main()
