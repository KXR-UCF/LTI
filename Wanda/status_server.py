from flask import Flask, render_template_string, Response
import psutil
import time
import json
import os
import socket


hostname = socket.gethostname()

app = Flask(__name__)

MAIN_PAGE = f'''
<!DOCTYPE html>
<html>
<head>
    <title id="title">{hostname} Pi Status</title>
    <style>
        body {{
            max-width: 800px;
            margin: 0 auto;
            background: #f5f5f5;
        }}
        .status-card {{
            background: white;
            padding: 20px;
            margin: 10px 0;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .metric {{
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #eee;
        }}
        .label {{
            font-weight: bold;
            color: #555;
        }}
        .value {{
            color: #007bff;
            font-family: monospace;
        }}
        h1 {{
            color: #333;
            text-align: center;
        }}
    </style>
</head>
<body>
    <h1>{hostname} Status Dashboard</h1>
    
    <div class="status-card">
        <h2>System Resources</h2>
        <div class="metric">
            <span class="label">CPU Usage:</span>
            <span class="value" id="cpu">--</span>
        </div>
        <div class="metric">
            <span class="label">Memory Usage:</span>
            <span class="value" id="memory">--</span>
        </div>
        <div class="metric">
            <span class="label">Disk Usage:</span>
            <span class="value" id="disk">--</span>
        </div>
        <div class="metric">
            <span class="label">CPU Temperature:</span>
            <span class="value" id="temp">--</span>
        </div>
    </div>
    
    <div class="status-card">
        <h2>Network</h2>
        <div class="metric">
            <span class="label">Bytes Sent:</span>
            <span class="value" id="net_sent">--</span>
        </div>
        <div class="metric">
            <span class="label">Bytes Received:</span>
            <span class="value" id="net_recv">--</span>
        </div>
    </div>

    <script>
        const eventSource = new EventSource('/stream');
        
        eventSource.onmessage = function(e) {{
            const data = JSON.parse(e.data);
            document.getElementById('cpu').textContent = data.cpu + '%';
            document.getElementById('memory').textContent = data.memory + '%';
            document.getElementById('disk').textContent = data.disk + '%';
            document.getElementById('temp').textContent = data.temp + '°C';
            document.getElementById('net_sent').textContent = data.net_sent;
            document.getElementById('net_recv').textContent = data.net_recv;
        }};
        
        eventSource.onerror = function() {{
            console.log('Connection error, retrying...');
        }};
    </script>
</body>
</html>
'''

def get_cpu_temp():
    try:
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            temp = float(f.read()) / 1000.0
            return round(temp, 1)
    except:
        return 0.0

def format_bytes(bytes):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes < 1024.0:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024.0

def get_status():
    cpu = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    temp = get_cpu_temp()
    net = psutil.net_io_counters()
    
    return {
        'cpu': round(cpu, 1),
        'memory': round(memory, 1),
        'disk': round(disk, 1),
        'temp': temp,
        'net_sent': format_bytes(net.bytes_sent),
        'net_recv': format_bytes(net.bytes_recv)
    }

@app.route('/')
def index():
    return render_template_string(MAIN_PAGE)

@app.route('/stream')
def stream():
    def generate():
        while True:
            data = get_status()
            yield f"data: {json.dumps(data)}\n\n"
            time.sleep(1)
    
    return Response(generate(), mimetype='text/event-stream')



SOCKET_VIEWER_PAGE = f'''
<!DOCTYPE html>
<html>
<head>
    <title>{hostname} Socket Status</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 50px auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .nav {{
            text-align: center;
            margin: 20px 0;
        }}
        .nav a {{
            margin: 0 10px;
            padding: 10px 20px;
            background: #007bff;
            color: white;
            text-decoration: none;
            border-radius: 5px;
        }}
        .nav a:hover {{
            background: #0056b3;
        }}
        h1 {{
            color: #333;
            text-align: center;
        }}
        .file-info {{
            background: white;
            padding: 15px;
            margin: 10px 0;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .file-content {{
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 20px;
            margin: 10px 0;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            font-family: 'Courier New', monospace;
            font-size: 14px;
            white-space: pre-wrap;
            word-wrap: break-word;
            max-height: 600px;
            overflow-y: auto;
        }}
        .controls {{
            text-align: center;
            margin: 20px 0;
        }}
        .controls button {{
            padding: 10px 20px;
            background: #28a745;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
        }}
        .controls button:hover {{
            background: #218838;
        }}
        .controls label {{
            margin-right: 10px;
            font-weight: bold;
        }}
        .controls input[type="checkbox"] {{
            margin-left: 5px;
            width: 20px;
            height: 20px;
            vertical-align: middle;
        }}
    </style>
</head>
<body>
    <h1>{hostname} Socket Status</h1>
    
    <div class="nav">
        <a href="/">Status</a>
        <a href="/file">View File</a>
    </div>
    
    <div class="file-info">
        <strong>File:</strong> {{ filename }}<br>
        <strong>Last modified:</strong> <span id="last-modified">{{ modified }}</span><br>
        <strong>Size:</strong> {{ size }}
    </div>
    
    <div class="controls">
        <label>
            Auto-refresh:
            <input type="checkbox" id="auto-refresh" checked>
        </label>
        <button onclick="refreshContent()">Refresh Now</button>
    </div>
    
    <div class="file-content" id="content">{{ content }}</div>

    <script>
        let autoRefresh = true;
        
        document.getElementById('auto-refresh').addEventListener('change', function(e) {{
            autoRefresh = e.target.checked;
        }});
        
        function refreshContent() {{
            fetch('/file/content')
                .then(response => response.json())
                .then(data => {{
                    document.getElementById('content').textContent = data.content;
                    document.getElementById('last-modified').textContent = data.modified;
                }})
                .catch(error => console.error('Error:', error));
        }}
        
        // Auto-refresh every 3 seconds if enabled
        setInterval(() => {{
            if (autoRefresh) {{
                refreshContent();
            }}
        }}, 3000);
    </script>
</body>
</html>
'''

SOCKET_STATUS_FILE = '/home/'

@app.route('/file')
def file_viewer():
    try:
        with open(SOCKET_VIEWER_PAGE, 'r') as f:
            content = f.read()
        
        # Get file stats
        stats = os.stat(SOCKET_VIEWER_PAGE)
        modified = time.ctime(stats.st_mtime)
        size = format_bytes(stats.st_size)
               
        return render_template_string(
            SOCKET_VIEWER_PAGE,
            filename=FILE_TO_DISPLAY,
            content=content,
            modified=modified,
            size=size
        )
    except Exception as e:
        return f"Error reading file: {str(e)}", 500

@app.route('/file/content')
def file_content():
    try:
        with open(FILE_TO_DISPLAY, 'r') as f:
            content = f.read()
        
        stats = os.stat(FILE_TO_DISPLAY)
        modified = time.ctime(stats.st_mtime)
        
        # Limit content size
        if len(content) > 50000:
            content = content[-50000:] + "\n\n[... showing last 50KB ...]"
        
        return json.dumps({
            'content': content,
            'modified': modified
        })
    except Exception as e:
        return json.dumps({'error': str(e)}), 500






if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)