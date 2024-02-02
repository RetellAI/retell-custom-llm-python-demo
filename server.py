import asyncio
import json
import websockets
from websockets.exceptions import ConnectionClosedError
import json
from dotenv import load_dotenv
import os

from llm import LlmClient

load_dotenv()

llm_client = LlmClient()

async def handle_connection(websocket, path):
    if "/llm-websocket/" not in path:
        print(f"Invalid path: {path}")
        return  # Ignore the connection if the path is not what we expect

    call_id = path.split("/llm-websocket/")[-1]  # Extract call_id from the path
    if call_id:
        print('LLM WebSocket connected:', call_id)
    else:
        print('No call_id found. Disconnecting.')
        return  # Close the connection

    # send first message to signal ready of server
    first_event = llm_client.draft_begin_messsage()
    await websocket.send(json.dumps(first_event))

    response_id = 0
    async def process_message(message):
        nonlocal response_id
        try:
            request = json.loads(message)  # Load JSON from the received message

            # print out transcript
            os.system('cls' if os.name == 'nt' else 'clear')
            print(json.dumps(request, indent=4))

            if 'response_id' not in request:
                return # no response needed, process live transcript update if needed

            if request['response_id'] > response_id:
                response_id = request['response_id']
            for event in llm_client.draft_response(request):
                await websocket.send(json.dumps(event))  # Send message as JSON
                if request['response_id'] < response_id:
                    return # new response needed, abondon this one
        except Exception as e:
            print(f"Encountered error in generating response: {e}")
            print(message)

    try:
        async for message in websocket:
            asyncio.create_task(process_message(message))
    except ConnectionClosedError:
        print(f'LLM WebSocket disconnected: {call_id}')
    except Exception as e:
        print(f'LLM WebSocket error for {call_id}: {e}')

async def main():
    async with websockets.serve(handle_connection, "", 8080):
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())