import os
import re
import time
import shutil
import filetype
import platform
import subprocess
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog, messagebox
import configparser
import requests
import zipfile
import rarfile
import ujson as json
import threading


CONFIG_FILE = "directory_config.ini"

LOADER_DIR = os.path.dirname(os.path.abspath(CONFIG_FILE))

os.makedirs(os.path.join(LOADER_DIR, "lib"), exist_ok=True)

LIB_DIR = os.path.join(LOADER_DIR, "lib")
start = False

def save_directory(path):   
    config = configparser.ConfigParser()
    config["DEFAULT"] = {"last_directory": path}
    try:
        with open(CONFIG_FILE, "w") as configfile:
            config.write(configfile)
    except: 
        print("Could not create config file.")
        pass
    try: update_ui()
    except: pass
    
def load_directory():
    if os.path.exists(CONFIG_FILE):
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE)
        mod_directory = config["DEFAULT"].get("last_directory", "")
        return mod_directory
    else:
        os.makedirs(os.path.join(LOADER_DIR, "mods"), exist_ok=True)
        save_directory(os.path.join(LOADER_DIR, "mods"))
        print(f"No config file found. Setting directory to '{LOADER_DIR}/mods'.")
        return os.path.join(LOADER_DIR, "mods")

MOD_DIR = load_directory()

print(f"Config file found. Mod directory: '{MOD_DIR}'")

def get_game_folder(parent=False):
    return find_game(get_complete_path(), parent)

def has_game_folder(folder_path):
    return os.path.exists(find_game(folder_path))

def find_game(root_dir, parent=False):
    return find_folder(root_dir, "game", parent)

def find_file(root_dir, file):
    return find_folder(root_dir, file, parent=False, file=True)

def find_folder(root_dir, folder, parent=False, file=False):
    global start        
    if file:
        for dirpath, dirnames, filenames in os.walk(root_dir):
            if folder in filenames:
                file_path = os.path.join(dirpath, folder)
                return file_path
    else:
        for dirpath, dirnames, filenames in os.walk(root_dir):
            if folder in dirnames:
                folder_path = os.path.join(dirpath, folder)
                if parent:
                    return dirpath
                return folder_path
    if not start:
        print(f"'{folder}' folder not found in '{root_dir}")
    return "fakepath"

def get_complete_path():
    return os.path.join(MOD_DIR, folder_dropdown.get())

def check_python3():
    lib_path = find_folder(get_complete_path(), "lib")
    python3 = os.path.join(lib_path, "python3.9")
    return os.path.exists(python3)

def get_renpy_version():
    folder_path = get_complete_path()
    renpy_path = find_folder(folder_path, "renpy")
    version_path = os.path.join(renpy_path, "vc_version.py")
    init_path = os.path.join(renpy_path, "__init__.py")
    txt_file_look = find_file(folder_path, "renpy-version.txt")

    if os.path.exists(version_path):
        try:
            with open(version_path, "r") as f:
                for line in f:
                    if line.strip().startswith("version = u'") or line.strip().startswith("version = '"):
                        version_numbers = re.findall(r'\b\d+\b', line)
                        if len(version_numbers) >= 3:               
                            return ".".join(version_numbers[:3])
        except Exception as e:
            print(f"Error reading version: {e}")
    if os.path.exists(init_path):
        try:
            with open(init_path, "r") as f:
                if check_python3():
                    for line in f:
                        if line.strip().startswith("version_tuple = (8") or line.strip().startswith("version_tuple = VersionTuple(8"):
                            version_numbers = re.findall(r'\b\d+\b', line)
                            if len(version_numbers) >= 3:
                                return ".".join(version_numbers[:3])
                else:
                    for line in f:
                        if line.strip().startswith("version_tuple = (7") or line.strip().startswith("version_tuple = VersionTuple(7)"):
                            version_numbers = re.findall(r'\b\d+\b', line)
                            if len(version_numbers) >= 3:
                                return ".".join(version_numbers[:3])
        except Exception as e:
            print(f"Error reading version: {e}")

    elif os.path.exists(txt_file_look):
        try:
            with open(txt_file_look, "r") as f:
                first_line = f.readline().strip()
                return first_line
        except Exception as e:
            print(f"Error reading version: {e}")
    else:
        return "6.99.12.4"
    return "None"

def create_renpy_version(path, version):
    try: open(path)
    except:
        print("Creating version txt file...")
        with open(path, "w") as f:
            f.write(f"{version}")

