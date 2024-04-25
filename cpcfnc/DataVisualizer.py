from matplotlib.animation import FuncAnimation
from datetime import datetime, timedelta
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.dates as mdates
import queue
import threading


class DataVisualizer:
    def __init__(self, root, config, cpc_names):
        self.root = root
        self.config = config
        self.cpc_names = cpc_names
        self.setup_layout()
        self.root.title("5 Channel Butanol CPC Data Viewer")
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.plot_data = {name: {'datetime': [], 'concentration': []} for name in self.cpc_names}
        self.root.after(1000, self.update_plot)
        self.stop_threads = threading.Event()

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
        self.figure = Figure(figsize=(8, 8), dpi=100)
        self.ax = self.figure.add_subplot(1, 1, 1)
        
        self.matplotlib_canvas = FigureCanvasTkAgg(self.figure, master=frame)
        self.canvas_widget = self.matplotlib_canvas.get_tk_widget()
        self.canvas_widget.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Particle Count, particles/cm³")

        # Start the animation
        self.ani = FuncAnimation(self.figure, self.update_plot, interval=1000, cache_frame_data=False)


    def create_overview_widgets(self, frame):
        self.cpc_tab = ttk.Frame(frame) 
        self.cpc_tab.pack(expand=1, fill="both")
        # Initialize CPC instrument frames
        self.init_cpc_frames()

    def init_cpc_frames(self):
        # Layout initialization
        for i in range(1, self.config['num_cpcs'] + 1):
            cpc_key = f"cpc{i}"
            cpc_config = self.config[cpc_key]
            frame = ttk.LabelFrame(self.cpc_tab, text=cpc_config['cpc_name'], padding=10)
            frame.grid(row=(i-1)//2, column=(i-1)%2, sticky='ew', padx=10, pady=10)

            # Add labels for each attribute except 'datetime'
            for key in self.config[cpc_key]['cpc_header']:
                if key != 'datetime':
                    ttk.Label(frame, text=f"{key}: N/A").grid()

    def update_cpc_display(self, index, data):
        frame = self.cpc_tab.winfo_children()[index]
        for label in frame.winfo_children():
            key = label.cget("text").split(":")[0]
            if key in data:
                label.config(text=f"{key}: {data[key]}")


    def update_plot(self,frame=None):
        # Get the current time
        current_time = datetime.now()
        # Calculate the time for two minutes ago
        ten_min_ago = current_time - timedelta(minutes=10)

        # Clear the current axes
        self.ax.clear()
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Particle Count, particles/cm³")
        
        # Re-plot data for each CPC
        for cpc_name, cpc_data in self.plot_data.items():
            if cpc_data['datetime']:
                filtered_datetimes = [dt for dt in cpc_data['datetime'] if dt >= ten_min_ago]
                filtered_concentrations = [concentration for dt, concentration in zip(cpc_data['datetime'], cpc_data['concentration']) if dt >= ten_min_ago]

                self.ax.plot(filtered_datetimes, filtered_concentrations, label=cpc_name)

        # Update the plot's x-axis limits and format
        self.ax.set_xlim([ten_min_ago, current_time])
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        plt.setp(self.ax.get_xticklabels(), rotation=45, ha="right")
        # Update the legend
        self.ax.legend(loc='upper center', bbox_to_anchor=(0.5, 1.1),ncol=3, fancybox=True)


    def close(self):
        self.stop_threads.set()
        print("Closing application...")
        self.root.destroy()