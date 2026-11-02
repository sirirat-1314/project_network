# คู่มือโปรเจค Network กลุ่ม G18

อ้างอิง project_network.pdf บท 14 หน้าเอกสาร 261–271 (PDF 11 หน้า)

สถานะ: เตรียมโค้ดและวิธีทดลองแล้ว ยังไม่ได้รัน Mininet ใน Ubuntu VM ของคุณ และยังไม่มีผลวัดจริง ห้ามใช้ค่าคาดการณ์แทนผลทดลอง

## 1. เราจะทำอะไร และทำไปเพื่ออะไร

สร้างเครือข่ายจำลอง h1 → s1 → h2 โดย h1 เป็นผู้ส่ง s1 เป็นสวิตช์ และ h2 เป็นผู้รับ ส่งข้อมูล UDP เป็นชุด ๆ แล้วเปรียบเทียบว่าเมื่อควบคุมการส่ง ข้อมูลที่ปลายทางได้รับเปลี่ยนไปอย่างไร

ทดลอง 3 สถานการณ์:

1. **Before:** ยังไม่ใส่ shaper ที่ h1 แต่เส้นทางยังมีข้อจำกัด 2 Mbps
2. **TBF:** ใส่ Token Bucket Filter ของ Linux อัตรา 1,024 kbit/s
3. **Leaky:** ใช้คิว Python ปล่อยแพ็กเก็ตตามจังหวะ ไม่ใส่ TBF ซ้ำ เพื่อดูผลของ Leaky Bucket โดยตรง

โจทย์ Part D มีคำว่า Optional แต่ข้อความระบุให้กลุ่มที่ได้ leaky_bucket เขียนเอง และรายการส่งงานขอโค้ดนี้สำหรับกลุ่มดังกล่าว จึงเตรียมส่วนนี้ให้ด้วยสำหรับ G18

ไม่ต้องต่อเครื่องจริง 3 เครื่อง Mininet จำลอง host ด้วย Linux network namespaces บน VM เดียว ส่วนสวิตช์ใช้ Open vSwitch

## 2. ค่าประจำกลุ่ม

ใช้รหัส **G18** ตามรูปแบบ G07 ในโจทย์ ไม่ใช้ 18 หรือ g18 เพราะ seed และผลสุ่มจะเปลี่ยน หากอาจารย์กำหนดรหัสรูปแบบอื่น ต้องสร้างค่าใหม่และแก้โค้ดที่ผูกกับ G18 ด้วย

| ตัวแปร | ค่า G18 | ความหมาย |
|---|---:|---|
| bandwidth_mbps | 2 | ความเร็วลิงก์จำลอง Mbps |
| token_rate_kbit | 1024 | อัตราเติม token / อัตราควบคุม kbit/s |
| bucket_size_kbit | 16 | ความจุ token pool ไม่ใช่จำนวนแพ็กเก็ตในคิว |
| burst_size_packets | 78 | จำนวนแพ็กเก็ตต่อชุด |
| burst_interval_ms | 200 | พักหลังส่งหรือใส่คิวแต่ละชุด 200 ms |
| packet_size_bytes | 1400 | ขนาด Raw payload ตามโค้ดตัวอย่างในโจทย์ |
| algorithm | leaky_bucket | อัลกอริทึมที่กลุ่มได้รับ |
| latency_ms | 400 | ค่าที่ใช้คำนวณขีดจำกัดคิวของ TBF |

โค้ดโจทย์นำ string รหัสกลุ่มไป hash ด้วย MD5 แล้วใช้เป็น seed ของ random.Random เพื่อให้รหัสเดิมได้ค่าเดิม ลำดับการเรียกสุ่มต้องเหมือนเดิม MD5 ในที่นี้ใช้สร้าง seed ไม่ได้ใช้รักษาความปลอดภัย

ส่ง 10 ชุด × 78 = **780 แพ็กเก็ตที่เสนอเข้าระบบ** ต่อการทดลอง

