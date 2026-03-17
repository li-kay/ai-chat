from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context
from chat_un_stream import ask_question, http, CHAT_URL, CHAT_ID, API_KEY
import json

app = Flask(__name__)

# 全局 session_id，应用启动后初始化一次并复用
_session_id = None

def get_session_id():
    """获取或初始化全局会话 ID"""
    global _session_id
    if _session_id is None:
        resp = ask_question("你好", stream=False)
        if resp and resp.get("code") == 0:
            _session_id = resp["data"].get("session_id")
            print(f"[会话] 初始化 session_id: {_session_id}")
        else:
            print("[会话] 初始化失败，将使用无会话模式")
    return _session_id


@app.route('/')
def index():
    return send_from_directory('.', 'chat.html')


@app.route('/ask', methods=['POST'])
def ask():
    """非流式接口（备用）"""
    data = request.get_json()
    if not data or not data.get('question'):
        return jsonify({'error': '请输入有效的问题'}), 400

    question   = data['question'].strip()
    session_id = get_session_id()
    response   = ask_question(question, stream=False, session_id=session_id)

    if response and response.get("code") == 0:
        return jsonify({'answer': response["data"]["answer"]})
    else:
        err_msg = (response.get('message', '未知错误') if response else '请求超时或服务不可用')
        return jsonify({'error': f'获取回答失败：{err_msg}'}), 500


@app.route('/ask_stream', methods=['POST'])
def ask_stream():
    """流式接口：将 RAGFlow SSE 直接转发给前端"""
    data = request.get_json()
    if not data or not data.get('question'):
        return jsonify({'error': '请输入有效的问题'}), 400

    question   = data['question'].strip()
    session_id = get_session_id()

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    payload = {
        "question": question,
        "stream": True
    }
    if session_id:
        payload["session_id"] = session_id

    def generate():
        try:
            with http.post(
                CHAT_URL.format(chat_id=CHAT_ID),
                headers=headers,
                json=payload,
                timeout=(10, 600),
                verify=False,
                stream=True
            ) as r:
                for line in r.iter_lines():
                    if not line:
                        continue
                    line = line.decode('utf-8') if isinstance(line, bytes) else line
                    if not line.startswith('data:'):
                        continue
                    raw = line[5:].strip()
                    if raw == 'true' or raw == '':
                        continue
                    try:
                        obj = json.loads(raw)
                        if obj.get('code') == 0:
                            d = obj.get('data', {})
                            if d is True:
                                # 流结束标志
                                yield f"data: [DONE]\n\n"
                                return
                            if isinstance(d, dict):
                                answer = d.get('answer', '')
                                # 过滤空 answer（最终汇总包）
                                if answer:
                                    yield f"data: {json.dumps({'answer': answer}, ensure_ascii=False)}\n\n"
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )


if __name__ == '__main__':
    print("[启动] 美团客服后端服务 - http://localhost:5050")
    with app.app_context():
        get_session_id()
    app.run(debug=False, port=5050, threaded=True)
