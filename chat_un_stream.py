import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 配置API的基本信息
BASE_URL = "http://localhost//api/v1"
CHAT_URL = f"{BASE_URL}/chats/{{chat_id}}/completions"
API_KEY  = "ragflow-k-j_EVpgxJcpAc6ODopiWqbhxKYR6RRjtzdWcGjtcdw"  # 替换为你的 API Key
CHAT_ID  = "c5e3e92e21e311f183f3c57b390577a0"                        # 替换为你的 Chat ID

# 配置 HTTP Session 与重试策略
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[500, 502, 503, 504]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
http = requests.Session()
http.mount("http://",  adapter)
http.mount("https://", adapter)


def _auth_headers() -> dict:
    """返回带鉴权的请求头"""
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }


def ask_question(question: str, stream: bool = False, session_id: str = None):
    """
    向 RAGFlow 发送非流式问答请求。

    Args:
        question:   用户问题
        stream:     是否请求流式响应（非流式模式下保持 False）
        session_id: 会话 ID，传入后维持上下文

    Returns:
        dict | None: RAGFlow 响应的 JSON 数据，失败时返回 None
    """
    payload = {"question": question, "stream": stream}
    if session_id:
        payload["session_id"] = session_id

    try:
        response = http.post(
            CHAT_URL.format(chat_id=CHAT_ID),
            headers=_auth_headers(),
            json=payload,
            timeout=(10, 600),  # 连接超时 10 s，读取超时 600 s
            verify=False        # 内网自签名证书，禁用 SSL 验证
        )

        if response.status_code == 200:
            return response.json()

        print(f"[RAGFlow] 请求失败，状态码: {response.status_code}")
        print(f"[RAGFlow] 错误详情: {response.text}")
        return None

    except requests.exceptions.RequestException as e:
        print(f"[RAGFlow] 请求异常: {e}")
        return None


# ── 调试入口 ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # 初始化会话
    init_resp = ask_question("你好", stream=False)
    if not (init_resp and init_resp.get("code") == 0):
        print("初始化会话失败")
        exit(1)

    session_id = init_resp["data"].get("session_id")
    print("欢迎消息:", init_resp["data"]["answer"])

    # 发送正式问题
    resp = ask_question("如何寻找合适的门店？", stream=False, session_id=session_id)
    if resp and resp.get("code") == 0:
        print("回答:", resp["data"]["answer"])
    else:
        print("未能获取回答。")
