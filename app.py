import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def receive_webhook():
    try:
        # 1. Obtener los tokens de Asana guardados en Render
        token_asana = os.environ.get("ASANA_TOKEN")
        project_id_asana = os.environ.get("ASANA_PROJECT_ID")

        # 2. Recibir los datos enviados por el formulario de HubSpot
        data = request.json or request.form.to_dict()
        print(">>> Datos recibidos de HubSpot:", data, flush=True)

        # Extraer campos enviados (ajusta los nombres si tus campos en HubSpot se llaman distinto)
        nombre = data.get("firstname", data.get("nombre", "Sin Nombre"))
        apellido = data.get("lastname", data.get("apellidos", ""))
        correo = data.get("email", data.get("correo", "Sin Correo"))
        municipio = data.get("municipio_de_residencia_en_yucatan", data.get("municipio", "No especificado"))

        # 3. Crear la tarea en Asana
        url_asana = "https://app.asana.com/api/1.0/tasks"
        headers_asana = {
            "Authorization": f"Bearer {token_asana}",
            "Content-Type": "application/json"
        }
        
        payload_asana = {
            "data": {
                "projects": [project_id_asana],
                "name": f"Nuevo Expediente: {nombre} {apellido} ({municipio})",
                "notes": f"Datos del registro:\n- Correo: {correo}\n- Municipio: {municipio}"
            }
        }
        
        res_asana = requests.post(url_asana, headers=headers_asana, json=payload_asana)
        
        if res_asana.status_code == 201:
            print(f">>> Tarea creada con éxito en Asana para {nombre} <<<", flush=True)
            return jsonify({"status": "success", "message": "Task created"}), 201
        else:
            print(f">>> Error al crear en Asana: {res_asana.text} <<<", flush=True)
            return jsonify({"status": "error", "message": res_asana.text}), res_asana.status_code

    except Exception as e:
        print(f">>> Error crítico en el Webhook: {str(e)} <<<", flush=True)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/')
def home():
    return jsonify({"status": "active"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
