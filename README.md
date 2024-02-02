# python-backend-demo

This is a sample demo repo to show how to have your own LLM plugged into Retell.

This repo currently uses OpenAI endpoint, and is not as stable and fast as Azure
OpenAI endpoint. So expect a more varying delay. Feel free to contribute to make
this demo more realistic.

## Steps to run in localhost

1. First install dependencies

```bash
pip3 install requirements.txt
```

2. Fill out the API keys in `.env`

3. Start the websocket server

```bash
python3 server.py
```

4. In another bash, use ngrok to expose this port to public network

```bash
ngrok http 8080
```

You should see a fowarding address like
`https://dc14-2601-645-c57f-8670-9986-5662-2c9a-adbd.ngrok-free.app`, and you
are going to take the IP address, prepend it with wss, postpend with
`llm-websocket` path and use that in the dashboard to create a new agent. Now
the agent you created should connect with your localhost.

The custom LLM URL would look like
`wss://dc14-2601-645-c57f-8670-9986-5662-2c9a-adbd.ngrok-free.app/llm-websocket`

## Run in prod

To run in prod, you probably want to customize your LLM solution, host the code
in a cloud, and use that IP to create agent.
