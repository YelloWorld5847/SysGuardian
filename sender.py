import socket
import sys
import os
import hashlib
import time
import base64
from cryptography.fernet import Fernet

PORT = 137  # Port NetBIOS ouvert par défaut sur Windows
BROADCAST_IP = "255.255.255.255"


def get_secret_key():
    """Récupère la clé depuis la variable d'environnement"""
    key = os.environ.get('REMOTE_KEY')
    if not key:
        print("ERREUR: Variable d'environnement REMOTE_KEY non définie")
        print("Définissez-la avec: set REMOTE_KEY=votre_cle_secrete (Windows)")
        print("ou: export REMOTE_KEY=votre_cle_secrete (Linux)")
        sys.exit(1)
    # Créer une clé Fernet à partir de la clé secrète
    key_hash = hashlib.sha256(key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key_hash))


def encrypt_message(cipher, command):
    """Chiffre la commande avec timestamp"""
    timestamp = str(int(time.time()))
    message = f"{timestamp}|{command}"
    return cipher.encrypt(message.encode())


def broadcast_command(command):
    try:
        cipher = get_secret_key()
        encrypted = encrypt_message(cipher, command)

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.sendto(encrypted, (BROADCAST_IP, PORT))
            print(f"✓ Commande '{command}' envoyée de manière sécurisée")
    except Exception as e:
        print(f"ERREUR: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python sender.py <COMMAND>")
        print("\nCommandes disponibles:")
        print("  PING         - Test de connexion")
        print("  SHUTDOWN     - Éteindre le PC")
        print("  OPEN_EXPLORER - Ouvrir l'explorateur")
        print("\nConfiguration requise:")
        print("  Windows: set REMOTE_KEY=votre_cle_secrete")
        print("  Linux:   export REMOTE_KEY=votre_cle_secrete")
        sys.exit(1)

    cmd = sys.argv[1].upper()
    broadcast_command(cmd)