IPv4 ไม่มี options ใช้ header 20 bytes และ UDP ใช้ 8 bytes ดังนั้น IP packet = 1,428 bytes; Ethernet frame ที่จับได้ทั่วไป = 1,442 bytes ไม่รวม FCS, preamble และ inter-frame gap โค้ดใส่เลขลำดับไว้ใน payload 1,400 bytes เดิม ไม่ได้เพิ่มความยาว

## 3. ทำความเข้าใจอัลกอริทึม

### Token Bucket

นึกถึงสิทธิ์ส่งข้อมูลที่สะสมไว้: ถ้ามี token พอ แพ็กเก็ตส่งได้ทันที ถ้าไม่พอต้องรอ และถ้าคิวเต็มจะถูกทิ้ง เมื่อว่างนาน token จะสะสมได้มากขึ้นจนเต็ม bucket จึงอนุญาตให้เกิด burst ได้ในขอบเขตหนึ่ง

rate = 1,024,000 bit/s = 128,000 byte/s และ bucket 16 kbit ใช้ข้อตกลงหน่วยฐานสิบเป็น 16,000 / 8 = **2,000 bytes** เราจึงระบุ `burst 2000` ให้ชัดเจน ไม่สับสนกับ kB หรือการตีความ suffix หน่วยของ tc แต่ละชนิด บันทึกข้อตกลงนี้ในรายงาน หากผู้สอนต้องการการตีความ suffix `16kbit` แบบตรงตัว ให้ตรวจ `man tc` ของเครื่องและรายงานจำนวน bytes ที่ tc แสดง

เวลาเติม bucket จากว่างจนเต็มโดยไม่มีการส่ง = 16,000 / 1,024,000 = **15.625 ms** ไม่ได้แปลว่าแต่ละแพ็กเก็ตต้องรอ 15.625 ms

`latency 400ms` ใช้ให้ tc คำนวณขนาดคิว ไม่ได้เป็นคำสั่งหน่วงทุกแพ็กเก็ต 400 ms และไม่ใช่การตรวจอายุแล้วทิ้งตรง 400 ms ของทุกแพ็กเก็ตแบบ real-time

### Leaky Bucket

เก็บแพ็กเก็ตใน FIFO (เข้าก่อนออกก่อน) และกำหนดระยะห่างการปล่อย เมื่อคิวเต็มแพ็กเก็ตใหม่ถูกทิ้ง คิวว่างก็ไม่มีข้อมูลให้ปล่อย จึงไม่ได้ส่งข้อมูลตลอดเวลาโดยไม่มี input

โค้ดนี้กำหนดจังหวะจาก Ethernet frame 1,442 bytes:

```text
drain rate = 1,024,000 / (1,442 × 8) ≈ 88.7656 packets/s
interval   = (1,442 × 8) / 1,024,000 = 0.011265625 s
           = 11.265625 ms/packet
queue capacity = floor(88.7656 × 0.4) = 35 packets
```

**35 packets เป็นตัวเลือกการออกแบบของเรา** ที่อิงงบเวลารอ 400 ms ไม่ใช่ค่า queue capacity ที่โจทย์สุ่มให้ และไม่ใช่การแปลง token bucket 16 kbit เป็นคิว Leaky Bucket นอกจากนี้อาจมี 1 แพ็กเก็ตที่ worker หยิบออกจากคิวแล้วกำลังรอส่ง

Python และระบบปฏิบัติการไม่รับประกันเวลาแม่นยำทุกไมโครวินาที ผลจริงอาจช้ากว่าอัตราที่ตั้ง เพราะมีเวลาส่งและ scheduling โค้ดไม่เร่งส่งชดเชยเป็น burst หลังเครื่องหยุดไปชั่วคราว จึงเป็นการสาธิต fixed pacing แบบ best effort ไม่ใช่ hardware real-time shaper

## 4. ไฟล์แต่ละตัวทำอะไร

