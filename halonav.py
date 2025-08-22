# All libraries
from flask import Flask, render_template_string, jsonify, request, Response, send_from_directory
import threading
import time
import webbrowser
import pyautogui
import cv2
import mediapipe as mp
import numpy as np
import speech_recognition as sr
import pyttsx3
import subprocess
from datetime import datetime

app = Flask(__name__)

# Global state
system_running = False
current_gesture = "none"
last_command = "none"
voice_active = False
gesture_active = False
terminal_output = []

frame_lock = threading.Lock()
current_frame = None  

# Initialize MediaPipe hands
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(
    static_image_mode=False, max_num_hands=2,
    min_detection_confidence=0.7, min_tracking_confidence=0.5
)

# Initialize speech recognition and TTS
recognizer = sr.Recognizer()
microphone = sr.Microphone()
tts_engine = pyttsx3.init()

# HTML Template 
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HoloNav Pro - Enhanced Control System</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
            overflow-x: hidden;
        }
        
        .header {
            background: rgba(0,0,0,0.3);
            padding: 20px 0;
            text-align: center;
            backdrop-filter: blur(15px);
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        
        .header h1 {
            font-size: 3rem;
            margin-bottom: 10px;
            background: linear-gradient(45deg, #00f2fe, #4facfe);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            font-weight: 700;
        }
        
        .subtitle {
            font-size: 1.2rem;
            opacity: 0.9;
            font-weight: 300;
        }
        
        .container {
            max-width: 1600px;
            margin: 20px auto;
            padding: 0 20px;
        }
        
        .control-panel {
            background: rgba(255,255,255,0.1);
            border-radius: 20px;
            padding: 30px;
            backdrop-filter: blur(15px);
            border: 1px solid rgba(255,255,255,0.2);
            text-align: center;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }
        
        .control-buttons {
            display: flex;
            gap: 20px;
            justify-content: center;
            margin-top: 20px;
        }
        
        .launch-btn {
            padding: 15px 40px;
            border: none;
            border-radius: 50px;
            font-size: 1.1rem;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 1px;
            min-width: 180px;
        }
        
        .btn-launch {
            background: linear-gradient(45deg, #00c851, #00ff41);
            color: #000;
            box-shadow: 0 8px 25px rgba(0, 200, 81, 0.4);
        }
        
        .btn-launch:hover:not(:disabled) {
            transform: translateY(-3px) scale(1.05);
            box-shadow: 0 15px 35px rgba(0, 200, 81, 0.6);
        }
        
        .btn-stop {
            background: linear-gradient(45deg, #ff4444, #cc0000);
            color: white;
            box-shadow: 0 8px 25px rgba(255, 68, 68, 0.4);
        }
        
        .btn-stop:hover:not(:disabled) {
            transform: translateY(-3px) scale(1.05);
            box-shadow: 0 15px 35px rgba(255, 68, 68, 0.6);
        }
        
        .btn-launch:disabled, .btn-stop:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }
        
        .status-dashboard {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .status-card {
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 25px;
            text-align: center;
            backdrop-filter: blur(15px);
            border: 1px solid rgba(255,255,255,0.2);
            transition: all 0.3s ease;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        
        .status-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 30px rgba(0,0,0,0.3);
        }
        
        .status-card h3 {
            font-size: 1rem;
            margin-bottom: 15px;
            opacity: 0.8;
        }
        
        .status-value {
            font-size: 1.4rem;
            font-weight: bold;
            text-transform: uppercase;
        }
        
        .status-online { color: #00ff41; }
        .status-offline { color: #ff4444; }
        .status-active { color: #4facfe; }
        
        .main-grid {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 30px;
            margin-bottom: 30px;
        }
        
        .video-section {
            background: rgba(0,0,0,0.4);
            border-radius: 20px;
            padding: 25px;
            backdrop-filter: blur(15px);
            border: 1px solid rgba(255,255,255,0.1);
        }
        
        .video-container {
            position: relative;
            margin-bottom: 20px;
        }
        
        .camera-feed {
            width: 100%;
            max-width: 640px;
            height: auto;
            border-radius: 15px;
            border: 3px solid #4facfe;
            box-shadow: 0 10px 30px rgba(79, 172, 254, 0.3);
            background: #1a1a1a;
        }
        
        .video-overlay {
            position: absolute;
            top: 10px;
            left: 10px;
            background: rgba(0,0,0,0.8);
            padding: 8px 15px;
            border-radius: 20px;
            font-size: 0.9rem;
            font-weight: bold;
        }
        
        .gesture-info {
            background: rgba(255,255,255,0.1);
            border-radius: 10px;
            padding: 15px;
            text-align: center;
            margin-top: 15px;
        }
        
        .current-gesture {
            font-size: 1.3rem;
            font-weight: bold;
            color: #4facfe;
            margin-top: 5px;
        }
        
        .terminal-section {
            background: rgba(0,0,0,0.6);
            border-radius: 20px;
            padding: 25px;
            backdrop-filter: blur(15px);
            height: fit-content;
        }
        
        .terminal-header {
            display: flex;
            align-items: center;
            margin-bottom: 15px;
            font-weight: bold;
        }
        
        .terminal {
            background: #000;
            border-radius: 10px;
            padding: 20px;
            font-family: 'Consolas', 'Monaco', monospace;
            height: 400px;
            overflow-y: auto;
            font-size: 0.9rem;
            line-height: 1.6;
            border: 1px solid #333;
        }
        
        .terminal::-webkit-scrollbar {
            width: 8px;
        }
        
        .terminal::-webkit-scrollbar-track {
            background: #1a1a1a;
        }
        
        .terminal::-webkit-scrollbar-thumb {
            background: #4facfe;
            border-radius: 4px;
        }
        
        .terminal-line {
            margin: 3px 0;
            display: flex;
            align-items: center;
        }
        
        .terminal-timestamp {
            color: #666;
            margin-right: 15px;
            font-size: 0.8rem;
            min-width: 70px;
        }
        
        .terminal-ready { color: #00ff41; }
        .terminal-command { color: #4facfe; }
        .terminal-gesture { color: #ffaa00; }
        .terminal-error { color: #ff4444; }
        
        .features-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-bottom: 30px;
        }
        
        .feature-section {
            background: rgba(255,255,255,0.1);
            border-radius: 20px;
            padding: 30px;
            backdrop-filter: blur(15px);
            border: 1px solid rgba(255,255,255,0.1);
        }
        
        .feature-section h2 {
            margin-bottom: 20px;
            font-size: 1.5rem;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .commands-grid {
            display: grid;
            gap: 15px;
        }
        
        .command-card {
            background: rgba(0,0,0,0.4);
            padding: 20px;
            border-radius: 12px;
            border-left: 4px solid #4facfe;
            transition: all 0.3s ease;
        }
        
        .command-card:hover {
            transform: translateX(10px);
            background: rgba(0,0,0,0.6);
        }
        
        .command-card strong {
            display: block;
            margin-bottom: 8px;
            color: #4facfe;
            font-size: 1.1rem;
        }
        
        .gesture-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 15px;
        }
        
        .gesture-item {
            background: rgba(0,0,0,0.4);
            padding: 20px;
            border-radius: 12px;
            text-align: center;
            transition: all 0.3s ease;
            cursor: pointer;
            border: 2px solid transparent;
        }
        
        .gesture-item:hover {
            transform: scale(1.05);
            border-color: #4facfe;
            background: rgba(0,0,0,0.6);
        }
        
        .gesture-icon {
            font-size: 2.5rem;
            margin-bottom: 10px;
            display: block;
        }
        
        .gesture-name {
            font-weight: bold;
            margin-bottom: 5px;
            color: #4facfe;
        }
        
        .gesture-action {
            font-size: 0.9rem;
            opacity: 0.8;
        }
        
        .alert {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 25px;
            border-radius: 10px;
            font-weight: bold;
            z-index: 1000;
            display: none;
            min-width: 300px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            backdrop-filter: blur(10px);
        }
        
        .alert-success {
            background: linear-gradient(45deg, #00c851, #00ff41);
            color: #000;
        }
        
        .alert-error {
            background: linear-gradient(45deg, #ff4444, #cc0000);
            color: white;
        }
        
        @keyframes pulse {
            0% { box-shadow: 0 10px 30px rgba(79, 172, 254, 0.3); }
            50% { box-shadow: 0 10px 30px rgba(79, 172, 254, 0.8); }
            100% { box-shadow: 0 10px 30px rgba(79, 172, 254, 0.3); }
        }
        
        .recording {
            animation: pulse 2s infinite;
        }
        
        @media (max-width: 768px) {
            .main-grid {
                grid-template-columns: 1fr;
            }
            
            .features-grid {
                grid-template-columns: 1fr;
            }
            
            .control-buttons {
                flex-direction: column;
                align-items: center;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 HoloNav Pro</h1>
        <p class="subtitle">Advanced Voice & Gesture Control System</p>
    </div>
    
    <div class="container">
        <!-- Control Panel -->
        <div class="control-panel">
            <h2>🎯 Mission Control Center</h2>
            <p style="margin: 15px 0; opacity: 0.8;">Activate the enhanced control system to begin voice and gesture recognition</p>
            <div class="control-buttons">
                <button id="launchBtn" class="launch-btn btn-launch">🚀 LAUNCH SYSTEM</button>
                <button id="stopBtn" class="launch-btn btn-stop" disabled>⏹️ STOP SYSTEM</button>
            </div>
        </div>
        
        <!-- Status Dashboard -->
        <div class="status-dashboard">
            <div class="status-card">
                <h3>🖥️ System Status</h3>
                <div id="systemStatus" class="status-value status-offline">STANDBY</div>
            </div>
            <div class="status-card">
                <h3>🎤 Voice Control</h3>
                <div id="voiceStatus" class="status-value status-offline">INACTIVE</div>
            </div>
            <div class="status-card">
                <h3>👋 Gesture Control</h3>
                <div id="gestureStatus" class="status-value status-offline">INACTIVE</div>
            </div>
            <div class="status-card">
                <h3>⚡ Last Command</h3>
                <div id="lastCommand" class="status-value">NONE</div>
            </div>
        </div>
        
        <!-- Main Content Grid -->
        <div class="main-grid">
            <div class="video-section">
                <h3>📹 Live Camera Feed</h3>
                <div class="video-container">
                    <img id="cameraFeed" class="camera-feed" src="{{ url_for('video_feed') }}" alt="Camera Feed">
                    <div class="video-overlay">
                        <span id="liveIndicator">🔴 LIVE</span>
                    </div>
                </div>
                
                <div class="gesture-info">
                    <div><strong>Current Gesture Detected:</strong></div>
                    <div id="currentGesture" class="current-gesture">None Detected</div>
                </div>
            </div>
            
            <div class="terminal-section">
                <div class="terminal-header">
                    <span>💻 System Terminal</span>
                </div>
                <div class="terminal" id="terminal">
                    <div class="terminal-line">
                        <span class="terminal-timestamp">[INIT]</span>
                        <span class="terminal-ready">HoloNav Pro v2.0 Ready</span>
                    </div>
                    <div class="terminal-line">
                        <span class="terminal-timestamp">[INFO]</span>
                        <span>Waiting for system activation...</span>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Features Grid -->
        <div class="features-grid">
            <!-- Voice Commands -->
            <div class="feature-section">
                <h2>🎤 Voice Commands</h2>
                <div class="commands-grid">
                    <div class="command-card">
                        <strong>🌐 Web Navigation</strong>
                        <p>"open youtube", "open google", "open github", "open facebook", "open instagram"</p>
                    </div>
                    <div class="command-card">
                        <strong>🔊 Audio Control</strong>
                        <p>"volume up", "volume down", "mute", "unmute"</p>
                    </div>
                    <div class="command-card">
                        <strong>🪟 Window Management</strong>
                        <p>"minimize window", "maximize window", "close window", "switch tab"</p>
                    </div>
                    <div class="command-card">
                        <strong>📱 Applications</strong>
                        <p>"open calculator", "open notepad", "open file manager", "open command prompt"</p>
                    </div>
                    <div class="command-card">
                        <strong>🎮 Navigation</strong>
                        <p>"scroll up", "scroll down", "go back", "go forward"</p>
                    </div>
                    <div class="command-card">
                        <strong>⚙️ System Control</strong>
                        <p>"exit program", "stop system", "restart system"</p>
                    </div>
                </div>
            </div>
            
            <!-- Gesture Controls -->
            <div class="feature-section">
                <h2>👋 Gesture Controls</h2>
                <div class="gesture-grid">
                    <div class="gesture-item" data-gesture="thumbs_up">
                        <div class="gesture-icon">👍</div>
                        <div class="gesture-name">Thumbs Up</div>
                        <div class="gesture-action">Volume Up</div>
                    </div>
                    <div class="gesture-item" data-gesture="peace">
                        <div class="gesture-icon">✌️</div>
                        <div class="gesture-name">Peace Sign</div>
                        <div class="gesture-action">Minimize Window</div>
                    </div>
                    <div class="gesture-item" data-gesture="ok">
                        <div class="gesture-icon">👌</div>
                        <div class="gesture-name">OK Sign</div>
                        <div class="gesture-action">Maximize Window</div>
                    </div>
                    <div class="gesture-item" data-gesture="fist">
                        <div class="gesture-icon">✊</div>
                        <div class="gesture-name">Fist</div>
                        <div class="gesture-action">Recent Apps</div>
                    </div>
                    <div class="gesture-item" data-gesture="palm_right">
                        <div class="gesture-icon">🤚➡️</div>
                        <div class="gesture-name">Right Palm</div>
                        <div class="gesture-action">Scroll Down</div>
                    </div>
                    <div class="gesture-item" data-gesture="palm_left">
                        <div class="gesture-icon">⬅️🤚</div>
                        <div class="gesture-name">Left Palm</div>
                        <div class="gesture-action">Scroll Left</div>
                    </div>
                     <div class="gesture-item" data-gesture="three_fingers_right">
                        <div class="gesture-icon">👆👆👆➡️</div>
                        <div class="gesture-name">Three Fingers Right</div>
                        <div class="gesture-description">Navigate to next app in recent apps</div>
                </div>

                </div>
            </div>
        </div>
    </div>
    
    <!-- Alert System -->
    <div id="successAlert" class="alert alert-success"></div>
    <div id="errorAlert" class="alert alert-error"></div>
    
    <script>
        // UI Elements
        const launchBtn = document.getElementById('launchBtn');
        const stopBtn = document.getElementById('stopBtn');
        const systemStatus = document.getElementById('systemStatus');
        const voiceStatus = document.getElementById('voiceStatus');
        const gestureStatus = document.getElementById('gestureStatus');
        const lastCommand = document.getElementById('lastCommand');
        const currentGesture = document.getElementById('currentGesture');
        const terminal = document.getElementById('terminal');
        const cameraFeed = document.getElementById('cameraFeed');
        const successAlert = document.getElementById('successAlert');
        const errorAlert = document.getElementById('errorAlert');
        
        let updateInterval;
        
        // Terminal logging
        function addTerminalLog(message, type = 'info') {
            const timestamp = new Date().toLocaleTimeString();
            const line = document.createElement('div');
            line.className = 'terminal-line';
            
            let className = '';
            switch(type) {
                case 'ready': className = 'terminal-ready'; break;
                case 'command': className = 'terminal-command'; break;
                case 'gesture': className = 'terminal-gesture'; break;
                case 'error': className = 'terminal-error'; break;
                default: className = '';
            }
            
            line.innerHTML = `
                <span class="terminal-timestamp">[${timestamp}]</span>
                <span class="${className}">${message}</span>
            `;
            
            terminal.appendChild(line);
            terminal.scrollTop = terminal.scrollHeight;
            
            // Keep only last 50 lines
            while (terminal.children.length > 50) {
                terminal.removeChild(terminal.firstChild);
            }
        }
        
        // Alert system
        function showAlert(alertElement, message) {
            alertElement.textContent = message;
            alertElement.style.display = 'block';
            setTimeout(() => {
                alertElement.style.display = 'none';
            }, 4000);
        }
        
        // Update system status
        function updateStatus() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'running') {
                        systemStatus.textContent = 'ONLINE';
                        systemStatus.className = 'status-value status-online';
                        voiceStatus.textContent = 'LISTENING';
                        voiceStatus.className = 'status-value status-active';
                        gestureStatus.textContent = 'TRACKING';
                        gestureStatus.className = 'status-value status-active';
                        launchBtn.disabled = true;
                        stopBtn.disabled = false;
                        
                        if (data.gesture && data.gesture !== 'none') {
                            currentGesture.textContent = data.gesture.replace('_', ' ').toUpperCase();
                            cameraFeed.classList.add('recording');
                        } else {
                            currentGesture.textContent = 'None Detected';
                            cameraFeed.classList.remove('recording');
                        }
                        
                        if (data.last_command && data.last_command !== 'none') {
                            lastCommand.textContent = data.last_command.toUpperCase();
                        }
                    } else {
                        systemStatus.textContent = 'STANDBY';
                        systemStatus.className = 'status-value status-offline';
                        voiceStatus.textContent = 'INACTIVE';
                        voiceStatus.className = 'status-value status-offline';
                        gestureStatus.textContent = 'INACTIVE';
                        gestureStatus.className = 'status-value status-offline';
                        launchBtn.disabled = false;
                        stopBtn.disabled = true;
                        currentGesture.textContent = 'None Detected';
                        cameraFeed.classList.remove('recording');
                    }
                })
                .catch(error => {
                    addTerminalLog('Connection error: ' + error.message, 'error');
                });
        }
        
        // Launch system
        launchBtn.addEventListener('click', () => {
            addTerminalLog('Initiating system launch sequence...', 'ready');
            showAlert(successAlert, '🚀 Launching HoloNav Pro...');
            
            fetch('/api/start', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        addTerminalLog('System successfully launched!', 'ready');
                        addTerminalLog('Voice and gesture recognition active', 'ready');
                        showAlert(successAlert, '✅ System Online - All Controls Active');
                        updateStatus();
                        updateInterval = setInterval(updateStatus, 1000);
                    } else {
                        addTerminalLog('Launch failed: ' + data.message, 'error');
                        showAlert(errorAlert, '❌ Launch Failed: ' + data.message);
                    }
                })
                .catch(error => {
                    addTerminalLog('Launch error: ' + error.message, 'error');
                    showAlert(errorAlert, '❌ System Error: ' + error.message);
                });
        });
        
        // Stop system
        stopBtn.addEventListener('click', () => {
            addTerminalLog('Initiating system shutdown...', 'ready');
            showAlert(successAlert, '⏹️ Stopping HoloNav Pro...');
            
            fetch('/api/stop', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        addTerminalLog('System shutdown complete', 'ready');
                        showAlert(successAlert, '✅ System Stopped Successfully');
                        updateStatus();
                        if (updateInterval) {
                            clearInterval(updateInterval);
                        }
                    } else {
                        addTerminalLog('Shutdown error: ' + data.message, 'error');
                        showAlert(errorAlert, '❌ Stop Failed: ' + data.message);
                    }
                })
                .catch(error => {
                    addTerminalLog('Stop error: ' + error.message, 'error');
                    showAlert(errorAlert, '❌ System Error: ' + error.message);
                });
        });
        
        // Gesture testing
        document.querySelectorAll('.gesture-item').forEach(item => {
            item.addEventListener('click', () => {
                const gesture = item.dataset.gesture;
                addTerminalLog(`Testing gesture: ${gesture.replace('_', ' ')}`, 'gesture');
                
                fetch('/api/test_gesture', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ gesture: gesture })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        addTerminalLog(`Gesture executed: ${gesture.replace('_', ' ')}`, 'command');
                        showAlert(successAlert, `✋ Gesture Simulated: ${gesture.replace('_', ' ')}`);
                    }
                });
            });
        });
        
        // Initialize
        addTerminalLog('HoloNav Pro v2.0 initialized successfully', 'ready');
        addTerminalLog('Camera feed ready for gesture detection', 'ready');
        updateStatus();
        
        // Handle camera feed errors
        cameraFeed.onerror = function() {
            addTerminalLog('Camera feed connection failed', 'error');
            cameraFeed.style.background = '#1a1a1a';
            cameraFeed.alt = 'Camera Not Available';
        };
        
        cameraFeed.onload = function() {
            addTerminalLog('Camera feed connected successfully', 'ready');
        };
    </script>
</body>
</html>
"""

VOICE_COMMANDS = {
    # Your voice command mappings unchanged
        "open youtube": lambda: [webbrowser.open("https://youtube.com"), log_command("Opened YouTube")],
    "open google": lambda: [webbrowser.open("https://google.com"), log_command("Opened Google")],
    "open facebook": lambda: [webbrowser.open("https://facebook.com"), log_command("Opened Facebook")],
    "open instagram": lambda: [webbrowser.open("https://instagram.com"), log_command("Opened Instagram")],
    "open github": lambda: [webbrowser.open("https://github.com"), log_command("Opened GitHub")],
    "minimize window": lambda: [pyautogui.hotkey("win", "down"), log_command("Minimized window")],
    "maximize window": lambda: [pyautogui.hotkey("win", "up"), log_command("Maximized window")],
    "close window": lambda: [pyautogui.hotkey("alt", "f4"), log_command("Closed window")],
    "switch tab": lambda: [pyautogui.hotkey("ctrl", "tab"), log_command("Switched tab")],
    "volume up": lambda: [pyautogui.press("volumeup"), log_command("Volume increased")],
    "volume down": lambda: [pyautogui.press("volumedown"), log_command("Volume decreased")],
    "mute": lambda: [pyautogui.press("volumemute"), log_command("Volume muted")],
    "unmute": lambda: [pyautogui.press("volumemute"), log_command("Volume unmuted")],
    "scroll up": lambda: [pyautogui.scroll(300), log_command("Scrolled up")],
    "scroll down": lambda: [pyautogui.scroll(-300), log_command("Scrolled down")],
    "go back": lambda: [pyautogui.hotkey("alt", "left"), log_command("Went back")],
    "go forward": lambda: [pyautogui.hotkey("alt", "right"), log_command("Went forward")],
    "open calculator": lambda: [subprocess.run("calc", shell=True), log_command("Opened Calculator")],
    "open notepad": lambda: [subprocess.run("notepad", shell=True), log_command("Opened Notepad")],
    "open file manager": lambda: [subprocess.run("explorer", shell=True), log_command("Opened File Manager")],
    "open command prompt": lambda: [subprocess.run("cmd", shell=True), log_command("Opened Command Prompt")],
    "exit program": lambda: [stop_system_func(), log_command("Exiting program")],
    "stop system": lambda: [stop_system_func(), log_command("System stopped")],
}



def log_command(message):
    terminal_output.append({'timestamp': datetime.now().strftime('%H:%M:%S'), 'message': message, 'type': 'command'})
    print("[COMMAND]", message)

def log_gesture(message):
    terminal_output.append({'timestamp': datetime.now().strftime('%H:%M:%S'), 'message': message, 'type': 'gesture'})
    print("[GESTURE]", message)

def stop_system_func():
    global system_running
    system_running = False
    print("[SYSTEM] Stopping system...")

def navigate_recent_apps_right():
    """Navigate to the next app in recent apps view"""
    try:
        
        pyautogui.press('right')
        time.sleep(0.1)  
    except Exception as e:
        print(f"[ERROR] Failed to navigate right: {e}")

def navigate_recent_apps_left():
    """Navigate to the previous app in recent apps view"""
    try:
       
        pyautogui.press('left')
        time.sleep(0.1)  
    except Exception as e:
        print(f"[ERROR] Failed to navigate left: {e}")


def detect_gesture(landmarks):
    if not landmarks:
        return "none"
    
    # Get landmark positions
    thumb_tip = landmarks[4]
    thumb_ip = landmarks[3]
    index_tip = landmarks[8]
    index_pip = landmarks[6]
    middle_tip = landmarks[12]
    middle_pip = landmarks[10]
    ring_tip = landmarks[16]
    ring_pip = landmarks[14]
    pinky_tip = landmarks[20]
    pinky_pip = landmarks[18]
    
    # 
    def is_finger_extended(tip_y, pip_y):
        return tip_y < pip_y  
    
    # Count extended fingers 
    extended_fingers = []
    
    # Check each finger
    if is_finger_extended(index_tip.y, index_pip.y):
        extended_fingers.append('index')
    if is_finger_extended(middle_tip.y, middle_pip.y):
        extended_fingers.append('middle')
    if is_finger_extended(ring_tip.y, ring_pip.y):
        extended_fingers.append('ring')
    if is_finger_extended(pinky_tip.y, pinky_pip.y):
        extended_fingers.append('pinky')
    
    thumb_extended = thumb_tip.y < thumb_ip.y
    
    # THREE FINGER GESTURES (NEW)
    if len(extended_fingers) == 3 and 'index' in extended_fingers and 'middle' in extended_fingers and 'ring' in extended_fingers and not thumb_extended:
        return "three_fingers_right"
    
    if len(extended_fingers) == 3 and 'middle' in extended_fingers and 'ring' in extended_fingers and 'pinky' in extended_fingers and not thumb_extended:
        return "three_fingers_left"
    
    if thumb_tip.y < thumb_ip.y and index_tip.y > index_pip.y and middle_tip.y > middle_pip.y:
        return "thumbs_up"
    if index_tip.y < index_pip.y and middle_tip.y < middle_pip.y and ring_tip.y > ring_pip.y and pinky_tip.y > pinky_pip.y:
        return "peace"
    dist = ((thumb_tip.x - index_tip.x)**2 + (thumb_tip.y - index_tip.y)**2)**0.5
    if dist < 0.05 and middle_tip.y < middle_pip.y:
        return "ok"
    if index_tip.y > index_pip.y and middle_tip.y > middle_pip.y and ring_tip.y > ring_pip.y and pinky_tip.y > pinky_pip.y:
        return "fist"
    if index_tip.y < index_pip.y and middle_tip.y < middle_pip.y and ring_tip.y < ring_pip.y and pinky_tip.y < pinky_pip.y:
        if thumb_tip.x > pinky_tip.x:
            return "palm_right"
        else:
            return "palm_left"
    return "none"


# gestures
GESTURE_ACTIONS = {
    "thumbs_up": lambda: [pyautogui.press('volumeup'), log_gesture("Thumbs up - Volume increased")],
    "peace": lambda: [pyautogui.hotkey('win', 'down'), log_gesture("Peace sign - Window minimized")],
    "ok": lambda: [pyautogui.hotkey('win', 'up'), log_gesture("OK sign - Window maximized")],
    "fist": lambda: [pyautogui.hotkey('win', 'tab'), log_gesture("Fist - Showing recent apps")],
    "palm_right": lambda: [pyautogui.scroll(-300), log_gesture("Right palm - Scrolled down")],
    "palm_left": lambda: [pyautogui.hscroll(-100), log_gesture("Left palm - Scrolled left")],
    "three_fingers_right": lambda: [navigate_recent_apps_right(), log_gesture("Three fingers right - Navigate to next app")],
    "three_fingers_left": lambda: [navigate_recent_apps_left(), log_gesture("Three fingers left - Navigate to previous app")],
}

def camera_capture_thread():
    global current_frame, current_gesture, system_running
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ERROR] Failed to open camera")
        return
    print("[SYSTEM] Camera capture thread started")

    while system_running:
        ret, frame = cap.read()
        if not ret:
            continue
        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb_frame)

        gesture = "none"
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                gesture = detect_gesture(hand_landmarks.landmark)
                if gesture != current_gesture and gesture != "none":
                    current_gesture = gesture
                    print(f"[GESTURE] Detected: {gesture}")
                    if gesture in GESTURE_ACTIONS:
                        try:
                            GESTURE_ACTIONS[gesture]()
                        except Exception as e:
                            print(f"[ERROR] Gesture action error: {e}")
        else:
            current_gesture = "none"

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

        with frame_lock:
            current_frame = frame.copy()

        time.sleep(0.03)

    cap.release()
    print("[SYSTEM] Camera capture thread stopped")

def generate_frames():
    global current_frame
    while True:
        if not system_running:
            time.sleep(0.1)
            continue
        with frame_lock:
            if current_frame is None:
                continue
            ret, buffer = cv2.imencode('.jpg', current_frame)
            frame_bytes = buffer.tobytes()
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.03)  # small delay to ease CPU load

def voice_recognition_thread():
    global last_command, system_running, voice_active
    with microphone as source:
        recognizer.adjust_for_ambient_noise(source)
    print("[SYSTEM] Voice recognition thread started")
    while system_running:
        try:
            voice_active = True
            with microphone as source:
                audio = recognizer.listen(source, timeout=1, phrase_time_limit=3)
            command = recognizer.recognize_google(audio).lower()
            print(f"[VOICE] Heard: {command}")
            if any(phrase in command for phrase in ["exit program", "stop system", "quit"]):
                last_command = "exit program"
                stop_system_func()
                break
            for voice_cmd in VOICE_COMMANDS:
                if voice_cmd in command:
                    last_command = voice_cmd
                    try:
                        VOICE_COMMANDS[voice_cmd]()
                    except Exception as e:
                        print(f"[ERROR] Voice command execution error: {e}")
                    break
        except sr.WaitTimeoutError:
            pass
        except sr.UnknownValueError:
            pass
        except sr.RequestError as e:
            print(f"[ERROR] Voice recognition request error: {e}")
            time.sleep(1)
        except Exception as e:
            print(f"[ERROR] Unexpected voice error: {e}")
            time.sleep(1)
    voice_active = False
    print("[SYSTEM] Voice recognition thread stopped")

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/status')
def get_status():
    return jsonify({
        'status': 'running' if system_running else 'stopped',
        'voice': 'active' if voice_active else 'inactive',
        'gesture_active': 'active' if gesture_active else 'inactive',
        'gesture': current_gesture,
        'last_command': last_command,
        'terminal': terminal_output[-50:] if terminal_output else []
    })

@app.route('/api/start', methods=['POST'])
def start_system():
    global system_running, gesture_active
    if system_running:
        return jsonify({'success': False, 'message': 'System already running'})
    system_running = True
    gesture_active = True
    threading.Thread(target=voice_recognition_thread, daemon=True).start()
    threading.Thread(target=camera_capture_thread, daemon=True).start()
    log_command("System started successfully")
    return jsonify({'success': True, 'message': 'System started successfully'})

@app.route('/api/stop', methods=['POST'])
def stop_system_api():
    global system_running, voice_active, gesture_active
    system_running = False
    voice_active = False
    gesture_active = False
    log_command('System stopped')
    return jsonify({'success': True, 'message': 'System stopped successfully'})


if __name__ == '__main__':
    threading.Timer(1.0, lambda: webbrowser.open('http://127.0.0.1:5000')).start()
    app.run(host='localhost', port=5000, debug=False, use_reloader=False)
