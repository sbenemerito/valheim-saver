import FreeSimpleGUI as sg
import requests
from datetime import datetime
from os.path import basename
from zipfile import ZipFile


def create_backup_gui():
    layout = [
        [sg.Text("Valheim Save Backup Tool")],
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
        [sg.Button("Create backup"), sg.Button("Exit")],
    ]

    window = sg.Window("Valheim Backup", layout)

    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED or event == "Exit":
            break
        if event == "Create backup":
            db_path = values[0]
            fwl_path = values[1]
            file_tag = values[2] or "backup"

            if db_path and fwl_path:
                new_file_path = (
                    f"{file_tag}_{datetime.now().strftime('%Y%m%d_%H%M')}.zip"
                )
                with ZipFile(new_file_path, "w") as myzip:
                    myzip.write(db_path, basename(db_path))
                    myzip.write(fwl_path, basename(fwl_path))

                headers = {"User-Agent": "ValheimBackupTool/1.0"}
                with open(new_file_path, "rb") as f:
                    response = requests.post(
                        "https://0x0.st", files={"file": f}, headers=headers
                    )
                    if response.status_code == 200:
                        sg.popup(f"Backup created and uploaded!\nURL: {response.text}")
                    else:
                        sg.popup(
                            f"Backup created but upload failed.\nStatus code: {response.status_code}"
                        )

    window.close()


create_backup_gui()