| ไฟล์ | หน้าที่ |
|---|---|
| generate_group_params.py | คำนวณค่ากลุ่มด้วยสูตรและลำดับสุ่มจากโจทย์ |
| topo_bucket.py | สร้าง h1–s1–h2, IP/MAC คงที่, ลิงก์ 2 Mbps, เปิด Mininet CLI |
| generate_burst_traffic.py | สร้างแพ็กเก็ต Scapy 780 แพ็กเก็ต ส่งแบบ direct หรือเข้า Leaky Bucket และบันทึก JSON |
| leaky_bucket_shaper.py | FIFO ขนาดจำกัดและ worker ปล่อยแพ็กเก็ตเป็นจังหวะ; รันเป็นโปรแกรมส่งแบบ leaky ได้ |
| udp_sink.py | เปิดพอร์ต 5000 ที่ h2 รับ UDP เพื่อไม่ให้ระบบตอบ ICMP port unreachable |
| analyze_pcap.py | อ่าน pcap จริง นับ sequence และคำนวณตัวชี้วัด |

ใช้ Scapy L2 socket เดิมตลอดการส่ง แทนการเปิด socket ใหม่ทุกแพ็กเก็ต เพื่อลด overhead ที่อาจทำให้ burst กลายเป็นการส่งช้า ๆ ส่วน IP/MAC ปลายทางล็อกไว้เฉพาะ topology นี้

## 5. เตรียม Ubuntu ใน VMware

ย้ายโฟลเดอร์ G18 ทั้งโฟลเดอร์เข้า Ubuntu เช่น `/home/ชื่อผู้ใช้/Project_Network/G18` ผ่าน shared folder หรือการคัดลอกไฟล์ที่ใช้อยู่ จากนั้นเปิด Terminal ในโฟลเดอร์ G18 จริง ๆ คำสั่งถัดไปใช้ relative paths จึงควรรันจากโฟลเดอร์นี้ตลอด

ตรวจของเดิมก่อน:

```bash
pwd
ls
python3 --version
mn --version
python3 -c "import mininet, scapy; print('Python dependencies OK')"
tc -V
tcpdump --version
sudo ovs-vsctl show
```

ถ้าขาดเครื่องมือ ให้ติดตั้งใน **Ubuntu Terminal**:

```bash
sudo apt update
sudo apt install -y mininet openvswitch-switch python3-scapy tcpdump wireshark iproute2
sudo systemctl start openvswitch-switch
```

Wireshark ใช้เปิดไฟล์ภายหลังได้ ไม่ต้องรันด้วย sudo เพราะเราใช้ tcpdump เป็นตัวจับแพ็กเก็ต หาก service เริ่มไม่ได้ให้เก็บข้อความ error ไว้วิเคราะห์ก่อน

ตรวจค่ากลุ่มและสร้างที่เก็บผล:

```bash
mkdir -p results
python3 generate_group_params.py G18 | tee results/group_params.json
```

**ผ่านขั้นนี้เมื่อ:** ค่าทั้ง 8 ตัวตรงตารางด้านบน และ import dependencies สำเร็จ

## 6. สร้างเครือข่าย (Part A)

ใน Ubuntu Terminal:

```bash
sudo python3 topo_bucket.py
```

เมื่อเห็น `mininet>` ให้พิมพ์คำสั่งด้านล่าง **ไม่ต้องพิมพ์คำว่า mininet> ซ้ำ**:

```text
nodes
net
h1 ping -c 3 h2
h1 ip addr show h1-eth0
h2 ip addr show h2-eth0
```

ควรพบ h1, h2, s1 และ ping ได้ โค้ดตั้ง switch เป็น standalone จึงไม่ต้องเปิด controller แยก และกำหนด ARP ไว้ล่วงหน้าเพื่อลด traffic ที่ไม่เกี่ยวกับการทดลอง

### จัดระบบคิวก่อนเริ่ม

