# =====================================================================
# Dockerfile - frontend (Nginx + static HTML)
# Image นี้เขียนเองทั้งหมด (custom nginx.conf + custom index.html)
# ไม่ได้ copy image สำเร็จรูปจากที่อื่นมาใช้ตรง ๆ
# =====================================================================

# ใช้ nginx:alpine เป็น base image เพราะเป็น Linux distro ขนาดเล็ก (alpine)
# ทำให้ image รวมมีขนาดเล็กกว่า nginx ปกติมาก เหมาะกับการเสิร์ฟไฟล์ static
FROM nginx:alpine

# ลบไฟล์ config เริ่มต้นของ nginx image ทิ้งก่อน
# เพื่อป้องกันไม่ให้ config เริ่มต้นมาชนกับ config ที่เราจะใส่เข้าไปเอง
RUN rm /etc/nginx/conf.d/default.conf

# copy ไฟล์ nginx.conf ที่เขียนเองเข้าไปแทนที่ config เดิมของ nginx
# เพื่อกำหนด route /api/ ให้ proxy ไปยัง backend container
COPY nginx.conf /etc/nginx/conf.d/default.conf

# copy หน้าเว็บ static (index.html) เข้าไปในโฟลเดอร์ที่ nginx ใช้เสิร์ฟไฟล์
COPY index.html /usr/share/nginx/html/index.html

# เปิด port 80 ให้รู้ว่า container นี้ให้บริการผ่าน port นี้ (documentation)
EXPOSE 80

# nginx:alpine กำหนด ENTRYPOINT/CMD ให้รัน nginx แบบ foreground ไว้แล้ว
# จึงไม่จำเป็นต้องเขียน CMD ใหม่ในไฟล์นี้ (ใช้ค่าที่สืบทอดมาจาก base image)
