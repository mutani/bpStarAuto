#!/usr/bin/env python3
"""
Blue Protocol Star Auto - メインエントリーポイント
プロジェクトルートから実行するためのスクリプト
"""

import sys
import os

# プロジェクトルートをPythonパスに追加
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# srcディレクトリも追加
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

if __name__ == '__main__':
    try:
        from src.main import *
        from multiprocessing import freeze_support
        
        freeze_support()
        
        # src/main.pyの内容を実行
        from src.gui import gui as run_gui
        run_gui.launch_gui()
        
    except ImportError as e:
        print(f"インポートエラー: {e}")
        print("依存関係を確認してください。")
        sys.exit(1)
    except Exception as e:
        print(f"実行エラー: {e}")
        sys.exit(1)