"""
starAuto.pickAuto モジュール - 自動実行機能
"""
import time
import multiprocessing
import os
import yaml
import pydirectinput
import pyautogui
import cv2
import numpy as np

from src.starAuto.core import capture_process_window

# 設定ファイルを読み込み
def load_pick_config():
    config_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'config', 'pickConfig.yaml'))
    with open(config_path, 'r', encoding='utf-8') as file:
        return yaml.safe_load(file)

config = load_pick_config()
WINDOWTITLE = config['window_title']


def pick_auto(pick_type, count_var, process_id):
    """
    自動採取機能のメイン関数
    
    Args:
        pick_type (str): 採取タイプ（1, 3, 4）
        count_var (tk.StringVar): 周回数を表示するための変数
        process_id (multiprocessing.Value): プロセスIDを格納する変数
    """

    # ターゲットウィンドウをアクティブ化
    windowState = capture_process_window(WINDOWTITLE,False)
    print(windowState)
    # 採取物を探す
    time.sleep(3)
    pydirectinput.press('m')
    pyautogui.press('m')


def find_gathering_materials(pick_type):
    # 画面のスクリーンショットを取得
    return None