Mininet TCLink ใส่ root qdisc ให้แล้ว จึงไม่ใช้ `tc qdisc add ... root` ทับโดยไม่ตรวจ เราจะเปลี่ยนเฉพาะ h1 เป็น FIFO เดียวกันสำหรับ baseline และ Leaky ส่วน s1-eth2 ยังคงจำกัดทางไป h2 ที่ 2 Mbps

```text
h1 tc qdisc replace dev h1-eth0 root pfifo limit 1000
h1 tc -s qdisc show dev h1-eth0
sh tc -s qdisc show dev s1-eth2
h2 sh -c 'python3 udp_sink.py > results/sink.log 2>&1 & echo $! > results/sink.pid'
```

การทดลองนี้จึงเป็น path bandwidth 2 Mbps ที่ยังคงอยู่ทั้งสามกรณี แต่ไม่ได้เก็บ root HTB ของ h1 ซ้อนใต้ TBF และไม่ได้อ้างว่า topology ไม่มีข้อจำกัดความเร็วใน baseline

**ผ่านขั้นนี้เมื่อ:** ping ผ่าน, h1 แสดง pfifo และ s1-eth2 ยังมีระบบคิวจำกัด bandwidth จาก Mininet ให้บันทึกภาพ topology/ผล ping และข้อความ qdisc

## 7. เก็บผลก่อน shaping (Part C)

คำสั่งทั้งหมดใน Mininet CLI:

```text
h2 sh -c 'tcpdump -Z root -i h2-eth0 -n -s 0 -U -w results/before_shaping.pcap "udp dst port 5000 and src host 10.0.0.1" > results/before_capture.log 2>&1 & echo $! > results/capture.pid'
sh sleep 1
h2 cat results/before_capture.log
h1 python3 generate_burst_traffic.py --log results/before_sender.json
sh sleep 6
h2 sh -c 'kill -INT "$(cat results/capture.pid)"'
sh sleep 1
h2 cat results/before_capture.log
```

ก่อนส่งต้องเห็น `listening on h2-eth0` ใน log หาก error ให้แก้ก่อนส่ง เราเริ่ม capture ก่อนเพื่อไม่ให้พลาดแพ็กเก็ตแรก และรอหลังส่งเพื่อให้ข้อมูลที่ค้างในคิวไปถึง h2

6 วินาทีเป็นเวลารอเผื่อสำหรับ input 780 แพ็กเก็ตของ G18 ตรวจ qdisc ว่า backlog หมดด้วยหาก VM ช้า หากยังค้างต้องรอเพิ่ม **ก่อนหยุด capture** การหยุดด้วย SIGINT ทำให้ tcpdump ปิดไฟล์และพิมพ์สถิติ

**ผ่านขั้นนี้เมื่อ:** sender มี offered=780, sent=780, queue_dropped=0; tcpdump log มี `0 packets dropped by kernel` ผลรับไม่จำเป็นต้องเท่ากับส่ง เพราะ network queue อาจ drop ได้

## 8. เปรียบเทียบกับ Linux TBF (Part B)

```text
h1 tc qdisc replace dev h1-eth0 root tbf rate 1024kbit burst 2000 latency 400ms
h1 tc -s qdisc show dev h1-eth0
h2 sh -c 'tcpdump -Z root -i h2-eth0 -n -s 0 -U -w results/after_tbf.pcap "udp dst port 5000 and src host 10.0.0.1" > results/tbf_capture.log 2>&1 & echo $! > results/capture.pid'
sh sleep 1
h2 cat results/tbf_capture.log
h1 python3 generate_burst_traffic.py --log results/tbf_sender.json
sh sleep 6
h1 tc -s qdisc show dev h1-eth0 > results/tbf_qdisc.txt
h2 sh -c 'kill -INT "$(cat results/capture.pid)"'
sh sleep 1
h2 cat results/tbf_capture.log
```

อ่าน `rate`, `burst`, `dropped`, `overlimits`, `backlog` ของ tc: overlimits เป็นเหตุการณ์ที่ shaper ต้องจำกัดการส่ง ไม่เท่ากับจำนวนแพ็กเก็ตสูญหาย ส่วน dropped คือแพ็กเก็ตที่คิวทิ้ง

