from flask import Flask, render_template_string, Response, jsonify, abort, request
import psutil 
import time
import json
import os
import socket
import subprocess

hostname = socket.gethostname().upper()
app = Flask(__name__)

BASE_DIR = '/home/lti/Production'
SERVICES = ['controller_socket', 'worker_socket', 'dataingestion', 'questdb', 'status_server']

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
    cfg_btns = '<span style="color:#888">No config files found</span>'
    
    if os.path.exists(BASE_DIR):
        logs = []
        cfgs = []
        for root, dirs, files in os.walk(BASE_DIR):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for f in files:
                rel_path = os.path.relpath(os.path.join(root, f), BASE_DIR).replace('\\', '/')
                if f.endswith(('.log', '.out', '.err', '.txt')):
                    logs.append(rel_path)
                elif f.endswith(('.yaml', '.yml', '.json', '.conf', '.ini')):
                    cfgs.append(rel_path)
        
        logs.sort()
        cfgs.sort()

        if logs:
            log_btns = ''.join([f'<a class="btn btn-primary" href="/file/{f}">{f}</a>' for f in logs])
            
        if cfgs:
            cfg_btns = ''.join([f'<a class="btn btn-primary" href="/file/{f}">{f}</a>' for f in cfgs])

    return render_template_string(CSS + f'''
    <h1>{hostname} Dashboard</h1>
    
    <div class="card">
        <h3>System Control</h3>
        <div class="btn-group">
            <button onclick="sys('reboot')" class="btn btn-restart" style="width:100%">Reboot</button>
            <button onclick="sys('shutdown')" class="btn btn-stop" style="width:100%">Shutdown</button>
        </div>
    </div>

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
            <div class="stat-item">
                <span class="stat-label">Uptime</span>
                <span class="stat-value" id="uptime" style="font-size: 1.2rem">--</span>
            </div>
        </div>
    </div>


    <div class="card">
        <h3>Services</h3>
        <div id="svc">Loading...</div>
    </div>

    <div class="card">
        <h3>Configuration</h3>
        <nav>
            {cfg_btns}
        </nav>
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
            document.getElementById('uptime').textContent = d.uptime;
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
        async function sys(a) {{
            if(!confirm('Are you sure you want to ' + a.toUpperCase() + ' the system?')) return;
            await fetch('/system/'+a, {{method:'POST'}});
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
            
            uptime_sec = time.time() - psutil.boot_time()
            m, s = divmod(uptime_sec, 60)
            h, m = divmod(m, 60)
            uptime_str = "%d:%02d:%02d" % (h, m, s)
            if h > 24:
                d, h = divmod(h, 24)
                uptime_str = "%dd %dh" % (d, h)

            data = {
                'cpu': psutil.cpu_percent(), 
                'memory': psutil.virtual_memory().percent, 
                'temp': t,
                'disk': psutil.disk_usage('/').percent,
                'uptime': uptime_str
            }
            yield f"data: {json.dumps(data)}\n\n"
            time.sleep(2)
    return Response(gen(), mimetype='text/event-stream')


@app.route('/file/<path:filename>')
def file_viewer(filename):
    allowed = ('.log', '.out', '.err', '.txt', '.yaml', '.yml', '.json', '.conf', '.ini')
    if not filename.endswith(allowed) or '..' in filename or filename.startswith('/'):
        return abort(400, description="Invalid filename")

    filepath = os.path.join(BASE_DIR, filename)
    
    if not os.path.exists(filepath):
        return abort(404, description=f"File {filename} not found in {BASE_DIR}")
        
    is_config = filename.endswith(('.yaml', '.yml', '.json', '.conf', '.ini'))

    if is_config:
        return render_template_string(CSS + '''
        <div style="margin-bottom:15px"><a href="/" class="btn btn-primary" style="display:inline-block; width:auto">Back to Dashboard</a></div>
        <div class="card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div><b>Editing Config:</b> {{ fn }}</div>
                <button onclick="saveFile()" class="btn btn-start" style="width:auto">Save Changes</button>
            </div>
        </div>
        <textarea id="fcontent" style="width:100%; height:600px; font-family:monospace; padding:10px; border:1px solid #ddd; border-radius:4px; resize:vertical; background:#f8f9fa; color:#333"></textarea>
        <script>
            async function load() {
                const response = await fetch('/content/{{ fn }}');
                const data = await response.json();
                document.getElementById('fcontent').value = data.content;
            }
            async function saveFile() {
                const content = document.getElementById('fcontent').value;
                if(!confirm('Save changes to ' + '{{ fn }}' + '?')) return;
                const resp = await fetch('/save/{{ fn }}', {
                    method:'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({content: content})
                });
                const res = await resp.json();
                if(res.status === 'ok') alert('Saved!');
                else alert('Error: ' + res.message);
            }
            load();
        </script>
        ''', fn=filename)
    else:
        return render_template_string(CSS + '''
        <div style="margin-bottom:15px"><a href="/" class="btn btn-primary" style="display:inline-block; width:auto">Back to Dashboard</a></div>
        <div class="card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div><b>File:</b> {{ fn }} <br><b>Updated:</b> <span id="update-time"></span></div>
                <button onclick="clearLog()" class="btn btn-stop" style="width:auto">Clear Log</button>
            </div>
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
            async function clearLog() {
                if(!confirm('Clear all content in ' + '{{ fn }}' + '?')) return;
                await fetch('/clear/{{ fn }}', {method:'POST'});
                up();
            }
            setInterval(up, 3000); up();
        </script>
        ''', fn=filename)

@app.route('/content/<path:filename>')
def file_content(filename):
    allowed = ('.log', '.out', '.err', '.txt', '.yaml', '.yml', '.json', '.conf', '.ini')
    if not filename.endswith(allowed) or '..' in filename or filename.startswith('/'):
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

@app.route('/save/<path:filename>', methods=['POST'])
def save_file(filename):
    if '..' in filename or filename.startswith('/'):
        return abort(400)
    if not filename.endswith(('.yaml', '.yml', '.json', '.conf', '.ini')):
        return abort(403)

    filepath = os.path.join(BASE_DIR, filename)
    try:
        data = request.get_json()
        with open(filepath, 'w') as f:
            f.write(data['content'])
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/clear/<path:filename>', methods=['POST'])
def clear_file(filename):
    if '..' in filename or filename.startswith('/'):
        return abort(400)
    if not filename.endswith(('.log', '.out', '.err', '.txt')):
        return abort(403)

    filepath = os.path.join(BASE_DIR, filename)
    try:
        with open(filepath, 'w') as f:
            f.write("")
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

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

@app.route('/system/<action>', methods=['POST'])
def system_control(action):
    if action not in ['reboot', 'shutdown']: return abort(400)
    cmd = ['sudo', 'reboot'] if action == 'reboot' else ['sudo', 'shutdown', '-h', 'now']
    try:
        subprocess.Popen(cmd)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    if not os.path.exists(BASE_DIR):
        print(f"Warning: {BASE_DIR} does not exist. Creating it for testing...")
        os.makedirs(BASE_DIR, exist_ok=True)
        
    app.run(host='0.0.0.0', port=5000)
