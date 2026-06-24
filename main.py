import cv2
from ultralytics import YOLO
import mysql.connector
import threading
import time
import os
from os_engine import TrafficScheduler

scheduler = TrafficScheduler()
lock = threading.Lock()

def run_system():
    detected_list = []
    crossed_ids = []
    db = mysql.connector.connect(host="localhost", user="root", password="", database="traffic_db")
    cursor = db.cursor()

    def os_worker():
        while True:
            with lock:
                next_v = scheduler.schedule_next()
            if next_v:
                time.sleep(next_v.burst_time)
                next_v.completion_time = time.time()
                next_v.turnaround_time = next_v.completion_time - next_v.arrival_time
                next_v.status = "Completed"
            time.sleep(0.5)

    threading.Thread(target=os_worker, daemon=True).start()

    model = YOLO("yolo11n.pt")
    cap = cv2.VideoCapture("traffic_video.mp4")
    
    while cap.isOpened():
        success, frame = cap.read()
        if not success: break

        results = model.track(frame, persist=True)
        if results[0].boxes.id is not None:
            # AI Analytics
            inf_speed = results[0].speed['inference']
            current_counts = {}
            
            ids = results[0].boxes.id.cpu().numpy().astype(int)
            clss = results[0].boxes.cls.cpu().numpy().astype(int)
            boxes = results[0].boxes.xyxy.cpu().numpy()

            for box, track_id, cls in zip(boxes, ids, clss):
                v_type = model.names[cls]
                current_counts[v_type] = current_counts.get(v_type, 0) + 1
                
                if track_id not in detected_list:
                    with lock: scheduler.add_vehicle(track_id, v_type)
                    detected_list.append(track_id)

                # Database Violation Logic
                cx, cy = int((box[0]+box[2])/2), int((box[1]+box[3])/2)
                if cy > 400 and track_id not in crossed_ids:
                    crossed_ids.append(track_id)
                    with lock:
                        v_p = next((p for p in scheduler.all_processes if p.pid == track_id), None)
                    if v_p:
                        sql = "INSERT INTO violations (track_id, vehicle_type, image_path, wait_time, turnaround_time, priority) VALUES (%s, %s, %s, %s, %s, %s)"
                        cursor.execute(sql, (int(track_id), v_type, "N/A", v_p.waiting_time, v_p.turnaround_time, v_p.priority))
                        db.commit()

            with lock: scheduler.update_ai_metrics(inf_speed, current_counts)

        cv2.imshow("SHU AI-OS Monitor", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    run_system()