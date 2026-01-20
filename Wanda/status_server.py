from flask import Flask, render_template_string, Response, jsonify, abort
import psutil 
import time
import json
import os
import socket

hostname = socket.gethostname()
app = Flask(__name__)

BASE_DIR = '/home/lti/Production'

CSS = '''
<style>
    body { font: 14px sans-serif; max-width: 700px; margin: 2% auto; padding: 0 15px; background: #eee; }
    .card { background: #fff; padding: 15px; margin: 10px 0; border: 1px solid #ddd; border-radius: 4px; }
    .row { display: flex; justify-content: space-between; border-bottom: 1px solid #eee; padding: 4px 0; }
    .v { font-family: monospace; color: blue; }
    pre { background: #222; color: #fff; padding: 10px; overflow-x: auto; white-space: pre-wrap; }
    nav { margin-bottom: 20px; display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .btn { text-decoration: none; background: #007bff; color: #fff; padding: 10px; text-align: center; border-radius: 3px; }
    .btn:hover { background: #0056b3; }
</style>
'''

@app.route('/')
def index():
    return render_template_string(CSS + f'''
    <h1>{hostname} Dashboard</h1>
    
    <div class="card">
        <h3>Process Logs</h3>
        <nav>
            <a class="btn" href="/file/socket.out">Socket Log</a>
            <a class="btn" href="/file/data.out">Data Log</a>
        </nav>
    </div>

    <div class="card">
        <div class="row"><span>CPU</span><span class="v" id="cpu">--</span></div>
        <div class="row"><span>RAM</span><span class="v" id="memory">--</span></div>
        <div class="row"><span>Temp</span><span class="v" id="temp">--</span></div>
    </div>

    <script>
        const s = new EventSource('/stream');
        s.onmessage = e => {{
            const d = JSON.parse(e.data);
            ['cpu','memory','temp'].forEach(k => document.getElementById(k).textContent = d[k] + (k=='temp'?'°C':'%'));
        }};
    </script>
    ''')


@app.route('/stream')
def stream():
    def gen():
        while True:
            t = 0.0
            try:
                with open('/sys/class/thermal/thermal_zone0/temp') as f: 
                    t = round(float(f.read())/1000, 1)
            except: 
                pass
            
            data = {
                'cpu': psutil.cpu_percent(), 
                'memory': psutil.virtual_memory().percent, 
                'temp': t
            }
            yield f"data: {json.dumps(data)}\n\n"
            time.sleep(2)
    return Response(gen(), mimetype='text/event-stream')


@app.route('/file/<filename>')
def file_viewer(filename):
    filepath = os.path.join(BASE_DIR, filename)
    
    if not os.path.exists(filepath):
        return abort(404, description=f"File {filename} not found in {BASE_DIR}")
        
    return render_template_string(CSS + '''
    <div style="margin-bottom:15px"><a href="/" class="btn" style="display:inline-block; width:auto">Back to Dashboard</a></div>
    <div class="card">
        <b>File:</b> {{ fn }} <br>
        <b>Updated:</b> <span id="m"></span>
    </div>
    <pre id="o">Loading...</pre>
    <script>
        async function up() {
            const r = await fetch('/content/{{ fn }}');
            const d = await r.json();
            document.getElementById('o').textContent = d.c;
            document.getElementById('m').textContent = d.m;
        }
        setInterval(up, 3000); up();
    </script>
    ''', fn=filename)

@app.route('/content/<filename>')
def file_content(filename):
    filepath = os.path.join(BASE_DIR, filename)
    try:
        with open(filepath, 'r') as f:
            content = f.read()[-20000:]
            if not content: content = "[Empty File]"
        return jsonify({'c': content, 'm': time.ctime(os.path.getmtime(filepath))})
    except Exception as e:
        return jsonify({'c': f'Error: {str(e)}', 'm': 'N/A'})

if __name__ == '__main__':
    if not os.path.exists(BASE_DIR):
        print(f"Warning: {BASE_DIR} does not exist. Creating it for testing...")
        os.makedirs(BASE_DIR, exist_ok=True)
        
    app.run(host='0.0.0.0', port=5000)