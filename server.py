import asyncio
import json
import os
from dotenv import load_dotenv
from aiohttp import web
from flask import Flask, Response
from llm import LlmClient
from twilio_server import TwilioClient
from retellclient.models import operations
from twilio.twiml.voice_response import VoiceResponse

load_dotenv()

flask_app = Flask(__name__)
llm_client = LlmClient()
twilio_client = TwilioClient()

# twilio_client.create_phone_number(213, os.environ['RETELL_AGENT_ID'])
# twilio_client.register_phone_agent("+12133548310", os.environ['RETELL_AGENT_ID'])
# twilio_client.delete_phone_number("+12133548310")
# twilio_client.create_phone_call("+12133548310", "+13123156212", os.environ['RETELL_AGENT_ID'])

@flask_app.route("/twilio-voice-webhook/<agent_id_path>", methods=["POST"])
def listen_twilio_voice_webhook(agent_id_path):
    try:
        call_response = twilio_client.retell.register_call(operations.RegisterCallRequestBody(agent_id=agent_id_path, audio_websocket_protocol="twilio", audio_encoding="mulaw", sample_rate=8000))
        if call_response.call_detail:
            response = VoiceResponse()
            start = response.connect()
            start.stream(url=f"wss://api.re-tell.ai/audio-websocket/{call_response.call_detail.call_id}")
            return Response(str(response), mimetype="text/xml")
    except Exception as err:
        print(f"Error in twilio voice webhook: {err}")
        return Response(status=500)

async def flask_handler(request):
    # Convert aiohttp request to Flask request
    with flask_app.test_request_context(
        path=request.path,
        method=request.method,
        headers={key: value for key, value in request.headers.items()},
        data=await request.read()
    ):
        # Handle the request using Flask
        flask_response = flask_app.full_dispatch_request()
        return web.Response(
            body=flask_response.get_data(),
            status=flask_response.status_code,
            headers={key: value for key, value in flask_response.headers.items()}
)
        
async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    call_id = request.match_info['call_id']
    print(f"Path parameter after 'llm-websocket': {call_id}")

    # send first message to signal ready of server
    response_id = 0
    first_event = llm_client.draft_begin_messsage()
    await ws.send_str(json.dumps(first_event))

    async def process_message(request):
        nonlocal response_id
        try:
            # print out transcript
            os.system('cls' if os.name == 'nt' else 'clear')
            print(json.dumps(request, indent=4))

            if 'response_id' not in request:
                return # no response needed, process live transcript update if needed

            if request['response_id'] > response_id:
                response_id = request['response_id']
            for event in llm_client.draft_response(request):
                await ws.send_str(json.dumps(event))
                if request['response_id'] < response_id:
                    return # new response needed, abondon this one
        except Exception as e:
            print(f"Encountered error in generating response: {e}")
            print(message)

    try:
        async for message in ws:
            if message.type == web.WSMsgType.TEXT:
                await process_message(json.loads(message.data))
            elif message.type == web.WSMsgType.ERROR:
                print(f'WebSocket connection closed with exception: {ws.exception()}')
    except Exception as e:
        print(f'LLM WebSocket error for {call_id}: {e}')    
    return ws

async def init_app():
    app = web.Application()
    app.router.add_route('*', '/twilio-voice-webhook/{agent_id_path}', flask_handler)
    app.router.add_get('/llm-websocket/{call_id:.*}', websocket_handler)  # Adjust the WebSocket route as needed
    return app

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    app = loop.run_until_complete(init_app())
    web.run_app(app, port=8080)
