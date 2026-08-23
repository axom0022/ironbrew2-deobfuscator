import os
import sys
import io
import re
import importlib
from flask import Flask, request, render_template_string, jsonify, send_file

from utils import asttools as parser
from utils.codec import instructionset, instructioncategories
from modules.luaengine.detect import detect, execute

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lua Deobfuscator</title>
    <style>
        :root {
            --bg: #f4f6f9;
            --card: #ffffff;
            --text: #1e293b;
            --border: #e2e8f0;
            --accent: #3b82f6;
            --accent-hover: #2563eb;
            --input-bg: #f8fafc;
            --shadow: 0 10px 25px -5px rgba(0,0,0,0.1);
            --radius: 12px;
            --font: 'Segoe UI', system-ui, sans-serif;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background: var(--bg);
            color: var(--text);
            font-family: var(--font);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
            transition: background 0.3s, color 0.3s;
        }
        .container {
            max-width: 1000px;
            width: 100%;
            background: var(--card);
            border-radius: var(--radius);
            box-shadow: var(--shadow);
            padding: 30px;
            transition: background 0.3s, box-shadow 0.3s;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 25px;
            flex-wrap: wrap;
            gap: 15px;
        }
        .header h1 {
            font-size: 28px;
            font-weight: 700;
            color: var(--text);
        }
        .theme-selector {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .theme-selector label { font-weight: 500; font-size: 14px; opacity: 0.8; }
        .theme-selector select {
            padding: 8px 14px;
            border-radius: 8px;
            border: 1px solid var(--border);
            background: var(--input-bg);
            color: var(--text);
            font-size: 14px;
            cursor: pointer;
            outline: none;
            transition: border 0.2s;
        }
        .theme-selector select:focus { border-color: var(--accent); }
        .section { margin-bottom: 25px; }
        .section-title {
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .section-title .badge {
            font-size: 12px;
            background: var(--accent);
            color: #fff;
            padding: 2px 10px;
            border-radius: 20px;
            font-weight: 500;
        }
        .input-area { display: flex; flex-direction: column; gap: 12px; }
        .file-upload {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
        }
        .file-upload label {
            padding: 10px 20px;
            background: var(--accent);
            color: #fff;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 500;
            font-size: 14px;
            transition: background 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        .file-upload label:hover { background: var(--accent-hover); }
        .file-upload input[type="file"] { display: none; }
        .file-upload .file-name {
            font-size: 14px;
            color: var(--text);
            opacity: 0.7;
            align-self: center;
        }
        textarea {
            width: 100%;
            min-height: 200px;
            padding: 14px;
            border: 1px solid var(--border);
            border-radius: 8px;
            background: var(--input-bg);
            color: var(--text);
            font-family: 'Fira Code', 'Consolas', monospace;
            font-size: 14px;
            line-height: 1.6;
            resize: vertical;
            transition: border 0.2s, background 0.3s, color 0.3s;
            outline: none;
        }
        textarea:focus {
            border-color: var(--accent);
            box-shadow: 0 0 0 3px rgba(59,130,246,0.15);
        }
        .action-row {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            margin-top: 10px;
        }
        .btn {
            padding: 10px 24px;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        .btn-primary {
            background: var(--accent);
            color: #fff;
        }
        .btn-primary:hover {
            background: var(--accent-hover);
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(59,130,246,0.3);
        }
        .btn-secondary {
            background: var(--border);
            color: var(--text);
        }
        .btn-secondary:hover { opacity: 0.8; transform: translateY(-1px); }
        .btn-success {
            background: #10b981;
            color: #fff;
        }
        .btn-success:hover {
            background: #059669;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(16,185,129,0.3);
        }
        .output-area { display: flex; flex-direction: column; gap: 12px; }
        .output-actions { display: flex; gap: 10px; flex-wrap: wrap; }
        .output-actions .btn { padding: 8px 18px; font-size: 13px; }
        .toast {
            position: fixed;
            bottom: 30px;
            left: 50%;
            transform: translateX(-50%);
            background: #1e293b;
            color: #f8fafc;
            padding: 12px 24px;
            border-radius: 40px;
            font-size: 14px;
            font-weight: 500;
            box-shadow: 0 8px 20px rgba(0,0,0,0.2);
            opacity: 0;
            transition: opacity 0.3s;
            pointer-events: none;
            z-index: 999;
        }
        .toast.show { opacity: 1; }
        body.theme-dark {
            --bg: #0f172a;
            --card: #1e293b;
            --text: #e2e8f0;
            --border: #334155;
            --input-bg: #0f172a;
            --shadow: 0 10px 25px -5px rgba(0,0,0,0.5);
            --accent: #60a5fa;
            --accent-hover: #3b82f6;
        }
        body.theme-ocean {
            --bg: #e0f2fe;
            --card: #ffffff;
            --text: #0c4a6e;
            --border: #bae6fd;
            --input-bg: #f0f9ff;
            --accent: #0284c7;
            --accent-hover: #0369a1;
        }
        body.theme-sunset {
            --bg: #fef3c7;
            --card: #fffbeb;
            --text: #78350f;
            --border: #fde68a;
            --input-bg: #fffbeb;
            --accent: #f59e0b;
            --accent-hover: #d97706;
        }
        body.theme-forest {
            --bg: #ecfdf5;
            --card: #ffffff;
            --text: #064e3b;
            --border: #a7f3d0;
            --input-bg: #f0fdf4;
            --accent: #10b981;
            --accent-hover: #059669;
        }
        body.theme-midnight {
            --bg: #1e1b4b;
            --card: #312e81;
            --text: #e0e7ff;
            --border: #4f46e5;
            --input-bg: #1e1b4b;
            --accent: #818cf8;
            --accent-hover: #6366f1;
        }
        body.theme-rose {
            --bg: #fce4ec;
            --card: #ffffff;
            --text: #880e4f;
            --border: #f8bbd0;
            --input-bg: #fce4ec;
            --accent: #e91e63;
            --accent-hover: #c2185b;
        }
        @media (max-width: 640px) {
            .container { padding: 20px; }
            .header { flex-direction: column; align-items: stretch; }
            .theme-selector { justify-content: flex-start; }
            textarea { min-height: 150px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Lua Deobfuscator</h1>
            <div class="theme-selector">
                <label for="theme">Theme</label>
                <select id="theme">
                    <option value="default">Default</option>
                    <option value="dark">Dark</option>
                    <option value="ocean">Ocean</option>
                    <option value="sunset">Sunset</option>
                    <option value="forest">Forest</option>
                    <option value="midnight">Midnight</option>
                    <option value="rose">Rose</option>
                </select>
            </div>
        </div>
        <div class="section">
            <div class="section-title">
                <span>📥 Input</span>
                <span class="badge">Lua source</span>
            </div>
            <div class="input-area">
                <div class="file-upload">
                    <label for="fileInput">📁 Upload File</label>
                    <input type="file" id="fileInput" accept=".lua,.luac,.txt">
                    <span class="file-name" id="fileName">No file selected</span>
                </div>
                <textarea id="inputCode" placeholder="Paste your obfuscated Lua code here..."></textarea>
                <div class="action-row">
                    <button class="btn btn-primary" id="deobfuscateBtn">⚡ Deobfuscate</button>
                    <button class="btn btn-secondary" id="clearInputBtn">🗑️ Clear</button>
                </div>
            </div>
        </div>
        <div class="section">
            <div class="section-title">
                <span>📤 Output</span>
                <span class="badge">Deobfuscated</span>
            </div>
            <div class="output-area">
                <textarea id="outputCode" readonly placeholder="Deobfuscated code will appear here..."></textarea>
                <div class="output-actions">
                    <button class="btn btn-success" id="copyBtn">📋 Copy</button>
                    <button class="btn btn-primary" id="saveBtn">💾 Save As File</button>
                    <button class="btn btn-secondary" id="clearOutputBtn">🗑️ Clear</button>
                </div>
            </div>
        </div>
    </div>
    <div id="toast" class="toast"></div>
    <script>
        (function(){
            const themeSelect = document.getElementById('theme');
            const body = document.body;
            const inputCode = document.getElementById('inputCode');
            const outputCode = document.getElementById('outputCode');
            const fileInput = document.getElementById('fileInput');
            const fileName = document.getElementById('fileName');
            const deobfuscateBtn = document.getElementById('deobfuscateBtn');
            const clearInputBtn = document.getElementById('clearInputBtn');
            const copyBtn = document.getElementById('copyBtn');
            const saveBtn = document.getElementById('saveBtn');
            const clearOutputBtn = document.getElementById('clearOutputBtn');
            const toast = document.getElementById('toast');
            let toastTimer = null;
            function showToast(msg) {
                toast.textContent = msg;
                toast.classList.add('show');
                clearTimeout(toastTimer);
                toastTimer = setTimeout(() => toast.classList.remove('show'), 3000);
            }
            function applyTheme(theme) {
                body.className = '';
                if (theme !== 'default') body.classList.add('theme-' + theme);
                localStorage.setItem('theme', theme);
            }
            themeSelect.addEventListener('change', function(){ applyTheme(this.value); });
            const savedTheme = localStorage.getItem('theme') || 'default';
            themeSelect.value = savedTheme;
            applyTheme(savedTheme);
            fileInput.addEventListener('change', function(e) {
                const file = e.target.files[0];
                if (!file) { fileName.textContent = 'No file selected'; return; }
                fileName.textContent = file.name;
                const reader = new FileReader();
                reader.onload = function(ev) {
                    inputCode.value = ev.target.result;
                    showToast('Loaded ' + file.name);
                };
                reader.onerror = function() { showToast('Error reading file'); };
                reader.readAsText(file);
            });
            clearInputBtn.addEventListener('click', function() {
                inputCode.value = '';
                fileInput.value = '';
                fileName.textContent = 'No file selected';
            });
            clearOutputBtn.addEventListener('click', function() {
                outputCode.value = '';
            });
            copyBtn.addEventListener('click', function() {
                if (!outputCode.value) { showToast('Nothing to copy'); return; }
                navigator.clipboard.writeText(outputCode.value).then(() => {
                    showToast('Copied to clipboard!');
                }).catch(() => {
                    outputCode.select();
                    document.execCommand('copy');
                    showToast('Copied!');
                });
            });
            saveBtn.addEventListener('click', function() {
                if (!outputCode.value) { showToast('No output to save'); return; }
                const blob = new Blob([outputCode.value], { type: 'text/plain' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'deobfuscated.lua';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
                showToast('File saved!');
            });
            deobfuscateBtn.addEventListener('click', function() {
                const code = inputCode.value.trim();
                if (!code) { showToast('Please enter some Lua code'); return; }
                showToast('Deobfuscating...');
                fetch('/deobfuscate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: 'code=' + encodeURIComponent(code)
                })
                .then(res => res.json())
                .then(data => {
                    if (data.error) {
                        showToast('Error: ' + data.error);
                    } else {
                        outputCode.value = data.result;
                        showToast('Deobfuscation complete!');
                    }
                })
                .catch(err => {
                    showToast('Network error: ' + err.message);
                });
            });
            document.addEventListener('keydown', function(e) {
                if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                    deobfuscateBtn.click();
                }
            });
        })();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/deobfuscate', methods=['POST'])
def deobfuscate():
    code = request.form.get('code', '')
    if not code:
        return jsonify({'error': 'No code provided'}), 400
    try:
        syntaxtree = parser.loadast(code)
        syntaxtree = parser.refineast(syntaxtree, {"renamevariables": True, "format": True})
        if detect(code):
            result = execute(syntaxtree)
        else:
            raise RuntimeError("No suitable engine found")
        return jsonify({'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
