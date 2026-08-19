"""
main.py
-------
Backend service สำหรับ "River Trash Detector Demo"

หน้าที่ของไฟล์นี้:
1. รับรูปภาพที่อัปโหลดมาจาก frontend
2. ใช้โมเดล YOLOv8n ที่เทรนเอง (best.pt) ตรวจจับขยะ 3 ประเภท:
   plastic, organic, recyclable
3. บันทึกจำนวนที่นับได้สะสมลงใน Redis แยกตามประเภท (container ที่ 3
   ใน docker-compose)
4. เปิด endpoint ให้ frontend ดึงสถิติสะสมไปแสดงผลบนแดชบอร์ด

หมายเหตุ: โมเดล best.pt เทรนมาจากงาน river-trash-detection เดิมของผู้เขียน
(Roboflow dataset, เทรนบน Google Colab) นำมาใช้ต่อในเดโมนี้โดยตัด hardware
(Jetson Nano/RTSP) ออก เพื่อให้ containerize และรันบนเครื่องใครก็ได้ผ่าน
docker compose
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
# โหลดโมเดล YOLOv8n ที่เทรนเอง (best.pt) ครั้งเดียวตอน container เริ่มทำงาน
# ไฟล์ best.pt ถูก copy เข้ามาใน image ตอน build (ดู Dockerfile)
# โมเดลนี้เทรนไว้ 3 คลาส: plastic, organic, recyclable
# -----------------------------------------------------------------
model = YOLO("best.pt")

# ชื่อคลาสที่ใช้แสดงผล (ภาษาอังกฤษตามที่โจทย์กำหนด) เรียงลำดับตายตัว
# เพื่อให้ /stats คืนค่าตามลำดับเดิมทุกครั้ง ไม่ว่า Redis จะมี key ไหนบ้าง
TRASH_CLASSES = ["plastic", "recyclable", "organic"]


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

    # บันทึกจำนวนสะสมลง Redis แยกตามคลาส เช่น key "trash_count:plastic"
    # (ไม่ต้องเก็บ "trash_count:total" แยก เพราะ /stats รวมยอดจาก 3 คลาส
    # ให้เองทุกครั้งที่เรียก กันข้อมูลไม่ตรงกันถ้ามีคลาสไหนหายไปกลางทาง)
    for class_name, count in counted_this_request.items():
        r.incrby(f"trash_count:{class_name}", count)

    return {
        "detections": detections,
        "detected_this_image": sum(counted_this_request.values()),
    }


@app.get("/stats")
def stats():
    """
    ดึงจำนวนขยะสะสมทั้งหมดจาก Redis มาแสดงบนแดชบอร์ด
    คืนค่าเรียงลำดับตายตัวเสมอ: plastic, recyclable, organic แล้วปิดท้าย
    ด้วย total เพื่อให้ frontend เอาไปแสดงผลทีละบรรทัดตามลำดับได้ง่าย
    """
    result = {}
    for class_name in TRASH_CLASSES:
        count = r.get(f"trash_count:{class_name}")
        result[class_name] = int(count) if count else 0
    result["total"] = sum(result.values())
    return result
