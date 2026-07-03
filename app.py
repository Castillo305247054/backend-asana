import os
import time
import requests
from flask import Flask, jsonify
from threading import Thread

app = Flask(__name__)

# Almacén en memoria para no duplicar tareas
PROCESSED_CONTACTS = set()

def buscar_y_crear_tareas():
    time.sleep(5)
    print(">>> SERVICIO DE MONITOREO TOTAL ACTIVADO <<<", flush=True)
    
    while True:
        try:
            token_hubspot = os.environ.get("HUBSPOT_TOKEN")
            token_asana = os.environ.get("ASANA_TOKEN")
            project_id_asana = os.environ.get("ASANA_PROJECT_ID")

            if not token_hubspot or not token_asana or not project_id_asana:
                print(">>> Error: Faltan variables de entorno en Render. <<<", flush=True)
                time.sleep(60)
                continue

            url_hubspot = "https://api.hubapi.com/crm/v3/objects/contacts/search"
            headers_hubspot = {
                "Authorization": f"Bearer {token_hubspot}",
                "Content-Type": "application/json"
            }
            
            # Trae los últimos 5 contactos creados en la historia del formulario, ordenados del más nuevo al más viejo
            query = {
                "sorts": [{"propertyName": "createdate", "direction": "DESCENDING"}],
                "properties": ["firstname", "lastname", "email", "municipio_de_residencia_en_yucatan"],
                "limit": 5
            }

            response = requests.post(url_hubspot, headers=headers_hubspot, json=query)
            
            if response.status_code == 200:
                contactos = response.json().get("results", [])
                for contacto in contactos:
                    contact_id = contacto.get("id")
                    
                    # Si ya lo procesó antes, lo ignora
                    if contact_id in PROCESSED_CONTACTS:
                        continue
                    
                    props = contacto.get("properties", {})
                    nombre = props.get("firstname", "Sin Nombre")
                    apellido = props.get("lastname", "")
                    correo = props.get("email", "Sin Correo")
                    municipio = props.get("municipio_de_residencia_en_yucatan", "No especificado")
                    
                    print(f">>> Contacto encontrado: {nombre} {apellido} <<<", flush=True)

                    # Crear tarea en Asana
                    url_asana = "https://app.asana.com/api/1.0/tasks"
                    headers_asana = {
                        "Authorization": f"Bearer {token_asana}",
                        "Content-Type": "application/json"
                    }
                    
                    payload_asana = {
                        "data": {
                            "projects": [project_id_asana],
                            "name": f"Nuevo Expediente: {nombre} {apellido} ({municipio})",
                            "notes": f"Datos:\n- Correo: {correo}\n- Municipio: {municipio}"
                        }
                    }
                    
                    res_asana = requests.post(url_asana, headers=headers_asana, json=payload_asana)
                    if res_asana.status_code == 201:
                        print(f">>> Tarea creada en Asana exitosamente para {nombre}. <<<", flush=True)
                        PROCESSED_CONTACTS.add(contact_id)
                    else:
                        print(f">>> Error Asana: {res_asana.text} <<<", flush=True)
            else:
                print(f">>> Error HubSpot API: {response.text} <<<", flush=True)

        except Exception as e:
            print(f">>> Error crítico en bucle: {str(e)} <<<", flush=True)

        # Revisa cada 3 minutos
        time.sleep(180)

monitor_thread = Thread(target=buscar_y_crear_tareas, daemon=True)
monitor_thread.start()

@app.route('/')
def home():
    return jsonify({"status": "active"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
