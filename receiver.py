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
import threading
import textwrap
import platform

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
# f = open(resource_path('C:\ProgramData\VAR\id_pc.txt'), 'r')
# pc_id = f.read().strip()
# f.close()
pc_id = platform.node()

CHECK_INTERVAL = 2
COUNTDOWN_SECONDS = 2

# Configuration auto-update
GITHUB_REPO = "YelloWorld5847/SysGuardian"
CURRENT_VERSION = "4.1.4"
CHECK_UPDATE_INTERVAL = 3600
# ========================================


def popup(msg):
    def gui():
        root = tk.Tk()
        root.wm_attributes("-topmost", True)

        # Taille de base de la fenêtre
        width, height = 600, 400
        root.geometry(f"{width}x{height}")

        # 1) Déterminer la taille de police en fonction de la longueur
        n = len(msg)

        # seuils à ajuster selon ton besoin
        if n < 80:
            font_size = 30
            use_scroll = False
        elif n < 250:
            font_size = 20
            use_scroll = False
        else:
            font_size = 14
            use_scroll = True

        if not use_scroll:
            # 2) Label simple, texte centré, wrap sur la largeur de la fenêtre
            l = tk.Label(
                root,
                text=msg,
                padx=40,
                pady=40,
                wraplength=width - 80,  # pour éviter que ça dépasse
                justify="center"
            )
            l.config(font=("Arial", font_size))
            l.pack(expand=True, fill="both")
        else:
            # 3) Beaucoup de texte : Text + Scrollbar
            frame = tk.Frame(root)
            frame.pack(expand=True, fill="both", padx=20, pady=20)

            text = tk.Text(
                frame,
                wrap="word",
                font=("Arial", font_size)
            )
            scroll = tk.Scrollbar(frame, command=text.yview)
            text.configure(yscrollcommand=scroll.set)

            text.pack(side="left", expand=True, fill="both")
            scroll.pack(side="right", fill="y")

            # on peut éventuellement couper manuellement en lignes
            # pour éviter les lignes trop longues :
            wrapped = "\n".join(textwrap.wrap(msg, width=90))
            text.insert("1.0", wrapped)
            text.config(state="disabled")  # lecture seule

        root.mainloop()

    t = threading.Thread(target=gui, daemon=True)
    t.start()

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
                self.log(f"Impossible de verifier les mises a jour (HTTP {response.status_code} : {response.text})", "WARNING")
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
    def __init__(self):
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
            url = f"https://sysguardian.neolysium.eu/api/commands?pc_id={pc_id}"
            r = requests.get(url)
            return r.json()
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

    def send_alive(self):
        try:
            url = f"https://sysguardian.neolysium.eu/api/online?pc_id={pc_id}"
            r = requests.get(url)
            print(f"réponse du serveur : {r.text}")
        except Exception as e:
            self.log(f"Erreur lecture messages : {e}", "ERROR")


    def process_message(self, msg, c_type):
        """Traite un message reçu"""
        self.log(f"Message : {msg}", "INFO")

        if c_type == "SHUTDOWN":
            self.shutdown_pc()
            return True
        elif c_type == "MSG":
            popup(msg)

        return False

    def run(self):
        """Lance l'écoute en continu"""
        self.log("=" * 60, "INFO")
        self.log("SCRIPT D'ECOUTE AUTONOME DEMARRE", "SUCCESS")
        self.log("=" * 60, "INFO")
        self.log(f"Version : {CURRENT_VERSION}", "INFO")
        self.log(f"ID de ce PC : {pc_id}", "INFO")
        self.log(f"Intervalle de verification : {CHECK_INTERVAL}s", "INFO")
        self.log(f"Verification des updates : {CHECK_UPDATE_INTERVAL}s", "INFO")
        self.log(f"Commande d'extinction : SHUTDOWN", "INFO")
        self.log("Appuyez sur Ctrl+C pour arreter", "INFO")
        self.log("=" * 60, "INFO")

        # Vérification initiale des mises à jour
        self.check_for_updates()

        consecutive_errors = 0
        max_errors = 5
        i = 1
        try:
            while True:
                try:
                    if i % 5 == 0:
                        self.check_for_updates()

                    if i % 10 == 0:
                        full_commands = self.get_messages()
                        consecutive_errors = 0
                        print(full_commands)
                        for full_command in full_commands:
                            command_info = full_command["command_info"]
                            c_type = command_info["type"]
                            command = command_info["command"]
                            if self.process_message(command, c_type):
                                return
                    
                    if i % 20 == 0:
                        self.send_alive()

                    time.sleep(1)

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

                finally:
                    i += 1

        except KeyboardInterrupt:
            self.log("", "INFO")
            self.log("Arret demande par l'utilisateur", "WARNING")
            self.log("Le PC ne s'eteindra plus a distance", "INFO")


if __name__ == '__main__':
    listener = AutonomousListener()
    listener.run()

    print("\n[*] Script termine")
