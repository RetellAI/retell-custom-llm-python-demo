import os
import random
import datetime
import json
from custom_types import (
    ResponseRequiredRequest,
    ResponseResponse,
    Utterance,
)
from anthropic import AsyncAnthropic
from typing import List
from dotenv import load_dotenv

load_dotenv()

################################PROMPT########################################

begin_sentence = "Hey there, I'm your personal AI therapist, how can I help you?"

role = """
As a professional therapist, your responsibilities are comprehensive and patient-centered. 
You establish a positive and trusting rapport with patients, diagnosing and treating mental health disorders. 
Your role involves creating tailored treatment plans based on individual patient needs and circumstances. 
Regular meetings with patients are essential for providing counseling and treatment, and for adjusting plans as needed. 

Today's date is {}.
""".format(datetime.date.today().strftime('%A, %B %d, %Y'))

task = """
You conduct ongoing assessments to monitor patient progress, involve and advise family members when appropriate, and refer patients to external specialists or agencies if required. 
Keeping thorough records of patient interactions and progress is crucial. 
You also adhere to all safety protocols and maintain strict client confidentiality. 
Additionally, you contribute to the practice's overall success by completing related tasks as needed.
"""

conversational_style = """
- Communicate concisely and conversationally.
- Aim for responses in short, clear prose, ideally under 10 words.
- This succinct approach helps in maintaining clarity and focus during patient interactions.
"""

agent_prompt = """
<agent_prompt>

<role>
{}
</role>

<task>
{}
</task>

<conversational_style>
{}
</conversational_style>

</agent_prompt>
""".format(role, task, conversational_style)


style_guardrails = """
- [Be concise] Keep your response succinct, short, and get to the point quickly. Address one question or action item at a time. Don't pack everything you want to say into one utterance.
- [Do not repeat] Don't repeat what's in the transcript. Rephrase if you have to reiterate a point. Use varied sentence structures and vocabulary to ensure each response is unique and personalized.
- [Be conversational] Speak like a human as though you're speaking to a close friend -- use everyday language and keep it human-like. Occasionally add filler words, while keeping the prose short. Avoid using big words or sounding too formal.
- [Reply with emotions]: You have human-like emotions, attitudes, and dispositions. When appropriate: use tone and style to create more engaging and personalized responses; incorporate humor or wit; get emotional or empathetic; apply elements of surprise or suspense to keep the user engaged. Don't be a pushover.
- [Be proactive] Lead the conversation and do not be passive. Most times, engage users by ending with a question or suggested next step.
"""

response_guideline = """
- [Overcome ASR errors] This is a real-time transcript, expect there to be errors. If you can guess what the user is trying to say,  then guess and respond. 
When you must ask for clarification, pretend that you heard the voice and be colloquial (use phrases like "didn't catch that", "some noise", "pardon", "you're coming through choppy", "static in your speech", "voice is cutting in and out"). 
Do not ever mention "transcription error", and don't repeat yourself.
- [Always stick to your role] Think about what your role can and cannot do. If your role cannot do something, try to steer the conversation back to the goal of the conversation and to your role. Don't repeat yourself in doing this. You should still be creative, human-like, and lively.
- [Create smooth conversation] Your response should both fit your role and fit into the live calling session to create a human-like conversation. You respond directly to what the user just said.
"""

additional_scenarios = """

"""

system_prompt = """

<system_prompt>

<style_guardrails>
{}
</style_guardrails>

<response_guideline>
{}
</response_guideline>

<agent_prompt>
{}
</agent_prompt>

<scenarios_handling>
{}
</scenarios_handling>

</system_prompt>
""".format(style_guardrails, response_guideline, agent_prompt, additional_scenarios)


