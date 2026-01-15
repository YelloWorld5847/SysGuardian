import requests
import time
import json
import os
import platform
import sys
from datetime import datetime
import random
import string
import subprocess
import tempfile
from pathlib import Path
from tkinter import *
import tkinter as tk
import os

# Forcer l'encodage UTF-8 pour la console Windows
if platform.system() == "Windows":
    if sys.stdout is not None:
        sys.stdout.reconfigure(encoding='utf-8')
    if sys.stderr is not None:
        sys.stderr.reconfigure(encoding='utf-8')

import sys

def resource_path(relative_path):
    """Retourne le chemin correct pour les fichiers bundlés dans PyInstaller"""
    try:
        # PyInstaller extrait les fichiers dans un dossier temporaire
        base_path = sys._MEIPASS
    except AttributeError:
        # Si on exécute le script .py directement
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ========================================
# CONFIGURATION
# ========================================
f = open(resource_path('key.txt'), 'r')
GITHUB_TOKEN = f.read().strip()
f.close()
# print(contenu)
# GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GIST_ID = "6ad1f414e4e4b4af15301e0a96c454ee"
SENDER_ID = ''.join(random.choice(string.ascii_letters) for x in range(10))
CHECK_INTERVAL = 3
COUNTDOWN_SECONDS = 2

# Configuration auto-update
GITHUB_REPO = "YelloWorld5847/socket_com"
CURRENT_VERSION = "3.0.3"
CHECK_UPDATE_INTERVAL = 3600
# ========================================