def check_and_copy_files(selected_folder):
    game_folder = find_game(selected_folder)
    if not os.path.exists(game_folder):
        return False, []

    required_files = []
    if get_renpy_version().startswith("6"):
        required_files = ["audio.rpa", "images.rpa", "fonts.rpa", "scripts.rpa"]
    else:
        required_files = ["audio.rpa", "images.rpa", "fonts.rpa"]
    missing_files = [f for f in required_files if not os.path.exists(os.path.join(game_folder, f))]

    if not missing_files:
        return True, []

    return False, missing_files

def copy_missing_files(selected_folder):
    _, missing_files = check_and_copy_files(selected_folder)

    if isinstance(missing_files, list):
        for file in missing_files:
            source = os.path.join(LIB_DIR, file)
            singleton = os.path.join(LIB_DIR, "singleton.py")
            char_source = os.path.join(LIB_DIR, "characters")
            packages = os.path.join(get_game_folder(), "python-packages")
            characters = os.path.join(get_game_folder(parent=True), "characters")
            os.makedirs(characters, exist_ok=True)
            os.makedirs(packages, exist_ok=True)
            pythons = os.path.join(packages, "singleton.py")
            destination = os.path.join(get_game_folder(), file)

            if os.path.exists(source):
                try:
                    shutil.copy2(source, destination)
                    shutil.copy2(singleton, pythons)
                    shutil.copytree(char_source, characters, dirs_exist_ok=True)
                except Exception as e:
                    print(f"Error while copying files: {e}")
                update_ui()
            else:
                messagebox.showerror("Error", "DDLC RPAs not found")
                update_ui()
                return

        return True
    return False

def search_valid_folders(directory):
    valid_folders = []
    if os.path.isdir(directory):
        for item in sorted(os.listdir(directory)):
            item_path = os.path.join(directory, item)
            if os.path.isdir(item_path) and has_game_folder(item_path):
                valid_folders.append(item)
    return valid_folders

def browse_directory():
    global start
    selected_dir = filedialog.askdirectory()
    if selected_dir:
        directory_entry.delete(0, tk.END)
        directory_entry.insert(0, selected_dir)
        save_directory(selected_dir)
    start = False
    update_ui()

def rescan_folders():
    global start
    start = False
    update_ui()

def print_game(event=None):
    game_folder = find_game(os.path.join(load_directory(), folder_dropdown.get()))
    print(f"Game path: {game_folder}")
    update_ui()


def update_ui(event=None):
    global start

    if not os.path.exists(os.path.join(LIB_DIR,"renpy-7.8.7-sdk")):
        install_button.configure(state="normal")
    if os.path.exists(os.path.join(LIB_DIR, "renpy-6.99.14.3-sdk")):
        install_button.configure(state="disabled")
    if not os.path.exists(os.path.join(LIB_DIR,"audio.rpa")):
        select_button.configure(state="normal")
    if os.path.exists(os.path.join(LIB_DIR,"audio.rpa")):
        select_button.configure(state="disabled")
        
    valid_renpy = specific_compat()
    valid_folders = search_valid_folders(load_directory())

    folder_dropdown.configure(values = valid_folders)
    valid_renpy = ["None"] + valid_renpy
    valid_renpys = [i.removeprefix("renpy-").removesuffix("-sdk") for i in valid_renpy]
    compat_folder_dropdown.configure(values = valid_renpys)

    if not start:
        if not valid_folders:
            messagebox.showinfo("Info", "No valid folders found")
            return
        compat_folder_dropdown.set(valid_renpys[0])
        folder_dropdown.set(valid_folders[0])
        start = True


    folder_dropdown.selection_clear()
    compat_folder_dropdown.selection_clear()

    if folder_dropdown.get() != '':
        version = get_renpy_version()
    else:
        version = "None"
    if version != "None":
        version_label.configure(text=f"Original Ren'Py Version: {version}")
        launch_button.configure(state="normal")
        status_label.configure(text="Ready to launch!")
        if is_compat() and compat_folder_dropdown.get() == "None":
            launch_button.configure(state="disabled")
            status_label.configure(text="")
        if check_downloaded():
            download_button.configure(state="disabled")
            download_button.configure(text="Compatibility Downloaded")
        else:
            download_button.configure(state="normal")
            download_button.configure(text="Download Original Mod's Ren'Py")
    else:
        version_label.configure(text="Original Ren'Py version unknown, use compatibility")

        if not (is_compat() and specific_compat()):
            launch_button.configure(state="disabled")
            status_label.configure(text="")
        if compat_folder_dropdown.get() == "None":
            launch_button.configure(state="disabled")
            status_label.configure(text="")
        status_label.configure(text="")
        copy_button.configure(state="disabled")
        download_button.configure(state="disabled")
        download_button.configure(text="Download Original Mod's Ren'Py")

    if folder_dropdown.get() != '':
        files_status, missing_files = check_and_copy_files(os.path.join(load_directory(), folder_dropdown.get()))
        if is_rpa_override():
            missing_files = False
        if not missing_files:
            copy_button.configure(state="disabled")
        else:
            status_label.configure(text=f"Missing files: {', '.join(missing_files)}")
            copy_button.configure(state="normal")
            launch_button.configure(state="disabled")

        if (files_status and version and (compat_folder_dropdown.get() != "None")) or (files_status and is_compat() and (compat_folder_dropdown.get() != "None")):
            status_label.configure(text="Ready to launch!")
            launch_button.configure(state="normal")