ถ้า error หรืออัตราจริงไม่ถึงเป้า ให้เก็บ qdisc และ log อย่าแก้ burst เงียบ ๆ เพราะเป็นค่ากลุ่ม ขนาด bucket เล็กและ scheduling ของ kernel มีผลต่ออัตราที่ทำได้

## 9. ทดลอง Leaky Bucket ของกลุ่ม 18 (Part D)

นำ TBF ออกโดยเปลี่ยนเป็น FIFO ก่อน ไม่อย่างนั้นจะวัด shaper สองชั้น:

```text
h1 tc qdisc replace dev h1-eth0 root pfifo limit 1000
h1 tc -s qdisc show dev h1-eth0
h2 sh -c 'tcpdump -Z root -i h2-eth0 -n -s 0 -U -w results/after_shaping.pcap "udp dst port 5000 and src host 10.0.0.1" > results/leaky_capture.log 2>&1 & echo $! > results/capture.pid'
sh sleep 1
h2 cat results/leaky_capture.log
h1 python3 leaky_bucket_shaper.py --log results/leaky_sender.json
sh sleep 6
h2 sh -c 'kill -INT "$(cat results/capture.pid)"'
sh sleep 1
h2 cat results/leaky_capture.log
```

ไฟล์ **after_shaping.pcap คือ Leaky Bucket** ที่เป็นงานหลักของ G18 ส่วน after_tbf.pcap เป็นผลเทียบเพิ่มเติม ระบุชื่อให้ตรงกันในรายงาน

ภายในโปรแกรม producer สร้าง burst 78 แพ็กเก็ต worker อีก thread ค่อย ๆ ปล่อยออกจากคิว ทั้งสองทำงานพร้อมกัน เมื่อจบ input จะรอให้คิวระบายหมดก่อนปิด socket และเขียน JSON

ใน leaky_sender.json ต้องมี `sent + queue_dropped = 780` จำนวน drop ไม่ควรเดาจากสูตรเป็นคำตอบจริง เพราะ worker และ producer ทำงานพร้อมกัน ใช้ค่าที่บันทึกจริง

ทั้งสามกรณีใช้ 10 ชุด × 78 และพักหลังแต่ละชุด 200 ms เหมือนกัน แต่ **เวลาขาเข้าจริงอาจต่างเล็กน้อย** เพราะ direct ส่งผ่าน socket ส่วน leaky ใส่คิว บันทึก burst_start_epochs ไว้ตรวจ ไม่อ้างว่า timestamp ของ input เหมือนกันทุกไมโครวินาที

## 10. หยุดเครือข่ายและคำนวณผล (Part E)

ใน Mininet:

```text
h2 sh -c 'kill "$(cat results/sink.pid)"'
exit
```

กลับสู่ Ubuntu Terminal ในโฟลเดอร์ G18:

```bash
python3 analyze_pcap.py results/before_shaping.pcap --log results/before_sender.json --output results/before_metrics.json
python3 analyze_pcap.py results/after_tbf.pcap --log results/tbf_sender.json --output results/tbf_metrics.json
python3 analyze_pcap.py results/after_shaping.pcap --log results/leaky_sender.json --output results/leaky_metrics.json
```

ใช้ pcap และ sender JSON ของรอบเดียวกัน หากรันซ้ำให้สำรองผลเก่าหรือใช้โฟลเดอร์ใหม่ก่อน เพื่อไม่ให้ไฟล์คนละรอบปนกัน

### ตัวชี้วัดหมายถึงอะไร

