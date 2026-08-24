import csv
import argparse
from matplotlib.animation import FuncAnimation
from datetime import datetime, timedelta
import os
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.dates as mdates

import numpy as np
import yaml

if __package__:
    from .cpcfnc import CPCSerial
else:
    from cpcfnc import CPCSerial


class App:
    def __init__(self, root, config_file, test_mode=False):

        # Load config file
        self.config_file = config_file
        self.program_path = os.path.dirname(os.path.realpath(__file__))
        config_path = self.config_file
        if not os.path.isabs(config_path):
            local_path = os.path.join(os.getcwd(), config_path)
            package_path = os.path.join(self.program_path, config_path)
            config_path = local_path if os.path.exists(local_path) else package_path
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        self.num_cpcs = self.config["num_cpcs"]
        try:
            self.data_dir = self.config["data_dir"]
        except KeyError:
            self.data_dir =os.getcwd()

        # Gather all serial ports into a list
        self.serial_ports = [self.config[f"cpc{i}"]["serial_port"] for i in range(1, self.num_cpcs + 1)]

        # Gather all cpc names into a list
        self.cpc_name = [self.config[f"cpc{i}"]["cpc_name"] for i in range(1, self.num_cpcs + 1)]
        
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
                None, test=test_mode
            )
            self.cpcs.append(cpc)

        # Setup tkinter GUI
        self.root = root
        self.root.title("5 Channel Butanol CPC Data Viewer")
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        # Initialize the GUI components
        self.setup_layout()

        # Setup CSV file
        self.current_date = datetime.now().strftime("%Y-%m-%d")
        self.cpc_headers = []
        for i in range(self.num_cpcs):
            cpc_header = self.config[f"cpc{i+1}"]["cpc_header"]
            self.cpc_headers.extend(cpc_header)
        self.start_time, self.csv_filepath = self.create_files(self.cpc_headers,self.data_dir)

        # Constants for flow intervals
        self.curr_time = time.monotonic()
        self.update_interval = 1  # seconds

        # Start threads for all CPCs
        for cpc in self.cpcs:
            cpc.start()
        
        # Check the queue every 1s
        root.after(1000, self.check_queue)

    def setup_layout(self):
        # Create the tab control (Notebook)
        tab_control = ttk.Notebook(self.root)

        # Create tabs (as frames)
        plots_tab = ttk.Frame(tab_control)
        overview_tab = ttk.Frame(tab_control)
        
        # Add tabs to the Notebook
        tab_control.add(plots_tab, text='Data & Plots')
        tab_control.add(overview_tab, text='System Overview')

        # Pack to make the tabs visible
        tab_control.pack(expand=1, fill="both")

        # self.create_settings_widgets(settings_tab)
        self.create_plots_widgets(plots_tab)
        self.create_overview_widgets(overview_tab)
        # self.create_serial_widgets(serial_tab)

        
    def create_plots_widgets(self, frame):
        self.figure = Figure(figsize=(7, 7), dpi=100)
        self.ax = self.figure.add_subplot(1, 1, 1)
        
        self.matplotlib_canvas = FigureCanvasTkAgg(self.figure, master=frame)
        self.canvas_widget = self.matplotlib_canvas.get_tk_widget()
        self.canvas_widget.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Particle Count, particles/cm³")

        # Initialize data structures for plotting
        self.plot_data = {name: {'datetime': [], 'concentration': []} for name in self.cpc_name}
        # Start the animation
        self.ani = FuncAnimation(self.figure, self.update_plot, interval=1000, cache_frame_data=False)


    def create_overview_widgets(self, frame):
        self.cpc_tab = ttk.Frame(frame) 
        self.cpc_tab.pack(expand=1, fill="both")
        # Initialize CPC instrument frames
        self.init_cpc_frames()

    def init_cpc_frames(self):
        # Layout initialization
        for i in range(1, self.config['num_cpcs']+  1):
            cpc_key = f"cpc{i}"
            cpc_config = self.config[cpc_key]
            frame = ttk.LabelFrame(self.cpc_tab, text=cpc_config['cpc_name'], padding=10)
            frame.grid(row=(i-1)//3, column=(i-1)%3, sticky='ew', padx=10, pady=10)

            # Add labels for each attribute except 'datetime'
            for key in self.config[cpc_key]['cpc_header']:
                if key != 'datetime':
                    ttk.Label(frame, text=f"{key}: N/A").grid()


    def check_queue(self):
        # Create new file on new day
        if datetime.now().day != self.start_time.day:
            self.current_date = datetime.now().strftime("%Y-%m-%d")
            self.start_time, self.csv_filepath = self.create_files(
                self.cpc_headers,self.data_dir
            )
        all_cpc_data = {}

        # Get data from all CPCs and store for plotting and writing to CSV
        for i in range(self.num_cpcs):
            try:
                data_point = self.serial_queues[i].get_nowait()
                # print(data_point)
                self.update_cpc_display(i, data_point)

                # Extract cpc_name from the data_point
                cpc_name = self.cpc_name[i]
                if cpc_name not in self.plot_data:
                    self.plot_data[cpc_name] = {'datetime': [], 'concentration': []}

                # Parse datetime and concentration, add to the plot data structure
                parsed_datetime = data_point['datetime']

                # Safe parsing of concentration with default value if empty or invalid
                try:
                    concentration = float(data_point['concentration']) if data_point['concentration'] else 0.0
                except:
                    concentration = 0.0  # Default value or decide if you want to log this error or take any specific action

                self.plot_data[cpc_name]['datetime'].append(parsed_datetime)
                self.plot_data[cpc_name]['concentration'].append(concentration)

                all_cpc_data[cpc_name] = data_point

            except queue.Empty:
                pass

        # Write all raw data to CSV file if all_cpc_data is populated
        if all_cpc_data:  # Checks if there's any data collected
            with open(self.csv_filepath, mode="a", newline="") as data_file:
                data_writer = csv.writer(data_file, delimiter=",",escapechar="\\")
                # Create a list that will hold one entry per CPC for this timestamp
                row = []
                for i, name in enumerate(self.cpc_name):  # Ensuring the order of data in the CSV
                    if name in all_cpc_data:
                        # Assuming all_cpc_data[name] is a dictionary containing all necessary data fields
                        row.extend(list(all_cpc_data[name].values()))
                    else:
                        # Extend row with NaNs or some placeholder if no data for this CPC
                        row.extend([np.nan] * len(self.config[f"cpc{i+1}"]["cpc_header"]))  # Adjust the number as per data fields

                data_writer.writerow(row)
         
        # Schedule the next update
        self.curr_time = self.curr_time + self.update_interval
        next_time = self.curr_time + self.update_interval - time.monotonic()
        if next_time < 0:
            next_time = 0
        next_time = int(next_time * 1000)
  

        # Check the queue again after 1s
        self.root.after(next_time, self.check_queue)

    def update_cpc_display(self, index, data):
        frame = self.cpc_tab.winfo_children()[index]
        for label in frame.winfo_children():
            key = label.cget("text").split(":")[0]
            if key in data:
                label.config(text=f"{key}: {data[key]}")

    def update_plot(self,frame=None):
        # Get the current time
        current_time = datetime.now()
        #print(current_time)
        # Calculate the time for two minutes ago
        ten_min_ago = current_time - timedelta(minutes=10)

        # Clear the current axes
        self.ax.clear()
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Particle Count, particles/cm³")
        
        # Collect max value across CPCs
        max_val = []

        # Re-plot data for each CPC
        for cpc_name, cpc_data in self.plot_data.items():
            if cpc_data['datetime']:
                filtered_datetimes = [dt for dt in cpc_data['datetime'] if dt >= ten_min_ago]
                filtered_concentrations = [concentration for dt, concentration in zip(cpc_data['datetime'], cpc_data['concentration']) if dt >= ten_min_ago]

                self.ax.scatter(filtered_datetimes, filtered_concentrations, label=cpc_name,s=10)

                max_val.append(max(filtered_concentrations))
        # Update the plot's x-axis limits and format
        self.ax.set_xlim([ten_min_ago, current_time])
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        # Setup y-lim
        filt_max = [val for val in max_val if val<= 299000]
        if not filt_max:
            ylim = 200000
        else:
            ylim = max(filt_max)
        self.ax.set_yscale('log')
        self.ax.set_ylim([1,ylim*1.1])
        plt.setp(self.ax.get_xticklabels(), rotation=45, ha="right")
        # Update the legend
        self.ax.legend(loc='upper center', bbox_to_anchor=(0.5, 1.1),ncol=3, fancybox=True)


    def close(self):
        self.stop_threads.set()
        print("Closing application...")
        self.root.destroy()

    def create_files(self, header, directory):
        # Create subfolder for current date
        subfolder_path = os.path.join(directory, self.current_date)
        os.makedirs(subfolder_path, exist_ok=True)

        # Create CSV file and writer
        csv_filename = f"MANY_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        csv_filepath = os.path.join(subfolder_path, csv_filename)

        # Open CSV logging file
        with open(csv_filepath, mode="w", newline="") as data_file:
            data_writer = csv.writer(data_file, delimiter=",")
            data_writer.writerow(header)

        return datetime.now(), csv_filepath


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Real-time CPC GUI data logger.")
    parser.add_argument("--config", default="config.yml", help="Path to the YAML CPC configuration file.")
    parser.add_argument("--test", action="store_true", help="Run with simulated CPC data instead of serial ports.")
    args = parser.parse_args()

    root = tk.Tk()
    app = App(root, args.config, test_mode=args.test)
    root.mainloop()
