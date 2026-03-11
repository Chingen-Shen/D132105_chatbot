"""
Gemini 2.5 Flash 多模態聊天室 — Gradio Web 介面
執行方式：python app.py
"""

import os
import gradio as gr

from chat import ChatAgent, IMAGE_EXTENSIONS, PDF_EXTENSIONS, TEXT_EXTENSIONS

# ── 初始化 Agent ──────────────────────────────────────────────
agent = ChatAgent()

# ── 自訂 CSS ──────────────────────────────────────────────────
CUSTOM_CSS = """
/* ── 全域 ─────────────────────────────────── */
.gradio-container {
    max-width: 900px !important;
    margin: 0 auto;
}

/* ── 頂部 Header ──────────────────────────── */
#app-header {
    text-align: center;
    padding: 28px 20px 18px;
    background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
    border-radius: 16px;
    margin-bottom: 8px;
    border: 1px solid rgba(255,255,255,.08);
    box-shadow: 0 8px 32px rgba(0,0,0,.35);
}
#app-header h1 {
    margin: 0 0 6px;
    font-size: 1.75rem;
    background: linear-gradient(90deg, #a78bfa, #60a5fa, #34d399);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 800;
    letter-spacing: -0.5px;
}
#app-header p {
    margin: 0;
    font-size: 0.85rem;
    color: rgba(255,255,255,0.65);
}

/* ── 聊天區域 ─────────────────────────────── */
#chatbot {
    border-radius: 14px !important;
    border: 1px solid rgba(255,255,255,.06) !important;
}
#chatbot .message {
    font-size: 0.95rem;
    line-height: 1.65;
}

/* ── 按鈕 ─────────────────────────────────── */
.action-btn {
    border-radius: 10px !important;
    font-weight: 600 !important;
    transition: all 0.2s ease !important;
}
.action-btn:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(0,0,0,.3) !important;
}
#save-btn {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
    color: white !important;
    border: none !important;
}
#clear-btn {
    border: 1px solid rgba(255,255,255,.15) !important;
}

/* ── 狀態列 ───────────────────────────────── */
#status-bar {
    font-size: 0.8rem;
    opacity: 0.6;
    text-align: center;
    padding: 6px;
}
"""

# ── 自訂主題 ──────────────────────────────────────────────────
theme = gr.themes.Soft(
    primary_hue=gr.themes.colors.indigo,
    secondary_hue=gr.themes.colors.purple,
    neutral_hue=gr.themes.colors.slate,
    font=gr.themes.GoogleFont("Inter"),
    font_mono=gr.themes.GoogleFont("JetBrains Mono"),
).set(
    body_background_fill="*neutral_950",
    body_background_fill_dark="*neutral_950",
    block_background_fill="*neutral_900",
    block_background_fill_dark="*neutral_900",
    input_background_fill="*neutral_800",
    input_background_fill_dark="*neutral_800",
    button_primary_background_fill="*primary_600",
    button_primary_background_fill_dark="*primary_600",
)


# ── Gradio 回呼函式 ───────────────────────────────────────────

def respond(message: dict, history: list) -> tuple:
    """
    Gradio MultimodalTextbox 的回呼。
    message = {"text": str, "files": list[str]}
    history = list of {"role": ..., "content": ...} dicts (messages format)
    """
    user_text = message.get("text", "").strip()
    uploaded_files = message.get("files", [])

    # 收集有效檔案路徑
    file_paths = []
    for f in uploaded_files:
        fp = f if isinstance(f, str) else f.get("path", "")
        if fp and os.path.isfile(fp):
            file_paths.append(fp)

    if not user_text and not file_paths:
        return history, gr.update()

    # ── 在 history 中加入使用者訊息 ──
    for fp in file_paths:
        ext = os.path.splitext(fp)[1].lower()
        basename = os.path.basename(fp)
        if ext in IMAGE_EXTENSIONS:
            history.append({"role": "user", "content": gr.Image(fp)})
        else:
            history.append({
                "role": "user",
                "content": f"📎 已上傳檔案：**{basename}**",
            })

    display_text = user_text if user_text else "請分析這個檔案的內容。"
    if file_paths:
        history.append({"role": "user", "content": display_text})
    elif user_text:
        history.append({"role": "user", "content": user_text})

    # ── 呼叫 Agent ──
    try:
        reply = agent.chat(user_text, file_paths if file_paths else None)
    except Exception as e:
        reply = f"❌ 發生錯誤：{e}"

    history.append({"role": "assistant", "content": reply})
    return history, gr.update(value=None)