1. **Peak throughput:** มากที่สุดในช่วงเวลา 10 ms โดยรวม bytes ของ frame ที่รับในช่วงนั้น ×8 /0.01 /1,000,000 เป็น Mbps การเปลี่ยน bin width ทำให้ peak เปลี่ยน จึงต้องใช้ 10 ms เหมือนกันทุกกรณี
2. **Average throughput:** bits ทั้งหมด /เวลาวัด /1,000,000 โค้ดใช้ขอบ bin 10 ms ที่ครอบแพ็กเก็ตแรกถึงสุดท้ายของแต่ละรอบ รวม bin ว่างระหว่างกลาง แต่ไม่รวมเวลารอ capture ก่อนและหลัง ต้องระบุวิธีนี้ เพราะหน้าต่างแต่ละรอบอาจยาวไม่เท่ากัน
3. **Packet loss:** `(offered − unique received) / offered ×100` offered=780 และใช้เลขลำดับแยก duplicate สำหรับ Leaky ค่านี้รวมที่ Python queue ทิ้งและที่เครือข่ายสูญหาย หากต้องการ network-only loss ให้เทียบกับ sent แยกต่างหาก
4. **Max inter-arrival:** มากที่สุดของ `เวลารับแพ็กเก็ต i − เวลารับแพ็กเก็ต i−1` ไม่ใช่ one-way latency
5. **Jitter ตามโจทย์:** ส่วนเบี่ยงเบนมาตรฐานของ inter-arrival ทั้งชุด โค้ดใช้ population standard deviation (`pstdev`) รวมช่องว่างระหว่าง bursts ด้วย จึงอาจสูงเพราะแหล่งส่งพัก ไม่ใช่ความผิดปกติของเครือข่ายอย่างเดียว

ห้ามใช้เพียง receiver capture อ้างว่า packet loss เกิดที่ TBF แน่นอน ต้องดู sender log, tc counters และ capture drops ประกอบ หาก tcpdump drop เองให้รันใหม่ก่อนสรุปผล

### เปิด Wireshark

เปิด before_shaping.pcap, after_shaping.pcap และ after_tbf.pcap ตามลำดับ อาจเปิดบน Windows หลังคัดลอกไฟล์ออกจาก VM ได้

ใช้ display filter:

```text
ip.src == 10.0.0.1 && ip.dst == 10.0.0.2 && udp.dstport == 5000
```

ไป Statistics → I/O Graphs ตั้ง Interval = 10 ms และใส่ filter เดียวกันในแถวกราฟด้วย ตั้ง Y Axis = Bits หรือ Bits/Tick ตามรุ่น หากเปิดตัวเลือกการแสดงค่าเป็นอัตราต่อวินาที ต้องตรวจหน่วยอีกครั้งก่อนแปลง

**Bits ต่อ 10 ms ไม่ใช่ bits/s:** ถ้าแสดง 10,240 bits ในหนึ่ง tick จะเท่ากับ 10,240/0.01 = 1,024,000 bit/s = 1.024 Mbps ห้ามแปลงซ้ำหากโปรแกรมแสดง bits/s อยู่แล้ว

เก็บภาพกราฟทุกกรณีด้วยช่วงแกนและ interval เทียบกันได้ กราฟ Wireshark กับสคริปต์อาจต่างเล็กน้อยที่ peak เพราะขอบ bin เริ่มคนละตำแหน่ง สคริปต์ align กับ epoch ส่วน GUI อาจ align กับ capture start และอาจเลือกหน้าต่างเวลาเฉลี่ยต่างกัน ต้องเขียนวิธีวัดให้ชัด

| ตัวชี้วัด | Before | Leaky (After) | TBF (เทียบเพิ่ม) |
|---|---|---|---|
| Peak throughput (Mbps) | รอวัด | รอวัด | รอวัด |
| Average throughput (Mbps) | รอวัด | รอวัด | รอวัด |
| Packet loss (%) | รอวัด | รอวัด | รอวัด |
| Max inter-arrival (ms) | รอวัด | รอวัด | รอวัด |
| Jitter / population SD (ms) | รอวัด | รอวัด | รอวัด |

## 11. คาดว่าจะเกิดอะไร โดยยังไม่ใช่ผลทดลอง