def extract_rpas():
    zip_file_path = filedialog.askopenfilename(
        title="Select DDLC ZIP file",
        filetypes=[("ZIP files", "*.zip"), ("All files", "*.*")]
    )

    if not zip_file_path:
        messagebox.showinfo("Info", "Not a valid DDLC zip file")
        return

    extract_to = LIB_DIR
    files_to_extract = [
        'DDLC-1.1.1-pc/game/audio.rpa',
        'DDLC-1.1.1-pc/game/fonts.rpa',
        'DDLC-1.1.1-pc/game/images.rpa',
        'DDLC-1.1.1-pc/game/scripts.rpa',
        'DDLC-1.1.1-pc/game/python-packages/singleton.py'
    ]
    characters_to_extract = [
        'DDLC-1.1.1-pc/characters/monika.chr',
        'DDLC-1.1.1-pc/characters/sayori.chr',
        'DDLC-1.1.1-pc/characters/natsuki.chr',
        'DDLC-1.1.1-pc/characters/yuri.chr'
    ]
    try:
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            for file in files_to_extract:
                if file in zip_ref.namelist():
                    extracted_data = zip_ref.read(file)
                    file_name = os.path.basename(file)
                    output_path = os.path.join(extract_to, file_name)
                    with open(output_path, 'wb') as output_file:
                        output_file.write(extracted_data)
                    status_label.configure(text=f'Extracted: {file}')
                else:
                    messagebox.showerror("Error", f'File not found in ZIP: {file}')
                    update_ui()
                    return
            for file in characters_to_extract:
                if file in zip_ref.namelist():
                    extracted_data = zip_ref.read(file)
                    file_name = os.path.basename(file)
                    os.makedirs((os.path.join(LIB_DIR, "characters")), exist_ok=True)
                    output_path = os.path.join(extract_to, "characters", file_name)
                    with open(output_path, 'wb') as output_file:
                        output_file.write(extracted_data)
                    status_label.configure(text=f'Extracted: {file}')
                else:
                    messagebox.showerror("Error", f'File not found in ZIP: {file}')
                    update_ui()
                    return

        select_button.configure(state="disabled")
        update_ui()

    except Exception as e:
        messagebox.showerror("Error", f"Error extracting files: {e}")

def get_platform_info():
    system = platform.system()
    platform_map = {
        'Windows': 'windows-x86_64',
        'Linux': 'linux-x86_64',
        'Darwin': 'mac-universal'
    }
    return (platform_map.get(system, 'Unknown'), '.exe' if system == 'Windows' else '.sh')

