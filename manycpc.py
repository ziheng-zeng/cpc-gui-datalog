import os
import queue
import threading
import tkinter as tk
import yaml

from cpcfnc import CPCSerial, DataLogger, DataVisualizer

class App:
    def __init__(self, root, config_file):
        # Load configuration, start threads, etc.
        self.root = root
        self.config_file = config_file
        self.program_path = os.path.dirname(os.path.realpath(__file__))
        with open(
            os.path.join(self.program_path, self.config_file),
            "r",
            encoding="utf-8",
        ) as f:
            self.config = yaml.safe_load(f)

        self.num_cpcs = self.config["num_cpcs"]
        # Gather all serial ports into a list
        self.serial_ports = [self.config[f"cpc{i}"]["serial_port"] for i in range(1, self.num_cpcs + 1)]
        # Gather all cpc names into a list
        self.cpc_names = [self.config[f"cpc{i}"]["cpc_name"] for i in range(1, self.num_cpcs + 1)]
        
        # Threading related initializations
        self.serial_queues = [queue.Queue() for _ in range(self.num_cpcs)]
        self.stop_threads = threading.Event()

        # Initialize CPC classes, test=True when testing GUI offline
        self.cpcs = []
        for i in range(self.num_cpcs):
            cpc = CPCSerial.CPCSerial(
                self.config[f"cpc{i+1}"],
                self.serial_queues[i],
                self.stop_threads,
                None, test=True
            )
            self.cpcs.append(cpc)

        self.logger = DataLogger.DataLogger(self.config, self.cpc_names)
        self.visualizer = DataVisualizer.DataVisualizer(root, self.config, self.cpc_names)

        # Start threads for all CPCs
        for cpc in self.cpcs:
            cpc.start()
        
        # Check the queue every 1s
        root.after(1000, self.check_queue)

    def check_queue(self):
        # Flag to track if we have new data
        new_data_available = False
        all_cpc_data = {}
        # Get data from all CPCs and store for plotting and writing to CSV
        for i in range(self.num_cpcs):
            try:
                data_point = self.serial_queues[i].get_nowait()
                #print(data_point['datetime'])
                self.visualizer.update_cpc_display(i, data_point)

                # Extract cpc_name from the data_point
                cpc_name = self.cpc_names[i]
                if cpc_name not in self.visualizer.plot_data:
                    self.visualizer.plot_data[cpc_name] = {'datetime': [], 'concentration': []}

                # Parse datetime and concentration, add to the plot data structure
                parsed_datetime = data_point['datetime']
                concentration = float(data_point['concentration'])
                self.visualizer.plot_data[cpc_name]['datetime'].append(parsed_datetime)
                self.visualizer.plot_data[cpc_name]['concentration'].append(concentration)

                all_cpc_data[cpc_name] = data_point

            except queue.Empty:
                pass

        if all_cpc_data:
            self.logger.log_data(all_cpc_data)
            self.visualizer.update_plot(all_cpc_data)

        self.root.after(1000, self.check_queue)

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root, "config.yml")
    root.mainloop()