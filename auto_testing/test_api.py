from enum import IntEnum
import requests
from urllib3.exceptions import InsecureRequestWarning
import random
from itertools import permutations
import time
import threading
import signal
import sys
import os
import time

#Setting Chinese timezone
os.environ['TZ'] = 'Asia/Shanghai' 
time.tzset()  

# Disable SSL warnings
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Vertex constant definitions
class Vertex(IntEnum):
    # W1 = 4   # Storage location 1
    # W2 = 5   # Storage location 2
    # S1 = 28  # Shelf 1
    S1 = 172   # Storage location 1
    W3 = 177   # Storage location 2
    W4 = 178  # Shelf 1
class AGVController:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "http://10.6.68.65:8080"
        self.running = True  # Control loop flag
        if not self.login():
            raise Exception("Login failed, please check credentials")

    def login(self):
        """Form-based authentication"""
        login_url = f"{self.base_url}/agvo/rest/auth/login"
        try:
            response = self.session.post(
                login_url,
                data={"username": "root", "password": "root"},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                verify=False
            )
            print(f"Login status: {response.status_code}")
            return response.json().get("success", False)
        except Exception as e:
            print(f"Login error: {str(e)}")
            return False

    def send_move_task(self, start: Vertex, end: Vertex, priority=2):
        """Send transport task (silent on failure)"""
        task_url = f"{self.base_url}/agvo/rest/task/task"
        payload = {
            "taskName": f"{start.name.lower()} to {end.name.lower()}",
            "taskType": 1,
            "startVertex": int(start),
            "endVertex": int(end),
            "priority": priority,
            "repeatTimes": 1
        }
        
        try:
            response = self.session.post(task_url, json=payload, verify=False)
            if response.status_code == 200:
                result = response.json()
                if result.get("success", False):
                    print(f"[SUCCESS] {payload['taskName']}")
                    return True
            return False
        except Exception:
            return False

    def generate_tasks(self):
        """Generate randomized task list"""
        vertices = [Vertex.S1, Vertex.W3, Vertex.W4]
        base_tasks = list(permutations(vertices, 2))
        tasks = base_tasks * 2
        random.shuffle(tasks)
        return tasks

    def run_periodically(self, interval=600):
        """Run tasks periodically with silent failures"""
        while self.running:
            print(f"\n{time.ctime()} - New task batch started")
            tasks = self.generate_tasks()
            success_count = 0
            
            for start, end in tasks:
                if not self.running:
                    break
                if self.send_move_task(start, end):
                    success_count += 1

            if success_count == 0:
                print("[INFO] No runnable tasks in this batch")

            # Wait for next cycle
            for _ in range(interval):
                if not self.running:
                    break
                time.sleep(1)
    
    def stop(self):
        """Graceful shutdown"""
        self.running = False
        print("\nAGV controller stopping...")

def signal_handler(sig, frame):
    """Handle Ctrl+C signal"""
    print('\nReceived shutdown signal')
    controller.stop()
    sys.exit(0)

if __name__ == "__main__":
    print("=== AGV Control System ===")
    print("Press Ctrl+C to stop\n")
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        controller = AGVController()
        task_thread = threading.Thread(target=controller.run_periodically)
        task_thread.daemon = True
        task_thread.start()
        
        while True:
            time.sleep(1)
            
    except Exception as e:
        print(f"System error: {str(e)}")
        if 'controller' in locals():
            controller.stop()
