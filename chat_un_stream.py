import requests
import json
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 配置API的基本信息
BASE_URL = "http://localhost//api/v1"
CHAT_URL = f"{BASE_URL}/chats/{{chat_id}}/completions"
DATASET_URL = f"{BASE_URL}/datasets"
API_KEY = "ragflow-k-j_EVpgxJcpAc6ODopiWqbhxKYR6RRjtzdWcGjtcdw"  # 替换为你的API Key
CHAT_ID = "c5e3e92e21e311f183f3c57b390577a0"  # 替换为你的Chat ID

# 配置重试策略
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[500, 502, 503, 504]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
http = requests.Session()
http.mount("http://", adapter)
http.mount("https://", adapter)

def create_dataset(name, avatar, description, language, embedding_model, permission, chunk_method, parser_config):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    data = {
        "name": name,
        "avatar": avatar,
        "description": description,
        "language": language,
        "embedding_model": embedding_model,
        "permission": permission,
        "chunk_method": chunk_method,
        "parser_config": parser_config
    }
    
    try:
        response = http.post(
            DATASET_URL,
            headers=headers,
            json=data,
            timeout=(10, 600),
            verify=False  # 禁用SSL验证
        )
        
        # print(f"数据集创建响应状态码: {response.status_code}")
        # print(f"数据集创建响应内容: {response.text}")
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"数据集创建失败，状态码: {response.status_code}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"数据集创建请求发生异常: {str(e)}")
        return None

def ask_question(question, stream=False, session_id=None):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    data = {
        "question": question,
        "stream": stream
    }
    
    if session_id:
        data["session_id"] = session_id
    
    try:
        # 发送POST请求，添加超时设置
        response = http.post(
            CHAT_URL.format(chat_id=CHAT_ID),
            headers=headers,
            json=data,
            timeout=(10, 600),  # 连接超时10秒，读取超时60秒
            verify=False  # 禁用SSL验证
        )
        
        # # 打印响应内容用于调试
        # print(f"响应状态码: {response.status_code}")
        # print(f"响应内容: {response.text}")
        
        if response.status_code == 200:
            # 处理流式响应
            if response.text.startswith("data:"):
                # 提取第一个有效JSON块
                json_str = response.text.split("\n")[0][5:]  # 去掉"data:"前缀
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    print("JSON解析失败，原始内容:", json_str)
                    return None
            return response.json()
        else:
            print(f"请求失败，状态码: {response.status_code}")
            print(f"错误详情: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"请求发生异常: {str(e)}")
        return None

# 示例：发送一个问题并获取回答
if __name__ == "__main__":
    # 获取初始会话ID
    init_response = ask_question("你好", stream=False)
    if init_response and init_response.get("code") == 0:
        session_id = init_response["data"].get("session_id")
        print("欢迎消息:", init_response["data"]["answer"])
        
        # 发送正式问题
        question = "如何寻找合适的门店？"
        response = ask_question(question, stream=False, session_id=session_id)
    
    if response and response.get("code") == 0:
        print("回答:", response["data"]["answer"])
    else:
        print("未能获取回答。")