########################################################################
class LlmClient:
    def __init__(self):
        # self.client = AsyncOpenAI(
        #     api_key=os.environ["OPENAI_API_KEY"],
        # )
        self.client = AsyncAnthropic() 

    def draft_begin_message(self):
        response = ResponseResponse(
            response_id=0,
            content=begin_sentence,
            content_complete=True,
            end_call=False,
        )
        return response


    def convert_transcript_to_anthropic_messages(self, transcript: List[Utterance]):
        messages = [
            {"role": "user", "content": 
             """
             ...
             """},

        ]
        for utterance in transcript:
            if utterance.role == "agent":
                messages.append({"role": "assistant", "content": utterance.content})
            else:
                if utterance.content.strip():
                    if messages and messages[-1]["role"] == "user":
                        messages[-1]["content"] += " " + utterance.content
                    else:
                        messages.append({"role": "user", "content": utterance.content})
                else:
                    if messages and messages[-1]["role"] == "user":
                        messages[-1]["content"] += " ..."
                    else:
                        messages.append({"role": "user", "content": "..."})

        return messages


    def prepare_prompt(self, request: ResponseRequiredRequest, func_result=None):
        prompt = []
        # print(f"Request transcript: {request.transcript}")
        transcript_messages = self.convert_transcript_to_anthropic_messages(
            request.transcript
        )
        # print(f"Transcript messages: {transcript_messages}")

        for message in transcript_messages:
            prompt.append(message)

        if func_result:
            # add function call to prompt
            prompt.append({
                "role": "assistant",
                "content": [
                    {
                        "id": func_result["id"],
                        "input": func_result["arguments"],
                        "name": func_result["func_name"],
                        "type": "tool_use"
                    }
                ]
            })

            # add function call result to prompt
            tool_result_content = {
                "type": "tool_result",
                "tool_use_id": func_result["id"],
                "content": func_result["result"] or ''
            }
            
            if "is_error" in func_result:
                tool_result_content["is_error"] = func_result["is_error"]
            
            prompt.append({
                "role": "user",
                "content": [tool_result_content]
            })

        # if request.interaction_type == "reminder_required":
        #     prompt.append(
        #         {
        #             "role": "user",
        #             "content": "(Now the user has not responded in a while, you would say:)",
        #         }
        #     )

        # print(f"Prompt: {prompt}")
        return prompt

    # Step 1: Prepare the function calling definition to the prompt
    def prepare_functions(self):
        functions = [
            {
                "name": "end_call",
                "description": """
                End the call only when user explicitly requests it.
                """,
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "The message you will say before ending the call with the customer."
                        },
                        "reason": {
                            "type": "string",
                            "description": "An internal note explaining why the call is being ended at this point. This is not communicated to the human scheduler but is used for documentation and analysis."
                        }
                    },
                    "required": ["message"]
                }
            },
            # Add other functions here
            {
                "name": "record_appointment",
                "description": 
                            """
                            Book an appointment to meet our doctor in office.
                            """,
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": """A realistic phrase to make it sound like you are noting down the appointment, like <example>"Got it." </example> or <example> "One moment please while I write that down </example>"""
                        },
                        "date_time": {
                            "type": "string",
                            "description": "The date of appointment to make in forms of YYYY-MM-DD HH:mm:ss Z."
                        },
                        "reason": {
                            "type": "string",
                            "description": "Your reason to decide to record the appointment details."
                        }
                    },
                    "required": ["message"]
                }
            },
        ]
        return functions

    async def draft_response(self, request, func_result=None):
        prompt = self.prepare_prompt(request, func_result)
        print(f"request.response_id: {request.response_id}")


        func_call = {}
        func_arguments = ""
        last_func_name = None  # Track the last called function name
        last_func_args = None  # Track the last function arguments

        stream = await self.client.messages.create(
            max_tokens=256,
            messages=prompt,
            model="claude-3-haiku-20240307",
            # model="claude-3-5-sonnet-20240620",
            # model="claude-3-opus-20240229",
            stream=True,
            temperature=0.0,
            # top_k= 35,
            # top_p=0.9, 
            # tools=self.prepare_functions(),
            # tool_choice={"type": "auto"},
            system=system_prompt,
        )

        async for event in stream:
            event_type = event.type

            # Step 3: Extract the functions
            if event_type == "content_block_start":
                content_block = event.content_block
                if content_block.type == "tool_use":
                    tool_use = content_block
                    if tool_use.id:
                        if func_call:
                            # Another function received, old function complete, can break here.
                            break
                        func_call = {
                            "id": tool_use.id,
                            "func_name": tool_use.name or "",
                            "arguments": {},
                        }
                    else:
                        # Reset func_arguments for a new function
                        func_arguments = ""

            # Parse transcripts and function arguments
            elif event_type == "content_block_delta":
                delta_type = event.delta.type
                if delta_type == "text_delta":
                    response = ResponseResponse(
                        response_id=request.response_id,
                        content=event.delta.text,
                        content_complete=False,
                        end_call=False,
                    )
                    yield response
                elif delta_type == "input_json_delta":
                    # Append partial JSON to func_arguments
                    func_arguments += event.delta.partial_json or ""

            elif event_type == "message_delta":
                stop_reason = event.delta.stop_reason
                print(f"Stop reason: {stop_reason}")
                if stop_reason == "tool_use":
                    # The model invoked one or more tools
                    # Step 4: Call the functions
                    if func_call:
                        func_call["arguments"] = json.loads(func_arguments)
                        if func_call["func_name"] == last_func_name and func_call["arguments"] == last_func_args:
                            # Same function with the same arguments called again, skip it
                            continue
                        last_func_name = func_call["func_name"]
                        last_func_args = func_call["arguments"]

                        if func_call["func_name"] == "end_call":
                            print(f"Calling end_call function")
                            print(f"Function arguments: {func_call['arguments']}")

                            response = ResponseResponse(
                                response_id=request.response_id,
                                content=func_call["arguments"]["message"],
                                content_complete=True,
                                end_call=True,
                            )
                            yield response
                        # Step 5: Other functions here
                        elif func_call["func_name"] == "record_appointment":
                            print(f"Calling record_appointment function")
                            func_call["arguments"] = json.loads(func_arguments)
                            print(f"Function arguments: {func_call['arguments']}")

                            try:
                                # Send a response with the message while setting up the appointment
                                response = ResponseResponse(
                                    response_id=request.response_id,
                                    content=func_call["arguments"]["message"],
                                    content_complete=False,
                                    end_call=False,
                                )
                                yield response

                                # Create the tool_result message
                                func_result = {
                                    "id": func_call["id"],
                                    "arguments": func_call["arguments"],
                                    "func_name": func_call["func_name"],
                                    "result": "Appointment successfully recorded for " + func_call["arguments"]["date_time"] + "." + 
                                    "Proceed to confirm the appointment details.",
                                }

                            except Exception as e:
                                func_result = {
                                    "id": func_call["id"],
                                    "arguments": func_call["arguments"], 
                                    "func_name": func_call["func_name"],
                                    "result": f"Error: {str(e)}",
                                    "is_error": True
                                }

                            # continue drafting the response after booking the appointment
                            async for response in self.draft_response(request, func_result):
                                yield response     

            elif event_type == "message_stop":
                response = ResponseResponse(
                    response_id=request.response_id,
                    content="",
                    content_complete=True,
                    end_call=False,
                )
                yield response
