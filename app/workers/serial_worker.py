# =======================================================================================
# app/workers/serial_worker.py - Background Serial Worker
# =======================================================================================
import json
import time
import threading
from typing import Optional
from ..config import config
from ..services.serial_service import SerialService

try:
    import serial
except ImportError:
    serial = None

class SerialWorker:
    """Background worker for serial communication."""
    
    def __init__(self):
        self.serial_service = SerialService()
        self.running = False
    
    def start(self):
        """Start the serial worker in a background thread."""
        if not self._should_start():
            return
        
        self.running = True
        thread = threading.Thread(target=self._run_loop, daemon=True)
        thread.start()
        
        if config.API_DEBUG:
            print("[serial] Worker started")
    
    def stop(self):
        """Stop the serial worker."""
        self.running = False
    
    def _should_start(self) -> bool:
        """Check if serial worker should start."""
        if serial is None:
            if config.API_DEBUG:
                print("[serial] pyserial not installed; skipping UART worker.")
            return False
        
        if not config.SERIAL_PORT:
            if config.API_DEBUG:
                print("[serial] SERIAL_PORT not configured; skipping UART worker.")
            return False
        
        required_ids = [config.GATE_ID, config.BOOTH_ID, config.DEVICE_ID, config.NODE_ID]
        if any(id is None for id in required_ids):
            if config.API_DEBUG:
                print("[serial] Missing gate/booth/device/node IDs; skipping UART worker.")
            return False
        
        return True
    
    def _run_loop(self):
        """Main serial communication loop."""
        while self.running:
            try:
                self._handle_serial_connection()
            except Exception as e:
                if config.API_DEBUG:
                    print(f"[serial] Connection error: {e} — retrying in 3s")
                time.sleep(3)
    
    def _handle_serial_connection(self):
        """Handle serial connection and message processing."""
        if config.API_DEBUG:
            print(f"[serial] Opening {config.SERIAL_PORT} @ {config.SERIAL_BAUD} …")
        
        with serial.Serial(config.SERIAL_PORT, config.SERIAL_BAUD, 
                          timeout=config.SERIAL_TIMEOUT) as ser:
            if config.API_DEBUG:
                print("[serial] Port open.")
            
            while self.running:
                line = ser.readline().decode(errors="ignore").strip()
                if not line:
                    continue
                
                message = self.serial_service.parse_serial_message(line)
                if not message:
                    continue
                
                if config.API_DEBUG:
                    print(f"[serial] Received: {message}")
                
                response = self.serial_service.process_rfid_request(message)
                if response:
                    response_json = json.dumps(response) + "\n"
                    ser.write(response_json.encode())
                    
                    if config.API_DEBUG:
                        print(f"[serial] Sent: {response}")

# Global serial worker instance
serial_worker = SerialWorker()

def start_serial_worker():
    """Function to start the serial worker (called from FastAPI startup)."""
    serial_worker.start()