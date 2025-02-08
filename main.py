import json
import os
import queue
import requests
import threading
import time
from datetime import datetime
from urllib.parse import urlparse
from zipfile import ZipFile

import FreeSimpleGUI as sg


def get_config_path():
    """Get the path to the config file in the user's AppData directory."""
    app_data = os.path.expanduser('~')
    config_dir = os.path.join(app_data, 'ValheimSaveShare')
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
    return os.path.join(config_dir, 'config.json')


def load_config():
    """Load the configuration from file."""
    config_path = get_config_path()
    default_config = {
        'db_path': '',
        'fwl_path': '',
        'file_tag': '',
        'save_local_copy': True,
        'download_dir': os.path.join(os.path.expanduser('~'), 'AppData', 'LocalLow', 'IronGate', 'Valheim', 'worlds_local')
    }

    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
                # Verify all paths still exist
                if not config.get('db_path', ''):
                    config['db_path'] = ''
                if not config.get('fwl_path', ''):
                    config['fwl_path'] = ''
                if not config.get('download_dir', ''):
                    config['download_dir'] = os.path.expanduser('~')
                return config
    except Exception as e:
        print(f"Error loading config: {e}")

    return default_config


def save_config(values, is_upload_tab=True):
    """Save the configuration to file."""
    config_path = get_config_path()
    current_config = load_config()

    if is_upload_tab:
        current_config.update({
            'db_path': values[0],
            'fwl_path': values[1],
            'file_tag': values[2],
            'save_local_copy': values['-SAVE-']
        })
    else:
        current_config.update({
            'download_dir': values['-DOWNLOAD-DIR-']
        })

    try:
        with open(config_path, 'w') as f:
            json.dump(current_config, f)
    except Exception as e:
        print(f"Error saving config: {e}")


def upload_file(new_file_path, progress_queue):
    """Handle file upload in a separate thread."""
    headers = {"User-Agent": "ValheimSaveShareTool/1.0"}
    try:
        with open(new_file_path, "rb") as f:
            response = requests.post(
                "https://0x0.st",
                files={"file": (new_file_path, f)},
                data={"secret": new_file_path, "expires": 72},
                headers=headers,
            )
        progress_queue.put(("complete", response))
    except Exception as e:
        progress_queue.put(("error", str(e)))


def download_save(url, download_dir, progress_queue):
    """Handle file download in a separate thread."""
    try:
        # Validate URL
        parsed_url = urlparse(url)
        if not parsed_url.netloc == "0x0.st":
            raise ValueError("Invalid URL. Must be a 0x0.st link.")

        # Download the file
        headers = {"User-Agent": "ValheimSaveShareTool/1.0"}
        response = requests.get(url, stream=True, headers=headers)
        if response.status_code != 200:
            raise Exception(f"Download failed with status code: {response.status_code}")

        # Get filename from Content-Disposition header or URL
        filename = "valheim_save.zip"
        cd = response.headers.get('content-disposition')
        if cd:
            filename = cd.split('filename=')[1].strip('"')
        else:
            filename = os.path.basename(url)

        if not filename.endswith('.zip'):
            filename += '.zip'

        download_path = os.path.join(download_dir, filename)

        # Download the file
        total_size = int(response.headers.get('content-length', 0))
        block_size = 8192
        downloaded = 0

        with open(download_path, 'wb') as f:
            for data in response.iter_content(block_size):
                downloaded += len(data)
                f.write(data)
                if total_size:
                    progress = int((downloaded / total_size) * 50)
                    progress_queue.put(("progress", progress))

        # Extract the ZIP file
        progress_queue.put(("status", "Extracting files..."))
        with ZipFile(download_path, 'r') as zip_ref:
            zip_ref.extractall(download_dir)

        # Remove the ZIP file
        os.remove(download_path)

        progress_queue.put(("complete", "Files downloaded and extracted successfully!"))

    except Exception as e:
        progress_queue.put(("error", str(e)))


