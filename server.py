import json
import os
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.websockets import WebSocketState
from llm_with_func_calling import LlmClient
from twilio_server import TwilioClient
# from retell.models import operations
from twilio.twiml.voice_response import VoiceResponse

load_dotenv(override=True)

app = FastAPI()

twilio_client = TwilioClient()

# twilio_client.create_phone_number(213, os.environ['RETELL_AGENT_ID'])
# twilio_client.delete_phone_number("+12133548310")
# twilio_client.register_phone_agent("+13392016322", os.environ['RETELL_AGENT_ID'])
# twilio_client.create_phone_call("+12133548310", "+14154750418", os.environ['RETELL_AGENT_ID'])

@app.post("/twilio-voice-webhook/{agent_id_path}")
async def handle_twilio_voice_webhook(request: Request, agent_id_path: str):
    try:
        # Check if it is machine
        post_data = await request.form()
        if 'AnsweredBy' in post_data and post_data['AnsweredBy'] == "machine_start":
            twilio_client.end_call(post_data['CallSid'])
            return PlainTextResponse("")
        elif 'AnsweredBy' in post_data:
            return PlainTextResponse("")

        # call_repsponse = twilio_client.retell.register_call(operations.RegisterCallRequestBody(
        call_response = twilio_client.retell.call.register(
            agent_id=agent_id_path,
            audio_websocket_protocol="twilio",
            audio_encoding="mulaw",
            sample_rate=8000, # Sample rate has to be 8000 for Twilio
        )

        print(f"Call response: {call_response}")

        response = VoiceResponse()
        start = response.connect()
        start.stream(url=f"wss://api.retellai.com/audio-websocket/{call_response.call_id}")
        return PlainTextResponse(str(response), media_type='text/xml')
    except Exception as err:
        print(f"Error in twilio voice webhook: {err}")
        return JSONResponse(status_code=500, content={"message": "Internal Server Error"})
    

@app.websocket("/llm-websocket/{call_id}")
async def websocket_handler(websocket: WebSocket, call_id: str):
    await websocket.accept()
    print(f"Handle llm ws for: {call_id}")

    llm_client = LlmClient()

    # Send first message to signal ready of server
    response_id = 0
    first_event = llm_client.draft_begin_message()
    await websocket.send_text(json.dumps(first_event))

    async def stream_response(request):
        nonlocal response_id
        for event in llm_client.draft_response(request):
            await websocket.send_text(json.dumps(event))
            if request['response_id'] < response_id:
                return # new response needed, abandon this one
    try:
        while True:
            message = await websocket.receive_text()
            request = json.loads(message)
            # print out transcript
            print(json.dumps(request, indent=4))
            
            # Clear the console
            # os.system('cls' if os.name == 'nt' else 'clear')

            # There are 4 types of interaction_type: call_details, update_only, response_required, and reminder_required.
            # Not all of them need to be handled, only response_required and reminder_required.
            if request['interaction_type'] == "call_details":
                continue
            if request['interaction_type'] == "update_only":
                continue
            response_id = request['response_id']
            asyncio.create_task(stream_response(request))
    except WebSocketDisconnect:
        print(f"LLM WebSocket disconnected for {call_id}")
    except Exception as e:
        print(f"Error in LLM WebSocket: {e}")
    finally:
        print(f"LLM WebSocket connection closed for {call_id}")

