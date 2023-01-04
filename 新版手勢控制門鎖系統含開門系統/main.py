import time
import RPi.GPIO as GPIO
import threading
from FingerNumber import FN
from flask import Flask, render_template, request
# ---------------------可調整區域----------------------
I2C_OLED = True            # 是否啟用OLED功能
cv2_Screen = True          # 顯示偵測手指的畫面(省資源可以設定成False關閉)
Detection_interval = 1.5   # 偵測間隔時間(單位:秒)
# ---------------------------------------------------
Password = None            # 設定的密碼 (網頁設定)
Entered = ""               # 已輸入的密碼
Survival_Time = None       # 密碼存活時間(單位:秒) (網頁設定)
Survival_start_Time = None # 密碼存活時間開始記錄時間 (依靠被設定密碼時觸發啟用)
#----------------------馬達設定-------------------------
GPIO.setmode(GPIO.BOARD)
GPIO.setup(11,GPIO.OUT)
servo1 = GPIO.PWM(11,50)
# ---------------------motor active------------------------
def doorlongactive():
    oled_control(['long open door',''])
    print("門保持開啟10秒")
    servo1.start(0)
    time.sleep(2)
    servo1.ChangeDutyCycle(7)
    time.sleep(10)
    print("close")
    servo1.ChangeDutyCycle(2)
    time.sleep(2)
    servo1.ChangeDutyCycle(0)
def doorshortactive():
    oled_control(['short open door',''])
    print("門保持開啟4秒")
    servo1.start(0)#start PWM running, but with value of 0 (pulse off)
    time.sleep(1)
    servo1.ChangeDutyCycle(7)#轉90度
    time.sleep(4)                    
    servo1.ChangeDutyCycle(2)#轉0度
    time.sleep(0.5)
    servo1.ChangeDutyCycle(0)
#----------------------------------------------------

# ----------- I2C OLED 點矩陣液晶顯示器----------
if I2C_OLED:
    from luma.core.interface.serial import i2c, spi
    from luma.core.render import canvas
    from luma.oled.device import ssd1306, ssd1325, ssd1331, sh1106
    serial = i2c(port=1, address=0x3C)
    device = ssd1306(serial)
# ---------------------------------------------

# ----------------- Flask 架設的網頁------------------
# 對應html如下
# passinput  輸入欄位
# send       送出按鈕
# timeliness 時效性

app = Flask(__name__)
@app.route('/',methods=['POST','GET'])
def index():
    global Password, Survival_Time, Survival_start_Time
    if request.method =='POST':
        if request.values['send']=='送出':
            Password = request.values['passinput']
            Survival_Time = float(request.values['timeliness'])
            #---------時效性計時----------
            Survival_start_Time = time.time()
            #----------------------------
            return render_template('index.html',tip=f"密碼已設定完成為:{Password} 有效時間為{Survival_Time}秒")
    return render_template('index.html',tip="請輸入你要設定的密碼")
# -------------------- OLED控制 ----------------------
oled_temp = [None,None] # 初始化暫存
def oled_control(text_list=oled_temp): #text_list[0] 代表 OLED 的第一行, text_list[1]代表第二行 #並且設定預設值
    global oled_temp
    if oled_temp != text_list:
        oled_temp = text_list # 暫存資料與新資料同步
        if I2C_OLED:
            device.cleanup = ""
            with canvas(device) as draw:
                draw.rectangle(device.bounding_box, outline="white", fill="black")
                if len(text_list[0]) < 15:
                    draw.text((30, 20), F"{text_list[0]}\n{text_list[1]}", fill="white")
                else:
                    draw.text((20, 20), F"{text_list[0]}\n{text_list[1]}", fill="white")
        else:
            for index in range(2):
                print('OLED顯示 :',text_list[index])
# ---------------------------------------------------
FingerNum = FN() # 將FN class 示例化
def main():
    global Password, Entered, Survival_start_Time
    Number_of_errors = 3 # 密碼錯誤次數 
    while True:
        # ------------------密碼判定----------------------
        if Password: # 若設定的密碼存在
            if str(FingerNum.dtnum) != "inter" and Password != "Pass_1" and Entered != "Pass": # 會加上and是因為要是沒比動作會直接回傳None所以這樣寫能防止輸入None
                Entered += str(FingerNum.dtnum) if FingerNum.dtnum else ""
                oled_control(['Enter Password:',Entered])
                # print("已輸入密碼 :", Entered)
            elif Entered == "Pass" and Password == "Pass_1":
                    print("1")
                    oled_control(['long open door','Please Great'])
                    print("門保持開啟4秒，請比 ok")
                    print("長時間保持開啟，請比 讚")
                    if FingerNum.dtnum == "Great" and FingerNum.dtnum:
                        doorlongactive()
                        Entered = ""  #  輸入的密碼清除
                        Password = "" #  設定的密碼清除
                    elif str(FingerNum.dtnum) =="ok" and FingerNum.dtnum:
                        doorshortactive()
                        Entered = ""  #  輸入的密碼清除
                        Password = "" #  設定的密碼清除
            elif str(FingerNum.dtnum) == "inter" and FingerNum.dtnum:
                if Password == Entered:
                    Entered = "Pass"
                    Password = "Pass_1" #  設定
                    oled_control(['Enter Password:','Pass'])
                    print("密碼正確")
                else:
                    Entered = "" # 已輸入清除
                    Number_of_errors -= 1 # 密碼輸入錯誤次數減少
                    print("密碼錯誤，大門未動作")
                    oled_control(['Enter Password:','Fail'])
                    if not Number_of_errors:
                        Password = None #  設定的密碼清除
                        Number_of_errors = 3 # 重新初始化密碼錯誤次數
                        print("錯誤次數過多，已重置密碼")
            # ---------------密碼時效---------------------
            if time.time() - Survival_start_Time >= Survival_Time: # 現在時間 - 設定密碼時間 >= 設定的密碼存活時間
                Password = None
                print("密碼時效性已過，密碼已經清除")
        else: # 若設定的密碼不存在
            oled_control(['No Password','Set Password'])
            print("密碼不存在 請設定密碼")
        # -----------------------------------------------
        time.sleep(Detection_interval) # 限制設定的偵測間隔時間

if __name__ == '__main__':
    threading.Thread(target=FingerNum.detect, args=(cv2_Screen,)).start() # 啟動偵測手勢的線程
    threading.Thread(target=main).start() # 啟動主要的線程
    app.run(host='0.0.0.0',port=8080) # 啟動Flask網頁框架
