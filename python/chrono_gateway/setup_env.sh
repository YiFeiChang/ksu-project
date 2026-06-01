#!/bin/bash

# ==========================================
# Python 虛擬環境與套件自動安裝腳本
# ==========================================

# 設定虛擬環境資料夾名稱
VENV_NAME=".venv"
REQUIREMENTS_FILE="requirements.txt"

# 1. 檢查是否安裝了 Python 3
if ! command -v python3 &> /dev/null
then
    echo "❌ 錯誤：找不到 python3，請先安裝 Python 3。"
    exit 1
fi

# 2. 建立虛擬環境
if [ -d "$VENV_NAME" ]; then
    echo "⚠️ 虛擬環境 '$VENV_NAME' 已經存在，跳過建立步驟。"
else
    echo "⏳ 正在建立虛擬環境 '$VENV_NAME'..."
    python3 -m venv $VENV_NAME
    echo "✅ 虛擬環境建立完成。"
fi

# 3. 啟動虛擬環境
echo "啟動虛擬環境..."
# 注意：腳本執行完畢後虛擬環境會留在腳本的子 shell 中，
# 若要在當前終端機生效，請使用 source 執行此腳本，或在腳本結束後手動啟動。
source $VENV_NAME/bin/activate

# 4. 更新 pip 工具
echo "⏳ 正在更新 pip..."
python3 -m pip install --upgrade pip

# 5. 安裝必要套件
if [ -f "$REQUIREMENTS_FILE" ]; then
    echo "⏳ 發現 $REQUIREMENTS_FILE，正在安裝相依套件..."
    pip install -r $REQUIREMENTS_FILE
    echo "✅ 套件安裝完成。"
else
    echo "⚠️ 找不到 $REQUIREMENTS_FILE。"
    echo "⏳ 將為您安裝專案必備套件 (python-dotenv, influxdb-client)..."
    # 專案實際依賴套件
    pip install python-dotenv influxdb-client --upgrade
    
    # 建立 requirements.txt 供下次使用
    pip freeze > $REQUIREMENTS_FILE
    echo "✅ 預設套件安裝完成，並已產生 $REQUIREMENTS_FILE。"
fi

echo "=========================================="
echo "🎉 環境設定成功！"
echo "👉 若要開始使用虛擬環境，請在終端機輸入："
echo "   source $VENV_NAME/bin/activate"
echo "👉 若要退出虛擬環境，請輸入："
echo "   deactivate"
echo "=========================================="
