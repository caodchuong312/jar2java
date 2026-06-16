import glob, subprocess, os, stat, shutil, time, threading
import urllib.request, json
import xml.dom.minidom
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

def find_files(folder, extensions):
    """Recursively find files in folder matching any of the extensions (case-insensitive)."""
    matched = []
    for root, dirs, files in os.walk(folder):
        for file in files:
            if any(file.lower().endswith(ext) for ext in extensions):
                matched.append(os.path.join(root, file))
    return matched

def checkJavaPath(java_path):
    try:
        cmd = subprocess.run(f"{java_path} -version", shell=True, capture_output=True, text=True)
        output = (cmd.stdout + cmd.stderr).strip()
        first_line = output.split('\n')[0] if output else "Unknown version"
        abs_path = shutil.which(java_path) or java_path
        abs_path = os.path.abspath(abs_path)
        print(f'FOUND Java: {first_line}')
        print(f'Java Path: {abs_path}')
    except Exception:
        print(f"ERROR: java not found, make sure is available on your PATH or specify it with '-jp' flag")
        exit()

_progress_lock = threading.Lock()
_progress_state = {
    'active': False,
    'iteration': 0,
    'total': 0,
    'prefix': '',
    'suffix': '',
    'start_time': None,
    'decimals': 1,
    'length': 40,
    'fill': '#'
}

