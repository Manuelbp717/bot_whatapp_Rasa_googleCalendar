# actions.py
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
import requests
from rasa_sdk.events import SlotSet
import re
from google.oauth2.service_account import Credentials

# Ruta al archivo de credenciales
SERVICE_ACCOUNT_FILE = "aqueous-cargo-470315-d0-871d1061f87f.json"
SCOPES = ["https://www.googleapis.com/auth/calendar"]
CALENDAR_ID = 'a2b0f49e11efd1722756ec8dc22382f0e8a50bf656c3c784183733d5beb4dbf6@group.calendar.google.com'

credentials = Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
service = build('calendar', 'v3', credentials=credentials)

# TOKEN y PHONE_NUMBER_ID de la API de Meta
META_TOKEN = "TU_TOKEN_DE_META"
PHONE_NUMBER_ID = "TU_PHONE_NUMBER_ID"
ADMIN_NUMBER = "5219992626201"  # Formato E.164

#Checa las clases en google calendar
class ActionChecarClases(Action):
    def name(self):
        return "action_checar_clases"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: dict):

        # Autenticación con Google Calendar usando credenciales globales
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        service = build("calendar", "v3", credentials=creds)

        now = datetime.utcnow().isoformat() + 'Z'
        max_time = (datetime.utcnow() + timedelta(days=7)).isoformat() + 'Z'

        events_result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=now,
            timeMax=max_time,
            maxResults=50,
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        events = events_result.get("items", [])

        if not events:
            dispatcher.utter_message(text="No hay clases programadas esta semana.")
            return []

        mensaje = "📅 Clases con cupo disponible:\n"
        clases_disponibles = False

        for event in events:
            nombre_clase = event.get("summary", "Clase sin nombre")
            descripcion = event.get("description", "")

            # Extraer fecha y hora de inicio y fin
            start = event["start"].get("dateTime", event["start"].get("date"))
            end = event["end"].get("dateTime", event["end"].get("date"))

            # Convertir a datetime
            inicio_dt = datetime.fromisoformat(start)
            fin_dt = datetime.fromisoformat(end)

            # Formatear fechas
            fecha_inicio_str = inicio_dt.strftime("%d-%m-%Y")
            fecha_fin_str = fin_dt.strftime("%d-%m-%Y")
            hora_inicio_str = inicio_dt.strftime("%I:%M %p")

            # Buscar cupo_maximo y reservas_actuales en la descripción
            cupo_match = re.search(r"cupo_maximo\s*:\s*(\d+)", descripcion, re.IGNORECASE)
            reservas_match = re.search(r"reservas_actuales\s*:\s*(\d+)", descripcion, re.IGNORECASE)

            if cupo_match and reservas_match:
                cupo_maximo = int(cupo_match.group(1))
                reservas_actuales = int(reservas_match.group(1))
                lugares_disponibles = cupo_maximo - reservas_actuales

                if lugares_disponibles > 0:
                    clases_disponibles = True
                    mensaje += (f"- {nombre_clase} del {fecha_inicio_str} al {fecha_fin_str} "
                                f"en horario de {hora_inicio_str}: quedan {lugares_disponibles} lugares disponibles.\n")

        if not clases_disponibles:
            mensaje = "Desafortunadamente no hay clases con cupo disponible en esta semana."

        dispatcher.utter_message(text=mensaje)
        return []

#Accion para agendar la clase
class ActionAgendarClase(Action):
    def name(self) -> str:
        return "action_agendar_clase"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: dict) -> List[Dict[Text, Any]]:

        clase = tracker.get_slot('clase')
        fecha = tracker.get_slot('fecha')
        hora = tracker.get_slot('hora')

        # Convertimos fecha y hora a datetime para Google Calendar
        try:
            # Ajusta el formato según el que recibes del usuario, ejemplo: 08-09-2025 11:00AM
            start_datetime = datetime.strptime(f"{fecha} {hora}", "%d-%m-%Y %I:%M%p")
            end_datetime = start_datetime + timedelta(hours=1)  # duración de 1 hora
        except ValueError:
            dispatcher.utter_message(text="No entendí la fecha u hora. Usa formato DD-MM-YYYY y HH:MMAM/PM")
            return []

        # Convertimos a formato RFC3339 para Google Calendar
        start_iso = start_datetime.isoformat() + 'Z'
        end_iso = end_datetime.isoformat() + 'Z'

        # Buscamos eventos en ese rango
        events_result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=start_iso,
            timeMax=end_iso,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        if not events:
            dispatcher.utter_message(text=f"No encontré la clase {clase} a esa hora.")
            return []

        for event in events:
            if event['summary'].lower() == clase.lower():
                # Extraemos cupo y reservas
                description = event.get('description', '')
                cupo_maximo = 0
                reservas_actuales = 0
                for line in description.split('\n'):
                    if 'cupo_maximo' in line:
                        cupo_maximo = int(line.split(':')[1].strip())
                    if 'reservas_actuales' in line:
                        reservas_actuales = int(line.split(':')[1].strip())

                if reservas_actuales >= cupo_maximo:
                    dispatcher.utter_message(text=f"La clase {clase} ya está llena.")
                    return []

                # Incrementamos reservas
                reservas_actuales += 1
                # Rearmamos la descripción
                new_description = f"cupo_maximo: {cupo_maximo}\nreservas_actuales: {reservas_actuales}"

                # Actualizamos el evento en Google Calendar
                event['description'] = new_description
                service.events().update(calendarId=CALENDAR_ID, eventId=event['id'], body=event).execute()

                dispatcher.utter_message(text=f"Tu lugar en {clase} ha sido reservado. ({reservas_actuales}/{cupo_maximo})")
                return []

        dispatcher.utter_message(text=f"No encontré la clase {clase} a esa hora exacta.")
        return []




# Acción para cancelar clases
class ActionCancelarClases(Action):
    def name(self) -> Text:
        return "action_cancelar_clases"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Mensaje para el usuario que escribió al bot
        dispatcher.utter_message(text="Permitame un momento, para notificar su cancelación")

        # Número del usuario que escribió (WhatsApp lo manda como sender_id)
        numero_cliente = tracker.sender_id

        # Mensaje a enviar al admin
        mensaje_admin = f"El usuario con número {numero_cliente} ha solicitado cancelar una clase. Porfavor, revisa la conversación"

        # Llamada a la API de WhatsApp Cloud para enviar al admin
        url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
        headers = {
            "Authorization": f"Bearer {META_TOKEN}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": ADMIN_NUMBER,
            "type": "text",
            "text": {"body": mensaje_admin}
        }

        response = requests.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            print(f"Error al enviar mensaje al admin: {response.text}")
        else:
            print("Notificación enviada al admin correctamente.")

        return []

# Acción fallback (cuando no entiende)
class ActionDefaultFallback(Action):
    def name(self) -> Text:
        return "action_default_fallback"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        dispatcher.utter_message(text="Lo siento, no entendí 🤔. ¿Podrías repetirlo?")
        return []
