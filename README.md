# 🚦 AI-Driven Smart Traffic & Lane Violation System

An intelligent traffic management and surveillance application that bridges the gap between **Computer Vision (AI)** and **Operating Systems (OS) Kernel scheduling principles** to identify vehicle types, track traffic violations, and dynamically optimize signal priorities in real-time.

---

## 🌟 Key Features

* **Real-Time Object Detection & Tracking:** Leverages cutting-edge **YOLOv11** architecture to accurately identify, classify, and track different vehicle types on the road.
* **Lane Violation Detection:** Monitors traffic lanes to automatically flag vehicle boundary cross-overs and illegal lane changes.
* **OS Kernel-Simulated Traffic Management:** Integrates detection data with an underlying **Priority-Based Scheduling Simulation** to dynamically adjust traffic light timings based on vehicle density and vehicle priority classes (e.g., emergency vehicles vs. standard transit).
* **Dynamic Backend Architecture:** Utilizes a lightweight backend framework to manage application logic, compute inference latency, and store traffic metrics seamlessly.

---

## 🛠️ Tech Stack & Concepts

* **AI & Computer Vision:** Python, Ultralytics YOLOv11
* **Backend Application:** Python, Flask
* **Database Management:** MySQL (for logging vehicle details, violations, and real-time statistics)
* **Operating Systems Theory:** Priority scheduling algorithms, mutual exclusion/synchronization simulations, and process queues

---

## 📂 Project Structure

```text
├── app.py                # Flask server and web interface application routing
├── core/
│   ├── detection.py      # YOLOv11 inference script for object tracking & lane logic
│   └── os_simulation.py  # Priority-based kernel simulation and scheduling logic
├── database/
│   └── schema.sql        # MySQL database structure for tracking logs and violations
├── templates/            # Web interface UI components
└── README.md             # Project documentation