def get_renpy_exe(renpy_version, original=False):
    compat_version = compat_folder_dropdown.get()
    if renpy_version:
        major_version = renpy_version.split('.')[0]
    elif compat_version != "None":
        major_version = compat_version.split('.')[0]
    else:
        return None
    print(f"Major Ren'Py version: {major_version}")
    platform_name, exe_suffix = get_platform_info()
    print(f"Platform: {platform_name}")
    if major_version == "6":
        lib_version = "6.99.14.3"
        python_version = ''
        if platform_name == "windows-x86_64":
            platform_name = "windows-i686"
    elif major_version == "7":
        python_version = 'py2-'
        lib_version = "7.8.7"
    else:
        python_version = 'py3-'
        lib_version = "8.3.7"

    python_name = python_version + platform_name
    version = get_renpy_version()

    if compat_mode.get():
        if compat_folder_dropdown.get() != "None":
            compat_version = compat_folder_dropdown.get()
            sdk_version = f"renpy-{compat_version}-sdk"
        else:
            sdk_version = f"renpy-{version}-sdk"
    else:
        sdk_version = f"renpy-{lib_version}-sdk"
    game_folder = find_game(os.path.join(load_directory(), folder_dropdown.get()), parent=True)
    for file in os.listdir(game_folder):
        if file.endswith("32.exe"):
            continue
        if file.endswith(".exe"):
            game_name = file.strip(".exe")
    full_renpy_path = os.path.join(LIB_DIR, sdk_version, "lib", python_name, "renpy")
    renpy_path = os.path.join(LIB_DIR, sdk_version, f"renpy{exe_suffix}")

    try: original_path = os.path.join(game_folder, f"{game_name}{exe_suffix}")
    except: original_path = "None"
    if platform_name == "linux-x86_64":
        os.popen(f'chmod +x "{renpy_path}"')
        os.popen(f'chmod +x "{full_renpy_path}"')
        os.popen(f'chmod +x "{original_path}"')

    if original:
        if os.path.exists(original_path):
            print(f"Original executable: '{original_path}'")
            return original_path
        else:
            return None
    else:
        if os.path.exists(renpy_path):
            print(f"Ren'Py path: '{renpy_path}'")
            return renpy_path
        else:
            return None

def specific_compat():
    renpy_versions = []
    for item in sorted(os.listdir(LIB_DIR)):
        item_path = os.path.join(LIB_DIR, item)
        if os.path.isdir(item_path) and item.startswith("renpy"):
            renpy_versions.append(item)
    return renpy_versions

def is_compat():
    return compat_mode.get()

def is_rpa_override():
    return override_rpas.get()

def check_downloaded():
    version = get_renpy_version()
    return os.path.exists(os.path.join(LIB_DIR, f"renpy-{version}-sdk"))


def launch_original():
    launch_game(original=True)

def launch_game(original=False):
    base_folder = os.path.join(MOD_DIR, folder_dropdown.get())
    full_path = find_game(base_folder, parent=True)

    version = get_renpy_version()

    renpy_exe = get_renpy_exe(version, original)
    if not renpy_exe:
        messagebox.showerror("Error", "Ren'Py executable not found. Install the base Ren'Py libraries first.")
        return
    time.sleep(0.5)
    if original:
        try:
            subprocess.Popen([renpy_exe], shell=True if platform.system() == "Windows" else False)
            status_label.configure(text="Launched successfully!")
        except Exception as e:
            messagebox.showerror(f"Launching {renpy_exe} Failed", f"Error: {str(e)}")
    else:
        try:
            subprocess.Popen([renpy_exe, full_path], shell=True if platform.system() == "Windows" else False)
            status_label.configure(text="Launched successfully!")
        except Exception as e:
            messagebox.showerror(f"Launching {renpy_exe} Failed", f"Error: {str(e)}")

def disable_all_widgets(parent):
    for child in parent.winfo_children():
        if isinstance(child, (ctk.CTkButton, ctk.CTkEntry, ctk.CTkButton, ctk.CTkEntry, ctk.CTkCheckBox)):
            child.configure(state='disabled')
        elif isinstance(child, (ctk.CTkFrame, ctk.CTkFrame)):
            disable_all_widgets(child)

def enable_all_widgets(parent):
    for child in parent.winfo_children():
        if isinstance(child, (ctk.CTkButton, ctk.CTkEntry, ctk.CTkButton, ctk.CTkEntry, ctk.CTkCheckBox)):
            child.configure(state='normal')
        elif isinstance(child, (ctk.CTkFrame, ctk.CTkFrame)):
            enable_all_widgets(child)

def download_and_extract():
    version = get_renpy_version()
    open_downloader(version)

def download_patch():
    url = "https://kaylathepianist.gay/z_patches.rpy"
    try:
        response = requests.get(url)
        response.raise_for_status()
        patch = os.path.join(LIB_DIR, "z_patches.rpy")
        with open(patch, 'wb') as file:
            file.write(response.content)
        print(f"Downloaded Ren'Py game patches from '{url}'")
    except Exception as e:
        messagebox.showerror("Error", f"An error occured: {e}")


