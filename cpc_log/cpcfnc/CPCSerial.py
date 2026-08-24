# Import libraries
from datetime import datetime
import threading
import time
import traceback

import serial
import random

class CPCSerial:
    def __init__(self, config, data_queue, stop_event, stop_barrier, test=False):
        self.config = config
        self.data_queue = data_queue
        self.stop_event = stop_event
        self.stop_barrier = stop_barrier

        self.process_name = self.config["cpc_name"]
        self.thread = threading.Thread(target=self.record_serial_data)
        
        # GUI testing code here
        self.test = test

    def start(self):
        self.thread.start()

    def serial_startup(self):
        self.ser = serial.Serial(
            port=self.config["serial_port"],
            baudrate=self.config["serial_baud"],
            bytesize=self.config["serial_bytesize"],
            parity=self.config["serial_parity"],
            timeout=self.config["serial_timeout"],
        )
        self.ser.flushInput()

    def serial_startup_commands(self):
        if self.config["start_commands"]:
            for start_command in self.config["start_commands"]:
                self.ser.write((start_command + "\r\n").encode())
                time.sleep(0.1)
                self.ser.flushInput()
        if self.config["set_time"]:
            date_strings= ["%y/%m/%d","%H:%M:%S"]
            for date_string in date_strings:
                self.ser.write((f"rtc,{datetime.now().strftime(date_string)}\r\n").encode())
                time.sleep(0.1)
                self.ser.flushInput()

    def record_serial_data(self):
        if self.test == False:
            # Setup CPC serial connection
            self.serial_startup()

            # Send startup commands
            self.serial_startup_commands()

        curr_time = time.monotonic()

        # Loop until stop event is set
        while not self.stop_event.is_set():
            try:
                # Send startup commands if CPC restarts often
                if self.process_name == "3025_Jim's":
                    if time.monotonic() % 60 < 1:
                        self.serial_startup_commands()
                
                # Store responses in a list
                responses = []

                if self.config["serial_commands"]:
                    for command in self.config["serial_commands"]:
                        # GUI testing code here
                        if self.test:
                            responses.append(random.randint(0,1000))
                            continue

                        # Send command to serial port
                        self.ser.write((command + "\r").encode())

                        # Read response from serial port
                        response = self.ser.readline().decode().rstrip()
                        response = response.split(",")

                        # Append response to the list
                        responses.extend(response)
                else:

                    # GUI testing code here
                    if self.test:
                        response_count = max(len(self.config["cpc_header"]) - 2, 1)
                        responses = [
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            random.randint(100, 10000),
                        ]
                        responses.extend(random.randint(0, 100) for _ in range(response_count - 2))

                    else:
                        # Read response from serial port
                        response = self.ser.readline().decode().rstrip()
                        response = response.split(",")

                        # Append response to the list
                        responses = response

                # Create dictionary with responses
                responses = [self.process_name, datetime.now()] + responses
                serial_output = dict(zip(self.config["cpc_header"], responses))

                # Modify concentration
                if not self.config["default_flow"]:
                    try:
                        calc_conc = (
                        float(serial_output["1 second counts"])
                        / self.config["cpc_flowrate"]
                        )
                        serial_output["concentration"] = "{:.2f}".format(calc_conc)
                    except ValueError:
                        serial_output["concentration"] = ""
                        
                # Share CPC data with other threads
                self.data_queue.put(serial_output)

                # Schedule the next update
                curr_time = sched_update(self.process_name, curr_time)

            except Exception as e:
                print(f"Error: {self.process_name}")
                print(traceback.format_exc())


def sched_update(process_name, curr_time, update_time=1):
    # Calculate sleep time based on seconds till next update
    next_time = curr_time + update_time - time.monotonic()

    # Set sleep time to 0 if program is behind
    if next_time < 0:
        # Skip loops if the program is behind
        missed_loops = abs(next_time) / update_time
        if missed_loops > 1:
            curr_time = curr_time + update_time * int(missed_loops)
        next_time = 0
        print(f"Slow: {process_name}" + str(datetime.now()))

    # Sleep
    time.sleep(next_time)

    # Update current time for next interval
    curr_time = curr_time + update_time
    return curr_time
    
