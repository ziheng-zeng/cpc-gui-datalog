import csv
from datetime import datetime
import os
import numpy as np


class DataLogger:
    def __init__(self, config, cpc_names):
        self.config = config
        self.cpc_names = cpc_names
        self.update_file_path()

    def update_file_path(self):
        # Get the current date in the required format
        current_date = datetime.now().strftime("%Y%m%d")
        # Check if we need to create a new file for a new day
        if not hasattr(self, 'current_date') or self.current_date != current_date:
            self.current_date = current_date
            # Create a subfolder named after the current date, if it doesn't already exist
            subfolder_path = os.path.join(os.getcwd(), self.current_date)
            os.makedirs(subfolder_path, exist_ok=True)
            # Create a new CSV file for the new day
            csv_filename = f"MANY_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            self.csv_filepath = os.path.join(subfolder_path, csv_filename)
            # Write the header to the new file
            self.write_header()

    def write_header(self):
        # Create header based on the CPC configuration
        header = self.construct_header()
        # Write header to the new CSV file
        with open(self.csv_filepath, 'w', newline='') as file:
            csv.writer(file).writerow(header)

    def construct_header(self):
        # Construct CSV header from configuration
        headers = []
        for i in range(len(self.cpc_names)):
            cpc_header = self.config[f"cpc{i+1}"]["cpc_header"]
            headers.extend(cpc_header)
        return headers

    def log_data(self, all_cpc_data):
        # Before logging, ensure the file is up-to-date
        self.update_file_path()
        # Now log the data
        with open(self.csv_filepath, mode="a", newline="") as data_file:
            data_writer = csv.writer(data_file, delimiter=",")
            row = []
            for name in self.cpc_names:
                if name in all_cpc_data:
                    row.extend(list(all_cpc_data[name].values()))
                else:
                    row.extend([np.nan] * len(self.config[f"cpc1"]["cpc_header"]))
            data_writer.writerow(row)