import FreeSimpleGUI as sg
import os
import zipfile
import requests

def create_backup_gui():
    layout = [
        [sg.Text("Valheim Save Backup Tool")],
        [sg.Text(".db file:"), sg.Input(), sg.FileBrowse(file_types=(("DB File", "*.db"),))],
        [sg.Text(".fwl file:"), sg.Input(), sg.FileBrowse(file_types=(("FWL File", "*.fwl"),))],
        [sg.Button("Create backup"), sg.Button("Exit")]
    ]
    
    window = sg.Window("Valheim Backup", layout)
    
    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED or event == "Exit":
            break
        if event == "Create backup":
            db_path = values[0]
            fwl_path = values[1]
            
            if db_path and fwl_path:
                # backup logic here
                print(db_path)
                print(fwl_path)
                pass
    
    window.close()

create_backup_gui()
