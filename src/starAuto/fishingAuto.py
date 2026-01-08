import os
import threading
import yaml
import time
import pyautogui
import pygetwindow as gw
import sys

from src.starAuto.core import *

# ログ用print関数
def log_print(*args, **kwargs):
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{now}]", *args, **kwargs)

# 設定ファイルを読み込み
def load_pick_config():
    # 実行ファイルと同じ場所のconfigフォルダから取得
    if getattr(sys, 'frozen', False):
        # EXE化されている場合: EXEファイルと同じフォルダ
        exe_dir = os.path.dirname(sys.executable)
    else:
        # 開発環境の場合: main.pyがあるフォルダ（プロジェクトルート）
        exe_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    config_path = os.path.join(exe_dir, 'config', 'fishingConfig.yaml')
    
    with open(config_path, 'r', encoding='utf-8') as file:
        return yaml.safe_load(file)

# プロジェクトルートも同様に設定
# EXE化
if getattr(sys, 'frozen', False):
    project_root = os.path.dirname(sys.executable)
else:
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

config = load_pick_config()
WINDOWTITLE = config['window_title']
# WINDOWTITLE = "Snipping Tool"

def get_confidence(config, key):
    """設定から信頼度を取得（キーが存在しない場合はデフォルト値）"""
    return config.get('confidence', {}).get(key, config.get('confidence', {}).get('default', 0.8))

def fishing_auto(pick_type, count_var, process_id):
    """
    自動釣り機能のメイン関数
    
    Args:
        pick_type (str): 釣りタイプ
        count_var (multiprocessing.Value): 周回数をカウントするための共有変数
        process_id (multiprocessing.Value): プロセスIDを格納する変数
    """

    # ターゲットウィンドウをアクティブ化
    windowState = capture_process_window(WINDOWTITLE,False)

    # 仮処理（TODO全画像が存在しているかチェック）
    fishing_image_path = os.path.join(project_root, config['default_fishing_image_path'])
    fishing_image_path = os.path.normpath(fishing_image_path)
    if not os.path.exists(fishing_image_path):
        log_print(f"釣り画像フォルダが存在しません: {fishing_image_path}")
        return
    # 全画像ファイルの存在チェック
    all_images_exist, missing_files = check_fishing_images_exist(fishing_image_path, config)
    if not all_images_exist:
        log_print("必要な画像ファイルが見つかりません:")
        for missing_file in missing_files:
            log_print(f"  - {missing_file}")
        log_print(f"画像フォルダ: {fishing_image_path}")
        return
    
    # 釣り画面であるかの確認
    if find_image(WINDOWTITLE, os.path.join(fishing_image_path, config['waiting_for_fishing']), confidence=get_confidence(config, 'waiting_for_fishing')) == False:
        log_print("釣り待機画面が見つかりません。釣り画面を開いてください。")
        return
    
    # 釣り処理ループ｛
    while True:
    # 釣り道具セット確認
        if find_image(WINDOWTITLE, os.path.join(fishing_image_path, config['add_button']), timeout=1, confidence=get_confidence(config, 'add_button')) != False:
            # 釣り道具セット
            pyautogui.press('m')
            time.sleep(1)
            find_button_and_click(WINDOWTITLE, os.path.join(fishing_image_path, config['use_button']), confidence=get_confidence(config, 'use_button'))
        
        # 釣りロジック開始
        window = gw.getWindowsWithTitle(WINDOWTITLE)
        if window:
            window[0].activate()
            #左クリック
            left_click()      
        
            referenceposition = find_image(WINDOWTITLE, os.path.join(fishing_image_path, config['fish_caught_indicator']), timeout=30, confidence=get_confidence(config, 'fish_caught_indicator'), sleep_time=0.2)
            # 釣れた画像を待つ(!)
            if referenceposition:
                left_click()
                log_print("釣りバトル判定")
            else:
                log_print("釣り失敗:タイムアウト")
                continue  # 釣り失敗の場合、再度釣りを試みる

            # 釣りバトル開始判定
            if find_image(WINDOWTITLE, os.path.join(fishing_image_path, config['fishing_battle_detection']), timeout=2, confidence=get_confidence(config, 'fishing_battle_detection')):
                if find_image(WINDOWTITLE, os.path.join(fishing_image_path, config['fishing_battle_indicator']), timeout=2, confidence=get_confidence(config, 'fishing_battle_indicator')):
                    log_print("釣りバトル開始")
                    fishing_battle_auto(fishing_image_path, count_var, referenceposition)
            else:
                # 釣り成功、続けるボタンを押す
                if find_button_and_click(WINDOWTITLE, os.path.join(fishing_image_path, config['continue_button']), confidence=get_confidence(config, 'continue_button')) == False:
                    log_print("続けるボタンが見つかりませんでした。")
                    # !が検知できなかった場合釣り中となるその後最初の画面に移行(失敗)するまで待機
                    if find_image(WINDOWTITLE, os.path.join(fishing_image_path, config['waiting_for_fishing']), confidence=get_confidence(config, 'waiting_for_fishing')) == False:
                        continue
                else:
                    # 通常釣り成功時のカウントアップ
                    count_var.value += 1
                    log_print(f"釣り成功！ 周回数: {count_var.value}")
                
        # 釣り処理ループ }