def create_gui():
    config = load_config()

    upload_tab_layout = [
        [
            sg.Text(".db file:"),
            sg.Input(default_text=config['db_path']),
            sg.FileBrowse(file_types=(("DB File", "*.db"),)),
        ],
        [
            sg.Text(".fwl file:"),
            sg.Input(default_text=config['fwl_path']),
            sg.FileBrowse(file_types=(("FWL File", "*.fwl"),)),
        ],
        [
            sg.Text("File tag (Optional)"),
            sg.Input(default_text=config['file_tag']),
        ],
        [sg.Checkbox("Retain local copy of .zip", default=config['save_local_copy'], key="-SAVE-")],
        [
            sg.Text(
                "Note: Files will be uploaded to 0x0.st file hosting service. Limited to 512MB."
            )
        ],
        [sg.Button("Share savefile")]
    ]

    download_tab_layout = [
        [sg.Text("0x0.st URL:"), sg.Input(key="-URL-")],
        [
            sg.Text("Download Location:"),
            sg.Input(default_text=config['download_dir'], key="-DOWNLOAD-DIR-"),
            sg.FolderBrowse(),
        ],
        [sg.Button("Download savefile")]
    ]

    layout = [
        [sg.Text("Valheim Save Sharing Tool", font=("Helvetica", 16))],
        [sg.TabGroup([
            [
                sg.Tab("Upload Save", upload_tab_layout),
                sg.Tab("Download Save", download_tab_layout)
            ]
        ])],
        [sg.Button("Exit")]
    ]

    window = sg.Window("Valheim Save Sharing", layout)

    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED or event == "Exit":
            break

        if event == "Share savefile":
            db_path = values[0]
            fwl_path = values[1]
            file_tag = values[2] or "save"
            save_local_copy = values["-SAVE-"]

            save_config(values, is_upload_tab=True)

            if not db_path or not fwl_path:
                sg.popup_error("Please select both .db and .fwl files.")
                continue

            try:
                db_size = os.path.getsize(db_path)
                fwl_size = os.path.getsize(fwl_path)
            except OSError:
                sg.popup_error("Error accessing selected files. Please verify the paths.")
                continue

            total_size = db_size + fwl_size
            MAX_SIZE = 512 * 1024 * 1024

            if total_size > MAX_SIZE:
                sg.popup_error(
                    f"Total file size ({total_size / 1024 / 1024:.1f}MB) exceeds the 512MB limit!\n"
                    "Please use a different sharing method for files this large."
                )
                continue

            # Create progress window
            progress_layout = [
                [sg.Text("Creating and uploading savefile share...")],
                [sg.ProgressBar(100, orientation="h", size=(30, 20), key="-PROG-")],
                [sg.Text("", key="-STATUS-")]
            ]
            progress_window = sg.Window("Processing", progress_layout, modal=True, finalize=True)
            progress_bar = progress_window["-PROG-"]
            status_text = progress_window["-STATUS-"]

            # Create ZIP file
            new_file_path = f"{file_tag}_{datetime.now().strftime('%Y%m%d_%H%M')}.zip"
            try:
                with ZipFile(new_file_path, "w") as myzip:
                    myzip.write(db_path, os.path.basename(db_path))
                    myzip.write(fwl_path, os.path.basename(fwl_path))
            except Exception as e:
                progress_window.close()
                sg.popup_error(f"Error creating ZIP file: {str(e)}")
                continue

            # Setup upload thread and queue
            import queue
            progress_queue = queue.Queue()
            upload_thread = threading.Thread(
                target=upload_file,
                args=(new_file_path, progress_queue),
                daemon=True
            )
            upload_thread.start()

            # Animate progress bar while uploading
            current_progress = 0
            start_time = time.time()
            steps = [
                (0, "Creating ZIP file..."),
                (30, "Preparing upload..."),
                (50, "Uploading files..."),
                (80, "Finalizing upload..."),
                (95, "Almost done...")
            ]
            step_index = 0
            
            while True:
                try:
                    # Check if upload is complete
                    try:
                        result = progress_queue.get_nowait()
                        if result[0] == "complete":
                            response = result[1]
                            progress_window.close()
                            
                            if response.status_code == 200:
                                url = response.text.strip()
                                sg.clipboard_set(url)

                                # Create success popup but don't close main window yet
                                layout = [
                                    [sg.Text("Save file zip created and uploaded! URL has been copied to clipboard.")],
                                    [sg.Button("OK")],
                                ]
                                popup_window = sg.Window("Success", layout, modal=True)
                                popup_window.read(close=True)
                                popup_window.close()

                                sg.clipboard_set(url)
                            else:
                                sg.popup(
                                    f"Savefile share created but upload failed.\nStatus code: {response.status_code}"
                                )
                            break
                        elif result[0] == "error":
                            progress_window.close()
                            sg.popup_error(f"Upload error: {result[1]}")
                            break
                    except queue.Empty:
                        pass

                    # Update progress animation
                    elapsed_time = time.time() - start_time
                    if elapsed_time > 0.5 and step_index < len(steps):
                        target_progress, status = steps[step_index]
                        if current_progress < target_progress:
                            current_progress += 1
                            progress_bar.update(current_progress)
                            status_text.update(status)
                        elif current_progress == target_progress:
                            step_index += 1
                        start_time = time.time()

                    progress_event, _ = progress_window.read(timeout=100)
                    if progress_event == sg.WIN_CLOSED:
                        break

                except Exception as e:
                    progress_window.close()
                    sg.popup_error(f"Unexpected error: {str(e)}")
                    break

            if not save_local_copy and os.path.exists(new_file_path):
                try:
                    os.remove(new_file_path)
                except Exception as e:
                    print(f"Error removing temporary file: {e}")

        elif event == "Download savefile":
            url = values["-URL-"].strip()
            download_dir = values["-DOWNLOAD-DIR-"]
            
            save_config(values, is_upload_tab=False)

            if not url:
                sg.popup_error("Please enter a valid 0x0.st URL.")
                continue

            if not download_dir or not os.path.exists(download_dir):
                sg.popup_error("Please select a valid download directory.")
                continue

            # Create progress window
            progress_layout = [
                [sg.Text("Downloading and extracting savefile...")],
                [sg.ProgressBar(100, orientation="h", size=(30, 20), key="-PROG-")],
                [sg.Text("", key="-STATUS-")]
            ]
            progress_window = sg.Window("Processing", progress_layout, modal=True, finalize=True)
            progress_bar = progress_window["-PROG-"]
            status_text = progress_window["-STATUS-"]

            # Setup download thread and queue
            import queue
            progress_queue = queue.Queue()
            download_thread = threading.Thread(
                target=download_save,
                args=(url, download_dir, progress_queue),
                daemon=True
            )
            download_thread.start()

            current_progress = 0
            while True:
                try:
                    try:
                        result = progress_queue.get_nowait()
                        if result[0] == "complete":
                            progress_window.close()
                            sg.popup("Success", result[1])
                            break
                        elif result[0] == "error":
                            progress_window.close()
                            sg.popup_error(f"Download error: {result[1]}")
                            break
                        elif result[0] == "progress":
                            current_progress = result[1]
                            progress_bar.update(current_progress)
                        elif result[0] == "status":
                            status_text.update(result[1])
                            current_progress = 75
                            progress_bar.update(current_progress)
                    except queue.Empty:
                        pass

                    progress_event, _ = progress_window.read(timeout=100)
                    if progress_event == sg.WIN_CLOSED:
                        break

                except Exception as e:
                    progress_window.close()
                    sg.popup_error(f"Unexpected error: {str(e)}")
                    break

    window.close()


create_gui()
