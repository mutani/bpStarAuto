"""
メインアプリケーションのエントリーポイント
"""
import gui.gui as run_gui
from multiprocessing import freeze_support

if __name__ == '__main__':
    freeze_support()
    run_gui.launch_gui()