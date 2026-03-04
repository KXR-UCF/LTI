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
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; max-width: 800px; margin: 2rem auto; padding: 0 15px; background: #f4f6f9; color: #333; }
    .card { background: #fff; padding: 20px; margin-bottom: 20px; border: 1px solid #e1e4e8; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    h1 { margin-bottom: 1.5rem; color: #2c3e50; }
    h3 { margin-top: 0; border-bottom: 2px solid #f0f0f0; padding-bottom: 10px; margin-bottom: 15px; color: #555; }
    
    /* Stats Grid */
    .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 15px; }
    .stat-item { background: #f8f9fa; padding: 15px; border-radius: 6px; text-align: center; border: 1px solid #eee; }
    .stat-label { display: block; font-size: 0.85rem; color: #666; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 0.5px; }
    .stat-value { font-size: 1.5rem; font-weight: bold; color: #007bff; font-family: monospace; }
    
    /* Services */
    .svc-row { display: flex; align-items: center; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid #eee; flex-wrap: wrap; gap: 10px; }
    .svc-row:last-child { border-bottom: none; }
    .svc-info { flex: 1; min-width: 150px; }
    .svc-name { font-weight: 600; font-size: 1.1rem; display: block; margin-bottom: 4px; }
    .svc-status { font-size: 0.75rem; display: inline-block; padding: 2px 8px; border-radius: 12px; font-weight: 600; text-transform: uppercase; }
    .status-active { background: #d4edda; color: #155724; }
    .status-inactive { background: #f8d7da; color: #721c24; }
    .status-enabled { color: #666; font-size: 0.85rem; margin-left: 8px; }
    
    /* Buttons */
    .btn-group { display: flex; gap: 5px; }
    .btn { text-decoration: none; padding: 6px 12px; text-align: center; border-radius: 4px; border: none; cursor: pointer; font-size: 0.9rem; font-weight: 500; transition: all 0.2s; color: white; display: inline-block; min-width: 80px; }
    .btn:hover { opacity: 0.9; transform: translateY(-1px); }
    .btn:active { transform: translateY(0); }
    
    .btn-primary { background: #007bff; width: 100%; }
    .btn-start { background: #28a745; }
    .btn-stop { background: #dc3545; }
    .btn-restart { background: #ffc107; color: #212529; }
    .btn-enable { background: #6610f2; }
    .btn-disable { background: #343a40; }
    
    nav { display: flex; gap: 10px; margin-bottom: 0; }
    pre { background: #ffffff; color: #000000; padding: 15px; border: 1px solid #999; border-radius: 6px; overflow-x: auto; font-size: 16px; white-space: pre-wrap; }
</style>
'''

@app.route('/')
def index():
    log_btns = '<span style="color:#888">No .log files found</span>'
    if os.path.exists(BASE_DIR):
        files = sorted([f for f in os.listdir(BASE_DIR) if f.endswith('.log') and os.path.isfile(os.path.join(BASE_DIR, f))])
        if files:
            log_btns = ''.join([f'<a class="btn btn-primary" href="/file/{f}">{f}</a>' for f in files])

    return render_template_string(CSS + f'''
    <h1>{hostname} Dashboard</h1>
    
    <div class="card">
        <h3>System Status</h3>
        <div class="stats-grid">
            <div class="stat-item">
                <span class="stat-label">CPU</span>
                <span class="stat-value" id="cpu">--</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">RAM</span>
                <span class="stat-value" id="memory">--</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Temp</span>
                <span class="stat-value" id="temp">--</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Disk</span>
                <span class="stat-value" id="disk">--</span>
            </div>
        </div>
    </div>

    <div class="card">
        <h3>Services</h3>
        <div id="svc">Loading...</div>
    </div>

    <div class="card">
        <h3>Logs</h3>
        <nav>
            {log_btns}
        </nav>
    </div>

    <script>
        const s = new EventSource('/stream');
        s.onmessage = e => {{
            const d = JSON.parse(e.data);
            const cpu = document.getElementById('cpu');
            cpu.textContent = d.cpu + '%';
            cpu.style.color = d.cpu > 80 ? '#dc3545' : '#007bff';
            
            const mem = document.getElementById('memory');
            mem.textContent = d.memory + '%';
            mem.style.color = d.memory > 80 ? '#dc3545' : '#007bff';

            const temp = document.getElementById('temp');
            temp.textContent = d.temp + '°C';
            temp.style.color = d.temp > 70 ? '#dc3545' : '#007bff';

            document.getElementById('disk').textContent = d.disk + '%';
        }};

        async function loadSvc() {{
            const r = await fetch('/services');
            const d = await r.json();
            document.getElementById('svc').innerHTML = d.map(s => `
                <div class="svc-row">
                    <div class="svc-info">
                        <span class="svc-name">${{s.name}}</span>
                        <span class="svc-status ${{s.active=='active'?'status-active':'status-inactive'}}">${{s.active}}</span>
                        <span class="status-enabled">${{s.enabled}}</span>
                    </div>
                    <div class="btn-group">
                        ${{s.active !== 'active' ? `<button onclick="sc('${{s.name}}','start')" class="btn btn-start">Start</button>` : ''}}
                        ${{s.active === 'active' ? `<button onclick="sc('${{s.name}}','stop')" class="btn btn-stop">Stop</button>` : ''}}
                        <button onclick="sc('${{s.name}}','restart')" class="btn btn-restart">Restart</button>
                        ${{s.enabled !== 'enabled' ? `<button onclick="sc('${{s.name}}','enable')" class="btn btn-enable">Enable</button>` : ''}}
                        ${{s.enabled === 'enabled' ? `<button onclick="sc('${{s.name}}','disable')" class="btn btn-disable">Disable</button>` : ''}}
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
    if '..' in filename or filename.startswith('/'):
        return abort(400, description="Invalid filename")

    filepath = os.path.join(BASE_DIR, filename)
    
    if not os.path.exists(filepath):
        return abort(404, description=f"File {filename} not found in {BASE_DIR}")
        
    return render_template_string(CSS + '''
    <div style="margin-bottom:15px"><a href="/" class="btn btn-primary" style="display:inline-block; width:auto">Back to Dashboard</a></div>
    <div class="card">
        <b>File:</b> {{ fn }} <br>
        <b>Updated:</b> <span id="update-time"></span>
    </div>
    <pre id="fcontent">Loading...</pre>
    <script>
        async function up() {
            const response = await fetch('/content/{{ fn }}');
            const data = await response.json();
            const el = document.getElementById('fcontent');
            const isBottom = el.scrollHeight - el.scrollTop === el.clientHeight;
            el.textContent = data.content;
            document.getElementById('update-time').textContent = data.uTime;
            if (isBottom || el.scrollTop === 0) el.scrollTop = el.scrollHeight;
        }
        setInterval(up, 3000); up();
    </script>
    ''', fn=filename)

@app.route('/content/<filename>')
def file_content(filename):
    if '..' in filename or filename.startswith('/'):
        return abort(400)

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
