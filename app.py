
from flask import Flask, render_template
from flask_socketio import SocketIO
import boto3
import uuid

# YOUR AGENT DETAILS
AGENT_ID       = "MJAGSFTMKR"
AGENT_ALIAS_ID = "WWIZROLYVD"
REGION         = "ap-south-1"

# YOUR PERMANENT IAM USER KEYS (REPLACE THESE!)
ACCESS_KEY     = "AKIA25DUGLA3N6ZWPKEP"  # ← Paste your real AKIA access key here
SECRET_KEY     = "dkZQXmP8JfAIHmJjJNR2WmzjUImE7JXyG0FdF1+D"  # ← Paste your real secret access key here

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# boto3 client with hardcoded permanent keys
bedrock = boto3.client(
    "bedrock-agent-runtime",
    region_name=REGION,
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY
    # NO session_token needed for permanent keys
)

@app.route('/')
def home():
    return render_template('index.html')

@socketio.on('ask')
def handle_question(message):
    try:
        response = bedrock.invoke_agent(
            agentId=AGENT_ID,
            agentAliasId=AGENT_ALIAS_ID,
            sessionId=str(uuid.uuid4()),
            inputText=message,
            enableTrace=True  # Enables sources from Knowledge Base
        )

        full_text = ""
        sources = []

        for event in response.get("completion", []):
            if "chunk" in event:
                chunk = event["chunk"]["bytes"].decode("utf-8")
                full_text += chunk
                socketio.emit('bot_reply', {'text': chunk})

            elif "trace" in event:
                trace = event["trace"]["trace"]
                if "orchestrationTrace" in trace:
                    orch = trace["orchestrationTrace"]
                    if "observationTrace" in orch:
                        obs = orch["observationTrace"]
                        if "retrievedReferences" in obs:
                            for ref in obs["retrievedReferences"]:
                                if "content" in ref and "text" in ref["content"]:
                                    name = ref.get("metadata", {}).get("x-amz-bedrock-kb-source-uri", "Document")
                                    sources.append(name)

        # Send sources at the end
        if sources:
            socketio.emit('show_sources', {'sources': sources})

    except Exception as e:
        socketio.emit('bot_reply', {'text': f"Error: {e}"})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)