def _draw_progress(iteration, total, prefix='', suffix='', decimals=1, length=40, fill='#', start_time=None):
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total))) if total > 0 else "0.0"
    filledLength = int(length * iteration // total) if total > 0 else 0
    bar = fill * filledLength + '-' * (length - filledLength)
    
    elapsed_str = ""
    if start_time is not None:
        elapsed = time.time() - start_time
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        seconds = int(elapsed % 60)
        if hours > 0:
            elapsed_str = f" [{hours:02d}:{minutes:02d}:{seconds:02d}]"
        else:
            elapsed_str = f" [{minutes:02d}:{seconds:02d}]"
            
    out = f'\r{prefix} |{bar}| {percent}%{elapsed_str} {suffix}'
    
    # Pad with spaces to clear any previous longer line
    max_len = getattr(show_progress, 'max_len', 0)
    if len(out) < max_len:
        out += ' ' * (max_len - len(out))
    else:
        show_progress.max_len = len(out)
        
    print(out, end='', flush=True)
    if iteration == total:
        print()
        show_progress.max_len = 0

def _progress_ticker():
    while True:
        time.sleep(1.0)
        with _progress_lock:
            if not _progress_state['active']:
                continue
            _draw_progress(
                _progress_state['iteration'],
                _progress_state['total'],
                _progress_state['prefix'],
                _progress_state['suffix'],
                _progress_state['decimals'],
                _progress_state['length'],
                _progress_state['fill'],
                _progress_state['start_time']
            )

# Start the background ticker thread
_ticker_thread = threading.Thread(target=_progress_ticker, daemon=True)
_ticker_thread.start()

def show_progress(iteration, total, prefix='', suffix='', decimals=1, length=40, fill='#', start_time=None):
    """Print a simple console progress bar and update the background ticker state."""
    with _progress_lock:
        if iteration == total:
            _progress_state['active'] = False
        else:
            _progress_state['active'] = True
            _progress_state['iteration'] = iteration
            _progress_state['total'] = total
            _progress_state['prefix'] = prefix
            _progress_state['suffix'] = suffix
            _progress_state['start_time'] = start_time
            _progress_state['decimals'] = decimals
            _progress_state['length'] = length
            _progress_state['fill'] = fill
            
        _draw_progress(iteration, total, prefix, suffix, decimals, length, fill, start_time)

def cleanup_old_vineflower_jars(keep_filename):
    """Delete any local vineflower-*.jar files in the current folder except the one we want to keep."""
    for f in os.listdir('.'):
        if f.startswith('vineflower-') and f.endswith('.jar') and f != keep_filename:
            try:
                os.remove(f)
                print(f'\nDELETED OLD FILE: {f}')
            except Exception as e:
                print(f'\nERROR: Failed to delete old file {f}: {e}')

def get_latest_vineflower_info():
    """Query GitHub API for the latest Vineflower release and return a tuple of (filename, download_url)."""
    api = 'https://api.github.com/repos/Vineflower/vineflower/releases/latest'
    try:
        with urllib.request.urlopen(api) as resp:
            data = json.load(resp)
        
        # Try to find the main jar (excluding -slim, -sources, -javadoc)
        for asset in data.get('assets', []):
            name = asset.get('name', '')
            if name.endswith('.jar') and not any(x in name for x in ['-slim', '-sources', '-javadoc']):
                return name, asset.get('browser_download_url')
                
        # Fallback to any .jar if the main jar is not found
        for asset in data.get('assets', []):
            name = asset.get('name', '')
            if name.endswith('.jar'):
                return name, asset.get('browser_download_url')
    except Exception as e:
        print(f'\nERROR: Unable to fetch latest Vineflower release: {e}')
    return None, None

def download_latest_vineflower():
    """Force download the latest Vineflower jar and delete any older vineflower jar files."""
    name, url = get_latest_vineflower_info()
    if not url or not name:
        print('\nERROR: Could not determine latest Vineflower URL')
        return None
    try:
        print(f'\nDOWNLOADING: {url}')
        urllib.request.urlretrieve(url, name)
        print(f'SUCCESS: Downloaded Vineflower to {name}')
        cleanup_old_vineflower_jars(name)
        return name
    except Exception as e:
        print(f'\nERROR: Failed to download Vineflower: {e}')
        return None

def get_vineflower_path():
    """Return the local path to the Vineflower jar, downloading the latest release if missing."""
    # Search for any existing vineflower-*.jar in the current directory
    jars = [f for f in os.listdir('.') if f.startswith('vineflower-') and f.endswith('.jar')]
    if jars:
        # Return the first one found (typically there's only one because of cleanup)
        return jars[0]

    name, url = get_latest_vineflower_info()
    if url and name:
        try:
            print(f'\nDOWNLOADING: {url}')
            urllib.request.urlretrieve(url, name)
            cleanup_old_vineflower_jars(name)
            return name
        except Exception as e:
            print(f'\nERROR: Failed to download Vineflower: {e}')

    raise FileNotFoundError('Vineflower jar not found and unable to download.')

def decompile(jav_file, out_jav_folder, JAVA_PATH, VINEFLOWER_PATH, timeout=180, max_memory='4G', debug=False):
    silent_flag = "" if debug else " --silent"
    command = f"{JAVA_PATH} -Xmx{max_memory} -jar {VINEFLOWER_PATH}{silent_flag} {jav_file} {out_jav_folder}"

    if debug:
        print(f"\n[DEBUG] Running: {command}")

    try:
        subprocess.run(command, check=True, shell=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        print(f"\nTIMEOUT: ignore this jar/class file: {jav_file}")
        return
    except Exception as e:
        print(f"\nERROR: Error decompile: {jav_file}")
        if debug:
            print(f"[DEBUG] Error details: {e}")
        return

    try:
        os.chmod(jav_file, os.stat(jav_file).st_mode | stat.S_IWRITE)
    except Exception:
        pass
    os.remove(jav_file)

def getReady(jar_file):
    jar_folder = os.path.splitext(os.path.basename(jar_file))[0]
    out_jar_folder = os.path.dirname(jar_file) + '/' + jar_folder
    out_jar_folder = out_jar_folder.replace('\\', '/')
    jar_file = jar_file.replace('\\', '/')
    return jar_file, out_jar_folder

def decompileJars(jar_files, JAVA_PATH, VINEFLOWER_PATH, timeout=180, max_memory='4G', debug=False):
    total = len(jar_files)
    if total == 0:
        return
    print(f'STATUS: found {total} jar files')
    start_time = time.time()
    for i, jar_file in enumerate(jar_files):
        jar_file, out_jar_folder = getReady(jar_file)
        show_progress(i, total, prefix='Decompiling JARs:', suffix=f'({i}/{total}) - {os.path.basename(jar_file)}', start_time=start_time)
        decompile(jar_file, out_jar_folder, JAVA_PATH, VINEFLOWER_PATH, timeout=timeout, max_memory=max_memory, debug=debug)
    show_progress(total, total, prefix='Decompiling JARs:', suffix=f'({total}/{total})', start_time=start_time)

def is_file_larger_than_300kb(filepath):
    return os.path.getsize(filepath) > 300_000

def decompileClasses(class_files, JAVA_PATH, VINEFLOWER_PATH, thread_num=4, timeout=180, max_memory='4G', debug=False):
    valid_classes = []
    for class_file in class_files:
        class_file, out_class_folder = getReady(class_file)
        out_class_folder = os.path.dirname(out_class_folder)

        if is_file_larger_than_300kb(class_file):
            print(f'\n[IGNORE] class file larger than 300kb: {class_file}')
            continue
        valid_classes.append((class_file, out_class_folder))

    total = len(valid_classes)
    if total == 0:
        return

    print(f'STATUS: found {len(class_files)} class files ({total} to decompile)')
    start_time = time.time()
    show_progress(0, total, prefix='Decompiling Classes:', start_time=start_time)
    
    completed = 0
    with ThreadPoolExecutor(max_workers=thread_num) as executor:
        futures = {
            executor.submit(decompile, cls_file, out_folder, JAVA_PATH, VINEFLOWER_PATH, timeout, max_memory, debug): cls_file
            for cls_file, out_folder in valid_classes
        }
        for future in as_completed(futures):
            completed += 1
            show_progress(completed, total, prefix='Decompiling Classes:', suffix=f'({completed}/{total})', start_time=start_time)

# beautify xml file, resource file in jar after decompile is minified
def beautifyXML(xml_files):
    total = len(xml_files)
    if total == 0:
        return
    print(f'STATUS: found {total} xml files')
    start_time = time.time()
    for i, xml_file in enumerate(xml_files):
        xml_file, out_xml_folder = getReady(xml_file)
        show_progress(i, total, prefix='Beautifying XMLs:', suffix=f'({i}/{total}) - {os.path.basename(xml_file)}', start_time=start_time)
        try:
            with open(file=xml_file, mode='r', encoding='utf-8') as f:
                text_lines = f.readlines()
                len_lines = len(text_lines)

            if len_lines < 3:
                text = ''.join(text_lines)
                parsed_xml = xml.dom.minidom.parseString(text)
                new_xml = parsed_xml.toprettyxml(indent="\t")
                with open(file=xml_file, mode='w', encoding='utf-8') as f:
                    f.write(new_xml)
        except Exception as e:
            print(f'\nERROR: Error beautifying: {xml_file}')
            print(e)
    show_progress(total, total, prefix='Beautifying XMLs:', suffix=f'({total}/{total})', start_time=start_time)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--folder', nargs='+', help='folder(s) containing jar files')
    parser.add_argument('-jp', '--java-path', help='specify java binary path')
    parser.add_argument('-t', '--thread', type=int, default=4, help='how many threads to use for decompiling classes, default is 4')
    parser.add_argument('-u', '--update-vineflower', action='store_true', help='download latest Vineflower jar from GitHub releases')
    parser.add_argument('-to', '--timeout', type=int, default=180, help='timeout in seconds for decompiling each file, default is 180')
    parser.add_argument('-mx', '--max-memory', default='4G', help='maximum memory allocation pool for JVM (e.g. 2G, 4G, 8G), default is 4G')
    parser.add_argument('-d', '--debug', action='store_true', help='enable debug mode to show detailed decompilation output and command execution')
    args = parser.parse_args()

    # Handle Vineflower update option
    if args.update_vineflower:
        downloaded = download_latest_vineflower()
        if downloaded:
            print('INFO: Updated Vineflower jar')
        if not args.folder:
            exit()

    # conf
    if not args.folder:
        print('ERROR: folder location is required, please specify with -f flag')
        exit()

    # Normalize paths
    folders = [os.path.normpath(f.strip()) for f in args.folder if f.strip()]
    if not folders:
        print('ERROR: folder location is required, please specify with -f flag')
        exit()

    print(f'INFO: Locations: {", ".join(folders)}')

    JAVA_PATH = 'java'
    if args.java_path != None:
        JAVA_PATH = args.java_path
    checkJavaPath(JAVA_PATH)

    # Resolve vineflower path in main thread to avoid thread safety issues
    VINEFLOWER_PATH = get_vineflower_path()

    jar_files = []
    class_files = []
    xml_files = []
    for folder in folders:
        jar_files.extend(find_files(folder, ['.jar']))
        class_files.extend(find_files(folder, ['.class']))
        xml_files.extend(find_files(folder, ['.xml']))

    start_time = time.time()

    decompileJars(jar_files, JAVA_PATH, VINEFLOWER_PATH, args.timeout, args.max_memory, args.debug)
    decompileClasses(class_files, JAVA_PATH, VINEFLOWER_PATH, args.thread, args.timeout, args.max_memory, args.debug)
    beautifyXML(xml_files)

    elapsed = time.time() - start_time
    hours = int(elapsed // 3600)
    minutes = int((elapsed % 3600) // 60)
    seconds = int(elapsed % 60)

    time_str = ""
    if hours > 0:
        time_str += f"{hours}h "
    if minutes > 0 or hours > 0:
        time_str += f"{minutes}m "
    time_str += f"{seconds}s"

    print(f"INFO: Finished all tasks in {time_str}")
