"""
Gemini 2.5 Flash 多模態聊天程式
支援純文字對話、圖片 (JPG/PNG)、PDF 以及純文字檔 (.txt) 的輸入。
使用 langchain-google-genai 串接 Gemini，具備對話記憶與 JSON 持久化功能。

可透過 CLI（python chat.py）或作為模組匯入（from chat import ChatAgent）使用。
"""

import base64
import json
import mimetypes
import os
import atexit
from datetime import datetime

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_community.document_loaders import PyPDFLoader

# ── 支援的檔案類型 ────────────────────────────────────────────
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
PDF_EXTENSIONS = {".pdf"}
TEXT_EXTENSIONS = {".txt"}
SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS | PDF_EXTENSIONS | TEXT_EXTENSIONS


# ── 檔案處理工具函式 ──────────────────────────────────────────

def load_image_as_base64(file_path: str) -> dict:
    """讀取圖片並轉換為 base64 資料，回傳 LangChain 多模態格式。"""
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        mime_type = "image/jpeg"

    with open(file_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    return {
        "type": "image_url",
        "image_url": {"url": f"data:{mime_type};base64,{image_data}"},
    }


def load_pdf_text(file_path: str) -> str:
    """使用 PyPDFLoader 讀取 PDF 並回傳完整文字內容。"""
    loader = PyPDFLoader(file_path)
    pages = loader.load()
    full_text = "\n\n".join(
        f"[第 {i + 1} 頁]\n{page.page_content}" for i, page in enumerate(pages)
    )
    return full_text


def load_txt_content(file_path: str) -> str:
    """讀取純文字檔內容。"""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


# ══════════════════════════════════════════════════════════════
#  ChatAgent 類別
# ══════════════════════════════════════════════════════════════

class ChatAgent:
    """封裝 Gemini 多模態聊天邏輯，支援對話記憶與 JSON 持久化。"""

    def __init__(self, api_key: str | None = None):
        load_dotenv()
        self._api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self._api_key:
            raise ValueError("請在 .env 檔案中設定 GEMINI_API_KEY")

        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=self._api_key,
            temperature=0.7,
        )
        self.chat_history = InMemoryChatMessageHistory()
        self.conversation_log: list[dict] = []

    # ── 紀錄管理 ──────────────────────────────────────────────

    def _add_to_log(
        self, role: str, content: str, file_info: dict | None = None
    ) -> None:
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "role": role,
            "content": content,
        }
        if file_info:
            entry["file"] = file_info
        self.conversation_log.append(entry)

    def save_conversation(self) -> str | None:
        """將對話紀錄存成 JSON 檔案，回傳檔案路徑。"""
        if not self.conversation_log:
            return None

        filename = datetime.now().strftime("chat_%Y%m%d_%H%M%S.json")
        filepath = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), filename
        )

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.conversation_log, f, ensure_ascii=False, indent=2)

        return filepath

    def get_conversation_json(self) -> str:
        """回傳目前對話紀錄的 JSON 字串。"""
        return json.dumps(self.conversation_log, ensure_ascii=False, indent=2)

    def reset(self) -> None:
        """清除對話歷史。"""
        self.chat_history = InMemoryChatMessageHistory()
        self.conversation_log.clear()

    # ── 聊天核心 ──────────────────────────────────────────────

    def chat(
        self, text: str, file_paths: list[str] | None = None
    ) -> str:
        """
        處理使用者輸入，回傳 AI 回覆。

        Args:
            text: 使用者文字訊息。
            file_paths: 可選的檔案路徑列表 (jpg/png/pdf/txt)。
        """
        file_paths = file_paths or []

        # 篩選有效的檔案
        valid_files = []
        for fp in file_paths:
            if os.path.isfile(fp):
                ext = os.path.splitext(fp)[1].lower()
                if ext in SUPPORTED_EXTENSIONS:
                    valid_files.append((fp, ext))

        if not valid_files:
            # ── 純文字對話 ──
            self.chat_history.add_user_message(text)
            self._add_to_log("user", text)

            response = self.llm.invoke(self.chat_history.messages)
            ai_content = response.content

            self.chat_history.add_ai_message(ai_content)
            self._add_to_log("ai", ai_content)
            return ai_content

        # ── 有檔案時的處理 ──
        message_parts: list[dict] = []
        all_file_info: list[dict] = []
        extra_texts: list[str] = []
        user_text = text if text else "請分析這個檔案的內容。"

        for fp, ext in valid_files:
            basename = os.path.basename(fp)
            file_info = {"filename": basename, "type": ext.lstrip(".")}

            if ext in IMAGE_EXTENSIONS:
                image_part = load_image_as_base64(fp)
                message_parts.append(image_part)
                file_info["description"] = f"圖片: {basename}"

            elif ext in PDF_EXTENSIONS:
                pdf_text = load_pdf_text(fp)
                extra_texts.append(
                    f"\n\n--- 以下是 PDF 檔案「{basename}」的內容 ---\n{pdf_text}"
                )
                file_info["page_count"] = pdf_text.count("[第 ")
                file_info["content_preview"] = pdf_text[:500]

            elif ext in TEXT_EXTENSIONS:
                txt_content = load_txt_content(fp)
                extra_texts.append(
                    f"\n\n--- 以下是文字檔「{basename}」的內容 ---\n{txt_content}"
                )
                file_info["content_preview"] = txt_content[:500]

            all_file_info.append(file_info)

        # 組合最終訊息
        combined_text = user_text + "".join(extra_texts)

        if message_parts:
            # 有圖片 → 使用多模態 HumanMessage
            message_parts.insert(0, {"type": "text", "text": combined_text})
            msg = HumanMessage(content=message_parts)
            self.chat_history.add_message(msg)
        else:
            # 只有 PDF / TXT → 純文字
            self.chat_history.add_user_message(combined_text)

        # 紀錄
        file_names = ", ".join(fi["filename"] for fi in all_file_info)
        log_content = f"[📎 {file_names}] {user_text}"
        self._add_to_log(
            "user",
            log_content,
            all_file_info[0] if len(all_file_info) == 1 else all_file_info,
        )

        # 取得 AI 回覆
        response = self.llm.invoke(self.chat_history.messages)
        ai_content = response.content

        self.chat_history.add_ai_message(ai_content)
        self._add_to_log("ai", ai_content)

        return ai_content

    # ── CLI 用：從文字輸入偵測檔案路徑 ────────────────────────

    def chat_from_text(self, user_input: str) -> str:
        """CLI 用途：自動從文字中偵測檔案路徑。"""
        file_path = self._detect_file_path(user_input)
        if file_path:
            extra_text = user_input.replace(file_path, "").strip()
            return self.chat(extra_text, [file_path])
        return self.chat(user_input)

    @staticmethod
    def _detect_file_path(user_input: str) -> str | None:
        """從使用者輸入中偵測是否包含有效的檔案路徑。"""
        candidate = user_input.strip().strip("'\"")
        if os.path.isfile(candidate):
            ext = os.path.splitext(candidate)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                return candidate

        for token in user_input.split():
            token = token.strip("'\"")
            if os.path.isfile(token):
                ext = os.path.splitext(token)[1].lower()
                if ext in SUPPORTED_EXTENSIONS:
                    return token
        return None


# ══════════════════════════════════════════════════════════════
#  CLI 入口
# ══════════════════════════════════════════════════════════════

def main() -> None:
    """主程式迴圈（CLI 模式）。"""
    agent = ChatAgent()
    atexit.register(agent.save_conversation)

    print("=" * 56)
    print("  🤖 Gemini 2.0 Flash 多模態聊天室")
    print("=" * 56)
    print("  支援格式：JPG / PNG / PDF / TXT")
    print("  用法：直接輸入文字，或貼上檔案路徑")
    print("  範例：C:\\photos\\image.jpg 這張圖片是什麼？")
    print("  輸入 'exit' 結束對話並儲存紀錄")
    print("=" * 56)

    while True:
        try:
            user_input = input("\n👤 You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n")
            break

        if not user_input:
            continue

        if user_input.lower() == "exit":
            print("\n👋 再見！")
            break

        try:
            reply = agent.chat_from_text(user_input)
            print(f"\n🤖 AI: {reply}")
        except Exception as e:
            print(f"\n❌ 發生錯誤：{e}")

    filepath = agent.save_conversation()
    if filepath:
        print(f"\n💾 對話紀錄已儲存至：{filepath}")


if __name__ == "__main__":
    main()
