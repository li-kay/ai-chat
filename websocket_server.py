import json
from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context
from chat_un_stream import ask_question, http, CHAT_URL, CHAT_ID, API_KEY, _auth_headers

app = Flask(__name__)

# 全局 session_id：服务启动后初始化一次，后续所有请求复用
_session_id = None


def get_session_id() -> str | None:
    """获取或初始化全局会话 ID"""
    global _session_id
    if _session_id is None:
        resp = ask_question("你好", stream=False)
        if resp and resp.get("code") == 0:
            _session_id = resp["data"].get("session_id")
            print(f"[会话] 初始化成功: {_session_id}")
        else:
            print("[会话] 初始化失败，将使用无会话模式")
    return _session_id


def _build_stream_payload(question: str) -> dict:
    """构建流式请求的 payload"""
    payload = {"question": question, "stream": True}
    sid = get_session_id()
    if sid:
        payload["session_id"] = sid
    return payload


# ── 路由 ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory('.', 'chat.html')


@app.route('/ask', methods=['POST'])
def ask():
    """非流式接口（备用）"""
    body = request.get_json()
    if not body or not body.get('question'):
        return jsonify({'error': '请输入有效的问题'}), 400

    resp = ask_question(body['question'].strip(), stream=False, session_id=get_session_id())
    if resp and resp.get("code") == 0:
        return jsonify({'answer': resp["data"]["answer"]})

    err_msg = resp.get('message', '未知错误') if resp else '请求超时或服务不可用'
    return jsonify({'error': f'获取回答失败：{err_msg}'}), 500


@app.route('/ask_stream', methods=['POST'])
def ask_stream():
    """流式接口：将 RAGFlow SSE 实时转发给前端"""
    body = request.get_json()
    if not body or not body.get('question'):
        return jsonify({'error': '请输入有效的问题'}), 400

    payload = _build_stream_payload(body['question'].strip())

    def generate():
        try:
            with http.post(
                CHAT_URL.format(chat_id=CHAT_ID),
                headers=_auth_headers(),
                json=payload,
                timeout=(10, 600),
                verify=False,
                stream=True
            ) as r:
                for line in r.iter_lines():
                    if not line:
                        continue
                    if isinstance(line, bytes):
                        line = line.decode('utf-8')
                    if not line.startswith('data:'):
                        continue

                    raw = line[5:].strip()
                    if not raw or raw == 'true':
                        continue

                    try:
                        obj = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    if obj.get('code') != 0:
                        continue

                    d = obj.get('data')
                    if d is True:           # 流结束标志
                        yield "data: [DONE]\n\n"
                        return
                    if isinstance(d, dict):
                        answer = d.get('answer', '')
                        if answer:          # 过滤空 answer（最终汇总包）
                            yield f"data: {json.dumps({'answer': answer}, ensure_ascii=False)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control':    'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )


# ── 启动 ────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("[启动] 美团客服后端服务 - http://localhost:5050")
    with app.app_context():
        get_session_id()
    app.run(debug=False, port=5050, threaded=True)
