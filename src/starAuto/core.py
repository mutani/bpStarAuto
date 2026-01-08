import os
import time
import cv2
import numpy as np
import pyautogui
import pygetwindow as gw
import random
from mss import mss
from PIL import ImageGrab

def capture_process_window(title_substring, screenshot=True):
    """
    指定されたタイトルの部分文字列を含むウィンドウのスクリーンショットを取得します。

    :param title_substring: ウィンドウタイトルの部分文字列
    :return: PIL Imageオブジェクト
    """
    # タイトルに部分文字列を含むウィンドウを検索
    windows = gw.getWindowsWithTitle(title_substring)
    if windows:
        window = windows[0]
        if window.isMinimized:
            window.restore()
        try:
            window.activate()
        except gw.PyGetWindowException as e:
            print(f"ウィンドウのアクティブ化に失敗しました: {e}")

        if screenshot == False:
            return None

        # ウィンドウの境界を取得
        left, top, right, bottom = window.left, window.top, window.right, window.bottom

        # スクリーンショットを取得
        screenshot = ImageGrab.grab(bbox=(left, top, right, bottom))
        return screenshot
    else:
        print(f"No window found with title substring: {title_substring}")
        return False

def find_image(window_title, image_path, timeout=3, confidence=0.8, return_rect=False, sleep_time=0.4, return_confidence=False):
    """
    指定されたウィンドウ内で特定の画像を探し、その位置を返します。
    Args:
        window_title (str): ウィンドウのタイトル
        image_path (str): 探す画像のパス
        timeout (int): タイムアウト時間（秒）
        confidence (float): 類似度の閾値（0.0〜1.0）
        return_rect (bool): Trueの場合、(left, top, right, bottom)を返す。Falseの場合、中心座標(x, y)を返す
        return_confidence (bool): Trueの場合、信頼度を返す
    """
    window = gw.getWindowsWithTitle(window_title)[0]
    window.activate()
    pyautogui.sleep(sleep_time)
    start_time = time.time()
    
    # マルチスケール設定
    scales = [0.8, 0.9, 1.0, 1.1, 1.2]  # 80% ~ 120%
    
    with mss() as sct:
        # モニターの情報を取得
        monitor = {"top": window.top, "left": window.left, "width": window.width, "height": window.height}
        while True:
            img = np.array(sct.grab(monitor))
            # BGRからRGBへ変換
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

            # ボタンの位置を特定するためにテンプレート画像をグレースケールで読み込む
            button_img_original = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

            # 入力画像もグレースケールに変換
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # マルチスケールでテンプレートマッチングを実行
            best_match = None
            best_confidence = 0
            best_scale = 1.0
            
            for scale in scales:
                # テンプレート画像をスケール
                if scale == 1.0:
                    button_img = button_img_original
                else:
                    width = int(button_img_original.shape[1] * scale)
                    height = int(button_img_original.shape[0] * scale)
                    button_img = cv2.resize(button_img_original, (width, height))
                
                # テンプレートマッチング実行
                result = cv2.matchTemplate(img, button_img, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(result)
                
                # より良いマッチが見つかった場合
                if max_val > best_confidence:
                    best_confidence = max_val
                    best_match = max_loc
                    best_scale = scale
            
            # 最高の結果で判定
            if best_confidence > confidence:  # 類似度が閾値以上の場合
                # スケールに応じてサイズを調整
                scaled_width = int(button_img_original.shape[1] * best_scale)
                scaled_height = int(button_img_original.shape[0] * best_scale)
                
                if return_rect:
                    # 矩形領域を返す（スクリーン座標）
                    left = window.left + best_match[0]
                    top = window.top + best_match[1]
                    right = left + scaled_width
                    bottom = top + scaled_height
                    return (left, top, right, bottom)
                else:
                    # ボタンの中心を計算して返す（スクリーン座標）
                    button_center = (best_match[0] + scaled_width // 2, best_match[1] + scaled_height // 2)
                    screen_x, screen_y = window.left + button_center[0], window.top + button_center[1]
                    # 中心座標から誤差を生成(0〜10ピクセル)
                    screen_x += random.randint(0, 10)
                    screen_y += random.randint(0, 10)
                    # 信頼度を返却する場合
                    if return_confidence:
                        return (screen_x, screen_y, best_confidence)
                    
                    return screen_x, screen_y

            if time.time() - start_time > timeout:
                # print("タイムアウト画像が見つかりません:" + image_path)
                # print("類似度: " + best_confidence.__str__() + ">" + confidence.__str__())
                return False

def find_button_and_click(window_title, button_image_path, timeout=5, confidence=0.8):
    """
    指定されたウィンドウ内で特定の画像を探し、見つかった場合にクリックします。
    Args:
        window_title (str): ウィンドウのタイトル
        button_image_path (str): 探す画像のパス
        timeout (int): タイムアウト時間（秒）
        confidence (float): 類似度の閾値（0.0〜1.0）
    """
    result = find_image(window_title, button_image_path, timeout, confidence)
    
    # find_imageがFalseを返した場合の処理
    if result == False:
        print(f"画像が見つからないためクリックできません: {button_image_path}")
        return False
    
    # 座標を取得してクリック
    screen_x, screen_y = result
    pyautogui.moveTo(screen_x, screen_y, duration=0.3)
    time.sleep(0.1)
    pyautogui.click(screen_x, screen_y)
    return True

def left_click():
    """
    左クリックをシミュレートします。
    """
    pyautogui.mouseDown()
    time.sleep(random.uniform(0.2, 0.3))
    pyautogui.mouseUp()
