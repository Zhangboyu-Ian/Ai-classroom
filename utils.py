import os
import random
import string
import time
import socket
from typing import Optional, List
from datetime import datetime

def generate_class_code(length: int = 4) -> str:
    """生成随机的课堂代码"""
    # 使用大写字母和数字
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def generate_student_id() -> str:
    """生成匿名学生ID"""
    # 格式: S-XXXX (X是字母或数字)
    chars = string.ascii_uppercase + string.digits
    return f"S-{''.join(random.choice(chars) for _ in range(4))}"

def find_available_port(start_port: int = 8000) -> int:
    """寻找可用的端口"""
    port = start_port
    max_port = start_port + 100  # 最多尝试100个端口
    
    while port < max_port:
        try:
            # 尝试绑定端口
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('localhost', port))
            sock.close()
            return port
        except OSError:
            # 端口已被占用，尝试下一个
            port += 1
    
    # 如果无法找到可用端口，返回一个默认值
    return 8501

def format_time(seconds: int) -> str:
    """将秒数格式化为mm:ss格式"""
    minutes, seconds = divmod(seconds, 60)
    return f"{minutes:02d}:{seconds:02d}"

def validate_input(text: str, min_length: int = 0, max_length: Optional[int] = None) -> bool:
    """验证输入文本"""
    if not text or len(text) < min_length:
        return False
    if max_length and len(text) > max_length:
        return False
    return True