"""
main.py
-------
Backend service สำหรับ "River Trash Detector Demo"

หน้าที่ของไฟล์นี้:
1. รับรูปภาพที่อัปโหลดมาจาก frontend
2. ใช้โมเดล YOLOv8n (ultralytics) ตรวจจับวัตถุในรูป
3. กรองเฉพาะคลาสที่เกี่ยวกับ "ขยะ" ที่มีอยู่ใน pretrained COCO model
   (bottle, cup) เพื่อจำลองการนับขยะลอยน้ำแบบง่าย ๆ
4. บันทึกจำนวนที่นับได้สะสมลงใน Redis (container ที่ 3 ใน docker-compose)
5. เปิด endpoint ให้ frontend ดึงสถิติสะสมไปแสดงผลบนแดชบอร์ด

หมายเหตุ: โปรเจกต์จริง (river-trash-detection) ใช้โมเดลที่เทรนเองบน
Roboflow dataset "floating-waste" (bottle, paper, plastic, can, carton)
และรันบน Jetson Nano ผ่าน RTSP แต่เดโมนี้ตัด hardware ออก
เพื่อให้ containerize และรันบนเครื่องใครก็ได้ผ่าน docker compose
"""

import io
import os
import time

import redis
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from ultralytics import YOLO

# -----------------------------------------------------------------
# ตั้งค่าแอป FastAPI
# -----------------------------------------------------------------
app = FastAPI(title="River Trash Detector API")

# เปิด CORS ให้ frontend (คนละ container / คนละ origin) เรียก API ได้
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------
# เชื่อมต่อ Redis (อ่านค่า host/port จาก environment variable
# ที่กำหนดไว้ใน docker-compose.yml -> ทำให้ backend ไม่ผูกติดกับ
# ชื่อ container ตายตัวในโค้ด)
# -----------------------------------------------------------------
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# -----------------------------------------------------------------
# โหลดโมเดล YOLOv8n ครั้งเดียวตอน container เริ่มทำงาน
# (โหลดตอน import ระดับโมดูล เพื่อไม่ต้องโหลดซ้ำทุก request)
# -----------------------------------------------------------------
model = YOLO("yolov8n.pt")

# คลาสใน COCO dataset ที่ใช้แทน "ขยะลอยน้ำ" สำหรับเดโม
TRASH_CLASSES = {"bottle", "cup"}


@app.get("/health")
def health():
    """ใช้เช็คว่า backend container พร้อมทำงานหรือยัง (healthcheck)"""
    return {"status": "ok", "time": time.time()}


@app.post("/detect")
async def detect(file: UploadFile = File(...)):
    """
    รับไฟล์รูปภาพ -> รัน YOLOv8n -> กรองเฉพาะคลาสขยะ ->
    บวกจำนวนสะสมใน Redis -> ส่งผลตรวจจับกลับไปให้ frontend วาดกรอบ
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="ต้องอัปโหลดไฟล์รูปภาพเท่านั้น")

    image_bytes = await file.read()
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    results = model.predict(image, verbose=False)[0]

    detections = []
    counted_this_request = {}

    for box in results.boxes:
        class_id = int(box.cls[0])
        class_name = model.names[class_id]
        confidence = float(box.conf[0])

        if class_name not in TRASH_CLASSES:
            continue

        x1, y1, x2, y2 = [float(v) for v in box.xyxy[0]]
        detections.append(
            {
                "class": class_name,
                "confidence": round(confidence, 3),
                "box": [x1, y1, x2, y2],
            }
        )
        counted_this_request[class_name] = counted_this_request.get(class_name, 0) + 1

    # บันทึกจำนวนสะสมลง Redis แยกตามคลาส เช่น key "trash_count:bottle"
    for class_name, count in counted_this_request.items():
        r.incrby(f"trash_count:{class_name}", count)
    if counted_this_request:
        r.incrby("trash_count:total", sum(counted_this_request.values()))

    return {
        "detections": detections,
        "detected_this_image": sum(counted_this_request.values()),
    }


@app.get("/stats")
def stats():
    """ดึงจำนวนขยะสะสมทั้งหมดจาก Redis มาแสดงบนแดชบอร์ด"""
    keys = r.keys("trash_count:*")
    result = {}
    for key in keys:
        label = key.split(":", 1)[1]
        result[label] = int(r.get(key))
    return result