def start_download():
    install_button.configure(state="disabled")
    open_downloader("6.99.14.3", startup = 1)

def start_download2():
    open_downloader("7.8.7", startup = 2)

def start_download3():
    open_downloader("8.3.7", startup = 3)
    status_label.configure(text="Downloads complete!")



def extract_rar(file, path=None):
    if path is None:
        path = os.path.join(MOD_DIR, os.path.basename(file))
    try:
        with rarfile.RarFile(file, 'r') as rf:
            rf.extractall(path)
        print(f"Successfully extracted '{file}' to '{path}'")
    except rarfile.Error as e:
        print(f"Error extracting '{file}': {e}")
    except Exception as e:
         print(f"An unexpected error occurred: {e}")
    os.remove(file)
    if not has_game_folder(path):
        move_to_game(path)
    rescan_folders()


def extract_zip(file, path=None):
    if path is None:
        path = os.path.join(MOD_DIR, os.path.basename(file))
    try:
        with zipfile.ZipFile(file, 'r') as zip_ref:
            zip_ref.extractall(path)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    try: os.remove(file)
    except Exception as e:
        print(f"{e}")
    # if not has_game_folder(path):
    #     print(path)
    #     move_to_game(path)
    rescan_folders()



def move_to_game(source):
    dest_dir = os.path.join(source, "game")

    try:
        os.makedirs(dest_dir, exist_ok=True)
    except OSError as e:
         print(f"Error creating directory {dest_dir}: {e}")
         return

    for filename in os.listdir(source):
        source_path = os.path.join(source, filename)
    
        if os.path.isfile(source_path):
            dest_path = os.path.join(dest_dir, filename)
            try:
                shutil.copy2(source_path, dest_path)
            except Exception as e:
                print(f"Error copying {filename}: {e}")


CHUNK_SIZE = 128 * 1024

def extractDownloadLink(contents):
    for line in contents.splitlines():
        m = re.search(r'href="(https://download[^"]+)', line)
        if m:
            return m.groups()[0]
    return None


def info_popup():

    popup = ctk.CTkToplevel()
    popup.title("Information and Setup")

    popup.geometry("680x350")

    label = ctk.CTkLabel(popup, text="Welcome to the experimental DDLC Mod Loader!\n\nThis is a project made entirely in Python and uses the command line interface of the Ren'Py launcher\nin order to attempt to run any DDLC mod with minimal effort installation!\n\nTo start off, browse for your mod folder (or use the one created here for you), select your DDLC zip to\ncopy over required files, and click the button to install the 3 main Ren'Py libraries that should run a good\namount of mods (I hope).\n\nThe Mod Loader should automatically detect the original Ren'Py version a mod was created on, and if\nanything goes wrong with the default launch library, you can use the \"Compatibility Download\" button\nin order to install the exact version that the mod was built on, which should basically always work.\n\nIf you have any questions, bugs, or suggestions, contact me on Discord at kayla_teehee.")
    label.pack(pady=5)

    close_button = ctk.CTkButton(popup, text="Close", command=popup.destroy)
    close_button.pack(side="bottom", pady=10)

    popup.focus()
    root.wait_window(popup)


mod_json = os.path.join(LOADER_DIR, "modlist.json")

with open(mod_json, 'r') as file:
    mods_data = json.load(file)
    mods_data = [item for item in mods_data if item['Focus'] == "Sayori"]

def open_modlist():
    popup = ctk.CTkToplevel(root)
    popup.title("Mods List")
    popup.geometry("400x300")
    
    scrollable_frame = ctk.CTkScrollableFrame(popup, width=380)
    close_button = ctk.CTkButton(popup, text="Close", command=popup.destroy)
    close_button.pack(side="bottom", pady=10)

    chunk_size = 20
    loaded_count = 0
    total_mods = len(mods_data)

    def load_items(start, end):
        nonlocal loaded_count
        for mod in mods_data[start:end]:
            button = ctk.CTkButton(
                scrollable_frame,
                text=mod["Mod Name"],
                command=lambda m=mod: button_click(m)
                )
            button.pack(pady=5)
        loaded_count = min(loaded_count + chunk_size, total_mods)

    def check_scroll(event=None):
        canvas = scrollable_frame._parent_canvas  # Access underlying canvas
        _, yview_end = canvas.yview()
        if yview_end > 0.9 and loaded_count < total_mods:
            # Load next chunk when 90% scrolled
            load_items(loaded_count, loaded_count + chunk_size)
        
    def on_mousewheel(event):
        canvas = scrollable_frame._parent_canvas
        if event.num == 4 or event.delta > 0:
            canvas.yview_scroll(-1, "units")
        elif event.num == 5 or event.delta < 0:
            canvas.yview_scroll(1, "units")
        check_scroll()

    popup.bind("<MouseWheel>", on_mousewheel)  # Windows
    popup.bind("<Button-4>", on_mousewheel)    # Linux scroll up
    popup.bind("<Button-5>", on_mousewheel)    # Linux scroll down
    popup.bind("<Configure>", check_scroll)   # Window resize

    load_items(0, chunk_size)
    
    scrollable_frame.pack(side="left", fill="both", expand=True)
    popup.focus()


