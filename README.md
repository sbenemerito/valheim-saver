# Valheim Save Sharing Tool

A simple GUI tool that helps Valheim players share their world saves with other players, enabling them to host the world when the original host is unavailable.

## Quick Start for Windows Users

Simply download `ValheimSaveShare.exe` from the `dist` folder. No installation or Python required!

## Purpose

This tool is designed to make it easy for Valheim players to share their world saves with friends. 

I mainly wrote this on a whim because the steps to share Valheim savefiles with friends was getting quite repetetive. Its primary purpose is to allow multiple players to host the same world, ensuring gameplay can continue even when the original host is offline.

## Features

- Simple graphical interface
- Packages both required save files (`.db` and `.fwl`) into a single ZIP file
- Automatically uploads the ZIP to 0x0.st file hosting service
- Generates a shareable URL that's valid for 72 hours
- Option to retain or delete the local ZIP file after upload
- File size check to ensure compatibility with the hosting service (512MB limit)
- Optional custom file tagging for better organization

## How to Use

1. Launch the tool
2. Select your Valheim world's `.db` file
3. Select the corresponding `.fwl` file
4. (Optional) Add a custom tag to identify the save
5. Choose whether to keep a local copy of the ZIP file
6. Click "Create savefile zip"
7. Once complete, copy the generated URL and share it with your friends

## Note

- Files are uploaded to 0x0.st and are automatically deleted after 72 hours
- Maximum total file size is 512MB
- This is not primarily intended as a backup solution - please maintain proper backups separately

## Requirements

- Python 3
- FreeSimpleGUI
- requests

## Disclaimer

This is an unofficial tool and is not affiliated with Iron Gate AB or Valheim.