import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

HUBSPOT_ACCESS_TOKEN = "CiRuYTEtODdmYi04Mzc1LTQ5YjEtYjkzOC00MTYxODJiNGMQ9-TSGBjV1Z0tKhKABeaRghR01WYQR0wHRQPrWyeFYK9gz5F7SgNuYTE"
ASANA_ACCESS_TOKEN = "2/1202835049817929/1216251919106019:2661152bd495497e8e06631e2c06957c"
ASANA_PROJECT_ID = "1216251895168402"

@app.route('/webhook-hubspot', methods=['POST'])
def hubspot_webhook():
    data = request.json
    for event in data:
        if event.get("subscriptionType") in ["contact.creation", "contact.propertyChange"]:
            contact_id = event.get("objectId")
            
            hs_url = f"https://api.hubapi.com/crm/v3/objects/contacts/{contact_id}"
            headers_hs = {
                "Authorization": f"Bearer {HUBSPOT_ACCESS_TOKEN}",
                "Content-Type": "application/json"
            }
            params = {
                "properties": "firstname,lastname,email,municipio_de_residencia_en_yucatan,cual_es_el_motivo_principal_de_su_solicitud"
            }
            
            hs_response = requests.get(hs_url, headers=headers_hs, params=params)
            if hs_response.status_code == 200:
                properties = hs_response.json().get("properties", {})
                
                nombre = properties.get("firstname", "Sin Nombre")
                apellido = properties.get("lastname", "Sin Apellido")
                correo = properties.get("email", "Sin Correo")
                municipio = properties.get("municipio_de_residencia_en_yucatan", "No especificado")
                motivo = properties.get("cual_es_el_motivo_principal_de_su_solicitud", "No especificado")
                
                crear_tarea_asana(nombre, apellido, correo, municipio, motivo)
                
    return jsonify({"status": "success"}), 200

def crear_tarea_asana(nombre, apellido, correo, municipio, motivo):
    asana_url = "https://app.asana.com/api/1.0/tasks"
    headers_asana = {
        "Authorization": f"Bearer {ASANA_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    nota_detalle = f"""⚖️ NUEVO EXPEDIENTE REGISTRADO:
-------------------------------------------
• Solicitante: {nombre} {apellido}
• Correo de Contacto: {correo}
• Municipio: {municipio}
• Motivo de Solicitud: {motivo}
-------------------------------------------
[Estatus]: Pendiente de revisión inicial jurídica."""

    payload = {
        "data": {
            "name": f"Caso: {nombre} {apellido} ({municipio})",
            "notes": nota_detalle,
            "projects": [ASANA_PROJECT_ID]
        }
    }
    
    requests.post(asana_url, headers=headers_asana, json=payload)

if __name__ == '__main__':
    app.run(port=5000, debug=True)