class AutoUpdater:
    def __init__(self, repo, current_version):
        self.repo = repo
        self.current_version = current_version
        self.api_url = f"https://api.github.com/repos/{repo}/releases/latest"

    def log(self, message, level="INFO"):
        """Affiche un message avec timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        symbol = {
            "INFO": "[i]",
            "SUCCESS": "[+]",
            "WARNING": "[!]",
            "ERROR": "[x]",
            "UPDATE": "[^]"
        }.get(level, "[*]")
        try:
            print(f"[{timestamp}] {symbol} {message}")
        except UnicodeEncodeError:
            print(f"[{timestamp}] [{level}] {message.encode('ascii', 'ignore').decode('ascii')}")

    def compare_versions(self, v1, v2):
        """Compare deux versions (format x.y.z)"""
        try:
            v1_parts = [int(x) for x in v1.lstrip('v').split('.')]
            v2_parts = [int(x) for x in v2.lstrip('v').split('.')]

            for i in range(max(len(v1_parts), len(v2_parts))):
                part1 = v1_parts[i] if i < len(v1_parts) else 0
                part2 = v2_parts[i] if i < len(v2_parts) else 0

                if part1 < part2:
                    return -1
                elif part1 > part2:
                    return 1
            return 0
        except:
            return 0

    def check_for_update(self):
        """Vérifie s'il y a une nouvelle version disponible"""
        try:
            response = requests.get(self.api_url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                latest_version = data['tag_name'].lstrip('v')

                if self.compare_versions(self.current_version, latest_version) < 0:
                    self.log(
                        f"Nouvelle version disponible : {latest_version} (actuelle : {self.current_version})",
                        "UPDATE"
                    )
                    return True, data
                else:
                    self.log(f"Version a jour ({self.current_version})", "SUCCESS")
                    return False, None
            else:
                self.log(f"Impossible de verifier les mises a jour (HTTP {response.status_code})", "WARNING")
                return False, None

        except Exception as e:
            self.log(f"Erreur lors de la verification des mises a jour : {e}", "ERROR")
            return False, None

    def download_update(self, release_data):
        """Télécharge la nouvelle version"""
        try:
            exe_asset = None
            for asset in release_data['assets']:
                if asset['name'].endswith('.exe'):
                    exe_asset = asset
                    break

            if not exe_asset:
                self.log("Aucun fichier .exe trouve dans la release", "ERROR")
                return None

            download_url = exe_asset['browser_download_url']
            self.log(f"Telechargement de {exe_asset['name']}...", "UPDATE")

            response = requests.get(download_url, stream=True, timeout=60)

            if response.status_code == 200:
                temp_dir = tempfile.gettempdir()
                temp_file = os.path.join(temp_dir, exe_asset['name'])

                with open(temp_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                self.log(f"Telechargement termine : {temp_file}", "SUCCESS")
                return temp_file
            else:
                self.log(f"Erreur de telechargement (HTTP {response.status_code})", "ERROR")
                return None

        except Exception as e:
            self.log(f"Erreur lors du telechargement : {e}", "ERROR")
            return None

    def apply_update(self, new_exe_path):
        """Applique la mise à jour"""
        try:
            if getattr(sys, 'frozen', False):
                # chemin actuel de l'exe lancé
                current_exe = os.path.abspath(sys.argv[0])
            else:
                self.log("Mode dev, pas d'update", "WARNING")
                return False

            # OPTIONNEL mais pratique : forcer un chemin "officiel"
            # par exemple C:\Listener\listener.exe
            official_dir = r"C:\Listener"
            official_exe = os.path.join(official_dir, os.path.basename(current_exe))

            if not os.path.exists(official_dir):
                os.makedirs(official_dir, exist_ok=True)

            # Si l'exe actuel n'est pas déjà dans le dossier officiel,
            # on copie pour que toutes les futures MAJ se fassent là
            if os.path.abspath(current_exe) != os.path.abspath(official_exe):
                self.log(f"Deplacement vers {official_exe}", "UPDATE")
                try:
                    # copier l'exe actuel dans le dossier officiel
                    import shutil
                    shutil.copy2(current_exe, official_exe)
                    current_exe = official_exe
                except Exception as e:
                    self.log(f"Erreur de deplacement: {e}", "ERROR")
                    return False

            if not current_exe.endswith('.exe'):
                self.log("Pas un .exe, update ignoree", "WARNING")
                return False

            self.log("Application de la mise a jour...", "UPDATE")

            current_dir = os.path.dirname(current_exe)
            backup_exe = os.path.join(current_dir, "backup.exe")

            batch_script = os.path.join(tempfile.gettempdir(), "update.bat")

            with open(batch_script, 'w') as f:
                f.write(f'''@echo off
timeout /t 3 /nobreak > nul

if exist "{current_exe}" (
    copy /y "{current_exe}" "{backup_exe}"
)

if exist "{new_exe_path}" (
    copy /y "{new_exe_path}" "{current_exe}"
    del /f /q "{new_exe_path}"
)

start "" "{current_exe}"

(goto) 2>nul & del "%~f0"
''')

            self.log("Redemarrage pour appliquer la mise a jour...", "UPDATE")
            subprocess.Popen(['cmd', '/c', batch_script], creationflags=subprocess.CREATE_NO_WINDOW)
            time.sleep(1)
            sys.exit(0)

        except Exception as e:
            self.log(f"Erreur lors de l'application de la mise a jour : {e}", "ERROR")
            return False



class AutonomousListener:
    def __init__(self, token, gist_id, sender_id):
        self.token = token
        self.gist_id = gist_id
        self.sender_id = sender_id
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.api_url = "https://api.github.com/gists"
        self.last_timestamp = time.time() - 10
        self.last_update_check = 0
        self.updater = AutoUpdater(GITHUB_REPO, CURRENT_VERSION)

    def log(self, message, level="INFO"):
        """Affiche un message avec timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        symbol = {
            "INFO": "[i]",
            "SUCCESS": "[+]",
            "WARNING": "[!]",
            "ERROR": "[x]",
            "SHUTDOWN": "[#]",
            "UPDATE": "[^]"
        }.get(level, "[*]")
        try:
            print(f"[{timestamp}] {symbol} {message}")
        except UnicodeEncodeError:
            print(f"[{timestamp}] [{level}] {message.encode('ascii', 'ignore').decode('ascii')}")

    def check_for_updates(self):
        """Vérifie et applique les mises à jour si nécessaire"""
        current_time = time.time()

        if current_time - self.last_update_check < CHECK_UPDATE_INTERVAL:
            return

        self.last_update_check = current_time
        self.log("Verification des mises a jour...", "UPDATE")

        has_update, release_data = self.updater.check_for_update()

        if has_update:
            new_exe = self.updater.download_update(release_data)
            if new_exe:
                self.updater.apply_update(new_exe)

    def get_messages(self):
        """Récupère tous les messages du Gist"""
        try:
            response = requests.get(
                f"{self.api_url}/{self.gist_id}",
                headers=self.headers,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                content = data['files']['messages.json']['content']
                return json.loads(content).get('messages', [])

            return []

        except Exception as e:
            self.log(f"Erreur lecture messages : {e}", "ERROR")
            return []

    def shutdown_pc(self):
        """Éteint le PC selon le système d'exploitation"""
        system = platform.system()

        self.log("COMMANDE SHUTDOWN RECUE !", "SHUTDOWN")
        self.log(f"Extinction dans {COUNTDOWN_SECONDS} secondes...", "WARNING")

        for i in range(COUNTDOWN_SECONDS, 0, -1):
            self.log(f"Extinction dans {i} secondes...", "WARNING")
            time.sleep(1)

        self.log("Extinction du PC maintenant...", "SHUTDOWN")

        try:
            if system == "Windows":
                os.system("shutdown /s /t 0")
            elif system == "Linux" or system == "Darwin":
                os.system("sudo shutdown -h now")
            else:
                self.log(f"Systeme non supporte : {system}", "ERROR")
        except Exception as e:
            self.log(f"Erreur lors de l'extinction : {e}", "ERROR")

    def process_message(self, msg):
        """Traite un message reçu"""
        content = msg['content'].strip()
        sender = msg['sender']

        self.log(f"Message de [{sender}] : {content}", "INFO")

        if content.upper() == "SHUTDOWN":
            self.shutdown_pc()
            return True
        elif "MSG " in content.upper():
            msg = content[4:]
            root = Tk()
            root.wm_attributes("-topmost", True)
            l = Label(root, text=msg, padx=100, pady=100)
            l.config(font=("Arial", 30))
            l.pack()
            tk.mainloop()

        return False

    def run(self):
        """Lance l'écoute en continu"""
        self.log("=" * 60, "INFO")
        self.log("SCRIPT D'ECOUTE AUTONOME DEMARRE", "SUCCESS")
        self.log("=" * 60, "INFO")
        self.log(f"Version : {CURRENT_VERSION}", "INFO")
        self.log(f"ID de ce PC : {self.sender_id}", "INFO")
        self.log(f"Gist ID : {self.gist_id}", "INFO")
        self.log(f"Intervalle de verification : {CHECK_INTERVAL}s", "INFO")
        self.log(f"Verification des updates : {CHECK_UPDATE_INTERVAL}s", "INFO")
        self.log(f"Commande d'extinction : SHUTDOWN", "INFO")
        self.log("Appuyez sur Ctrl+C pour arreter", "INFO")
        self.log("=" * 60, "INFO")

        # Vérification initiale des mises à jour
        self.check_for_updates()

        consecutive_errors = 0
        max_errors = 5

        try:
            while True:
                try:
                    self.check_for_updates()

                    messages = self.get_messages()
                    consecutive_errors = 0

                    for msg in messages:
                        if msg['timestamp'] <= self.last_timestamp:
                            continue

                        if msg['sender'] == self.sender_id:
                            continue

                        if self.process_message(msg):
                            return

                        self.last_timestamp = msg['timestamp']

                    time.sleep(CHECK_INTERVAL)

                except requests.exceptions.RequestException as e:
                    consecutive_errors += 1
                    self.log(f"Erreur de connexion ({consecutive_errors}/{max_errors})", "ERROR")

                    if consecutive_errors >= max_errors:
                        self.log("Trop d'erreurs consecutives, arret du script", "ERROR")
                        break

                    time.sleep(CHECK_INTERVAL * 2)

                except Exception as e:
                    self.log(f"Erreur inattendue : {e}", "ERROR")
                    time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            self.log("", "INFO")
            self.log("Arret demande par l'utilisateur", "WARNING")
            self.log("Le PC ne s'eteindra plus a distance", "INFO")


if __name__ == '__main__':
    if not GITHUB_TOKEN or GITHUB_TOKEN == "VOTRE_TOKEN_ICI":
        print("[x] ERREUR : GITHUB_TOKEN non configure !")
        print("Modifiez le script et ajoutez votre token GitHub")
        exit(1)

    if not GIST_ID:
        print("[x] ERREUR : GIST_ID non configure !")
        print("Creez un Gist et ajoutez l'ID dans le script")
        exit(1)

    listener = AutonomousListener(GITHUB_TOKEN, GIST_ID, SENDER_ID)
    listener.run()

    print("\n[*] Script termine")
