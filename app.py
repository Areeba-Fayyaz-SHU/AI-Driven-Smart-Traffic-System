from flask import Flask, render_template, jsonify, send_from_directory
import cv2
from ultralytics import YOLO
import mysql.connector
import threading
import time
import os
import queue

app = Flask(__name__)

# --- 1. SHARED SYSTEM ARCHITECTURE ---
class VehicleProcess:
    def __init__(self, vehicle_id, vehicle_type, priority):
        # Convert to standard Python int to avoid JSON errors
        self.pid = int(vehicle_id) 
        self.type = str(vehicle_type)
        self.priority = int(priority)
        self.arrival_time = time.time()
        self.status = "Waiting"
        self.waiting_time = 0
        self.turnaround_time = 0
        self.burst_time = 4 

    def __lt__(self, other): 
        return self.arrival_time < other.arrival_time

class TrafficScheduler:
    def __init__(self):
        self.ready_queue = queue.PriorityQueue()
        self.all_processes = []
        self.ai_stats = {"latency": 0, "counts": {}}

    def add_vehicle(self, v_id, v_type):
        prio = 1 if v_type in ['ambulance', 'police'] else (2 if v_type == 'bus' else 3)
        new_v = VehicleProcess(int(v_id), str(v_type), prio)
        self.ready_queue.put((prio, new_v))
        self.all_processes.append(new_v)
        print(f"📥 OS KERNEL: Admitted Vehicle #{v_id}")

    def get_data(self):
        comp = [p for p in self.all_processes if p.status == "Completed"]
        relevant = [p for p in self.all_processes if p.status in ["Running", "Completed"]]
        
        awt = round(sum(p.waiting_time for p in relevant) / len(relevant), 2) if relevant else 0
        att = round(sum(p.turnaround_time for p in comp) / len(comp), 2) if comp else 0
        
        return {
            "processes": [vars(p) for p in self.all_processes][-10:],
            "metrics": {"awt": float(awt), "att": float(att), "count": int(len(comp))},
            "ai_metrics": self.ai_stats
        }

scheduler = TrafficScheduler()
lock = threading.Lock()

# --- 2. OS KERNEL WORKER ---
def os_kernel_worker():
    current_running = None
    
    while True:
        if not scheduler.ready_queue.empty():
            # Look at the highest priority item waiting without removing it
            prio, next_v = scheduler.ready_queue.queue[0]
            
            with lock:
                # If nothing is running, or an incoming vehicle has higher priority (lower number)
                if current_running is None or prio < current_running.priority:
                    
                    if current_running and current_running.status == "Running":
                        # Preempt the current vehicle! Push it back to the queue
                        print(f"⚠️ PREEMPTION: Vehicle #{current_running.pid} paused for Ambulance/Police!")
                        current_running.status = "Waiting"
                        scheduler.ready_queue.put((current_running.priority, current_running))
                    
                    # Remove the high priority item from the queue and run it
                    _, current_running = scheduler.ready_queue.get()
                    current_running.status = "Running"
                    if not hasattr(current_running, 'start_time'):
                        current_running.start_time = time.time()
                        current_running.waiting_time = round(current_running.start_time - current_running.arrival_time, 2)
                    print(f"🟢 OS KERNEL: Vehicle #{current_running.pid} is now RUNNING")

        # Simulate execution in small steps to allow mid-burst preemption
        if current_running and current_running.status == "Running":
            time.sleep(0.1) 
            current_running.burst_time -= 0.1
            
            if current_running.burst_time <= 0:
                with lock:
                    current_running.completion_time = time.time()
                    current_running.turnaround_time = round(current_running.completion_time - current_running.arrival_time, 2)
                    current_running.status = "Completed"
                print(f"🏁 OS KERNEL: Vehicle #{current_running.pid} COMPLETED")
                current_running = None
        else:
            time.sleep(0.2)                         

# --- 3. AI DETECTION SYSTEM ---
def run_ai_system():
    detected, crossed = [], []
    if not os.path.exists('violations'): 
        os.makedirs('violations')
    
    # Wait for MySQL Connection
    db, cursor = None, None
    while True:
        try:
            db = mysql.connector.connect(host="localhost", user="root", password="", database="traffic_db")
            cursor = db.cursor()
            print("✅ AI SYSTEM: Connected to Database")
            break
        except:
            print("⏳ AI SYSTEM: Waiting for Database...")
            time.sleep(2)

    model = YOLO("yolo11n.pt")
    cap = cv2.VideoCapture("traffic_video.mp4")

    while cap.isOpened():
        success, frame = cap.read()
        if not success: 
            break
    
        res = model.track(frame, persist=True)
        annotated_frame = res[0].plot() 

        if res[0].boxes.id is not None:
            ids = res[0].boxes.id.cpu().numpy().astype(int).tolist()
            clss = res[0].boxes.cls.cpu().numpy().astype(int).tolist()
            boxes = res[0].boxes.xyxy.cpu().numpy().tolist()
            counts = {}

            for box, tid, cls in zip(boxes, ids, clss):
                v_type = model.names[cls]
                counts[v_type] = counts.get(v_type, 0) + 1
                
                if tid not in detected:
                    with lock: 
                        scheduler.add_vehicle(tid, v_type)
                    detected.append(tid)

                # Line crossing detection (Y-coordinate > 400)
                if int((box[1] + box[3]) / 2) > 400 and tid not in crossed:
                    crossed.append(tid)
                    path = f"violations/car_{tid}.jpg"
                    cv2.imwrite(path, frame)
                    
                    with lock: 
                        v_p = next((p for p in scheduler.all_processes if p.pid == tid), None)
                        if v_p:
                            cursor.execute(
                                "INSERT INTO violations (track_id, vehicle_type, image_path, wait_time, turnaround_time, priority) VALUES (%s,%s,%s,%s,%s,%s)", 
                                (int(tid), str(v_type), str(path), float(v_p.waiting_time), float(v_p.turnaround_time), int(v_p.priority))
                            )
                            db.commit()
            
            with lock: 
                scheduler.ai_stats = {
                    "latency": float(round(res[0].speed['inference'], 2)), 
                    "counts": counts
                }
        
        cv2.imshow("SHU AI-OS Integrated Feed", annotated_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): 
            break

    cap.release()
    cv2.destroyAllWindows()

# --- 4. FLASK ROUTES ---
@app.route('/')
def index():
    try:
        db = mysql.connector.connect(host="localhost", user="root", password="", database="traffic_db")
        cur = db.cursor(dictionary=True)
        cur.execute("SELECT * FROM violations ORDER BY id DESC LIMIT 12")
        v = cur.fetchall()
        db.close()
    except: 
        v = []
    return render_template('index.html', violations=v)

@app.route('/get_data')
def get_data(): 
    return jsonify(scheduler.get_data())

@app.route('/violations/<path:f>')
def serve(f): 
    return send_from_directory('violations', f)

if __name__ == '__main__':
    threading.Thread(target=os_kernel_worker, daemon=True).start()
    threading.Thread(target=run_ai_system, daemon=True).start()
    app.run(debug=True, port=5000, use_reloader=False)