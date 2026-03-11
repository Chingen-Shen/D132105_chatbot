# AI Chatbot 專案名稱

## 小組：

### 組員：

* D1321025 沈慶言

## 專案簡介

本專案是一個使用 Gradio 製作的多模態 AI 聊天機器人，透過 LangChain 串接 Google Gemini 2.5 Flash 模型，支援圖片 (JPG/PNG)、PDF 文件與純文字檔 (.txt) 的上傳與分析，具備多輪對話記憶、訊息編輯重新生成，以及對話紀錄 JSON 匯出功能。

## 目前功能

- 💬 多輪對話記憶（使用 LangChain InMemoryChatMessageHistory）
- 🖼️ 圖片分析（JPG/PNG，透過 Gemini 多模態 API）
- 📄 PDF 文件讀取與分析（使用 PyPDFLoader）
- 📝 純文字檔讀取與分析
- ✏️ 編輯先前訊息並重新產生 AI 回應
- 💾 對話紀錄匯出為 JSON 檔案（含時間戳記、角色、內容）
- 🌐 Gradio Web GUI（深色主題、氣泡式對話介面）

## 執行方式

1. 下載專案
2. 安裝 Python 套件
3. 建立 `.env` 檔案並填入 API Key
4. 啟動程式

範例指令：

```bash
git clone https://github.com/Chingen-Shen/D132105_chatbot.git
cd D132105_chatbot
pip install -r requirements.txt
python app.py
```

啟動後在瀏覽器開啟 `http://127.0.0.1:7860` 即可使用。

也可使用終端機模式：

```bash
python chat.py
```

---

## 環境變數說明

請自行建立 `.env` 檔案，並填入自己的 API key。

範例：

```env
GEMINI_API_KEY=your_api_key_here
```

## 遇到的問題與解法

### 問題 1

問題：安裝完 Git 後在 PowerShell 中無法使用 `git` 指令，顯示「無法辨識 'git' 詞彙」。
解法：需要重新開啟終端，或手動刷新系統 PATH 變數後才能使用。

### 問題 2

問題：Gradio 6.x 版本的 API 與舊版不相容，`theme` 和 `css` 參數不再放在 `gr.Blocks()` 建構子中。
解法：將 `theme` 和 `css` 參數改為傳入 `demo.launch()` 方法中，並移除 `Chatbot` 中已棄用的 `type` 參數。

---

## 學習心得

> 透過本次作業，學習了如何使用 LangChain 框架串接 Google Gemini API，實作多模態 AI Agent。也學到了如何使用 Gradio 建立 Web GUI，以及 Git 版本控制的基本操作流程（init → add → commit → push）。

---

## GitHub 專案連結

- [D132105_chatbot](https://github.com/Chingen-Shen/D132105_chatbot)
