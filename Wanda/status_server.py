from flask import Flask, render_template_string, Response, jsonify, abort
import psutil 
import time
import json
import os
import socket
import subprocess

hostname = socket.gethostname().upper()
app = Flask(__name__)

BASE_DIR = '/home/lti/Production'
SERVICES = ['controller_socket', 'worker_socket', 'dataingestion', 'questdb']

CSS = '''
<style>
    body { font: 14px sans-serif; max-width: 700px; margin: 2% auto; padding: 0 15px; background: #eee; }
    .card { background: #fff; padding: 15px; margin: 10px 0; border: 1px solid #ddd; border-radius: 4px; }
    .row { display: flex; justify-content: space-between; border-bottom: 1px solid #eee; padding: 4px 0; }
    .v { font-family: monospace; color: blue; }
    pre { background: #222; color: #fff; padding: 10px; overflow-x: auto; white-space: pre-wrap; }
    nav { margin-bottom: 20px; display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .btn { text-decoration: none; background: #007bff; color: #fff; padding: 10px; text-align: center; border-radius: 3px; border: none; }
    .btn:hover { filter: brightness(0.8); }
</style>
'''

@app.route('/')
def index():
    return render_template_string(CSS + f'''
    <h1>{hostname} Dashboard</h1>
    
    <div class="card">
        <h3>Service Logs</h3>
        <nav>
            <a class="btn" href="/file/socket.out">Socket Log</a>
            <a class="btn" href="/file/data.out">Data Log</a>
        </nav>
    </div>

    <div class="card">
        <h3>Services</h3>
        <div id="svc">Loading...</div>
    </div>

    <div class="card">
        <div class="row"><span>CPU</span><span class="v" id="cpu">--</span></div>
        <div class="row"><span>RAM</span><span class="v" id="memory">--</span></div>
        <div class="row"><span>Temp</span><span class="v" id="temp">--</span></div>
        <div class="row"><span>Disk</span><span class="v" id="disk">--</span></div>
    </div>

    <script>
        const s = new EventSource('/stream');
        s.onmessage = e => {{
            const d = JSON.parse(e.data);
            document.getElementById('cpu').textContent = d.cpu + '%';
            document.getElementById('memory').textContent = d.memory + '%';
            document.getElementById('temp').textContent = d.temp + '°C';
            document.getElementById('disk').textContent = d.disk + '%';
        }};

        async function loadSvc() {{
            const r = await fetch('/services');
            const d = await r.json();
            document.getElementById('svc').innerHTML = d.map(s => `
                <div class="row" style="align-items:center; padding:8px 0; flex-wrap:wrap">
                    <div style="flex:1; min-width:120px"><b>${{s.name}}</b> <br> <small style="color:${{s.active=='active'?'green':'red'}}">${{s.active}}</small> | <small>${{s.enabled}}</small></div>
                    <div style="display:flex; gap:4px">
                        ${{s.active !== 'active' ? `<button onclick="sc('${{s.name}}','start')" class="btn">Start</button>` : ''}}
                        ${{s.active === 'active' ? `<button onclick="sc('${{s.name}}','stop')" class="btn" style="background:#dc3545">Stop</button>` : ''}}
                        <button onclick="sc('${{s.name}}','restart')" class="btn" style="background:#ffc107; color:#000">Reset</button>
                        ${{s.enabled !== 'enabled' ? `<button onclick="sc('${{s.name}}','enable')" class="btn" style="background:#17a2b8">Enable</button>` : ''}}
                        ${{s.enabled === 'enabled' ? `<button onclick="sc('${{s.name}}','disable')" class="btn" style="background:#6c757d">Disable</button>` : ''}}
                    </div>
                </div>
            `).join('');
        }}
        async function sc(n, a) {{
            if(!confirm(a.toUpperCase() + ' ' + n + '?')) return;
            await fetch('/control/'+n+'/'+a, {{method:'POST'}});
            setTimeout(loadSvc, 1000);
        }}
        loadSvc();
        setInterval(loadSvc, 5000);
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
                'temp': t,
                'disk': psutil.disk_usage('/').percent
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
        <b>Updated:</b> <span id="update-time"></span>
    </div>
    <pre id="fcontent">Loading...</pre>
    <script>
        async function up() {
            const response = await fetch('/content/{{ fn }}');
            const data = await response.json();
            document.getElementById('fcontent').textContent = data.content;
            document.getElementById('update-time').textContent = data.uTime;
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

        return jsonify({
            'content': content, 
            'uTime': time.ctime(os.path.getmtime(filepath))
        })
    
    except Exception as e:
        return jsonify({
            'content': f"Error: {str(e)}", 
            'uTime': 'N/A'
        })

@app.route('/services')
def services_status():
    res = []
    for s in SERVICES:
        try:
            p = subprocess.run(['systemctl', 'is-active', s], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            active = p.stdout.strip()
            p2 = subprocess.run(['systemctl', 'is-enabled', s], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            enabled = p2.stdout.strip()
            res.append({'name': s, 'active': active, 'enabled': enabled})
        except Exception as e:
            res.append({'name': s, 'active': 'error', 'enabled': str(e)})
    return jsonify(res)

@app.route('/control/<service>/<action>', methods=['POST'])
def service_control(service, action):
    if service not in SERVICES: return abort(400)
    if action not in ['start', 'stop', 'restart', 'enable', 'disable']: return abort(400)
    try:
        subprocess.run(['sudo', 'systemctl', action, service], check=True)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    if not os.path.exists(BASE_DIR):
        print(f"Warning: {BASE_DIR} does not exist. Creating it for testing...")
        os.makedirs(BASE_DIR, exist_ok=True)
        
    app.run(host='0.0.0.0', port=5000)