ถ้ามองข้ามเวลาส่งแต่ละชุด อัตรา offered payload = 78×1,400×8/0.2 = **4.368 Mbps** และหากนับ Ethernet frame = **4.49904 Mbps** สูงกว่าลิงก์ 2 Mbps และ shaper 1.024 Mbps จึงมีแนวโน้มคิวสะสมและ drop

แต่ generator พัก 200 ms หลังส่งทั้งชุด ไม่ใช่รับประกันเริ่มทุก 200 ms พอดี และ VM/Scapy มี overhead จึงต้องใช้ timestamps ตรวจอัตราขาเข้าจริงด้วย

Baseline เองอาจมี drop และ smooth บางส่วนอยู่แล้วเพราะลิงก์ 2 Mbps ส่วน Leaky มักมีระยะห่างแพ็กเก็ตใกล้จังหวะที่กำหนดขณะมี backlog และอาจ drop มากเนื่องจากคิวเล็ก TBF bucket ของ G18 มีเพียงประมาณหนึ่ง frame เต็ม จึงอาจดูคล้าย Leaky ได้ อย่าคาดว่ากราฟต้องต่างชัดทุกช่วงเวลา

## 12. แนวตอบคำถาม Part F ทั้ง 5 ข้อ

ข้อความต่อไปนี้เป็นแนวคิด ต้องเติมหลักฐานจากผลจริงและแยกสิ่งที่ทดลองกับสิ่งที่อธิบายตามทฤษฎี

**1. เพิ่ม burst ของ TBF แล้วกราฟเปลี่ยนอย่างไร?**

เมื่อ bucket ใหญ่ขึ้นจะสะสมสิทธิ์ส่งได้มากขึ้น ช่วงเริ่มหรือหลังว่างจึงอาจส่งได้มากในเวลาสั้น peak ในกราฟอาจสูงขึ้น แต่ยังถูกจำกัดด้วยลิงก์ 2 Mbps สำหรับ traffic ยาวต่อเนื่อง rate ยังคุมระยะยาว ถ้าจะทดลองเพิ่มจาก 2,000 เป็น 4,000 bytes ให้ทำรอบแยก เก็บ pcap และระบุว่าเป็นการเปลี่ยน parameter เพื่อวิเคราะห์ ไม่ใช้แทนผลหลัก

**2. ลด rate ต่ำกว่า input มาก ๆ เกิดอะไร?**

คิวโต แพ็กเก็ตที่รอมี queueing delay เพิ่ม เมื่อคิวเต็มแพ็กเก็ตใหม่ถูกทิ้ง throughput ขาออกถูกจำกัด อ้างอิง tc dropped, sender/receiver counts และรูปกราฟ การเห็นช่องว่างระหว่าง packet จาก receiver อย่างเดียวไม่พิสูจน์ one-way latency หากต้องการวัด latency ต้องมี timestamp ต้นทางและจับคู่ sequence บนนาฬิกาที่เทียบกันได้

**3. Token กับ Leaky ต่างกันอย่างไรเมื่อ input แบบเดียวกัน?**

Token อนุญาต burst ตามสิทธิ์ที่สะสม Leaky เน้น spacing ที่สม่ำเสมอขณะมีคิว เปรียบเทียบ after_tbf.pcap กับ after_shaping.pcap และอธิบายข้อจำกัดว่า Python scheduling, queue capacity และต้นทุนการส่งทำให้ไม่ใช่ implementation ที่เหมือนกันทุกเงื่อนไข หากเทียบกับเพื่อนต่างกลุ่มต้องระวัง parameter อื่นไม่เท่ากัน

**4. ISP ควรเลือกอะไรสำหรับ video กับ download?**

Token Bucket เหมาะกับการให้ bandwidth เฉลี่ยพร้อมเผื่อการส่งเป็น burst เช่นการดาวน์โหลดหรือเว็บ ส่วน pacing แบบ Leaky มีประโยชน์เมื่อให้ความสำคัญกับความสม่ำเสมอ อย่างไรก็ตาม video streaming สมัยใหม่อาจดาวน์โหลดเป็นช่วง ๆ และระบบจริงอาจใช้หลายเทคนิคร่วมกัน จึงไม่มีคำตอบว่าประเภทหนึ่งต้องใช้วิธีเดียวเสมอ ต้องพิจารณา latency, buffer และรูปแบบ traffic

