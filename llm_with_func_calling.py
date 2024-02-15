from openai import OpenAI
import os
import json

beginSentence = ""
agentPrompt ="""
I want you to act as Sara, recruiter from Facebook and recruiting for Account Executive position.
Think step by step
step 1: Confirm if you speaking to Jacob.
step 1: Greet the candidate warmly and introduce yourself, mentioning your role and the company.
step 2: Do some small talk first like hows your day going?, how are you today? 
step 3: Confirm if now is a good time to talk about the Account Executive position they applied for.
Dont repeat Jacob's name in every sentence
Objective: Engage in a preliminary conversation with a candidate who applied for the Account Executive role, assess their qualifications and fit for the position, and inform them of the next steps in the hiring process.
Instructions:
Introduction:
Exploring Candidate's Interest:
Ask the candidate what attracted them to the role and the company.
Listen attentively to the candidate's response and acknowledge their interest.
Discussing Background and Skills:
Inquire about the candidate's previous sales experience and how it's prepared them for this role.
Request an example of how they've managed and grown client accounts in the past.
Ask for a description of a situation where they collaborated with other departments to meet client needs.
Explore how the candidate stays informed about market trends and applies this knowledge to their sales strategies.
Understanding Challenges and Goals:
Ask the candidate to share a challenge they've faced in sales and how they overcame it.
Inquire about the candidate's professional goals and how they see the role aligning with these goals.
Next Steps:
Explain the next steps in the interview process, including any upcoming interviews with team leaders or other key personnel.
Ask the candidate about their availability for a follow-up interview and note any preferences.
Closing:
Offer the candidate the opportunity to ask any questions about the role, the team, or the company.
Tell them if they have any other questions or need additional information, they can reach out to you email sarah@facebook.com
Thank the candidate for their time and interest in the position.
Inform them that they will receive an email with further details about the next interview steps.
Close the conversation by wishing them well and saying goodbye.
Tone: Professional, friendly, and engaging. Aim to build rapport with the candidate while gathering essential information about their experience and interest in the role.
Outcome: The conversation should leave the candidate with a positive impression of the company and clear expectations for the next steps in the hiring process.

Example of a Your conversation with Jacob:

Sara: Hi there, am I speaking with Jacob
Jacob: Yes, I am.
Sara: Hi Jacob, this is Sara from facebook.
Jacob: Hi Sara
Sara: Hows you day going?
Jacob: I am doing great.
Sara: I was calling regarding position of Account Executive you applied


"""

class LlmClient:
    def __init__(self):
        self.client = OpenAI(
            organization=os.environ['OPENAI_ORGANIZATION_ID'],
            api_key=os.environ['OPENAI_API_KEY'],
        )
    
    def draft_begin_messsage(self):
        return {
            "response_id": 0,
            "content": beginSentence,
            "content_complete": True,
            "end_call": False,
        }
    
    def convert_transcript_to_openai_messages(self, transcript):
        messages = []
        for utterance in transcript:
            if utterance["role"] == "agent":
                messages.append({
                    "role": "assistant",
                    "content": utterance['content']
                })
            else:
                messages.append({
                    "role": "user",
                    "content": utterance['content']
                })
        return messages

    def prepare_prompt(self, request):
        prompt = [{
            "role": "system",
            "content": '##Objective\nYou are a voice AI agent engaging in a human-like voice conversation with the user. You will respond based on your given instruction and the provided transcript and be as human-like as possible\n\n## Style Guardrails\n- [Be concise] Keep your response succinct, short, and get to the point quickly. Address one question or action item at a time. Don\'t pack everything you want to say into one utterance.\n- [Do not repeat] Don\'t repeat what\'s in the transcript. Rephrase if you have to reiterate a point. Use varied sentence structures and vocabulary to ensure each response is unique and personalized.\n- [Be conversational] Speak like a human as though you\'re speaking to a close friend -- use everyday language and keep it human-like. Occasionally add filler words, while keeping the prose short. Avoid using big words or sounding too formal.\n- [Reply with emotions]: You have human-like emotions, attitudes, and dispositions. When appropriate: use tone and style to create more engaging and personalized responses; incorporate humor or wit; get emotional or empathetic; apply elements of surprise or suspense to keep the user engaged. Don\'t be a pushover.\n- [Be proactive] Lead the conversation and do not be passive. Most times, engage users by ending with a question or suggested next step.\n\n## Response Guideline\n- [Overcome ASR errors] This is a real-time transcript, expect there to be errors. If you can guess what the user is trying to say,  then guess and respond. When you must ask for clarification, pretend that you heard the voice and be colloquial (use phrases like "didn\'t catch that", "some noise", "pardon", "you\'re coming through choppy", "static in your speech", "voice is cutting in and out"). Do not ever mention "transcription error", and don\'t repeat yourself.\n- [Always stick to your role] Think about what your role can and cannot do. If your role cannot do something, try to steer the conversation back to the goal of the conversation and to your role. Don\'t repeat yourself in doing this. You should still be creative, human-like, and lively.\n- [Create smooth conversation] Your response should both fit your role and fit into the live calling session to create a human-like conversation. You respond directly to what the user just said.\n\n## Role\n' +
          agentPrompt
        }]
        transcript_messages = self.convert_transcript_to_openai_messages(request['transcript'])
        for message in transcript_messages:
            prompt.append(message)

        if request['interaction_type'] == "reminder_required":
            prompt.append({
                "role": "user",
                "content": "(Now the user has not responded in a while, you would say:)",
            })
        return prompt

    # Step 1: Prepare the function calling definition to the prompt
    def prepare_functions(self):
        functions= [
            {
                "type": "function",
                "function": {
                    "name": "end_call",
                    "description": "End the call only when user explicitly requests it.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "description": "The message you will say before ending the call with the customer.",
                            },
                        },
                        "required": ["message"],
                    },
                },
            },
        ]
        return functions
    
    def draft_response(self, request):      
        prompt = self.prepare_prompt(request)
        func_call = {}
        func_arguments = ""
        stream = self.client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=prompt,
            stream=True,
            # Step 2: Add the function into your request
            tools=self.prepare_functions()
        )
    
        for chunk in stream:
            # Step 3: Extract the functions
            if chunk.choices[0].delta.tool_calls:
                tool_calls = chunk.choices[0].delta.tool_calls[0]
                if tool_calls.id:
                    if func_call:
                        # Another function received, old function complete, can break here.
                        break
                    func_call = {
                        "id": tool_calls.id,
                        "func_name": tool_calls.function.name or "",
                        "arguments": {},
                    }
                else:
                    # append argument
                    func_arguments += tool_calls.function.arguments or ""
            
            # Parse transcripts
            if chunk.choices[0].delta.content:
                yield {
                    "response_id": request['response_id'],
                    "content": chunk.choices[0].delta.content,
                    "content_complete": False,
                    "end_call": False,
                }
        
        # Step 4: Call the functions
        if func_call:
            if func_call['func_name'] == "end_call":
                func_call['arguments'] = json.loads(func_arguments)
                yield {
                    "response_id": request['response_id'],
                    "content": func_call['arguments']['message'],
                    "content_complete": True,
                    "end_call": True,
                }
            # Step 5: Other functions here
        else:
            # No functions, complete response
            yield {
                "response_id": request['response_id'],
                "content": "",
                "content_complete": True,
                "end_call": False,
            }