def button_click(mod):
    open_downloader(mod, is_mod=True)

def open_downloader(url, is_mod=False, startup=None):
    popup = ctk.CTkToplevel(root)
    popup.title("DDLC Mod Loader")
    popup.geometry("400x130")
    popup.wait_visibility()
    popup.grab_set()
    popup.focus_set()
    root.grab_release()
    progress_text = ctk.CTkLabel(popup, text="Downloading...")
    progress_text.pack(pady=8)

    progress_bar = ctk.CTkProgressBar(popup, orientation="horizontal", width=300, height=30, mode="determinate")
    progress_bar.pack(pady=5)
    progress_bar.set(0)

    close_button = ctk.CTkButton(popup, text="Close", command=popup.destroy)
    close_button.pack(side="bottom", pady=10)
    if is_mod:
        mod = url
        url = str(mod["Download Link"])
    else:
        pass
    def download_thread(link, startup=None):

        if link.startswith("https"): 
            if link.startswith("https://drive.google.com"):
                url = link.strip("https://drive.google.com/file/d/")
                url = url.split("/", 1)[0]
                url = f"https://drive.usercontent.google.com/download?id={url}&export=download&authuser=0&confirm=t"
            else:
                url = link
        else:
            url = f"https://www.renpy.org/dl/{link}/renpy-{link}-sdk.zip"
        if link.startswith("https://www.mediafire"):
            url_origin = link
            sess = requests.Session()
            sess.headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            }

            while True:
                try:
                    res = sess.get(url_origin, stream=True, verify=True)
                except requests.exceptions.SSLError as e:
                    print(f"SSL error: {e}")
                    return
                except requests.exceptions.RequestException as e:
                    print(f"Request error: {e}")
                    return

                if 'Content-Disposition' in res.headers:
                    # This is the file
                    break

                # Need to redirect with confirmation
                url_origin = extractDownloadLink(res.text)
                if url_origin is None:
                    print(f'Permission denied: {url}')
                    print("Maybe you need to change permission to 'Anyone with the link'?")
                    return
                
                
            file_name = mod["Mod Name"]
            with open(file_name, 'wb') as file:

                try:
                    total = res.headers.get('Content-Length')
                    if total is not None:
                        total = int(total)
                    downloaded_size = 0
                    for chunk in res.iter_content(chunk_size=CHUNK_SIZE):
                        file.write(chunk)
                        downloaded_size += len(chunk)
                        progress = (downloaded_size / total) if total > 0 else 0
                        root.after(0, progress_bar.set(value=progress))
                        root.after(0, popup.update_idletasks)
                    print("Done")

                except Exception as e:
                    print(e)
                    return
        else:
            status_label.configure(text=f"Downloading from: {url}")
            try:
                response = requests.get(url, stream=True)
                response.raise_for_status()
                total_size = int(response.headers.get('content-length', 0))
                block_size = (1024 * 128)
                downloaded_size = 0
                if is_mod:
                    file_name = mod["Mod Name"]
                else:
                    file_name = url.split('/')[-1]
                with open(file_name, 'wb') as file:
                    for data in response.iter_content(block_size):
                        file.write(data)
                        downloaded_size += len(data)
                        progress = (downloaded_size / total_size)
                        root.after(0, progress_bar.set(value=progress))
                        root.after(0, popup.update_idletasks)
            except Exception as e:
                root.after(0, print("Error", f"An error occurred: {e}"))
                root.after(0, lambda: progress_text.configure(text="Download or extraction failed."))
        root.after(0, lambda: progress_text.configure(text="Extracting..."))
        type = filetype.guess(file_name)
        if type.extension == "rar":
            root.after(0, extract_rar(file_name))
        else:
            root.after(0, extract_zip(file_name))
        if startup == 1:
            root.after(0, start_download2)
        elif startup == 2:
            root.after(0, start_download3)
        else:
            root.after(0, lambda: progress_text.configure(text="Download and extraction complete!"))
            root.after(0, update_ui)




    thread = threading.Thread(target=download_thread, args=(url, startup), daemon=True)
    thread.start()
    popup.focus()


