import os
import time
import requests
from flask import Flask, jsonify
from threading import Thread

app = Flask(__name__)

# Configuración de variables de entorno (Deben estar configuradas en Render)
HUBSPOT_TOKEN = os.environ.get("HUBSPOT_TOKEN")
ASANA_TOKEN = os.environ.get("ASANA_TOKEN")
ASANA_PROJECT_ID = os.environ.get("ASANA_PROJECT_ID")

# Almacén temporal en memoria para evitar duplicados en ejecuciones cortas
PROCESSED_CONTACTS = set()

def buscar_y_crear_tareas():
    """Función en segundo plano que consulta HubSpot y crea tareas en Asana."""
    print("Iniciando servicio de monitoreo de HubSpot...")
    
    while True:
        try:
            if not HUBSPOT_TOKEN or not ASANA_TOKEN or not ASANA_PROJECT_ID:
                print("Error: Faltan variables de entorno obligatorias.")
                time.sleep(60)
                continue

            # 1. Consultar los contactos más recientes en HubSpot (ordenados por fecha de creación)
            url_hubspot = "https://api.hubapi.com/crm/v3/objects/contacts/search"
            headers_hubspot = {
                "Authorization": f"Bearer {HUBSPOT_TOKEN}",
                "Content-Type": "application/json"
            }
            
            # Pedimos los campos necesarios y filtramos los creados en los últimos 10 minutos
            query = {
                "filterGroups": [{
                    "filters": [{
                        "propertyName": "createdate",
                        "operator": "GT",
                        "value": str(int((time.time() - 600) * 1000)) # Hace 10 minutos en milisegundos
                    }]
                }],
                "sorts": [{"propertyName": "createdate", "direction": "DESCENDING"}],
                "properties": ["firstname", "lastname", "email", "phone", "municipio_de_residencia_en_yucatan"],
                "limit": 10
            }

            response = requests.post(url_hubspot, headers=headers_hubspot, json=query)
            
            if response.status_code == 200:
                contactos = response.json().get("results", [])
                
                for contacto in contactos:
                    contact_id = contacto.get("id")
                    
                    # Evitar procesar el mismo contacto en ciclos seguidos
                    if contact_id in PROCESSED_CONTACTS:
                        continue
                    
                    props = contacto.get("properties", {})
                    nombre = props.get("firstname", "Sin Nombre")
                    apellido = props.get("lastname", "")
                    correo = props.get("email", "Sin Correo")
                    municipio = props.get("municipio_de_residencia_en_yucatan", "No especificado")
                    
                    print(f"Nuevo contacto detectado: {nombre} {apellido} - {municipio}")

                    # 2. Enviar los datos a Asana para crear la tarea
                    url_asana = "https://app.asana.com/api/1.0/tasks"
                    headers_asana = {
                        "Authorization": f"Bearer {ASANA_TOKEN}",
                        "Content-Type": "application/json"
                    }
                    
                    payload_asana = {
                        "data": {
                            "projects": [ASANA_PROJECT_ID],
                            "name": f"Nuevo Expediente: {nombre} {apellido} ({municipio})",
                            "notes": f"Datos del postulante:\n- Correo: {correo}\n- Municipio: {municipio}\n- Origen: Registro HubSpot"
                        }
                    }
                    
                    res_asana = requests.post(url_asana, headers=headers_asana, json=payload_asana)
                    
                    if res_asana.status_code == 201:
                        print(f"Tarea creada en Asana con éxito para {nombre}.")
                        PROCESSED_CONTACTS.add(contact_id)
                    else:
                        print(f"Error al crear tarea en Asana: {res_asana.text}")
            else:
                print(f"Error al consultar HubSpot: {response.text}")

        except Exception as e:
            print(f"Error en el bucle de sincronización: {str(e)}")

        # Esperar 5 minutos (300 segundos) antes de la siguiente revisión
        time.sleep(300)

# Ruta base para que Render mantenga el servicio activo (Web Service)
@app.route('/')
def home():
    return jsonify({"status": "running", "service": "HubSpot to Asana Poller"}), 200

if __name__ == "__main__":
    # Iniciamos la sincronización en un hilo secundario para no bloquear el servidor web
    updater_thread = Thread(target=buscar_y_crear_tareas, daemon=True)
    updater_thread.start()
    
    # Render usa el puerto asignado en la variable PORT
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
