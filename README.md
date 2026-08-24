# CPC Live Logger

Tkinter GUI for real-time CPC instrument readings and data acquisition. The app opens one serial-reading thread per configured CPC, displays current instrument values, plots recent concentration readings live, and writes daily CSV log files.

## Main features

- Real-time Matplotlib plot embedded in a Tkinter GUI.
- One serial worker thread per CPC instrument.
- YAML configuration for serial ports, baud rates, startup commands, CPC names, output columns, and output folder.
- Daily `MANY_YYYYMMDD_HHMMSS.csv` log creation.
- Offline `--test` mode for opening the GUI with simulated readings before connecting hardware.

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -e .
```

Tkinter ships with most standard Python installs on Windows. If the GUI does not open, install a Python distribution that includes Tcl/Tk.

## Configure instruments

Start from the example file:

```powershell
Copy-Item examples\config.yml config.yml
```

Edit `config.yml` for your CPCs:

- `num_cpcs`: number of instruments to read.
- `data_dir`: folder where daily CSV logs should be written.
- `serial_port`: Windows COM port, for example `COM4`.
- `serial_baud`, `serial_bytesize`, `serial_parity`, `serial_timeout`: serial connection settings.
- `start_commands`: commands sent when the serial connection opens.
- `serial_commands`: commands polled once per update. Leave empty for instruments that stream rows.
- `cpc_header`: output fields expected from that CPC.

## Run with connected CPC hardware

```powershell
python -m cpc_log.run_many --config config.yml
```

## Run the GUI without hardware

```powershell
python -m cpc_log.run_many --config examples\config.yml --test
```

Test mode generates simulated concentration values so you can check the live plot and layout without opening serial ports.

## Output

For each run, the app creates a dated subfolder inside `data_dir` and writes a file like:

```text
MANY_20240426_000000.csv
```

Each row contains the latest values received from the configured CPCs. If one CPC has no reading for a cycle, the app fills that CPC's fields with missing values so the row still matches the configured header.

## Related repo

Use `cpc-data-plotter` for offline plots of these CSV logs, instrument comparisons, and CPC FARM size-distribution contour plots.
