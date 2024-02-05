from twilio.rest import Client
import retellclient
import os

class TwilioClient:
    def __init__(self):
        self.client = Client(os.environ['TWILIO_ACCOUNT_ID'], os.environ['TWILIO_AUTH_TOKEN'])
        self.retell = retellclient.RetellClient(
            api_key=os.environ['RETELL_API_KEY'],
        )
         
    def create_phone_number(self, area_code, agent_id):
        try:
            local_number = self.client.available_phone_numbers('US').local.list(area_code=area_code,
                                           limit=1)
            if (local_number is None or local_number[0] == None):
                raise "No phone numbers of this area code."
            phone_number_object = self.client.incoming_phone_numbers.create(phone_number=local_number[0].phone_number, voice_url=f"{os.getenv('NGROK_IP_ADDRESS')}/twilio-voice-webhook/{agent_id}")
            print("Getting phone number:", vars(phone_number_object))
            return phone_number_object
        except Exception as err:
            print(err)
            
    def update_voice_webhook_url(self, phone_number, agent_id):
        try:
            phone_number_objects = self.client.incoming_phone_numbers.list(limit=200)
            number_sid = ''
            for phone_number_object in phone_number_objects:
                if phone_number_object.phone_number == phone_number:
                    number_sid = phone_number_object.sid
            if number_sid is None:
                print("Unable to locate this number in your Twilio account, is the number you used in BCP 47 format?")
                return
            phone_number_object = self.client.incoming_phone_numbers(number_sid).update(voice_url=f"{os.getenv('NGROK_IP_ADDRESS')}/twilio-voice-webhook/{agent_id}")
            print("Getting phone number:", vars(phone_number_object))
            return phone_number_object
        except Exception as err:
            print(err)
    
    def delete_phone_number(self, phone_number):
        try:
            phone_number_objects = self.client.incoming_phone_numbers.list(limit=200)
            number_sid = ''
            for phone_number_object in phone_number_objects:
                if phone_number_object.phone_number == phone_number:
                    number_sid = phone_number_object.sid
            if number_sid is None:
                print("Unable to locate this number in your Twilio account, is the number you used in BCP 47 format?")
                return
            phone_number_object = self.client.incoming_phone_numbers(number_sid).delete()
            print("Removed phone number:", phone_number)
            return phone_number_object
        except Exception as err:
            print(err)
    
    def create_phone_call(self, from_number, to_number, agent_id):
        try:
            self.client.calls.create(url=f"{os.getenv('NGROK_IP_ADDRESS')}/twilio-voice-webhook/{agent_id}", to=to_number, from_=from_number)
            print(f"Call from: {from_number} to: {to_number}")
        except Exception as err:
            print(err)