root = ctk.CTk()
root.title("DDLC Mod Launcher")
root.geometry("600x700")

directory_frame = ctk.CTkFrame(root)
directory_frame.pack(pady=5, padx=5)

directory_instructions = ctk.CTkLabel(directory_frame, text="Choose the folder where you store your mods")
directory_instructions.pack(pady=5)

directory_entry = ctk.CTkEntry(directory_frame, width=300)
directory_entry.pack(side="left", padx=5)
directory_entry.insert(0, str(load_directory()))

browse_button = ctk.CTkButton(directory_frame, text="Browse", command=browse_directory)
browse_button.pack(side="left", padx=5)

dropdown_frame = ctk.CTkFrame(root)
dropdown_frame.pack(pady=5)

select_button = ctk.CTkButton(dropdown_frame, text="Select DDLC Zip File (First time only)", state="disabled", command=extract_rpas)
select_button.pack(pady=5)

install_button = ctk.CTkButton(dropdown_frame, text="Click to install base Ren'Py libraries (first time only)", state="disabled", command=start_download)
install_button.pack(pady=5)

folder_label = ctk.CTkLabel(dropdown_frame, text="Select Mod:")
folder_label.pack(pady=5)

folder_dropdown = ctk.CTkComboBox(dropdown_frame, width=360, state="readonly", command=print_game)
folder_dropdown.pack(side="left", padx=5)

folder_refresh = ctk.CTkButton(dropdown_frame, text="Rescan", command=lambda: rescan_folders())
folder_refresh.pack(side="left", padx=5)

version_label = ctk.CTkLabel(root, text="Original Ren'Py Version: Not detected")
version_label.pack(pady=5)

launch_frame = ctk.CTkFrame(root)
launch_frame.pack(pady=5)

copy_button = ctk.CTkButton(launch_frame, text="Copy Missing Files", state="disabled", command=lambda: copy_missing_files(os.path.join(load_directory(), folder_dropdown.get())))
copy_button.pack(pady=5, padx=5)

launch_button = ctk.CTkButton(launch_frame, text="Launch", state="normal", command=launch_game)
launch_button.pack(pady=5)


test_button = ctk.CTkButton(launch_frame, text="test", state="normal", command=open_modlist)
test_button.pack(pady=5)


status_label = ctk.CTkLabel(launch_frame, text="")
status_label.pack(pady=5)

compatibility_frame = ctk.CTkFrame(root)
compatibility_frame.pack(pady=5, padx=5)

compat_label = ctk.CTkLabel(compatibility_frame, text="Extra Compatibility (Usually Not Required)")
compat_label.pack(pady=5)

download_button = ctk.CTkButton(compatibility_frame, text="Download Original Mod's Ren'Py", state="disabled", command=lambda: download_and_extract())
download_button.pack(pady=5)

compat_mode = ctk.BooleanVar()
check_compat = ctk.CTkCheckBox(compatibility_frame, text="Compatibility Mode (Launch using a specific downloaded Ren'Py version)", command=update_ui, variable=compat_mode, onvalue=True, offvalue=False)
check_compat.pack(pady=5, padx=5)

compat_folder_label = ctk.CTkLabel(compatibility_frame, text="Select specific Ren'Py version (may not work!):")
compat_folder_label.pack(pady=5)

compat_folder_dropdown = ctk.CTkComboBox(compatibility_frame, width=300, state="readonly", command=update_ui)
compat_folder_dropdown.pack(pady=5)

override_rpas = ctk.BooleanVar()
check_rpas = ctk.CTkCheckBox(compatibility_frame, text="Override missing RPA files (Will likely not work)", command=update_ui, variable=override_rpas, onvalue=True, offvalue=False)
check_rpas.pack(pady=5)

open_popup_button = ctk.CTkButton(root, text="Info and Setup", command=info_popup)
open_popup_button.pack(pady=20)

print_game()
root.mainloop()