def fishing_battle_auto(fishing_image_path, count_var, referenceposition):
    # 共有データ
    shared_data = {
        'tension': False,
        'now_rod_position': 0,
        'rod_position': 0,
        'battle_end': False,
        'failure': False
    }
    data_lock = threading.Lock()
    stop_event = threading.Event()  # 停止イベント
    
    # 画像パス
    tension_message_path = os.path.join(fishing_image_path, config['tension_message'])
    continue_button_path =  os.path.join(fishing_image_path, config['continue_button'])
    failure_path = os.path.join(fishing_image_path, config['failure'])
    left_indicator_path = os.path.join(fishing_image_path, config['left_indicator'])
    right_indicator_path = os.path.join(fishing_image_path, config['right_indicator'])

    # 張力検知スレッド
    def tension_detector():
        while not stop_event.is_set():
            try:
                tension = find_image(WINDOWTITLE, tension_message_path, timeout=0, confidence=get_confidence(config, 'tension_message')) != False
                with data_lock:
                    shared_data['tension'] = tension
                # time.sleep(0.02)  # 50FPS
            except:
                break
    
    # 竿位置検知スレッド（基準位置を引数で受け取り）
    def rod_position_detector(reference_pos):
        loop_count = 0
        while not stop_event.is_set():
            try:
                loop_count += 1
                
                # 竿位置取得左
                left_result = find_image(WINDOWTITLE, left_indicator_path, timeout=0, confidence=get_confidence(config, 'left_indicator')
                                        , sleep_time=0.01, return_confidence=True)
                if left_result != False:
                    left_x, left_y, left_confidence = left_result
                    indicatorLeft = left_confidence
                    log_print(f"[{loop_count}] 左検知: 座標({left_x}, {left_y}), 信頼度:{left_confidence:.3f}")
                else:
                    indicatorLeft = False
                    left_x, left_y = None, None

                # 竿位置取得右
                right_result = find_image(WINDOWTITLE, right_indicator_path, timeout=0, confidence=get_confidence(config, 'right_indicator')
                                         , sleep_time=0.01, return_confidence=True)
                if right_result != False:
                    right_x, right_y, right_confidence = right_result
                    indicatorRight = right_confidence
                    log_print(f"[{loop_count}] 右検知: 座標({right_x}, {right_y}), 信頼度:{right_confidence:.3f}")
                else:
                    indicatorRight = False
                    right_x, right_y = None, None

                # デバッグ：検知状況を表示
                if indicatorLeft != False or indicatorRight != False:
                    log_print(f"[{loop_count}] 検知状況: 左={indicatorLeft}, 右={indicatorRight}, 基準位置={reference_pos}")

                
                if indicatorLeft != False and indicatorRight != False:                
                    # 左右誤検知対策基準位置
                    # 同位置判定
                    if left_x - right_x < 30:
                        if (left_x + right_x)/2 < reference_pos[0]:
                            log_print(f"[{loop_count}] 両方検知だが基準より左 -> 左に変更")
                            indicatorRight = False
                            indicatorLeft = True
                        else:
                            log_print(f"[{loop_count}] 両方検知だが基準より右 -> 右に変更")
                            indicatorLeft = False
                            indicatorRight = True
                    # 非同位置判定の場合信頼度が高い方を優先
                    else:
                        log_print(f"[{loop_count}] 両方検知 - 左:{indicatorLeft:.3f} vs 右:{indicatorRight:.3f}")
                        if indicatorLeft > indicatorRight:
                            indicatorRight = False
                            log_print(f"[{loop_count}] 左を優先")
                        else:
                            indicatorLeft = False
                            log_print(f"[{loop_count}] 右を優先")

                # 左右どちらかが検出された場合、左右誤検知を防ぐため基準位置と比較
                elif indicatorLeft != False or indicatorRight != False:
                    log_print(f"[{loop_count}] 単独検知による基準位置比較開始")
                    if left_x != None and left_x > reference_pos[0]:
                        log_print(f"[{loop_count}] 左検知だが座標が基準より右 -> 右に変更")
                        indicatorLeft = False
                        indicatorRight = True
                    elif right_x != None and right_x < reference_pos[0]:
                        log_print(f"[{loop_count}] 右検知だが座標が基準より左 -> 左に変更")
                        indicatorLeft = True
                        indicatorRight = False
                

                # 最終的な判定結果をログ出力
                final_position = 0
                if indicatorLeft != False:
                    final_position = -1
                elif indicatorRight != False:
                    final_position = 1
                
                if final_position != 0:
                    log_print(f"[{loop_count}] 最終判定: {final_position} ({'左' if final_position == -1 else '右'})")

                with data_lock:
                    if indicatorLeft != False:
                        shared_data['rod_position'] = -1  # 左
                    elif indicatorRight != False:
                        shared_data['rod_position'] = 1  # 右
                    else:
                        shared_data['rod_position'] = 0  # 中央
                
                # 10回ごとにまとめ情報を表示
                if loop_count % 10 == 0:
                    log_print(f"[{loop_count}回目] 現在の竿位置: {shared_data['rod_position']}")
                
                time.sleep(0.005)
                
            except Exception as e:
                log_print(f"[竿位置検知エラー] {e}")
                break

    # 終了検知スレッド
    def end_detector():
        while not stop_event.is_set():
            try:
                end = find_image(WINDOWTITLE, continue_button_path, timeout=0, confidence=get_confidence(config, 'continue_button')) != False
                failure = find_image(WINDOWTITLE, failure_path, timeout=0, confidence=get_confidence(config, 'failure')) != False
                with data_lock:
                    shared_data['battle_end'] = end
                    shared_data['failure'] = failure
                time.sleep(0.05)  # 20FPS
            except:
                break
    
    # スレッド開始（基準位置を引数として渡す）
    t1 = threading.Thread(target=tension_detector, daemon=True)
    t2 = threading.Thread(target=end_detector, daemon=True)
    t3 = threading.Thread(target=rod_position_detector, args=(referenceposition,), daemon=True)
    t1.start()
    t2.start()
    t3.start()

    # メインループ（制御）
    try:
        # キーの押下状態を追跡
        key_a_pressed = False
        key_d_pressed = False
        
        #キー入力状態制御
        pyautogui.mouseDown()
        mouseLeftClick = True
        while not stop_event.is_set():
            with data_lock:
                # 終了条件チェック
                if shared_data['battle_end'] != False or shared_data['failure'] != False:
                    break
                # 張力に応じてマウス左クリック操作
                if shared_data['tension'] != False:
                    if mouseLeftClick == True:
                        log_print("張力が高すぎるため、釣り竿を緩めます。")
                        pyautogui.mouseUp()
                        mouseLeftClick = False
                else:
                    if mouseLeftClick == False:
                        log_print("張力が適正範囲内のため、釣り竿を引っ張ります。")
                        pyautogui.mouseDown()
                        mouseLeftClick = True

                # 真ん中
                if shared_data['now_rod_position'] == 0:
                    if shared_data['rod_position'] == 1:
                        log_print("釣り竿を右に移動します。")
                        pyautogui.keyDown('d')
                        key_d_pressed = True
                        shared_data['now_rod_position'] = 1
                        shared_data['rod_position'] = None
                    elif shared_data['rod_position'] == -1:
                        log_print("釣り竿を左に移動します。")
                        pyautogui.keyDown('a')
                        key_a_pressed = True
                        shared_data['now_rod_position'] = -1
                        shared_data['rod_position'] = None
                # 右
                elif shared_data['now_rod_position'] == 1:
                    if shared_data['rod_position'] == -1:
                        # Dキーアップで中央に戻す
                        log_print("釣り竿を右から中央に移動します。")
                        if key_d_pressed:
                            pyautogui.keyUp('d')
                            key_d_pressed = False
                        shared_data['now_rod_position'] = 0
                        shared_data['rod_position'] = None
                # 左
                elif shared_data['now_rod_position'] == -1:
                    if shared_data['rod_position'] == 1:
                        # Aキーアップで中央に戻す
                        log_print("釣り竿を左から中央に移動します。")
                        if key_a_pressed:
                            pyautogui.keyUp('a')
                            key_a_pressed = False
                        shared_data['now_rod_position'] = 0
                        shared_data['rod_position'] = None

            time.sleep(0.01)
    finally:
        # 停止イベント発火
        stop_event.set()
        
        # 押下状態を確認してからキーを離す
        if key_a_pressed:
            pyautogui.keyUp('a')
        if key_d_pressed:
            pyautogui.keyUp('d')
        
        # スレッド終了を待機
        t1.join(timeout=1)
        t2.join(timeout=1)
        
        pyautogui.mouseUp()
        log_print("釣りバトル終了")
        log_print("判定は下記です。")
        # バトル結果処理
        if shared_data['battle_end'] != False:
            log_print("釣りバトル成功")
            find_button_and_click(WINDOWTITLE, continue_button_path, confidence=get_confidence(config, 'continue_button'))
            # 釣りバトル成功時のカウントアップ
            count_var.value += 1
            log_print(f"釣りバトル成功！ 周回数: {count_var.value}")
        elif shared_data['failure'] != False:
            log_print("釣りバトル失敗")

    
def check_fishing_images_exist(fishing_image_path, config):
    """
    釣り用画像ファイルがすべて存在するかチェック
    
    Args:
        fishing_image_path (str): 釣り画像フォルダのパス
        config (dict): 設定辞書
    
    Returns:
        tuple: (bool: 全て存在するか, list: 存在しないファイルのリスト)
    """
    # チェック対象の画像ファイル一覧（configから取得）
    required_images = [
        config['waiting_for_fishing'],
        config['add_button'], 
        config['continue_button'],
        config['use_button'],
        config['fish_caught_indicator'],
        config['fishing_battle_detection'],
        config['fishing_battle_indicator'],
        config['tension_message'],
        config['left_indicator'],
        config['right_indicator'],
        config['failure']
    ]
    
    missing_files = []
    
    for image_file in required_images:
        image_path = os.path.join(fishing_image_path, image_file)
        if not os.path.exists(image_path):
            missing_files.append(image_file)
    
    return len(missing_files) == 0, missing_files