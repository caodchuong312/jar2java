# jar2java
simple tool that implements vineflower to decompile java source code in a folder. This tool will decompile `.jar/.class` file to `.java`. Useful for searching when audit source code

options:
```
-f : folder contain jar file
-t: number of thread when decompile class file (main4big.py only)
-jp : specify java binary path if it's not available on your path env (jdk >= 17)
```

examples:
```python
# decompile all files in folder
python3 main.py -f /path/to/folder/

# when dealing with large files
python3 main4big.py -t 4 -f /path/to/folder/
# specify jdk path to use
python3 main.py -f /path/to/folder/ -jp /opt/jdk17/bin/java
```