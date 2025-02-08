import FreeSimpleGUI as sg
import json
import os
import queue
import requests
import threading
import time
from datetime import datetime
from zipfile import ZipFile


def get_config_path():
    """Get the path to the config file in the user's AppData directory."""
    app_data = os.getenv('APPDATA') or os.path.expanduser('~')
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
        'save_local_copy': True
    }

    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
                # Verify all paths still exist
                if not os.path.exists(config.get('db_path', '')):
                    config['db_path'] = ''
                if not os.path.exists(config.get('fwl_path', '')):
                    config['fwl_path'] = ''
                return config
    except Exception as e:
        print(f"Error loading config: {e}")

    return default_config


def save_config(values):
    """Save the configuration to file."""
    config_path = get_config_path()
    config = {
        'db_path': values[0],
        'fwl_path': values[1],
        'file_tag': values[2],
        'save_local_copy': values['-SAVE-']
    }

    try:
        with open(config_path, 'w') as f:
            json.dump(config, f)
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


def create_gui():
    config = load_config()

    layout = [
        [sg.Text("Valheim Save Sharing Tool")],
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
        [sg.Button("Share savefile"), sg.Button("Exit")],
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

            save_config(values)

            if not db_path or not fwl_path:
                sg.popup_error("Please select both .db and .fwl files.")
                continue

            try:
                db_size = os.path.getsize(db_path)
                fwl_size = os.path.getsize(fwl_path)
            except OSError:
                sg.popup_error("Error accessing selected files. Please verify the paths.")
                continue

            db_size = os.path.getsize(db_path)
            fwl_size = os.path.getsize(fwl_path)
            total_size = db_size + fwl_size

            # 512MB in bytes
            MAX_SIZE = 512 * 1024 * 1024

            if total_size > MAX_SIZE:
                sg.popup_error(
                    f"Total file size ({total_size / 1024 / 1024:.1f}MB) exceeds the 512MB limit!\n"
                    "Please use a different sharing method for files this large."
                )
                continue

            if db_path and fwl_path:
                progress_layout = [
                    [sg.Text("Creating and uploading savefile share...")],
                    [sg.ProgressBar(100, orientation="h", size=(30, 20), key="-PROG-")],
                    [sg.Text("", key="-STATUS-")]
                ]
                progress_window = sg.Window("Processing", progress_layout, modal=True, finalize=True)
                progress_bar = progress_window["-PROG-"]
                status_text = progress_window["-STATUS-"]

                new_file_path = (
                    f"{file_tag}_{datetime.now().strftime('%Y%m%d_%H%M')}.zip"
                )
                with ZipFile(new_file_path, "w") as myzip:
                    myzip.write(db_path, os.path.basename(db_path))
                    myzip.write(fwl_path, os.path.basename(fwl_path))

                headers = {"User-Agent": "ValheimSaveShareTool/1.0"}
                with open(new_file_path, "rb") as f:
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
                                        layout = [
                                            [sg.Text("Savefile zip created and uploaded!")],
                                            [
                                                sg.Text("URL:"),
                                                sg.Input(url, key="-URL-", readonly=True),
                                                sg.Button("Copy URL"),
                                            ],
                                            [sg.Button("OK")],
                                        ]
                                        popup_window = sg.Window("Success", layout)
                                        while True:
                                            popup_event, _ = popup_window.read()
                                            if popup_event == "Copy URL":
                                                sg.clipboard_set(url)
                                                sg.popup_quick_message(
                                                    "URL copied to clipboard!", auto_close_duration=1
                                                )
                                            if popup_event in (sg.WIN_CLOSED, "OK"):
                                                break
                                        popup_window.close()
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
                            if elapsed_time > 0.1 and step_index < len(steps):
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

                    window.close()
                    break

    window.close()


create_gui()
