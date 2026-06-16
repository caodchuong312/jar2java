import glob, subprocess, os, stat, shutil
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

def show_progress(iteration, total, prefix='', suffix='', decimals=1, length=40, fill='#'):
    """Print a simple console progress bar."""
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total))) if total > 0 else "0.0"
    filledLength = int(length * iteration // total) if total > 0 else 0
    bar = fill * filledLength + '-' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end='', flush=True)
    if iteration == total:
        print()

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

def decompile(jav_file, out_jav_folder, JAVA_PATH, VINEFLOWER_PATH):
    command = f"{JAVA_PATH} -Xmx16G -jar {VINEFLOWER_PATH} --silent {jav_file} {out_jav_folder}"

    try:
        # For classes, we use a 120s timeout like in main4big.py.
        # But if it's a jar, 180s might be better. Let's use 180s timeout.
        subprocess.run(command, check=True, shell=True, timeout=180)
    except subprocess.TimeoutExpired as e:
        print(f"\nTIMEOUT: ignore this jar/class file: {jav_file}")
        return
    except Exception as e:
        print(f"\nERROR: Error decompile: {jav_file}")
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

def decompileJars(jar_files, JAVA_PATH, VINEFLOWER_PATH):
    total = len(jar_files)
    if total == 0:
        return
    print(f'STATUS: found {total} jar files')
    show_progress(0, total, prefix='Decompiling JARs:')
    for i, jar_file in enumerate(jar_files):
        jar_file, out_jar_folder = getReady(jar_file)
        decompile(jar_file, out_jar_folder, JAVA_PATH, VINEFLOWER_PATH)
        show_progress(i + 1, total, prefix='Decompiling JARs:', suffix=f'({i+1}/{total})')

def is_file_larger_than_300kb(filepath):
    return os.path.getsize(filepath) > 300_000

def decompileClasses(class_files, JAVA_PATH, VINEFLOWER_PATH, thread_num=4):
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
    show_progress(0, total, prefix='Decompiling Classes:')
    
    completed = 0
    with ThreadPoolExecutor(max_workers=thread_num) as executor:
        futures = {
            executor.submit(decompile, cls_file, out_folder, JAVA_PATH, VINEFLOWER_PATH): cls_file
            for cls_file, out_folder in valid_classes
        }
        for future in as_completed(futures):
            completed += 1
            show_progress(completed, total, prefix='Decompiling Classes:', suffix=f'({completed}/{total})')

# beautify xml file, resource file in jar after decompile is minified
def beautifyXML(xml_files):
    total = len(xml_files)
    if total == 0:
        return
    print(f'STATUS: found {total} xml files')
    show_progress(0, total, prefix='Beautifying XMLs:')
    for i, xml_file in enumerate(xml_files):
        xml_file, out_xml_folder = getReady(xml_file)

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
        show_progress(i + 1, total, prefix='Beautifying XMLs:', suffix=f'({i+1}/{total})')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--folder', nargs='+', help='folder(s) containing jar files')
    parser.add_argument('-jp', '--java-path', help='specify java binary path')
    parser.add_argument('-t', '--thread', type=int, default=4, help='how many threads to use for decompiling classes, default is 4')
    parser.add_argument('-u', '--update-vineflower', action='store_true', help='download latest Vineflower jar from GitHub releases')
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

    decompileJars(jar_files, JAVA_PATH, VINEFLOWER_PATH)
    decompileClasses(class_files, JAVA_PATH, VINEFLOWER_PATH, args.thread)
    beautifyXML(xml_files)
