# actions.py
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher

# Ruta al archivo de credenciales
SERVICE_ACCOUNT_FILE = "../aqueous-cargo-470315-d0-0bc8aa6304fe.json"
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

class ActionListarClases(Action):
    def name(self):
        return "action_checar_clases"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: dict):

        # Autenticación con Google
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)

        service = build("calendar", "v3", credentials=creds)

        # ID de tu calendario (puede ser tu correo)
        calendar_id = "tu_calendario@gmail.com"

        # Fechas para buscar eventos (hoy + 7 días)
        now = datetime.utcnow().isoformat() + 'Z'
        max_time = (datetime.utcnow() + timedelta(days=7)).isoformat() + 'Z'

        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=now,
            timeMax=max_time,
            maxResults=10,
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        events = events_result.get("items", [])

        if not events:
            dispatcher.utter_message(text="No hay clases programadas esta semana.")
        else:
            mensaje = "Estas son las clases:\n"
            for event in events:
                start = event["start"].get("dateTime", event["start"].get("date"))
                mensaje += f"- {event['summary']} a las {start}\n"
            dispatcher.utter_message(text=mensaje)

        return []

# Acción para agendar clase
class ActionAgendarClase(Action):
    def name(self) -> Text:
        return "action_agendar_clase"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        # Aquí podrías guardar en BD, pero de momento solo responderemos
        dispatcher.utter_message(text="Perfecto, tu clase ha sido agendada ✅. ¡Nos vemos en el gym!")
        return []

# Acción para preguntar disponibilidad
class ActionPreguntarDisponibilidad(Action):
    def name(self) -> Text:
        return "action_preguntar_disponibilidad"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        disponibilidad = "En este momento tenemos cupos disponibles en todas las clases excepto Zumba (lleno)."
        dispatcher.utter_message(text=disponibilidad)
        return []

# Acción para cancelar clases
class ActionCancelarClases(Action):
    def name(self) -> Text:
        return "action_cancelar_clases"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        dispatcher.utter_message(text="Tu clase ha sido cancelada ❌. Esperamos verte pronto en otra sesión.")
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
