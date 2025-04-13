import os
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, Response
import uuid
import json
from dotenv import load_dotenv
from datetime import datetime
from langchain_azure_ai.chat_models import AzureAIChatCompletionsModel
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Default HTML template
DEFAULT_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>My Website</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100">
    <div class="container mx-auto p-4">
        <h1 class="text-2xl font-bold text-center">Welcome to My Website</h1>
        <p class="text-center mt-4">This is a template. Ask the AI to create something amazing!</p>
    </div>
</body>
</html>"""

# Helper Functions
def get_tag(site_id):
    """Generate a footer tag with site info and remix link"""
    return f"""<p style="border-radius: 8px; text-align: center; font-size: 12px; color: #fff; margin-top: 16px;position: fixed; left: 8px; bottom: 8px; z-index: 10; background: rgba(0, 0, 0, 0.8); padding: 4px 8px;">Made with DeepSite Python - 🧬 <a href="/remix/{site_id}" style="color: #fff;text-decoration: underline;" target="_blank">Remix</a></p>"""

def generate_site_id():
    """Generate a unique site ID"""
    return f"{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8]}"


def stream_response(prompt, html=None, previous_prompt=None):
    """Call Azure OpenAI API with streaming and yield chunks"""
    system_message = "ONLY USE HTML, CSS AND JAVASCRIPT. If you want to use ICON make sure to import the library first. Try to create the best UI possible by using only HTML, CSS and JAVASCRIPT. Use as much as you can TailwindCSS for the CSS, if you can't do something with TailwindCSS, then use custom CSS (make sure to import <script src=\"https://cdn.tailwindcss.com\"></script> in the head). Also, try to elaborate as much as you can, to create something unique. ALWAYS GIVE THE RESPONSE INTO A SINGLE HTML FILE"
    
    # Initialize messages list with system message
    messages = [
        SystemMessage(content=system_message)
    ]
    
    # Add previous prompt if exists
    if previous_prompt:
        messages.append(HumanMessage(content=previous_prompt))
    
    # Add current HTML state if exists (as an AI response)
    if html and html != DEFAULT_HTML:
        messages.append(AIMessage(content=f"The current code is: {html}"))
    
    # Add the current user prompt
    messages.append(HumanMessage(content=prompt))

    # Initialize deepseek model
    deep_seek_model = AzureAIChatCompletionsModel(
        endpoint=os.getenv("AZURE_AI_ENDPOINT"),
        credential=os.getenv("AZURE_AI_API_KEY"),
        model_name="DeepSeek-R1",
        temperature=0.7,
        max_tokens=4000
    )

    # Variables to track modes and content
    in_thinking_mode = False
    in_html_mode = False
    in_code_block = False
    html_code_block_started = False
    current_thought = ""
    current_html = ""
    current_description = ""
    buffer = ""
    
    # Stream the response
    try:
        response = deep_seek_model.stream(messages)
        
        for chunk in response:
            content = chunk.content
            if not content:
                continue
                
            buffer += content
            
            # Check for thinking tags
            if "<think>" in buffer:
                # Extract everything before <think> as description if not in thinking mode yet
                if not in_thinking_mode:
                    parts = buffer.split("<think>", 1)
                    if parts[0].strip():
                        current_description += parts[0].strip()
                        yield f"data: {json.dumps({'description': parts[0].strip()})}\n\n"
                    buffer = "<think>" + parts[1]
                
                in_thinking_mode = True
                buffer = buffer.replace("<think>", "", 1)
                current_thought += buffer
                yield f"data: {json.dumps({'thinking': buffer})}\n\n"
                buffer = ""
                
            elif "</think>" in buffer and in_thinking_mode:
                parts = buffer.split("</think>", 1)
                current_thought += parts[0]
                yield f"data: {json.dumps({'thinking': parts[0]})}\n\n"
                in_thinking_mode = False
                buffer = parts[1]  # Keep remainder for further processing
                
            elif in_thinking_mode:
                current_thought += buffer
                yield f"data: {json.dumps({'thinking': buffer})}\n\n"
                buffer = ""
                
            # Check for HTML code blocks
            elif "```html" in buffer and not in_code_block:
                parts = buffer.split("```html", 1)
                # If there's text before the code block, treat it as description
                if parts[0].strip():
                    current_description += parts[0].strip()
                    yield f"data: {json.dumps({'description': parts[0].strip()})}\n\n"
                in_code_block = True
                html_code_block_started = True
                buffer = parts[1]
                
            elif "```" in buffer and in_code_block and html_code_block_started:
                parts = buffer.split("```", 1)
                # The content before ``` is HTML code
                current_html += parts[0]
                yield f"data: {json.dumps({'content': parts[0]})}\n\n"
                in_code_block = False
                html_code_block_started = False
                buffer = parts[1]
                
            elif in_code_block and html_code_block_started:
                current_html += buffer
                yield f"data: {json.dumps({'content': buffer})}\n\n"
                buffer = ""
                
            # Check for HTML tags outside of code blocks (legacy support)
            elif buffer.strip() and not in_code_block:
                # If we find any HTML doctype or tags, consider this HTML content
                if "<!DOCTYPE html>" in buffer or "<html" in buffer or buffer.strip().startswith("<"):
                    in_html_mode = True
                    current_html += buffer
                    yield f"data: {json.dumps({'content': buffer})}\n\n"
                    buffer = ""
                else:
                    # If we have accumulated enough non-HTML text or hit a sentence end
                    if buffer.endswith(".") or buffer.endswith("!") or buffer.endswith("?") or buffer.endswith("\n") or len(buffer) > 50:
                        current_description += buffer
                        yield f"data: {json.dumps({'description': buffer})}\n\n"
                        buffer = ""
            
    except Exception as e:
        error_message = f"API call failed: {str(e)}"
        yield f"data: {json.dumps({'error': error_message})}\n\n"
        
    # Send any remaining buffer
    if buffer:
        if in_thinking_mode:
            yield f"data: {json.dumps({'thinking': buffer})}\n\n"
        elif in_code_block and html_code_block_started:
            yield f"data: {json.dumps({'content': buffer})}\n\n"
        elif in_html_mode or buffer.strip().startswith("<"):
            yield f"data: {json.dumps({'content': buffer})}\n\n"
        else:
            yield f"data: {json.dumps({'description': buffer})}\n\n"

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/create')
def create():
    html = session.get('html', DEFAULT_HTML)
    return render_template('editor.html', html=html)

@app.route('/api/ask-ai', methods=['POST'])
def ask_ai():
    data = request.get_json()
    prompt = data.get('prompt')
    html = data.get('html')
    previous_prompt = data.get('previousPrompt')
    
    if not prompt:
        return jsonify({"ok": False, "message": "Missing prompt"}), 400
    
    # If html is equal to DEFAULT_HTML, don't pass it to the API
    if html == DEFAULT_HTML:
        html = None
    
    def generate():
        return stream_response(prompt, html, previous_prompt)
    
    return Response(generate(), mimetype='text/event-stream')

@app.route('/api/deploy', methods=['POST'])
def deploy():
    data = request.get_json()
    html = data.get('html')
    title = data.get('title', 'My Website')
    
    if not html:
        return jsonify({"ok": False, "message": "Missing HTML content"}), 400
    
    # Generate a site ID
    site_id = generate_site_id()
    
    # Add footer tag
    tagged_html = html.replace('</body>', f"{get_tag(site_id)}</body>")
    
    # Create a directory for this site
    site_dir = os.path.join('static', 'sites', site_id)
    os.makedirs(site_dir, exist_ok=True)
    
    # Save the HTML file
    with open(os.path.join(site_dir, 'index.html'), 'w') as f:
        f.write(tagged_html)
    
    # Save metadata
    metadata = {
        "title": title,
        "created": datetime.now().isoformat(),
        "id": site_id
    }
    
    with open(os.path.join(site_dir, 'metadata.json'), 'w') as f:
        json.dump(metadata, f)
    
    return jsonify({"ok": True, "site_id": site_id, "url": f"/site/{site_id}"})

@app.route('/site/<site_id>')
def view_site(site_id):
    """Render a deployed site"""
    site_path = os.path.join('static', 'sites', site_id, 'index.html')
    
    if not os.path.exists(site_path):
        return "Site not found", 404
    
    with open(site_path, 'r') as f:
        html_content = f.read()
    
    return html_content

@app.route('/remix/<site_id>')
def remix_site(site_id):
    """Load a site for remixing"""
    site_path = os.path.join('static', 'sites', site_id, 'index.html')
    
    if not os.path.exists(site_path):
        return "Site not found", 404
    
    with open(site_path, 'r') as f:
        html_content = f.read()
    
    # Remove the footer tag
    html_content = html_content.replace(get_tag(site_id), '')
    
    # Store in session
    session['html'] = html_content
    
    return redirect(url_for('create'))

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs(os.path.join('static', 'sites'), exist_ok=True)
    
    # Run the app
    app.run(debug=True, port=int(os.getenv('PORT', 5000)))