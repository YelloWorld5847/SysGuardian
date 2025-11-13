import socket
import subprocess
import sys
import os
import hashlib
import time
import requests
import tempfile
import shutil
from cryptography.fernet import Fernet

HOST = "0.0.0.0"
PORT = 137  # Port NetBIOS
VERSION = "1.0.0"
GITHUB_REPO = "YelloWorld5847/socket_com"
MAX_TIME_DIFF = 30  # Accepte les messages de max 30 secondes


def get_secret_key():
    # cherche dans plusieurs emplacements possibles
    key = os.environ.get('REMOTE_KEY') or os.environ.get('RK') or os.environ.get('SYSTEM_REMOTE')
    if not key:
        # tente de lire depuis un fichier caché (optionnel)
        config_paths = [
            os.path.join(os.path.expanduser('~'), '.remote_config'),
            'C:\\Windows\\System32\\config\\remote.key' if sys.platform.startswith('win') else '/etc/.remote_key'
        ]
        for path in config_paths:
            if os.path.exists(path):
                try:
                    with open(path, 'r') as f:
                        key = f.read().strip()
                        break
                except:
                    pass

    if not key:
        print("ERREUR: Clé de chiffrement non trouvée")
        print("Configurez REMOTE_KEY dans les variables d'environnement")
        sys.exit(1)

    key_hash = hashlib.sha256(key.encode()).digest()
    return Fernet(hashlib.urlsafe_b64encode(key_hash))


def decrypt_message(cipher, encrypted_data):
    try:
        decrypted = cipher.decrypt(encrypted_data).decode()
        timestamp, command = decrypted.split('|', 1)

        # vérifier que le message n'est pas trop vieux (protection contre replay attacks)
        msg_time = int(timestamp)
        current_time = int(time.time())
        if abs(current_time - msg_time) > MAX_TIME_DIFF:
            return None

        return command
    except Exception:
        return None


def check_for_updates():
    """vérifie si une nouvelle version est disponible sur GitHub"""
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            latest = response.json()
            latest_version = latest['tag_name'].lstrip('v')

            if latest_version > VERSION:
                print(f"🔄 Nouvelle version disponible: {latest_version} (actuelle: {VERSION})")
                return latest
        return None
    except Exception as e:
        print(f"⚠ Impossible de vérifier les mises à jour: {e}")
        return None


def download_and_update(release_info):
    try:
        # cherche le fichier .exe dans les assets
        exe_asset = None
        for asset in release_info['assets']:
            if asset['name'].endswith('.exe'):
                exe_asset = asset
                break

        if not exe_asset:
            print("⚠ Aucun fichier .exe trouvé dans la release")
            return False

        print(f"⬇ Téléchargement de {exe_asset['name']}...")
        response = requests.get(exe_asset['browser_download_url'], stream=True)

        # télécharge dans un fichier temporaire
        with tempfile.NamedTemporaryFile(delete=False, suffix='.exe') as tmp_file:
            for chunk in response.iter_content(chunk_size=8192):
                tmp_file.write(chunk)
            tmp_path = tmp_file.name

        # remplace l'ancien fichier
        current_exe = sys.executable if getattr(sys, 'frozen', False) else __file__
        backup_path = current_exe + '.backup'

        # sauvegarde l'ancien
        if os.path.exists(current_exe):
            shutil.copy2(current_exe, backup_path)

        # installe le nouveau
        shutil.move(tmp_path, current_exe)
        print("✓ Mise à jour installée avec succès!")
        print("⚠ Redémarrez le programme pour utiliser la nouvelle version")
        return True
    except Exception as e:
        print(f"❌ Erreur lors de la mise à jour: {e}")
        return False


def execute_command(data):
    print(f"📥 Commande: {data}")

    if data == "PING":
        print("   → PONG")
    elif data == "OPEN_EXPLORER":
        if sys.platform.startswith("win"):
            subprocess.Popen(["explorer"])
        else:
            subprocess.Popen(["xdg-open", "."])
        print("   → Explorateur ouvert")
    elif data == "SHUTDOWN":
        print("   → Extinction imminente...")
        if sys.platform.startswith("win"):
            subprocess.Popen(["shutdown", "/s", "/t", "5"])
        else:
            subprocess.Popen(["sudo", "shutdown", "-h", "+1"])
    elif data == "UPDATE":
        release = check_for_updates()
        if release:
            download_and_update(release)
    else:
        print(f"   → Commande inconnue: {data}")


def server_loop():
    cipher = get_secret_key()

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind((HOST, PORT))
        print(f"Receiver v{VERSION} démarré sur port {PORT}")
        print("En attente de commandes sécurisées...")

        # vérifier les mises à jour au démarrage
        release = check_for_updates()
        if release:
            print(f"💡 Pour mettre à jour, envoyez la commande UPDATE")

        while True:
            try:
                data, addr = s.recvfrom(1024)
                command = decrypt_message(cipher, data)

                if command:
                    print(f"\n[{addr[0]}] ", end="")
                    execute_command(command)
                else:
                    print(f"⚠ Message invalide ou expiré de {addr[0]}")

            except Exception as e:
                print(f"❌ Erreur: {e}")


if __name__ == "__main__":
    try:
        server_loop()
    except KeyboardInterrupt:
        print("\n👋 Arrêt demandé par l'utilisateur.")