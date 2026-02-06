from flask import Flask, request, jsonify, render_template, Response
import json
import queue
import threading
import time

app = Flask(__name__)

# Stockage des clients SSE
sse_clients = []

PC_STATUS = {
    
}

import uuid

commands = {}
alive_pcs = []

# SERVEUR

def update_pc_dead(timeout):
    global alive_pcs
    print("UDPATE EN COURS")
    copy_alive_pcs = alive_pcs.copy()
    for i, alive_pc in enumerate(copy_alive_pcs):
        now = time.time()
        time_alive_pc = alive_pc["time"]
        time_end = now - time_alive_pc
        if time_end > timeout:
            a = alive_pc["pc_id"]
            print(f"SUPPRESSION DE {a}")
            alive_pcs.pop(i)
    print(f"[DEAD] LISTE DES PC EN VIE : {alive_pcs}")


def worker():
    while True:
        update_pc_dead(30)
        time.sleep(5)

t = threading.Thread(target=worker, daemon=True)
t.start()


def add_command(command_info, pc_id):
    id = str(uuid.uuid4())
    print(id)
    commands[id] = {"command_info": command_info, "pc_id": pc_id}
    print(commands)
    print(f"Command Ajouté dans la liste, liste complète : {commands}")

def get_commands(pc_id):
    command_filre = []

    for id, command in commands.items():
        if command["pc_id"] == pc_id:
            print()
            command_filre.append({"command_id": id, "command_info" : command["command_info"]})

    return command_filre

def send_sse_update(event_type, data):
    """Envoie une mise à jour à tous les clients SSE"""
    for client_queue in sse_clients[:]:
        try:
            client_queue.put({
                'event': event_type,
                'data': data
            })
        except:
            sse_clients.remove(client_queue)

def del_command(command_id):
    del commands[command_id]
    print("Command supprimé !")

# ===== ROUTES POUR RECUPERER LES COMMANDES =====
@app.route("/api/commands", methods=["GET"])
def get_text():
    pc_id = request.args.get('pc_id')
    commands_filtred = get_commands(pc_id)
    if commands_filtred:
        for command_filtred in commands_filtred:
            del_command(command_filtred["command_id"])
    return jsonify(commands_filtred)


@app.route("/api/pc_online")
def get_value():
    print(f"alive_pcs : {alive_pcs}")
    return jsonify(alive_pcs)

# ===== ROUTES POUR RECUPERER LES PC ALUME =====
@app.route("/api/online", methods=["GET"])
def update_pc_alive():
    global alive_pcs

    pc_id = request.args.get('pc_id')
    
    for i, alive_pc in enumerate(alive_pcs):
        if alive_pc["pc_id"] == pc_id:
            alive_pcs[i]["time"] = int(time.time())
            break
    else:
        alive_pcs.append({
            "pc_id" : pc_id,
            "time": int(time.time())
        })
    print(f"LISTE DES PC EN VIE : {alive_pcs}")
    return "OK"

# ===== ROUTES POUR RECEVOIR LES ACTIONS DU FRONTEND =====

@app.route("/api/send_message", methods=["POST"])
def send_message():
    """Recevoir un message depuis le frontend"""
    data = request.json
    
    pc_name = data.get('pc_name')
    message = data.get('message')
    
    print(f"Message reçu pour {pc_name}: {message}")

    add_command({"type": "MSG", "command": message}, pc_name)
    
    # Notifier tous les clients que le message a été envoyé
    send_sse_update('message_sent', {
        'pc_name': pc_name,
        'message': message,
        'status': 'success'
    })
    
    return jsonify({
        "status": "success",
        "message": f"Message envoyé à {pc_name}"
    }), 200


@app.route("/api/shutdown_pc", methods=["POST"])
def shutdown_pc():
    """Éteindre un PC"""
    data = request.json
    pc_name = data.get('pc_name')
    
    print(f"Demande d'extinction de {pc_name}")
    
    add_command({"type": "SHUTDOWN", "command": ""}, pc_name)
    
    return jsonify({
        "status": "error",
        "message": "PC introuvable"
    }), 404

@app.route("/api/upload_file", methods=["POST"])
def upload_file():
    """Recevoir des fichiers depuis le frontend"""
    pc_name = request.form.get('pc_name')
    
    if 'files' not in request.files:
        return jsonify({
            "status": "error",
            "message": "Aucun fichier reçu"
        }), 400
    
    files = request.files.getlist('files')
    uploaded_files = []
    
    for file in files:
        if file.filename:
            # Sauvegarder le fichier
            filename = file.filename
            # file.save(f'uploads/{filename}')  # Décommenter pour sauvegarder
            
            uploaded_files.append(filename)
            print(f"Fichier reçu: {filename} pour {pc_name}")
    
    # TODO: Envoyer les fichiers au PC cible
    
    # Notifier les clients
    send_sse_update('file_uploaded', {
        'pc_name': pc_name,
        'files': uploaded_files,
        'count': len(uploaded_files)
    })
    
    return jsonify({
        "status": "success",
        "message": f"{len(uploaded_files)} fichier(s) téléchargé(s)",
        "files": uploaded_files
    }), 200

@app.route("/api/stream")
def stream():
    """Endpoint SSE pour les mises à jour en temps réel"""
    client_queue = queue.Queue()
    sse_clients.append(client_queue)
    
    def generate():
        try:
            # Envoyer l'état initial
            yield f"data: {json.dumps({'event': 'init', 'pc_status': PC_STATUS})}\n\n"
            
            while True:
                try:
                    message = client_queue.get(timeout=30)
                    yield f"event: {message['event']}\ndata: {json.dumps(message['data'])}\n\n"
                except queue.Empty:
                    yield f": heartbeat\n\n"
        except GeneratorExit:
            sse_clients.remove(client_queue)
    
    return Response(generate(), mimetype='text/event-stream')

@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True, threaded=True)
