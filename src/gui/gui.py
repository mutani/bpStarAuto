import tkinter as tk
from tkinter import ttk
import threading
import ctypes
import keyboard
import time
import psutil
import multiprocessing
from datetime import timedelta
from ttkbootstrap import Style
from PIL import Image, ImageTk
import yaml
import os
import sys

# プロジェクトルートをPythonパスに追加
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.starAuto import pickAuto
from src.starAuto import fishingAuto

# 設定ファイルを読み込み
def load_config():
    config_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'config', 'guiConfig.yaml'))
    with open(config_path, 'r', encoding='utf-8') as file:
        return yaml.safe_load(file)

config = load_config()
MODE_OPTIONS = config['mode_options']
MODE2_OPTIONS = config['mode2_options']
HOTKEY_OPTIONS = config['hotkey_options']
GUI_CONFIG = config['gui']

class BpStarAutoGUI:
    def __init__(self, master):
        self.master = master
        style = Style(theme=GUI_CONFIG['theme'])
        self.master = style.master
        self.master.title(GUI_CONFIG['title'])
        self.master.geometry(GUI_CONFIG['geometry'])
        self.master.resizable(False, False)
        icon = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        icon = ImageTk.PhotoImage(icon)
        self.master.wm_iconphoto(True, icon)
        self.create_widgets()

        self.thread = None
        self.hotkey = None
        self.start_time = None
        self.running = False
        
        # プロセス間共有変数
        self.process_id = multiprocessing.Value(ctypes.c_int)
        self.shared_count = multiprocessing.Value(ctypes.c_int)  # プロセス間共有用

    def create_widgets(self):
        main_frame = ttk.Frame(self.master, padding="20 20 20 20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.columnconfigure(1, weight=1)

        # モードセレクトボックス
        ttk.Label(main_frame, text="mode:").grid(row=0, column=0, sticky=tk.W, pady=10)
        self.arg1 = ttk.Combobox(main_frame, values=MODE_OPTIONS, style='primary.TCombobox')
        self.arg1.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=10)
        self.arg1.set("fishing")
        self.arg1.bind('<<ComboboxSelected>>', self.on_mode_change)

        # モード2セレクトボックス
        self.arg2_label = ttk.Label(main_frame, text="options:")
        self.arg2_label.grid(row=1, column=0, sticky=tk.W, pady=10)
        self.arg2 = ttk.Combobox(main_frame, values=MODE2_OPTIONS["fishing"], style='primary.TCombobox')
        self.arg2.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=10)
        self.arg2.set(MODE2_OPTIONS["fishing"][0] if MODE2_OPTIONS["fishing"] else "")

        # 強制終了ボタンのセレクトボックス
        ttk.Label(main_frame, text="強制終了ボタン").grid(row=2, column=0, sticky=tk.W, pady=10)
        self.stop_key = ttk.Combobox(main_frame, values=HOTKEY_OPTIONS, style='primary.TCombobox')
        self.stop_key.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=10)
        self.stop_key.set(HOTKEY_OPTIONS[0] if HOTKEY_OPTIONS else "esc")

        # 自動実行ボタン
        self.run_button = ttk.Button(main_frame, text="自動実行", command=self.start_auto_pick, style='success.TButton')
        self.run_button.grid(row=3, column=0, columnspan=2, pady=20)

        # 実行状態表示
        self.status_var = tk.StringVar(value="待機中")
        self.status_label = ttk.Label(main_frame, textvariable=self.status_var, font=('Helvetica', 12, 'bold'))
        self.status_label.grid(row=4, column=0, columnspan=2, pady=10)

        # 実行時間表示
        ttk.Label(main_frame, text="時間:", font=('Helvetica', 12)).grid(row=5, column=0, sticky=tk.W, pady=10)
        self.time_var = tk.StringVar(value="00:00:00")
        self.time_label = ttk.Label(main_frame, textvariable=self.time_var, font=('Helvetica', 12))
        self.time_label.grid(row=5, column=1, sticky=(tk.W, tk.E), pady=10)

        # カウント表示
        ttk.Label(main_frame, text="周回:", font=('Helvetica', 12)).grid(row=6, column=0, sticky=tk.W, pady=10)
        self.count_var = tk.StringVar(value="0")
        self.count_label = ttk.Label(main_frame, textvariable=self.count_var, font=('Helvetica', 12))
        self.count_label.grid(row=6, column=1, sticky=(tk.W, tk.E), pady=10)

        # プログレスバー
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate', style='info.Horizontal.TProgressbar')
        self.progress.grid(row=7, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)

    def on_mode_change(self, event=None):
        """モードが変更されたときに呼び出される"""
        selected_mode = self.arg1.get()
        
        # arg2の選択肢を更新
        if selected_mode in MODE2_OPTIONS:
            options = MODE2_OPTIONS[selected_mode]
            self.arg2.config(values=options)
            
            # デフォルト値を設定
            if options:
                self.arg2.set(options[0])
            else:
                self.arg2.set("")
            
            # ラベルを更新
            if selected_mode == "pick":
                self.arg2_label.config(text="採取種類")
            elif selected_mode == "soloID":
                self.arg2_label.config(text="soloID")
            else:
                self.arg2_label.config(text="オプション")
        
        
    def start_auto_pick(self):
        if self.thread and self.thread.is_alive():
            print("自動実行は既に実行中です")
            return

        # ホットキーを事前に登録
        stop_key = self.stop_key.get()
        if self.hotkey:
            keyboard.remove_hotkey(self.hotkey)
        
        self.hotkey = keyboard.add_hotkey(stop_key, self.stop_auto_pick, suppress=False)
        print(f"ホットキー {stop_key} 登録完了")

        arg1 = self.arg1.get()
        arg2 = self.arg2.get()
        self.thread = threading.Thread(target=self.run_with_timer, args=(arg1, arg2))
        self.thread.start()

        self.status_var.set("実行中")
        self.run_button.config(state='disabled')
        self.progress.start()


    def run_with_timer(self, arg1, arg2):
        self.start_time = time.time()
        self.running = True
        self.update_timer()
        
        # モードに応じて適切なメソッドを呼び出し
        if arg1 == "pick":
            # 別プロセスで実行（tkinter変数は渡さない）
            self.shared_count.value = 0  # カウンターリセット
            process = multiprocessing.Process(target=pickAuto.pick_auto, args=(arg2, self.shared_count, self.process_id))
            process.start()
            self.process_id.value = process.pid  # プロセスIDを保存
            
            # カウンター更新スレッドを開始
            counter_thread = threading.Thread(target=self.update_count_from_shared)
            counter_thread.daemon = True
            counter_thread.start()
            
            process.join()  # プロセス終了を待機
            
        elif arg1 == "fishing":
            # 別プロセスで実行（tkinter変数は渡さない）
            self.shared_count.value = 0  # カウンターリセット
            process = multiprocessing.Process(target=fishingAuto.fishing_auto, args=(arg2, self.shared_count, self.process_id))
            process.start()
            self.process_id.value = process.pid  # プロセスIDを保存
            
            # カウンター更新スレッドを開始
            counter_thread = threading.Thread(target=self.update_count_from_shared)
            counter_thread.daemon = True
            counter_thread.start()
            
            process.join()  # プロセス終了を待機
            
        elif arg1 == "soloID":
            # テスト用処理（スレッドのまま）
            pass
            
        self.running = False
        self.master.after(0, self.update_status, "完了")

    def update_count_from_shared(self):
        """共有カウンターをGUIに反映"""
        while self.running:
            try:
                current_count = self.shared_count.value
                self.master.after(0, lambda: self.count_var.set(str(current_count)))
                time.sleep(0.5)  # 0.5秒間隔で更新
            except:
                break

    def update_timer(self):
        if self.running:
            elapsed_time = time.time() - self.start_time
            self.time_var.set(str(timedelta(seconds=int(elapsed_time))))
            self.master.after(1000, self.update_timer)

    def stop_auto_pick(self):
        print("*** 強制終了ボタンが押されました ***")  # デバッグログ
        if self.thread and self.thread.is_alive():
            # まず running フラグを停止
            self.running = False
            # プロセス終了処理（process_idが設定されている場合）
            if self.process_id.value != 0:
                self.terminate_process(self.process_id)
                print(f"プロセス {self.process_id.value} を終了しました")
            else:
                # プロセスIDが0の場合はスレッド強制終了
                thread_id = self.thread.ident
                res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(thread_id), ctypes.py_object(SystemExit))
                if res > 1:
                    ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(thread_id), None)
                    self.update_status("プロセス強制終了失敗")
                else:
                    self.update_status("スレッド強制終了")
            
            # ホットキーを削除
            if self.hotkey:
                keyboard.remove_hotkey(self.hotkey)
                self.hotkey = None
                
            self.update_status("強制終了")
        else:
            self.update_status("待機中")


    def terminate_process(self, pid):
        try:
            # pid が Synchronized オブジェクトの場合、.value を使用して整数値を取得
            if isinstance(pid, multiprocessing.sharedctypes.Synchronized):
                pid = pid.value
            p = psutil.Process(pid)
            p.terminate()  # プロセスを終了させる
            p.wait(timeout=3)
        except psutil.NoSuchProcess:
            print(f"プロセス {pid} は存在しません。")
        except psutil.TimeoutExpired:
            print(f"プロセス {pid} の終了がタイムアウトしました。強制終了を試みます。")
            p.kill()
        except Exception as e:
            print(f"プロセス {pid} の終了中にエラーが発生しました: {e}")

    def update_status(self, status):
        self.status_var.set(status)
        self.run_button.config(state='normal')
        self.running = False
        self.progress.stop()

    def on_closing(self):
        # ウィンドウが閉じられるときにホットキーを削除
        if self.hotkey:
            keyboard.remove_hotkey(self.hotkey)
        self.master.destroy()

def launch_gui():
    root = tk.Tk()
    app = BpStarAutoGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    launch_gui()