**5. ทำไม bucket ใหญ่มากอาจดูเหมือนไม่มี shaping?**

หาก token ที่สะสมพอสำหรับข้อมูลทั้งหมดในการทดลองสั้น ข้อมูลอาจผ่านได้เกือบทั้งหมดโดยไม่ต้องรอเติม token จึงดูเหมือนไม่มี shaping แต่เมื่อส่งต่อเนื่องยาวพอให้ token หมด rate ยังจำกัดอยู่ ข้อนี้ขึ้นกับระยะทดลองและ input ไม่ใช่ว่าเพิ่ม bucket แล้ว rate ไม่มีผลถาวร

## 13. จัดรายงานและส่งงาน (Part G)

รายงาน PDF ควรเรียงดังนี้:

1. ชื่อโปรเจค กลุ่ม 18 รายชื่อสมาชิก
2. วัตถุประสงค์และหลักการ Token/Leaky ที่อธิบายด้วยภาษาของตนเอง
3. parameter G18 และข้อตกลงหน่วย payload/frame/bucket
4. topology และสภาพแวดล้อม Ubuntu, Python, Mininet, tc พร้อมรุ่นจริง
5. วิธีทดลองทั้งสามแบบและคำสั่งที่ใช้จริง
6. ภาพกราฟ ตารางผลจริง และคำอธิบายค่าที่ผิดจากคาด
7. คำตอบ Part F ทั้ง 5 ข้อ
8. ข้อจำกัด: timing ของ VM/Python, measurement window, byte accounting และ queue capacity ที่เราเลือก

ส่ง PDF report + ZIP source code และ pcap ตามโจทย์ โดยมี before_shaping.pcap, after_shaping.pcap, after_tbf.pcap เพิ่มเติม, source ทุกไฟล์, params, metrics และ logs ห้ามเติมตารางด้วยค่าคาดการณ์แล้วเรียกว่าเป็นผลจริง

## 14. เมื่อพบปัญหา

- `File exists` ตอนตั้ง tc: ใช้คำสั่ง replace ในคู่มือนี้และตรวจ qdisc ปัจจุบัน
- ping ไม่ผ่าน: ตรวจ Open vSwitch service, `net`, IP, และ standalone switch ก่อนเริ่ม capture
- `No module named scapy`: ติดตั้ง python3-scapy ใน Ubuntu และใช้ `/usr/bin/python3` ที่ตรงกับแพ็กเกจระบบ
- pcap ว่าง: ตรวจ listening log, sender error, interface และการรันคำสั่งบน h1/h2 ที่ถูกตัว
- rate ต่ำกว่าคาด: ตรวจ CPU VM, sender burst timestamps, queue drops, bucket size และช่วงเวลาที่ใช้เฉลี่ย
- Mininet รอบก่อนค้าง: หลังออกจากงานและแน่ใจว่าไม่มี lab อื่นรันอยู่ ค่อยใช้ `sudo mn -c` เพื่อเก็บกวาดทรัพยากร Mininet เดิม แล้วเริ่มใหม่

## เอกสารประกอบ

- โจทย์หลัก: project_network.pdf หน้าเอกสาร 261–271
- Mininet CLI และ namespaces: https://mininet.org/walkthrough/
- TCLink / TCIntf: https://mininet.org/api/classmininet_1_1link_1_1TCIntf.html
- Linux TBF (rate, burst, latency/limit): https://man7.org/linux/man-pages/man8/tc-tbf.8.html
- Scapy: https://scapy.readthedocs.io/en/latest/usage.html
- Wireshark I/O Graphs: https://www.wireshark.org/docs/wsug_html_chunked/ChStatIOGraphs.html

