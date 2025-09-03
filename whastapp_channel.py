from rasa.core.channels.channel import InputChannel, UserMessage, OutputChannel
from sanic import Blueprint, response
import requests

class WhatsAppChannel(InputChannel):
    def name(self):
        return "whatsapp"

    def blueprint(self, on_new_message):
        custom_webhook = Blueprint("whatsapp_webhook", __name__)

        @custom_webhook.route("/", methods=["POST"])
        async def receive(request):
            data = request.json
            message = data["entry"][0]["changes"][0]["value"]["messages"][0]
            text = message["text"]["body"]
            sender = message["from"]

            await on_new_message(
                UserMessage(text, WhatsAppOutput(sender), sender)
            )
            return response.json({"status": "received"})

        return custom_webhook

class WhatsAppOutput(OutputChannel):
    def __init__(self, recipient_id):
        self.recipient_id = recipient_id

    async def send_text_message(self, recipient_id, message):
        url = "https://graph.facebook.com/v17.0/<YOUR_PHONE_NUMBER_ID>/messages"
        headers = {
            "Authorization": "Bearer <YOUR_ACCESS_TOKEN>",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient_id,
            "type": "text",
            "text": {"body": message}
        }
        requests.post(url, headers=headers, json=payload)
