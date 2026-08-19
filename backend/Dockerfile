# =====================================================================
# Dockerfile - backend (FastAPI + YOLOv8n)
# Image นี้เขียนเองทั้งหมด ไม่ได้ copy มาจากที่อื่น
# =====================================================================

# ใช้ python:3.11-slim เป็น base image เพราะเบากว่า python:3.11 ปกติ
# (ตัด tool ที่ไม่จำเป็นออก ทำให้ image เล็กลงและ build เร็วขึ้น)
FROM python:3.11-slim

# ตั้งค่า working directory ภายใน container เป็น /app
# คำสั่งถัดไปทั้งหมด (COPY, RUN, CMD) จะอ้างอิง path นี้เป็นฐาน
WORKDIR /app

# ติดตั้ง system library ที่ ultralytics/opencv ต้องใช้ตอน runtime
# (libgl1, libglib2.0-0 จำเป็นสำหรับการประมวลผลภาพของ OpenCV)
# ใช้ --no-install-recommends เพื่อไม่ติดตั้ง package เสริมที่ไม่จำเป็น
# และลบ apt cache ทิ้งในบรรทัดเดียวกันเพื่อไม่ให้ layer นี้บวมโดยไม่จำเป็น
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# copy เฉพาะไฟล์ requirements.txt ก่อน (ยังไม่ copy โค้ดทั้งหมด)
# เหตุผล: Docker cache แต่ละ layer ตามลำดับคำสั่ง ถ้า requirements.txt
# ไม่เปลี่ยน แต่โค้ดใน main.py เปลี่ยนบ่อย การแยก copy แบบนี้ทำให้
# ไม่ต้อง pip install ใหม่ทุกครั้งที่แก้โค้ด (build เร็วขึ้นมาก)
COPY requirements.txt .

# ติดตั้ง Python package ตามที่ระบุใน requirements.txt
# --no-cache-dir ทำให้ pip ไม่เก็บ cache ไว้ใน image -> image เล็กลง
RUN pip install --no-cache-dir -r requirements.txt

# copy โค้ดของแอปและไฟล์โมเดลที่เทรนเอง (main.py, best.pt) เข้าไปใน /app
# ภายใน container — best.pt เป็นโมเดล YOLOv8n ที่เทรนจับขยะ 3 ประเภท
# (plastic, organic, recyclable) มาก่อนแล้ว จึงไม่ต้องดาวน์โหลดโมเดล
# จากอินเทอร์เน็ตตอน build หรือตอน runtime อีกเลย
COPY . .

# เปิด port 8000 ให้รู้ว่า container นี้ให้บริการผ่าน port นี้
# (เป็นแค่ documentation ให้ผู้ใช้ image รู้ ไม่ได้ publish port จริง
#  การ publish port จริงกำหนดใน docker-compose.yml ด้วย "ports:")
EXPOSE 8000

# คำสั่งที่รันเมื่อ container เริ่มทำงาน
# ใช้ uvicorn รัน FastAPI app ชื่อ "app" ที่อยู่ในไฟล์ main.py
# --host 0.0.0.0 เพื่อให้เข้าถึงได้จากนอก container (ไม่ใช่แค่ localhost ภายใน)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
