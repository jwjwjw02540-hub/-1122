# เครื่องมือวิเคราะห์ฟุตบอล (สำเร็จรูป)

Dixon-Coles · สูงต่ำ · แฮนดิแคป · คาดสกอร์  
พร้อมขึ้นเว็บด้วย Streamlit Cloud ได้ทันที

## ไฟล์ในแพ็กเกจ

- `app.py` — เว็บแอป Streamlit
- `football_analyzer.py` — แกนโมเดล
- `requirements.txt` — dependencies
- `README.md` — คู่มือนี้

## ขึ้นเว็บฟรี (Streamlit Cloud) — 3 ขั้นตอน

### 1. อัปขึ้น GitHub
1. สร้าง repository ใหม่บน [github.com](https://github.com) (Public)
2. อัปโหลดไฟล์ทั้ง 4 ไฟล์นี้ขึ้นไป (drag & drop ได้เลย)

### 2. Deploy
1. ไปที่ [share.streamlit.io](https://share.streamlit.io)
2. Sign in ด้วย GitHub
3. กด **New app**
4. เลือก repository ที่เพิ่งสร้าง
5. Main file path: `app.py`
6. กด **Deploy**

### 3. เสร็จ
รอประมาณ 1-2 นาที จะได้ลิงก์เว็บ เช่น  
`https://yourname-football-analyzer.streamlit.app`

เปิดลิงก์นั้นได้จากทุกที่

## ใช้งานบนเว็บ

1. เปิดลิงก์
2. (ถ้าต้องการข้อมูลจริง) ดาวน์โหลด CSV จาก [football-data.co.uk/data.php](https://www.football-data.co.uk/data.php)
3. อัปโหลดใน Sidebar หรือใช้ข้อมูลจำลองก่อน
4. กด **โหลด & ฟิตโมเดล**
5. เลือกทีมแล้วกดวิเคราะห์

## รันบนเครื่องตัวเอง (ถ้าอยากทดสอบก่อน)

```bash
pip install -r requirements.txt
streamlit run app.py
```

## ข้อมูลที่รองรับ

CSV จาก football-data.co.uk ใช้ได้ทันที  
คอลัมน์ที่ต้องมี: `Date`, `HomeTeam`, `AwayTeam`, `FTHG`, `FTAG`

---

**หมายเหตุ:** โมเดลนี้เป็น baseline ที่ดี แต่ตลาดโดยเฉพาะ Asian Handicap / Over/Under ถูกตั้งราคาแน่น ควรใช้เป็นเครื่องมือวิเคราะห์ ไม่ใช่สัญญาณเดิมพันโดยตรง
