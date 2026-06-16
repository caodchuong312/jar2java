# jar2java
A simple tool that utilizes Vineflower to decompile Java source code in a folder. This tool decompiles `.jar` and `.class` files to `.java`, which is useful for searching during source code audits.

## Options
```
-f : One or more folders containing JAR/class files
-t : Number of threads when decompiling class files (default: 4)
-jp: Specify java binary path if it's not available in your PATH environment variable (requires JDK >= 17)
-u : Download/update to the latest Vineflower jar from GitHub releases
```

## Examples
```bash
# Decompile all files in a folder (defaults to 4 threads for class files)
python3 main.py -f /path/to/folder/

# Decompile multiple folders at once
python3 main.py -f /path/to/folder1 /path/to/folder2

# Decompile using 8 threads
python3 main.py -t 8 -f /path/to/folder/

# Specify JDK path to use
python3 main.py -f /path/to/folder/ -jp /opt/jdk17/bin/java

# Update/download the latest Vineflower jar from GitHub releases and cleanup old ones
python3 main.py -u
```

## Updates
- Merged `main4big.py` functionality into `main.py` using `ThreadPoolExecutor` for safe and fast parallel decompilation.
- Added multi-folder support to the `-f` flag (space-separated folders) to aggregate and parallelize files across all paths under a single run.
- Automatically detects and prints the current Java/JDK version and its absolute executable path prior to running.
- Fully compatible with Linux systems (case-insensitive extension scanning, OS-native path normalization, and bitwise OR file-permission modifications).
- Added a visual progress bar (zero-dependency, terminal-safe) for decompiling JARs, class files, and XML formatting.
- Integrated a Vineflower update feature (`-u` option) that auto-downloads the latest release from GitHub and automatically cleans up older `vineflower-*.jar` files.
- Skips class files larger than 300KB to prevent high RAM utilization/freezes.
- Added a 3-minute timeout for each decompilation to avoid hang-ups on highly complex files.