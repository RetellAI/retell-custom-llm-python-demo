import json
import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.websockets import WebSocketState
# from llm import LlmClient
from llm_with_func_calling import LlmClient
from twilio_server import TwilioClient
from retellclient.models import operations
from twilio.twiml.voice_response import VoiceResponse
import logging
from db import DBClient

load_dotenv()

app = FastAPI()

llm_client = LlmClient()
twilio_client = TwilioClient()
db_client = DBClient('callee.db')
user = db_client.get_username_by_phone_number(14159646968)
print(user)

logging.basicConfig(
    filename='app.log',
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(message)s'

)

logger = logging.getLogger(__name__)

call_list = {}

# twilio_client.create_phone_number(213, os.environ['RETELL_AGENT_ID'])
# twilio_client.register_phone_agent("+12133548310", os.environ['RETELL_AGENT_ID'])
# twilio_client.delete_phone_number("+12133548310")
#twilio_client.create_phone_call("+15123801351", "+14159646968", os.environ['RETELL_AGENT_ID'])

async def index(request):
    return web.Response(text="Welcome home!")

async def call_number(request):
    to_number = request.match_info['to_number']
    print(f"Calling {to_number}")
    twilio_client.create_phone_call("+15123801351", to_number, os.environ['RETELL_AGENT_ID'])

@app.post("/twilio-voice-webhook/{agent_id_path}")
async def handle_twilio_voice_webhook(request: Request, agent_id_path: str):
    try:
        logger.debug(f"Call Request: {request}")
        # Check if it is machine
        post_data = await request.form()
        logger.debug(f"Post Data: {post_data}")
        logger.debug(f"Called Number: {post_data['Called']}")
        if 'AnsweredBy' in post_data and post_data['AnsweredBy'] == "machine_start":
            twilio_client.end_call(post_data['CallSid'])
            return PlainTextResponse("")

        call_response = twilio_client.retell.register_call(operations.RegisterCallRequestBody(
            agent_id=agent_id_path, 
            audio_websocket_protocol="twilio", 
            audio_encoding="mulaw", 
            sample_rate=8000
        ))
        if call_response.call_detail:
            response = VoiceResponse()
            start = response.connect()
            start.stream(url=f"wss://api.re-tell.ai/audio-websocket/{call_response.call_detail.call_id}")
            logger.debug(f"twilio webhook call_id: {call_response.call_detail.call_id}")
            user = db_client.get_username_by_phone_number(post_data['Called'].lstrip('+'))
            call_list[call_response.call_detail.call_id]=user
            
            return PlainTextResponse(str(response), media_type='text/xml')
    except Exception as err:
        print(f"Error in twilio voice webhook: {err}")
        return JSONResponse(status_code=500, content={"message": "Internal Server Error"})

@app.websocket("/llm-websocket/{call_id}")
async def websocket_handler(websocket: WebSocket, call_id: str):
    await websocket.accept()
    logger.debug(f"Handle llm ws for: {call_id}")
    
    call_id_value = call_id.split('/')[1]
    username=call_list.get(call_id_value, 'John')

    logger.debug(f"Calling to: {username}")

    # send first message to signal ready of server
    response_id = 0
    first_event = llm_client.draft_begin_messsage(username)
    await websocket.send_text(json.dumps(first_event))

    try:
        while True:
            message = await websocket.receive_text()
            request = json.loads(message)
            # print out transcript
            #os.system('cls' if os.name == 'nt' else 'clear')
            print(json.dumps(request, indent=4))

            if 'response_id' not in request:
                continue # no response needed, process live transcript update if needed

            if request['response_id'] > response_id:
                response_id = request['response_id']
            for event in llm_client.draft_response(request):
                await websocket.send_text(json.dumps(event))
                if request['response_id'] < response_id:
                    continue # new response needed, abondon this one
    except Exception as e:
        print(f'LLM WebSocket error for {call_id}: {e}')
    finally:
        try:
            await websocket.close()
        except RuntimeError as e:
            print(f"Websocket already closed for {call_id}")
        print(f"Closing llm ws for: {call_id}")