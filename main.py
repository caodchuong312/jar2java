import glob, subprocess, os, stat
import xml.dom.minidom
import argparse

def checkJavaPath():
    try:
        cmd = subprocess.run("java -version", shell=True, capture_output=True, text=True)
        print('[FOUND] - found java, recommend jdk17 or higher')
    except subprocess.CalledProcessError:
        print(f"[ERROR] - java not found, make sure is available on your PATH or specify it with '-jp' flag")
        exit()

def decompile(jav_file, out_jav_folder, JAVA_PATH):
    VINEFLOWER_PATH = 'vineflower-1.11.1.jar'
    command = f"{JAVA_PATH} -Xmx6G -jar {VINEFLOWER_PATH} --silent {jav_file} {out_jav_folder}"

    try:
        subprocess.run(command, check=True, shell=True)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] - Error decompile: {jav_file}")
        return

    os.chmod(jav_file, stat.S_IWRITE)
    os.remove(jav_file)

def getReady(jar_file):
    jar_folder = os.path.splitext(os.path.basename(jar_file))[0]
    out_jar_folder = os.path.dirname(jar_file) + '/' + jar_folder
    out_jar_folder = out_jar_folder.replace('\\', '/')
    jar_file = jar_file.replace('\\', '/')
    return jar_file, out_jar_folder

def decompileJars(jar_files, JAVA_PATH):
    print(f'[STATUS] - found {len(jar_files)} jar files')
    for i, jar_file in enumerate(jar_files):
        jar_file, out_jar_folder = getReady(jar_file)
        decompile(jar_file, out_jar_folder, JAVA_PATH)

        if i % 10 == 0 and i != 0:
            print(f'[STATUS] - done {i} jars')
    print(f'[STATUS] - done all jars')

def decompileClasses(class_files, JAVA_PATH):
    print(f'[STATUS] - found {len(class_files)} class files')
    for i, class_file in enumerate(class_files):
        class_file, out_class_folder = getReady(class_file)
        out_class_folder = os.path.dirname(out_class_folder)
        decompile(class_file, out_class_folder, JAVA_PATH)

        if i % 50 == 0 and i != 0:
            print(f'[STATUS] - done {i} classes')
    print(f'[STATUS] - done all classes')

# beautify xml file, resource file in jar after decompile is minified
def beautifyXML(xml_files):
    print(f'[STATUS] - found {len(xml_files)} xml files')
    for xml_file in xml_files:
        xml_file, out_xml_folder = getReady(xml_file)

        try:
            with open(file=xml_file, mode='r', encoding='utf-8') as f:
                text_lines = f.readlines()
                len_lines = len(text_lines)

            if len_lines < 3:
                print(f'[STATUS] - beautifying: {xml_file}')
                text = ''.join(text_lines)
                parsed_xml = xml.dom.minidom.parseString(text)
                new_xml = parsed_xml.toprettyxml(indent="\t")
                with open(file=xml_file, mode='w', encoding='utf-8') as f:
                    f.write(new_xml)
        except Exception as e:
            print(f'[ERROR] Error beautifying: {xml_file}')
            print(e)

if __name__ == '__main__':
    checkJavaPath()

    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--folder', help='folder contain jar files')
    parser.add_argument('-jp', '--java-path', help='specify java path')
    args = parser.parse_args()

    # conf
    PROJECT_FOLDER_PATH = (args.folder).strip()
    if PROJECT_FOLDER_PATH == None or PROJECT_FOLDER_PATH == '':
        print('[ERORR] - folder location is required, please specify with -f flag')
        exit()
    else:
        print(f'[INFO] - Location: {PROJECT_FOLDER_PATH}')

    ALL_JARS_REGEX = '/**/*.jar'
    ALL_CLASSES_REGEX = '/**/*.class'
    ALL_XML_REGEX = '/**/*.xml'

    JAVA_PATH = 'java'
    if args.java_path != None:
        JAVA_PATH = args.java_path

    jar_files = glob.glob(PROJECT_FOLDER_PATH + ALL_JARS_REGEX, recursive=True)
    decompileJars(jar_files, JAVA_PATH)

    class_files = glob.glob(PROJECT_FOLDER_PATH + ALL_CLASSES_REGEX, recursive=True)
    decompileClasses(class_files, JAVA_PATH)

    xml_files = glob.glob(PROJECT_FOLDER_PATH + ALL_XML_REGEX, recursive=True)
    beautifyXML(xml_files)

