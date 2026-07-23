import json
import os
import subprocess
import requests
# ==============================
# OpenRouter Configuration
# ==============================

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

MODEL = "deepseek/deepseek-v4-flash"

URL = "https://openrouter.ai/api/v1/chat/completions"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

SYSTEM_PROMPT = """
You are an autonomous terminal coding assistant.

You have these tools:

read_file(path)
write_file(path, content)
run_command(command)

When you need one, reply ONLY with JSON.

Example:

{
  "tool":"read_file",
  "path":"main.py"
}

or

{
  "tool":"write_file",
  "path":"hello.txt",
  "content":"hello"
}

or

{
  "tool":"run_command",
  "command":"python main.py"
}

When you have the final answer, reply normally.
"""

conversation = [
    {
        "role": "system",
        "content": SYSTEM_PROMPT
    }
]

summary = ""

MAX_MESSAGES = 18


def chat(messages):
    r = requests.post(
        URL,
        headers=HEADERS,
        json={
            "model": MODEL,
            "messages": messages,
            "reasoning": {"enabled": True}
        },
        timeout=300
    )

    r.raise_for_status()

    return r.json()["choices"][0]["message"]


def summarize():
    global conversation
    global summary

    msgs = [
        {
            "role": "system",
            "content":
            "Summarize the conversation for future memory. Keep important facts, file names, decisions, plans, variables and objectives."
        }
    ]

    msgs.extend(conversation[1:])

    result = chat(msgs)

    summary = result["content"]

    conversation = [
        conversation[0],
        {
            "role": "system",
            "content":
            "Conversation memory:\n" + summary
        }
    ]


def read_file(path):
    try:
        with open(path, "r", encoding="utf8") as f:
            return f.read()
    except Exception as e:
        return str(e)


def write_file(path, content):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
    except:
        pass

    try:
        with open(path, "w", encoding="utf8") as f:
            f.write(content)
        return "File written."
    except Exception as e:
        return str(e)


def run_command(cmd):
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True
        )

        return result.stdout + result.stderr

    except Exception as e:
        return str(e)


def execute_tool(message):

    try:
        tool = json.loads(message["content"])

    except:
        return None

    if tool.get("tool") == "read_file":

        return read_file(tool["path"])

    if tool.get("tool") == "write_file":

        return write_file(
            tool["path"],
            tool["content"]
        )

    if tool.get("tool") == "run_command":

        return run_command(tool["command"])

    return None


print("=" * 60)
print("Gemma Agent")
print("Type exit to quit.")
print("=" * 60)

while True:

    user = input("\nYou > ")

    if user.lower() in ("exit", "quit"):
        break

    conversation.append(
        {
            "role": "user",
            "content": user
        }
    )

    while True:

        response = chat(conversation)

        conversation.append(
            {
                "role": "assistant",
                "content": response["content"]
            }
        )

        tool_result = execute_tool(response)

        if tool_result is None:

            print("\nGemma:\n")
            print(response["content"])
            break

        print("\n[Tool Executed]\n")
        print(tool_result)

        conversation.append(
            {
                "role": "user",
                "content":
                f"Tool result:\n{tool_result}"
            }
        )

    if len(conversation) > MAX_MESSAGES:
        summarize()