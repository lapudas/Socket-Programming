import socket      # 匯入標準庫 socket，提供 TCP / IP 網路通訊功能
import threading   # 匯入 threading 模組，用於多執行緒處理多個客戶端

# === 基本伺服器設定 ===
HOST = "127.0.0.1"   # 伺服器綁定的 IP（127.0.0.1 為本機）
PORT = 5678          # 伺服器監聽的 TCP 埠號（client 端需一致）
BUFFER_SIZE = 256    # 每次接收資料的最大位元組數
BACKLOG = 5          # listen 時最多允許等待的連線數

# === 建立伺服器 socket ===
srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)     # 建立 IPv4 / TCP socket
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)   # 允許位址重用（避免重啟時綁定失敗）
srv.bind((HOST, PORT))                                      # 綁定 IP 與埠號
srv.listen(BACKLOG)                                         # 進入監聽狀態，等待客戶端連線
print(f"[server] Listening on {HOST}:{PORT} ...")

# === 儲存所有已連線的客戶端 socket ===
all_client = []             # 用來廣播訊息給所有客戶端
lock = threading.Lock()     # 多執行緒下使用 lock 避免同時修改 all_client 發生衝突

def client_OOT(conn, addr):
    end_m = f"!!! Out of time, connection closed. !!!"
    conn.sendall(end_m.encode())
    conn.close()
    print(f"{addr} OOT, close connection.")

def client_chart(conn, addr):
    """
    處理單一客戶端的連線。
    - 先接收使用者名稱
    - 進入訊息接收 / 廣播迴圈
    - 客戶端中斷後清理資源
    """
    try:
        # 設置計時器處理超時
        timer = threading.Timer(60, client_OOT, args=(conn,addr))
        timer.start()
        
        # 收取使用者名稱
        user_name = conn.recv(BUFFER_SIZE).decode(errors="replace").strip()
        start_m = f"hello, {user_name}. Now you are in chatting room."
        conn.sendall(start_m.encode())

        # 開始聊天迴圈：不斷接收並廣播訊息
        while True:
            data = conn.recv(BUFFER_SIZE)   # 從客戶端接收資料
            
            # 重置計時器
            timer.cancel()
            timer = threading.Timer(60, client_OOT, args=(conn,addr))
            timer.start()
            
            if not data:
                # 收到空資料代表對端關閉連線
                print(f"[server] {addr} closed the connection.")
                break

            text = data.decode(errors="replace")  # 將位元組轉成字串（不合法字元用替代符號）
            print(f"Read Message: {text}", end="")  # 顯示接收到的訊息（不自動換行）

            # 將發送者名稱附加到訊息前方
            message = f"{user_name}: {text}"
            data_to_send = message.encode()

            print(f"Send Message: {message.strip()}")  # 顯示伺服器即將發送的內容

            # 廣播給所有已連線的客戶端
            with lock:
                for c in all_client:
                    try:
                        c.sendall(data_to_send)
                    except Exception:
                        # 若有連線中斷或錯誤，移除該客戶端
                        all_client.remove(c)
                        c.close()

    finally:
        # 離開聊天室時清除連線
        with lock:
            if conn in all_client:
                all_client.remove(conn)
        conn.close()
        print(f"[server] {addr} connection closed and removed.")


if __name__ == "__main__":
    try:
        # 主迴圈：持續接受新的客戶端連線
        while True:
            conn, addr = srv.accept()  # 阻塞等待一個客戶端連線
            print(f"[server] Connected by {addr}")

            # 將新連線加入列表（供廣播使用）
            with lock:
                all_client.append(conn)

            # 傳送初始訊息要求使用者輸入名稱
            success_m = "connection success\nYour name is ?"
            conn.sendall(success_m.encode())

            # 啟動新執行緒處理該客戶端
            thread_ = threading.Thread(target=client_chart, args=(conn, addr))
            thread_.start()

    except KeyboardInterrupt:
        print("\n[server] Shutting down by user interrupt...")

    finally:
        # 關閉所有連線與伺服器 socket
        with lock:
            for c in all_client:
                c.close()
        srv.close()
        print("[server] Socket closed.")
