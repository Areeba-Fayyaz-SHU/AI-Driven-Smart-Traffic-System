import time
import queue

class VehicleProcess:
    def __init__(self, vehicle_id, vehicle_type, priority):
        self.pid = vehicle_id
        self.type = vehicle_type
        self.priority = priority
        self.arrival_time = time.time()
        self.start_time = None
        self.completion_time = None
        self.waiting_time = 0
        self.turnaround_time = 0
        self.burst_time = 5  # Simulation of time needed to clear the intersection
        self.status = "Waiting"

    # Fixes the 'TypeError' when comparing two vehicles with the same priority
    def __lt__(self, other):
        return self.arrival_time < other.arrival_time

class TrafficScheduler:
    def __init__(self):
        self.ready_queue = queue.PriorityQueue()
        self.all_processes = []
        self.ai_stats = {"latency": 0, "counts": {}}

    def add_vehicle(self, v_id, v_type):
        priority = 3 
        if v_type in ['ambulance', 'fire truck', 'police']: priority = 1
        elif v_type == 'bus': priority = 2
        
        new_process = VehicleProcess(v_id, v_type, priority)
        self.ready_queue.put((priority, new_process))
        self.all_processes.append(new_process)
        return new_process

    def schedule_next(self):
        if not self.ready_queue.empty():
            priority, vehicle = self.ready_queue.get()
            vehicle.status = "Running"
            vehicle.start_time = time.time()
            vehicle.waiting_time = vehicle.start_time - vehicle.arrival_time
            return vehicle
        return None

    def get_all_data(self):
        completed = [p for p in self.all_processes if p.status == "Completed"]
        total = len(completed)
        awt = round(sum(p.waiting_time for p in completed) / total, 2) if total > 0 else 0
        att = round(sum(p.turnaround_time for p in completed) / total, 2) if total > 0 else 0
        
        return {
            "processes": [vars(p) for p in self.all_processes],
            "metrics": {"awt": awt, "att": att, "count": total},
            "ai_metrics": self.ai_stats
        }