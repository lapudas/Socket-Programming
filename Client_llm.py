import socket          # 提供 TCP/IP 通訊功能
import threading       # 用於建立多執行緒（背景接收訊息）
import wx              # GUI 框架：wxPython

# === 基本連線設定 ===
HOST = "127.0.0.1"       # 伺服器 IP（需與 server.py 一致）
PORT = 5678              # 伺服器 TCP 埠號（需與 server.py 一致）
BUFFER_SIZE = 256        # 每次接收的最大位元組數（對應 C 程式 buf 大小）

# === 建立與伺服器的連線 ===
def build_connect():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # 建立 IPv4/TCP socket
    sock.connect((HOST, PORT))  # 連線至伺服器
    data = sock.recv(BUFFER_SIZE)  # 接收伺服器初始回覆
    print(data.decode(errors='replace').strip())  # 顯示伺服器訊息（去除多餘換行）
    return sock

sock = build_connect()

# === 從伺服器接收訊息的執行緒函式 ===
def recieve_m(sock, m_box, panel):
    """
    背景執行緒函式：負責不斷接收伺服器訊息並更新 GUI。
    - sock: 與伺服器的 TCP socket
    - m_box: 聊天訊息的 BoxSizer（垂直排列）
    - panel: 承載訊息的 wx.ScrolledWindow
    """

    def add_box(m_box, panel, data):
        """在 GUI 執行緒中新增一條訊息文字"""
        m_text = wx.StaticText(panel, label=data)
        m_box.Add(m_text, 0, wx.ALL, 2)  # 增加一點間距讓訊息更清楚
        panel.Layout()                   # 更新版面配置
        panel.FitInside()                # 更新捲軸大小（若內容超出可見範圍）

    while True:
        data = sock.recv(BUFFER_SIZE)  # 等待伺服器發來訊息
        if not data:
            break  # 伺服器斷線時退出迴圈
        text = data.decode(errors='replace').strip()
        # wx.CallAfter 確保在 GUI 主執行緒更新介面（避免 thread 衝突）
        wx.CallAfter(add_box, m_box, panel, text)


# === 初始輸入名稱的視窗 ===
class InputFrame(wx.Frame):
    """
    第一步輸入名稱的視窗。
    在送出名稱後，切換至主聊天視窗。
    """
    def __init__(self):
        super().__init__(None, title="輸入名稱", size=(300, 100))
        panel = wx.Panel(self)

        self.name = wx.TextCtrl(panel, pos=(10, 10))
        button = wx.Button(panel, wx.ID_ANY, '確認', pos=(140, 10))
        button.Bind(wx.EVT_BUTTON, self.closing)

    def closing(self, event):
        """送出使用者名稱並切換至主聊天畫面"""
        my_name = self.name.GetValue()
        sock.sendall(my_name.encode())  # 傳送使用者名稱給伺服器

        start_msg = sock.recv(BUFFER_SIZE)
        print(start_msg.decode(errors='replace').strip())

        self.Close()              # 關閉目前輸入視窗
        MainFrame(my_name).Show() # 顯示主聊天視窗


# === 主聊天視窗 ===
class MainFrame(wx.Frame):
    """
    主聊天室介面：
    - 顯示所有訊息
    - 輸入框可發送訊息
    - 支援自動捲動顯示新訊息
    """
    def __init__(self, title):
        super().__init__(None, title=title, size=(600, 600))

        panel = wx.Panel(self)

        # === 訊息顯示區（可捲動） ===
        self.msg_panel = wx.ScrolledWindow(panel, size=(600, 500))
        self.msg_panel.SetScrollRate(5, 5)  # 設定捲動速度
        self.message_box = wx.BoxSizer(wx.VERTICAL)
        self.msg_panel.SetSizer(self.message_box)

        # === 輸入框與按鈕 ===
        self.msg_input = wx.TextCtrl(panel, pos=(10, 510), size=(480, 30))
        send_btn = wx.Button(panel, wx.ID_ANY, '發送', pos=(500, 510))
        send_btn.Bind(wx.EVT_BUTTON, self.send)

        # === 關閉視窗事件 ===
        self.Bind(wx.EVT_CLOSE, self.disconnect)

        # === 建立接收執行緒 ===
        thread_ = threading.Thread(target=recieve_m, args=(sock, self.message_box, self.msg_panel))
        thread_.daemon = True   # 設為背景執行緒，主程式結束時自動退出
        thread_.start()

    def send(self, event):
        """將輸入文字送出給伺服器"""
        global sock
        text = self.msg_input.GetValue().strip()
        
        if not text:  # 若輸入為空，直接返回
            return
        
        try:
            # 嘗試直接送訊息
            sock.sendall(text.encode())
            self.msg_input.Clear()
        except:
            # 若送訊息失敗，代表 socket 可能斷線
            sock = build_connect()
            
            # 送出當前使用者名稱給 server
            sock.sendall(self.GetTitle().encode())
            start_m = sock.recv(BUFFER_SIZE)
            print(start_m.decode(errors='replace').strip())
            
            # 啟動新的接收訊息 thread
            thread_ = threading.Thread(target=recieve_m, args=(sock, self.message_box, self.msg_panel))
            thread_.daemon = True
            thread_.start()
            
            # 最後再送出使用者原本輸入的訊息
            sock.sendall(text.encode())
            self.msg_input.Clear()

    def disconnect(self, event):
        """當使用者關閉視窗時斷開連線"""
        print("Close connection!")
        try:
            sock.close()
        except Exception:
            pass
        self.Destroy()


# === 主程式入口 ===
if __name__ == "__main__":
    app = wx.App()
    InputFrame().Show()
    app.MainLoop()