def handle_edit(history: list, edit_data: gr.EditData) -> list:
    """
    當使用者編輯先前的訊息時，截斷歷史並從該訊息重新產生回應。
    """
    edited_idx = edit_data.index
    new_value = edit_data.value

    # 只處理使用者訊息的編輯
    if edited_idx >= len(history) or history[edited_idx].get("role") != "user":
        return history

    # 計算被編輯的訊息屬於第幾輪（以 assistant 訊息數為基準）
    agent_turn = sum(
        1 for i in range(edited_idx) if history[i].get("role") == "assistant"
    )

    # 截斷 Agent 內部狀態至該輪之前
    agent.truncate_to_turn(agent_turn)

    # 截斷 Gradio 顯示歷史：找到該輪的起始位置
    cut_point = 0
    for i in range(edited_idx - 1, -1, -1):
        if history[i].get("role") == "assistant":
            cut_point = i + 1
            break
    truncated_history = history[:cut_point]

    # 加入編輯後的訊息
    truncated_history.append({"role": "user", "content": new_value})

    # 呼叫 Agent 取得新回覆
    try:
        reply = agent.chat(new_value)
    except Exception as e:
        reply = f"❌ 發生錯誤：{e}"

    truncated_history.append({"role": "assistant", "content": reply})
    return truncated_history


def clear_chat() -> tuple:
    """清除對話歷史。"""
    agent.reset()
    return [], gr.update(value=None), gr.update(visible=False, value=None)


def save_chat() -> tuple:
    """儲存對話紀錄並提供下載。"""
    filepath = agent.save_conversation()
    if filepath:
        return gr.update(value=filepath, visible=True)
    return gr.update(visible=False, value=None)


# ── 建立 Gradio 介面 ─────────────────────────────────────────

with gr.Blocks(title="Gemini Chat") as demo:

    # ── Header ──
    gr.HTML(
        """
        <div id="app-header">
            <h1>🤖 Gemini 2.5 Flash 聊天室</h1>
            <p>支援圖片 (JPG/PNG) · PDF 文件 · 純文字檔 (.txt) · 多輪對話記憶</p>
        </div>
        """
    )

    # ── 聊天區域 ──
    chatbot = gr.Chatbot(
        elem_id="chatbot",
        show_label=False,
        height=520,
        buttons=["copy"],
        render_markdown=True,
        layout="bubble",
        placeholder="💬 開始與 Gemini 對話吧！",
        editable="user",
    )

    # ── 輸入區 ──
    textbox = gr.MultimodalTextbox(
        placeholder="輸入訊息，或點選 📎 上傳檔案 (JPG/PNG/PDF/TXT)…",
        show_label=False,
        file_count="multiple",
        file_types=[".jpg", ".jpeg", ".png", ".pdf", ".txt"],
        submit_btn=True,
    )

    # ── 按鈕列 ──
    with gr.Row():
        clear_btn = gr.Button(
            "🗑️ 清除對話", elem_id="clear-btn", elem_classes="action-btn"
        )
        save_btn = gr.Button(
            "💾 儲存對話紀錄", elem_id="save-btn", elem_classes="action-btn"
        )

    # ── 下載區 ──
    download_file = gr.File(
        label="📥 下載對話紀錄",
        elem_id="download-area",
        visible=False,
        interactive=False,
    )

    # ── 狀態列 ──
    gr.HTML(
        '<div id="status-bar">'
        "Powered by Google Gemini 2.5 Flash · LangChain · Gradio"
        "</div>"
    )

    # ── 事件綁定 ──
    textbox.submit(
        fn=respond,
        inputs=[textbox, chatbot],
        outputs=[chatbot, textbox],
    )

    chatbot.edit(
        fn=handle_edit,
        inputs=[chatbot],
        outputs=[chatbot],
    )

    clear_btn.click(
        fn=clear_chat,
        outputs=[chatbot, textbox, download_file],
    )

    save_btn.click(
        fn=save_chat,
        outputs=[download_file],
    )


if __name__ == "__main__":
    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        inbrowser=True,
        theme=theme,
        css=CUSTOM_CSS,
    )
