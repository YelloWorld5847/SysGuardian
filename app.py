from flask import Flask, request, jsonify, render_template, Response, send_file, session, redirect, url_for
from functools import wraps
import json
import queue
import threading
import time
from io import BytesIO
from PIL import Image
import base64
import uuid

# Identifiants du professeur
ADMIN_USERNAME = "prof"
ADMIN_PASSWORD = "0"  # à changer !

last_screenshots = {}

app = Flask(__name__)
app.secret_key = "45fe4145f6e41s56fes654ef1s351ve8641zf65e1z6"  # clé secrète pour les sessions

# Stockage des clients SSE
sse_clients = []

PC_STATUS = {}

pending_files = {}


commands = {}
alive_pcs = []

# SERVEUR

# def update_pc_dead(timeout):
#     global alive_pcs
#     now = time.time()
    
#     # Filtrer la liste en une seule passe
#     alive_pcs = [
#         pc for pc in alive_pcs 
#         if now - pc["time"] <= timeout
#     ]
    
#     print(f"[DEAD CHECK] PCs en vie : {[pc['pc_id'] for pc in alive_pcs]}")


# def worker():
#     while True:
#         update_pc_dead(30)
#         time.sleep(5)

# t = threading.Thread(target=worker, daemon=True)
# t.start()

# Décorateur pour protéger les routes
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def add_command(command_info, pc_id):
    id = str(uuid.uuid4())
    print(id)
    commands[id] = {"command_info": command_info, "pc_id": pc_id, "timestamp": time.time()}
    print(commands)
    print(f"Command Ajouté dans la liste, liste complète : {commands}")

def get_commands(pc_id):
    command_filre = []
    commands_copy = commands.copy()

    for id, command in commands_copy.items():
        if time.time() - command["timestamp"] > 60:
            del_command(id)
        elif command["pc_id"] == pc_id:
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

@app.route("/api/upload_screen", methods=["POST"])
def upload_screen():
    pc_id = request.form.get("pc_id")
    file = request.files.get("image")
    if not pc_id or not file:
        return jsonify({"status": "error", "message": "pc_id ou image manquant"}), 400

    print(file)
    print(pc_id)

    # on garde uniquement la dernière image en RAM
    last_screenshots[pc_id] = file.read()
    print(f"last_screenshots[:500] : {str(last_screenshots)[:500]}")

    return jsonify({"status": "success"}), 200

@app.route("/api/screen/<pc_id>")
def get_screen(pc_id):
    img_bytes = last_screenshots.get(pc_id)
    if not img_bytes:
        return "Pas d'image disponible", 404
    return send_file(
        BytesIO(img_bytes),
        mimetype="image/jpeg",
        as_attachment=False
    )

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
@login_required
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
@login_required
def shutdown_pc():
    """Éteindre un PC"""
    data = request.json
    pc_name = data.get('pc_name')
    
    print(f"Demande d'extinction de {pc_name}")
    
    add_command({"type": "SHUTDOWN", "command": ""}, pc_name)
    
    return jsonify({
        "status": "success",
        "message": "Message Envoyer"
    }), 200

# Remplacer la fonction upload_file() existante :
@app.route("/api/upload_file", methods=["POST"])
@login_required
def upload_file():
    pc_name = request.form.get('pc_name')
    
    if 'files' not in request.files:
        return jsonify({"status": "error", "message": "Aucun fichier reçu"}), 400
    
    files = request.files.getlist('files')
    uploaded_files = []
    
    if pc_name not in pending_files:
        pending_files[pc_name] = []

    for file in files:
        if file.filename:
            pending_files[pc_name].append({
                "filename": file.filename,
                "data": file.read()  # stocké en RAM
            })
            uploaded_files.append(file.filename)
            print(f"Fichier mis en attente: {file.filename} pour {pc_name}")

    send_sse_update('file_uploaded', {
        'pc_name': pc_name,
        'files': uploaded_files,
        'count': len(uploaded_files)
    })
    
    return jsonify({
        "status": "success",
        "message": f"{len(uploaded_files)} fichier(s) en attente",
        "files": uploaded_files
    }), 200

# Ajouter cette nouvelle route :
@app.route("/api/get_files", methods=["GET"])
def get_files():
    """Le receiver poll cette route pour récupérer ses fichiers en attente"""
    pc_id = request.args.get('pc_id')
    
    files = pending_files.pop(pc_id, [])  # récupère et vide la liste
    
    if not files:
        return jsonify([])
    
    # Retourne les fichiers encodés en base64
    result = []
    for f in files:
        result.append({
            "filename": f["filename"],
            "data": base64.b64encode(f["data"]).decode("utf-8")
        })
    
    print(f"Envoi de {len(result)} fichier(s) à {pc_id}")
    return jsonify(result)

@app.route("/api/stream")
@login_required
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

@app.route("/", methods=["GET"])
@login_required
def index():
    pc_selected = request.args.get('pc_selected', "")
    print(f"pc_selected : {pc_selected}")
    return render_template("index.html", pc_selected=pc_selected)

@app.route("/map")
@login_required
def map():
    return render_template("map.html")

# Nouvelles routes login/logout :
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            error = "Identifiants incorrects"
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True, threaded=True)
