import FreeSimpleGUI as sg
import os
import requests
from datetime import datetime
from zipfile import ZipFile


def create_gui():
    layout = [
        [sg.Text("Valheim Save Sharing Tool")],
        [
            sg.Text(".db file:"),
            sg.Input(),
            sg.FileBrowse(file_types=(("DB File", "*.db"),)),
        ],
        [
            sg.Text(".fwl file:"),
            sg.Input(),
            sg.FileBrowse(file_types=(("FWL File", "*.fwl"),)),
        ],
        [
            sg.Text("File tag (Optional)"),
            sg.Input(),
        ],
        [sg.Checkbox("Retain local copy of .zip", default=True, key="-SAVE-")],
        [
            sg.Text(
                "Note: Files will be uploaded to 0x0.st file hosting service. Limited to 512MB."
            )
        ],
        [sg.Button("Create savefile zip"), sg.Button("Exit")],
    ]

    window = sg.Window("Valheim Save Sharing", layout)

    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED or event == "Exit":
            break
        if event == "Create savefile zip":
            db_path = values[0]
            fwl_path = values[1]
            file_tag = values[2] or "save"
            save_local_copy = values["-SAVE-"]

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
                loading_window = sg.Window(
                    "Processing",
                    [
                        [sg.Text("Creating and uploading savefile share...")],
                        [
                            sg.ProgressBar(
                                100, orientation="h", size=(20, 20), key="-PROG-"
                            )
                        ],
                    ],
                    modal=True,
                )
                loading_event, _ = loading_window.read(timeout=0)

                new_file_path = (
                    f"{file_tag}_{datetime.now().strftime('%Y%m%d_%H%M')}.zip"
                )
                with ZipFile(new_file_path, "w") as myzip:
                    myzip.write(db_path, os.path.basename(db_path))
                    myzip.write(fwl_path, os.path.basename(fwl_path))

                headers = {"User-Agent": "ValheimSaveShareTool/1.0"}
                with open(new_file_path, "rb") as f:
                    response = requests.post(
                        "https://0x0.st",
                        files={"file": (new_file_path, f)},
                        data={"secret": new_file_path, "expires": 72},
                        headers=headers,
                    )
                    loading_window.close()

                    if response.status_code == 200:
                        url = response.text.strip()
                        layout = [
                            [sg.Text("Save file zip created and uploaded!")],
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

                    if not save_local_copy:
                        os.remove(new_file_path)

                window.close()

    window.close()


create_gui()
