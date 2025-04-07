# Reload timestamp: 2023-09-13 12:00:00  # Updated timestamp to force reload
import streamlit as st
import os
import pandas as pd
from datetime import datetime
import random
import string
import time
import logging
import sys
import requests
import base64
import tempfile
import json
from urllib.parse import urlparse
import sqlite3

# Configure logging to console only, at INFO level (removing file logging)
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.info("Application started")

# Import project modules
from database import Database, get_api_key
from llm import AIService
from utils import (
    generate_class_code,
    generate_student_id,
    format_time,
    validate_input,
)

# Configure page - must be the first Streamlit command
st.set_page_config(
    page_title="Intelligent Education Tool",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import AI feedback components
sys.path.append(os.path.join(os.path.dirname(__file__), 'components'))
try:
    # Completely ignore original AI feedback components
    pass
except ImportError:
    pass

# Fix the rendering function to more aggressively filter suggestions
def render_ai_feedback(evaluation_result):
    """Render AI feedback with consistent black background and white text style"""
    if not evaluation_result:
        st.info("Evaluation result not available")
        return
    
    try:
        # 检查评估结果的基本结构
        print(f"DEBUG: Evaluation result: {type(evaluation_result)}")
        if not isinstance(evaluation_result, dict):
            st.error("Invalid evaluation format")
            return
            
        # 获取分数并确保它是一个有效的数字
        if 'score' in evaluation_result and evaluation_result['score'] is not None:
            try:
                score = int(float(evaluation_result['score']) * 100)
                # 确保分数在0-100之间
                score = max(0, min(100, score))
            except (ValueError, TypeError):
                score = 50  # 默认分数
        else:
            score = 50
            
        # 获取反馈文本
        feedback = evaluation_result.get('feedback', 'No feedback available')
        # 确保反馈是字符串
        if not isinstance(feedback, str):
            feedback = "No feedback available"
            
        # 获取并处理建议
        raw_suggestions = evaluation_result.get('suggestions', [])
        if not isinstance(raw_suggestions, list):
            print("WARNING: suggestions is not a list")
            raw_suggestions = []
            
        # 预定义的默认建议，以防建议列表为空或无效
        default_suggestions = [
            "Focus on addressing the question directly",
            "Provide more detailed examples and evidence",
            "Structure your answer with a clear introduction and conclusion"
        ]
        
        # 处理和过滤建议
        clean_suggestions = []
        for suggestion in raw_suggestions:
            # 确保建议是字符串
            if not isinstance(suggestion, str):
                continue
                
            # 清理文本
            clean_text = suggestion.strip()
            if not clean_text:
                continue
                
            # 过滤掉可能的指令性文本或非英文内容
            if any(char in clean_text for char in ['，', '。', '学', '生', '请', '你', '找', '无法', '点击']):
                print(f"DEBUG: Filtering out suspicious content: {clean_text}")
                continue
                
            # 过滤掉任何疑似控制字符的内容
            if '<' in clean_text or '>' in clean_text:
                continue
                
            # 过滤掉可能的指令性短语
            if any(phrase in clean_text.lower() for phrase in ['reload', 'refresh button', 'find the', 'student click']):
                continue
                
            # 通过检查的建议添加到清洁列表
            clean_suggestions.append(clean_text)
            
        # 如果没有有效建议，使用默认建议
        if not clean_suggestions:
            clean_suggestions = default_suggestions.copy()
            
        # 限制为最多3个建议
        clean_suggestions = clean_suggestions[:3]
        
        # 如果不足3个，添加默认建议
        while len(clean_suggestions) < 3:
            for default in default_suggestions:
                if default not in clean_suggestions:
                    clean_suggestions.append(default)
                    break
            # 防止无限循环
            if len(clean_suggestions) >= 3:
                break
                
        # 设置分数颜色
        if score >= 80:
            score_color = "#4CAF50"  # 绿色 - 优秀
        elif score >= 60:
            score_color = "#FFC107"  # 黄色 - 良好
        else:
            score_color = "#FF5722"  # 橙红色 - 需要改进
        
        # 构建HTML - 保持简洁整洁
        feedback_html = f"""
        <div class="ai-feedback-container">
            <div class="ai-feedback-title">AI Assessment Results</div>
            
            <div class="ai-feedback-score-container">
                <div class="ai-feedback-score" style="color: {score_color};">{score}%</div>
                <div class="ai-feedback-score-label">Overall Score</div>
            </div>
            
            <div class="ai-feedback-section">
                <div class="ai-feedback-header">Detailed Feedback</div>
                <div class="ai-feedback-text">{feedback}</div>
            </div>
            
            <div class="ai-feedback-section">
                <div class="ai-feedback-header">Improvement Suggestions</div>
                <div class="ai-feedback-suggestions-container">
        """
        
        # 添加建议条目 - 确保仅包含有效的建议
        for i, suggestion in enumerate(clean_suggestions):
            feedback_html += f'<div class="ai-feedback-suggestion"><span class="suggestion-number">{i+1}</span> {suggestion}</div>'
        
        # 完成HTML
        feedback_html += """
                </div>
            </div>
        </div>
        """
        
        # 渲染HTML
        st.markdown(feedback_html, unsafe_allow_html=True)
        
    except Exception as e:
        # 如果渲染过程中发生错误，记录并显示简单的反馈
        print(f"Error rendering AI feedback: {str(e)}")
        st.error("There was a problem displaying the AI feedback. Please try again.")

# Add custom CSS - ensure higher style priority
def load_css():
    st.markdown("""
    <style>
    /* Global font settings */
    * {
        font-family: 'Noto Sans', sans-serif;
    }
    
    h1, h2, h3 {
        font-family: 'Source Han Sans CN', 'Noto Sans CJK SC', sans-serif;
        font-weight: bold;
    }
    
    /* Button styles */
    .stButton>button {
        min-height: 40px;
        min-width: 40px;
    }
    
    /* Input box styles */
    .stTextInput>div>div>input {
        min-height: 40px;
    }
    
    /* Error box styles */
    .error-box {
        border: 2px solid red;
        border-radius: 5px;
        padding: 10px;
        margin: 10px 0;
        background-color: #ffeeee;
        color: #333333;
    }
    
    /* Word counter styles */
    .word-counter {
        text-align: right;
        font-size: 0.8em;
        color: #888;
    }
    
    /* Score display styles */
    .score-display {
        font-size: 1.2em;
        font-weight: bold;
        color: #333333;
    }
    
    /* Redefine AI feedback styles - enforce black background and white text */
    .ai-feedback-container {
        background-color: #1E1E1E !important;
        color: #FFFFFF !important;
        border-radius: 10px !important;
        padding: 25px !important;
        margin: 20px 0 !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2) !important;
        font-family: 'Noto Sans', sans-serif !important;
        border: none !important;
    }
    
    .ai-feedback-title {
        font-size: 1.5em !important;
        font-weight: bold !important;
        text-align: center !important;
        margin-bottom: 20px !important;
        color: #FFFFFF !important;
        border-bottom: 1px solid #444 !important;
        padding-bottom: 15px !important;
    }
    
    .ai-feedback-score-container {
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        margin: 15px 0 25px 0 !important;
        padding: 15px !important;
        border-radius: 8px !important;
        background-color: rgba(255, 255, 255, 0.05) !important;
    }
    
    .ai-feedback-score {
        font-size: 3em !important;
        font-weight: bold !important;
        margin: 5px 0 !important;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3) !important;
    }
    
    .ai-feedback-score-label {
        font-size: 0.9em !important;
        color: #BBBBBB !important;
    }
    
    .ai-feedback-header {
        font-size: 1.2em !important;
        font-weight: bold !important;
        margin: 20px 0 15px 0 !important;
        padding-bottom: 8px !important;
        border-bottom: 1px solid #444 !important;
        color: #FFFFFF !important;
    }
    
    .ai-feedback-text {
        margin: 15px 0 !important;
        line-height: 1.6 !important;
        background-color: rgba(255, 255, 255, 0.05) !important;
        padding: 15px !important;
        border-radius: 6px !important;
        color: #EEEEEE !important;
    }
    
    .ai-feedback-section {
        margin-top: 20px !important;
    }
    
    .ai-feedback-suggestions-container {
        padding: 10px 0 !important;
    }
    
    .ai-feedback-suggestion {
        margin: 10px 0 !important;
        padding: 12px 15px 12px 15px !important;
        border-radius: 6px !important;
        background-color: rgba(255, 255, 255, 0.05) !important;
        position: relative !important;
        color: #FFFFFF !important;
    }
    
    .suggestion-number {
        display: inline-block !important;
        width: 24px !important;
        height: 24px !important;
        background-color: #4CAF50 !important;
        color: white !important;
        border-radius: 50% !important;
        text-align: center !important;
        line-height: 24px !important;
        font-size: 0.85em !important;
        margin-right: 10px !important;
    }
    
    .ai-feedback-no-suggestions {
        text-align: center !important;
        padding: 15px !important;
        color: #BBBBBB !important;
        font-style: italic !important;
    }
    
    /* Auto-refresh indicator styles */
    .refresh-indicator {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        padding: 8px !important;
        background-color: #f0f2f6 !important;
        border-radius: 4px !important;
        margin: 10px 0 !important;
        font-size: 0.9em !important;
        color: #4a4a4a !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1) !important;
        animation: pulse 2s infinite !important;
    }
    
    .refresh-icon {
        margin-right: 8px !important;
        font-size: 1.2em !important;
        display: inline-block !important;
        animation: spin 4s linear infinite !important;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    @keyframes pulse {
        0% { background-color: #f0f2f6; }
        50% { background-color: #e1e5ea; }
        100% { background-color: #f0f2f6; }
    }
    </style>
    """, unsafe_allow_html=True)

# Now load CSS, ensuring it's after set_page_config
load_css()

# Initialize database
db = Database()

# Initialize session states
if 'user_type' not in st.session_state:
    # Check if user_type is in query params first
    if "user_type" in st.query_params:
        st.session_state.user_type = st.query_params["user_type"]
    else:
        st.session_state.user_type = None
        
if 'class_code' not in st.session_state:
    # Check if class_code is in query params first
    if "class_code" in st.query_params:
        st.session_state.class_code = st.query_params["class_code"]
    else:
        st.session_state.class_code = None
        
if 'student_id' not in st.session_state:
    # Check if student_id is in query params first
    if "student_id" in st.query_params:
        st.session_state.student_id = st.query_params["student_id"]
    else:
        st.session_state.student_id = None
        
if 'current_question' not in st.session_state:
    st.session_state.current_question = None
if 'questions' not in st.session_state:
    st.session_state.questions = []
if 'current_question_index' not in st.session_state:
    st.session_state.current_question_index = -1
if 'timer_active' not in st.session_state:
    st.session_state.timer_active = False
if 'time_remaining' not in st.session_state:
    st.session_state.time_remaining = 0
if 'answer_submitted' not in st.session_state:
    st.session_state.answer_submitted = False
if 'evaluation_result' not in st.session_state:
    st.session_state.evaluation_result = None
if 'connected_students' not in st.session_state:
    st.session_state.connected_students = []
if 'editing_question_index' not in st.session_state:
    st.session_state.editing_question_index = -1
if 'delete_confirm' not in st.session_state:
    st.session_state.delete_confirm = None
if 'video_request_id' not in st.session_state:
    st.session_state.video_request_id = None
if 'video_status' not in st.session_state:
    st.session_state.video_status = None
if 'video_url' not in st.session_state:
    st.session_state.video_url = None
if 'generating_video' not in st.session_state:
    st.session_state.generating_video = False
if 'show_video_form' not in st.session_state:
    st.session_state.show_video_form = False

# D-ID API related functions
def get_basic_auth_header(api_key):
    """Convert API key to Basic Auth format"""
    auth_bytes = api_key.encode("utf-8")
    auth_base64 = base64.b64encode(auth_bytes).decode("utf-8")
    return f"Basic {auth_base64}"

def create_video(image_url, text, voice_id="en-US-JennyNeural"):
    """Create D-ID video task"""
    # D-ID API configuration
    API_KEY = "c3RhcnRiaW5neGlhQGdtYWlsLmNvbQ:EBt57JcdPOqPdfhj6SpwM"
    API_URL = "https://api.d-id.com/talks"
    
    # Set authorization header
    headers = {
        "Authorization": get_basic_auth_header(API_KEY),
        "Content-Type": "application/json"
    }

    # Build video task request parameters
    payload = {
        "source_url": image_url,
        "script": {
            "type": "text",
            "input": text,
            "provider": {
                "type": "microsoft",
                "voice_id": voice_id
            }
        }
    }

    try:
        # Send request to create video task
        response = requests.post(API_URL, headers=headers, json=payload)
        if response.status_code != 201:
            logging.error(f"Failed to create video task: {response.text}")
            return None, f"Error ({response.status_code}): {response.text}"
        
        # Return video task ID
        result = response.json()
        return result.get("id"), None
    except Exception as e:
        logging.error(f"Exception while creating video task: {str(e)}")
        return None, str(e)

def get_video_status(video_id):
    """Get D-ID video task status"""
    API_KEY = "c3RhcnRiaW5neGlhQGdtYWlsLmNvbQ:EBt57JcdPOqPdfhj6SpwM"
    API_URL = "https://api.d-id.com/talks"
    
    headers = {
        "Authorization": get_basic_auth_header(API_KEY)
    }
    
    try:
        response = requests.get(f"{API_URL}/{video_id}", headers=headers)
        if response.status_code != 200:
            return None, f"Error ({response.status_code}): {response.text}"
        
        return response.json(), None
    except Exception as e:
        return None, str(e)

def is_valid_url(url):
    """Check if URL is valid"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def find_database_files():
    """Find all database files in the workspace"""
    import glob
    
    # Get all .db files in the current working directory
    db_files = glob.glob("*.db")
    # Get all .db files in the workspace directory
    workspace_db_files = glob.glob("/workspaces/QUIZ_NEW/*.db")
    
    all_db_files = list(set(db_files + workspace_db_files))
    return all_db_files

# Add a debug helper function to sanitize suggestions
def debug_sanitize_suggestions(suggestions):
    """Debug function to sanitize suggestions data before display"""
    if not isinstance(suggestions, list):
        print(f"WARNING: suggestions is not a list, but {type(suggestions)}")
        return ["Focus on addressing the question directly", 
                "Provide more specific examples", 
                "Organize your answer with a clear structure"]
    
    clean_suggestions = []
    for item in suggestions:
        if not isinstance(item, str):
            print(f"WARNING: suggestion item is not a string, but {type(item)}")
            continue
        
        # Remove any suspicious content (Chinese characters, directives, etc.)
        if any(x in item for x in ['，', '学生', '点击', '请你']):
            print(f"WARNING: suspicious content in suggestion: {item}")
            continue
            
        clean_suggestions.append(item)
    
    # Ensure we have something to display
    if not clean_suggestions:
        return ["Focus on addressing the question directly", 
                "Provide more specific examples", 
                "Organize your answer with a clear structure"]
                
    return clean_suggestions

# Add this new function for displaying only suggestions
def display_suggestions(suggestions):
    """
    Display a simple list of suggestions without any complex HTML or scoring.
    """
    if not suggestions or not isinstance(suggestions, list):
        suggestions = [
            "Focus on addressing the main question more directly.",
            "Include specific examples to support your key points.",
            "Structure your answer with a clear introduction and conclusion."
        ]
    
    st.subheader("Suggestions for Improvement")
    
    # Display each suggestion as a simple bullet point
    for i, suggestion in enumerate(suggestions[:3]):
        if isinstance(suggestion, str) and suggestion.strip():
            st.markdown(f"**{i+1}.** {suggestion.strip()}")
    
    st.info("These suggestions aim to help you improve your answer. Consider them for your next responses.")

# Update the student_view function to ensure video generation works properly
def student_view():
    """Student terminal view"""
    st.title("Student Terminal 👨‍🎓")
    
    if not st.session_state.class_code:
        st.header("Join Class")
        
        col1, col2 = st.columns(2)
        
        with col1:
            class_code = st.text_input("Enter class code:", max_chars=4).upper()
            
            if st.button("Join", type="primary"):
                if len(class_code) == 4:
                    # Show database connection status for debugging
                    st.info(f"Connecting to database at: {db.db_path}")
                    
                    # Validate class code exists
                    conn = sqlite3.connect(db.db_path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM classrooms WHERE class_code = ?", (class_code,))
                    count = cursor.fetchone()[0]
                    conn.close()
                    
                    if count == 0:
                        st.error(f"Class code '{class_code}' does not exist in the database. Please check the code.")
                        return
                    
                    # Create student ID and add to class    
                    student_id = generate_student_id()
                    if db.add_student(student_id, class_code):
                        st.session_state.class_code = class_code
                        st.session_state.student_id = student_id
                        st.query_params.class_code = class_code
                        st.query_params.student_id = student_id
                        st.success(f"Successfully joined class: {class_code}")
                        st.rerun()
                    else:
                        st.error(f"Failed to join: Class code '{class_code}' does not exist or is closed. Please check the class code.")
                else:
                    st.error("Class code must be 4 characters")
        
        with col2:
            st.info("Tip: Ask your teacher for the class code")
    
    else:
        st.header(f"Joined Class: {st.session_state.class_code}")
        st.subheader(f"Your ID: {st.session_state.student_id}")
        
        # IMPORTANT: Get current classroom info first, before rendering anything else
        db_info = db.get_classroom_info(st.session_state.class_code)
        if db_info and db_info['question'] != st.session_state.current_question:
            st.session_state.current_question = db_info['question']
            st.session_state.answer_submitted = False
            st.session_state.video_url = None
            st.session_state.video_request_id = None
            st.session_state.generating_video = False
            st.session_state.show_video_form = False

        # Refresh button - separate from the auto-check
        col_refresh1, col_refresh2 = st.columns([1, 3])
        with col_refresh1:
            if st.button("Refresh Question", type="primary", 
                         help="Click to get the latest question from the teacher"):
                db_info = db.get_classroom_info(st.session_state.class_code)
                if db_info and db_info.get('question'):
                    current_question = db_info.get('question')
                    # Force reset answer state even if the question is the same
                    if current_question != st.session_state.current_question:
                        st.session_state.current_question = current_question
                        st.session_state.answer_submitted = False  # Key line
                        st.session_state.evaluation_result = None
                        st.session_state.video_url = None
                        st.session_state.video_request_id = None
                        st.session_state.generating_video = False
                        st.session_state.show_video_form = False
                        st.success("New question loaded!")
                        # Force an immediate rerun to update the UI
                        st.rerun()
                    else:
                        st.info("You already have the latest question")
                else:
                    st.warning("Couldn't retrieve question. Please try again.")
        
        with col_refresh2:
            st.info(f"Current question last updated: {datetime.now().strftime('%H:%M:%S')}")
        
        # Show the question
        st.markdown("### 📝 Discussion Question:")
        st.info(st.session_state.current_question or "Waiting for teacher to post a question...")
        
        # Conditional UI based on answer_submitted state
        if st.session_state.current_question:
            if st.session_state.answer_submitted:
                st.info("You already submitted your answer for this question.")
                st.write("**Your Answer:**")
                st.info(st.session_state.answer_text)
                
                # Add AI video button - ensure it's displayed
                video_col1, video_col2 = st.columns([1, 3])
                
                with video_col1:
                    if not st.session_state.generating_video and not st.session_state.video_url:
                        if st.button("Generate AI Video Explanation", type="primary"):
                            st.session_state.show_video_form = True
                            st.rerun()
                
                with video_col2:
                    if not st.session_state.generating_video and not st.session_state.video_url:
                        st.info("Click the button to generate a video explanation based on AI feedback")
                
                # Update the video generation form to allow gender-based image selection
                if st.session_state.show_video_form and not st.session_state.video_url:
                    # Add a back button at the top of the form
                    if st.button("← Back to Answer Page", key="back_to_answer"):
                        st.session_state.show_video_form = False
                        st.rerun()
                    
                    with st.form("video_generation_form"):
                        st.subheader("Set AI Video Parameters")
                        
                        # Default image URLs for male and female
                        male_image_url = "https://i.imgur.com/GODJ74i.png"
                        female_image_url = "https://i.imgur.com/BKQDkfy.png"
                        
                        # Gender selection
                        gender = st.radio(
                            "Select Character Gender:",
                            ["Male", "Female"],
                            horizontal=True
                        )
                        
                        # Set image URL based on gender selection
                        image_url = male_image_url if gender == "Male" else female_image_url
                        
                        # Display selected image preview
                        st.write("### Image Preview")
                        st.image(image_url, width=150)
                        
                        # Voice options
                        voice_option = st.radio(
                            "Select Voice:",
                            ["Male", "Female"],
                            horizontal=True
                        )
                        
                        # Use the appropriate voice for the selected gender
                        voice_id = "en-US-GuyNeural" if voice_option == "Male" else "en-US-JennyNeural"
                        
                        # Create a more detailed and clear script with the suggestions
                        suggestions_list = st.session_state.answer_suggestions if hasattr(st.session_state, 'answer_suggestions') else []
                        
                        if not suggestions_list or len(suggestions_list) < 3:
                            suggestions_list = [
                                "Focus on addressing the main question more directly.",
                                "Include specific examples to support your key points.",
                                "Structure your answer with a clear introduction and conclusion."
                            ]
                            
                        default_script = f"""Hello! I've reviewed your answer to the discussion question.

Here are three suggestions to improve your response:

First, {suggestions_list[0]}

Second, {suggestions_list[1]}

And finally, {suggestions_list[2]}

Implementing these suggestions will strengthen your answer and make it more effective!
"""
                        
                        video_script = st.text_area(
                            "Video Explanation Content:",
                            value=default_script,
                            height=200
                        )
                        
                        submitted = st.form_submit_button("Start Generating Video")
                        cancelled = st.form_submit_button("Cancel", type="secondary")
                        
                        if submitted:
                            # Confirm URL is valid
                            if not is_valid_url(image_url):
                                st.error("Please provide a valid image URL")
                                return
                            
                            with st.spinner("Creating video task..."):
                                video_id, error = create_video(image_url, video_script, voice_id)
                                if error:
                                    st.error(f"Failed to create video: {error}")
                                else:
                                    st.session_state.video_request_id = video_id
                                    st.session_state.generating_video = True
                                    st.session_state.show_video_form = False
                                    st.success("Video task created!")
                                    st.rerun()
                        
                        if cancelled:
                            st.session_state.show_video_form = False
                            st.rerun()
                
                # Check video generation status and display video
                if st.session_state.generating_video and st.session_state.video_request_id:
                    with st.spinner("Generating video..."):
                        status, error = get_video_status(st.session_state.video_request_id)
                        if error:
                            st.error(f"Error checking video status: {error}")
                            st.session_state.generating_video = False
                        elif status:
                            if status.get("status") == "done":
                                result_url = status.get("result_url")
                                if result_url:
                                    st.session_state.video_url = result_url
                                    st.session_state.generating_video = False
                                    st.success("Video generated successfully!")
                                    st.rerun()
                            elif status.get("status") == "error":
                                st.error("Video generation failed")
                                st.session_state.generating_video = False
                            else:
                                # Display generation progress
                                progress = st.progress(0)
                                status_text = status.get("status", "processing")
                                st.text(f"Video Status: {status_text}")
                                time.sleep(2)  # Wait 2 seconds before refreshing
                                st.rerun()
                
                # Display generated video
                if st.session_state.video_url:
                    st.subheader("AI Video Explanation")
                    # Use HTML video tag to display video, add autoplay attribute
                    video_html = f"""
                    <video width="100%" controls autoplay>
                        <source src="{st.session_state.video_url}" type="video/mp4">
                        Your browser does not support the video tag.
                    </video>
                    """
                    st.markdown(video_html, unsafe_allow_html=True)
                    
                    # Add new "Next Question" button
                    next_col1, next_col2 = st.columns([1, 3])
                    with next_col1:
                        if st.button("Next Question", type="primary"):
                            # Check if teacher has moved to a new question
                            current_db_info = db.get_classroom_info(st.session_state.class_code)
                            if current_db_info and current_db_info['question'] != st.session_state.current_question:
                                # Teacher has updated the question, reset the UI
                                st.session_state.current_question = current_db_info['question']
                                st.session_state.answer_submitted = False
                                st.session_state.video_url = None
                                st.session_state.video_request_id = None
                                st.session_state.generating_video = False
                                st.session_state.show_video_form = False
                                st.success("New question loaded!")
                                st.rerun()
                            else:
                                # No new question yet
                                st.warning("The teacher hasn't moved to a new question yet. Please try again later.")
                    
                    # Add regenerate video button
                    with next_col2:
                        if st.button("Generate New Video"):
                            st.session_state.video_url = None
                            st.session_state.video_request_id = None
                            st.session_state.generating_video = False
                            st.session_state.show_video_form = True
                            st.rerun()
                
                # Display suggestions using the simple function
                if hasattr(st.session_state, 'answer_suggestions'):
                    display_suggestions(st.session_state.answer_suggestions)
                else:
                    display_suggestions([])  # Display default suggestions if none available
            
            else:
                answer_text = st.text_area("Enter your answer:")
                if st.button("Submit Answer", type="primary"):
                    if answer_text.strip() == "":
                        st.error("Answer cannot be empty. Please provide a valid response.")
                    else:
                        with st.spinner("Analyzing your answer..."):
                            try:
                                # Get only suggestions instead of full evaluation
                                suggestions = AIService.get_simple_suggestions(
                                    st.session_state.current_question, 
                                    answer_text
                                )
                                
                                # Store only suggestions in session state
                                st.session_state.answer_suggestions = suggestions
                                st.session_state.answer_submitted = True
                                st.session_state.answer_text = answer_text
                                
                                # Use a simpler approach to store in database
                                # Just create a minimal evaluation object
                                simple_eval = {
                                    "score": 0.7,  # Default score (not shown to student)
                                    "feedback": "Thank you for your answer.",
                                    "suggestions": suggestions
                                }
                                
                                # Save to database
                                db.save_answer(
                                    st.session_state.student_id,
                                    st.session_state.class_code,
                                    st.session_state.current_question,
                                    answer_text,
                                    simple_eval
                                )
                                
                                st.rerun()
                            except Exception as e:
                                st.error(f"Could not analyze your answer: {e}")
        else:
            st.info("No question available at the moment.")
        
        if st.button("Leave Class"):
            st.session_state.class_code = None
            st.session_state.student_id = None
            st.session_state.current_question = None
            st.session_state.answer_submitted = False
            st.session_state.evaluation_result = None
            st.query_params.clear()
            st.rerun()

# Define the teacher_view function with complete implementation
def teacher_view():
    """Teacher view with tabs for question creation and classroom management"""
    # 创建标签页
    tab1, tab2, tab3 = st.tabs([
        "Question Creation", 
        "Classroom Management",
        "Data Export"
    ])

    # Question Creation tab
    with tab1:
        col1, col2 = st.columns(2)
        
        # Manual Input Column
        with col1:
            st.subheader("Manual Input")
            question_text = st.text_area("Enter question:", height=150)
            if st.button("Add This Question", key="manual_question"):
                if validate_input(question_text):
                    if "questions" not in st.session_state:
                        st.session_state.questions = []
                    st.session_state.questions.append(question_text)
                    if len(st.session_state.questions) == 1 or st.session_state.current_question is None:
                        st.session_state.current_question = question_text
                        st.session_state.current_question_index = 0
                    st.success("Question added!")
                else:
                    st.error("Question cannot be empty. Please enter content.")
        
        # AI Generated Questions Column
        with col2:
            st.subheader("AI-Generated Questions")
            subject = st.selectbox("Subject:", ["Science", "Math", "Literature", "History", "Geography", "Art", "General"])
            difficulty = st.select_slider("Difficulty:", options=["Easy", "Medium", "Hard"])
            keywords = st.text_input("Keywords (separated by commas):")
            
            # 将生成的问题存储在 session_state 中
            if "generated_question" not in st.session_state:
                st.session_state.generated_question = None
            
            # Generate Question Button
            generate_clicked = st.button("Generate Question", key="generate_question_btn")
            
            if generate_clicked:
                with st.spinner("AI is generating a question..."):
                    try:
                        params = {
                            "subject": subject.lower(),
                            "difficulty": difficulty.lower(),
                            "keywords": [k.strip() for k in keywords.split(",") if k.strip()]
                        }
                        generated_question = AIService.generate_question(params)
                        st.session_state.generated_question = generated_question
                        st.info(generated_question)
                    except Exception as e:
                        st.error(f"Failed to generate question: {e}")
            
            # 如果有生成的问题，显示添加按钮
            if st.session_state.generated_question:
                if st.button("Add to Question List", key="add_ai_question"):
                    if "questions" not in st.session_state:
                        st.session_state.questions = []
                    st.session_state.questions.append(st.session_state.generated_question)
                    if len(st.session_state.questions) == 1 or st.session_state.current_question is None:
                        st.session_state.current_question = st.session_state.generated_question
                        st.session_state.current_question_index = 0
                    st.success("Question added to list!")
                    st.session_state.generated_question = None  # 清除已添加的问题
                    st.rerun()     
        if st.session_state.questions:
            st.markdown("---")
            st.subheader("Question Management")
            st.info("Manage all your created questions here. You can edit, delete, or reorder these questions. During class, you can browse these questions in the 'Classroom Management' tab.")
            
            question_manager = st.container()
            
            with question_manager:
                for i, question in enumerate(st.session_state.questions):
                    with st.expander(f"Question {i+1}", expanded=(i == st.session_state.current_question_index)):
                        if i == st.session_state.current_question_index:
                            st.markdown("📌 **Current Active Question**")
                        
                        if st.session_state.editing_question_index == i:
                            edited_question = st.text_area(
                                "Edit question:", 
                                value=question, 
                                height=150, 
                                key=f"edit_question_{i}"
                            )
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("Save Changes", key=f"save_edit_{i}"):
                                    if validate_input(edited_question):
                                        st.session_state.questions[i] = edited_question
                                        if i == st.session_state.current_question_index:
                                            st.session_state.current_question = edited_question
                                            if st.session_state.class_code:
                                                db.update_classroom_question(st.session_state.class_code, edited_question)
                                        st.session_state.editing_question_index = -1
                                        st.success("Question updated!")
                                        st.rerun()
                                    else:
                                        st.error("Question cannot be empty. Please enter content.")
                            with col2:
                                if st.button("Cancel Editing", key=f"cancel_edit_{i}"):
                                    st.session_state.editing_question_index = -1
                                    st.rerun()
                        else:
                            st.markdown(f"**Question Content:**")
                            st.info(question)
                            col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
                            
                            with col1:
                                if st.button("Edit", key=f"edit_{i}"):
                                    st.session_state.editing_question_index = i
                                    st.rerun()
                            
                            with col2:
                                if st.button("Delete", key=f"delete_{i}"):
                                    if "delete_confirm" not in st.session_state:
                                        st.session_state.delete_confirm = None
                                    st.session_state.delete_confirm = i
                                    st.rerun()
                            
                            with col3:
                                if i > 0:
                                    if st.button("Move Up", key=f"move_up_{i}"):
                                        st.session_state.questions[i], st.session_state.questions[i-1] = st.session_state.questions[i-1], st.session_state.questions[i]
                                        if i == st.session_state.current_question_index:
                                            st.session_state.current_question_index = i-1
                                        elif i-1 == st.session_state.current_question_index:
                                            st.session_state.current_question_index = i
                                        st.rerun()
                            
                            with col4:
                                if i < len(st.session_state.questions) - 1:
                                    if st.button("Move Down", key=f"move_down_{i}"):
                                        st.session_state.questions[i], st.session_state.questions[i+1] = st.session_state.questions[i+1], st.session_state.questions[i]
                                        if i == st.session_state.current_question_index:
                                            st.session_state.current_question_index = i+1
                                        elif i+1 == st.session_state.current_question_index:
                                            st.session_state.current_question_index = i
                                        st.rerun()
                
                if hasattr(st.session_state, 'delete_confirm') and st.session_state.delete_confirm is not None:
                    i = st.session_state.delete_confirm
                    st.warning(f"Are you sure you want to delete Question {i+1}? This action cannot be undone.")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Confirm Delete", key=f"confirm_delete_{i}"):
                            deleted_question = st.session_state.questions.pop(i)
                            if i == st.session_state.current_question_index:
                                if st.session_state.questions:
                                    new_index = min(i, len(st.session_state.questions) - 1)
                                    st.session_state.current_question_index = new_index
                                    st.session_state.current_question = st.session_state.questions[new_index]
                                    if st.session_state.class_code:
                                        db.update_classroom_question(st.session_state.class_code, st.session_state.current_question)
                                else:
                                    st.session_state.current_question_index = -1
                                    st.session_state.current_question = None
                            elif i < st.session_state.current_question_index:
                                st.session_state.current_question_index -= 1
                            st.session_state.delete_confirm = None
                            st.success(f"Question {i+1} deleted")
                            st.rerun()
                    with col2:
                        if st.button("Cancel Delete", key=f"cancel_delete_{i}"):
                            st.session_state.delete_confirm = None
                            st.rerun()
    
    # Classroom Management tab
    with tab2:
        st.header("Classroom Management")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.session_state.class_code:
                st.subheader(f"Current Class Code: {st.session_state.class_code}")
                
                # Question navigation area
                if st.session_state.questions:
                    st.write("### Question Navigation")
                    question_count = len(st.session_state.questions)
                    current_index = st.session_state.current_question_index
                    
                    # Display current question number
                    st.write(f"Current Question: {current_index + 1}/{question_count}")
                    
                    # Fix: Move dropdown to separate line
                    question_options = [f"Question {i+1}" for i in range(question_count)]
                    selected_question = st.selectbox(
                        "Select Question:", 
                        options=question_options, 
                        index=current_index
                    )
                    selected_index = question_options.index(selected_question)
                    if selected_index != current_index:
                        st.session_state.current_question_index = selected_index
                        st.session_state.current_question = st.session_state.questions[selected_index]
                        db.update_classroom_question(st.session_state.class_code, st.session_state.current_question)
                        st.rerun()
                    
                    # Add previous/next buttons in separate row
                    col_nav1, col_nav2 = st.columns(2)
                    
                    with col_nav1:
                        if current_index > 0:
                            if st.button("← Previous Question", key="prev_question", use_container_width=True):
                                st.session_state.current_question_index -= 1
                                st.session_state.current_question = st.session_state.questions[st.session_state.current_question_index]
                                db.update_classroom_question(st.session_state.class_code, st.session_state.current_question)
                                st.rerun()
                        else:
                            st.button("← Previous Question", disabled=True, key="prev_question_disabled", use_container_width=True)
                    
                    with col_nav2:
                        if current_index < question_count - 1:
                            if st.button("Next Question →", key="next_question", use_container_width=True):
                                st.session_state.current_question_index += 1
                                st.session_state.current_question = st.session_state.questions[st.session_state.current_question_index]
                                db.update_classroom_question(st.session_state.class_code, st.session_state.current_question)
                                st.rerun()
                        else:
                            st.button("Next Question →", disabled=True, key="next_question_disabled", use_container_width=True)
                
                # Display current question
                if st.session_state.current_question:
                    st.write("**Current Question:**")
                    st.info(st.session_state.current_question)
                    
                    # Add student answers list button
                    if st.button("View Student Answers", key="view_student_answers", type="primary"):
                        # Get all student answers for current question
                        student_answers = db.get_answers_for_question(
                            st.session_state.class_code, 
                            st.session_state.current_question
                        )
                        
                        if student_answers:
                            st.session_state.student_answers = student_answers
                        else:
                            st.session_state.student_answers = []
                        
                        # Set display state
                        if 'show_answers' not in st.session_state:
                            st.session_state.show_answers = True
                        else:
                            st.session_state.show_answers = True
                        
                        st.rerun()
                    
                    # Display student answers list
                    if 'show_answers' in st.session_state and st.session_state.show_answers and 'student_answers' in st.session_state:
                        if st.button("Hide Student Answers", key="hide_student_answers"):
                            st.session_state.show_answers = False
                            st.rerun()
                        
                        st.subheader(f"Student Answers ({len(st.session_state.student_answers)} responses)")
                        
                        if not st.session_state.student_answers:
                            st.info("No students have submitted answers yet")
                        else:
                            # Create a table displaying all answers
                            answer_data = []
                            for idx, answer in enumerate(st.session_state.student_answers):
                                # Format score as percentage
                                score_pct = int(answer['score'] * 100)
                                # Format time
                                submitted_time = answer['submitted_at']
                                if isinstance(submitted_time, str):
                                    try:
                                        submitted_time = datetime.strptime(submitted_time, "%Y-%m-%d %H:%M:%S.%f")
                                    except:
                                        pass
                                # Format time string
                                if isinstance(submitted_time, datetime):
                                    time_str = submitted_time.strftime("%H:%M:%S")
                                else:
                                    time_str = str(submitted_time)
                                
                                # Add to table data
                                answer_data.append({
                                    "No.": idx + 1,
                                    "Student ID": answer['student_id'],
                                    "Time": time_str,
                                    "Score": f"{score_pct}%",
                                    "Preview": answer['answer'][:30] + "..." if len(answer['answer']) > 30 else answer['answer']
                                })
                            
                            # Convert to DataFrame and display
                            answer_df = pd.DataFrame(answer_data)
                            st.dataframe(answer_df, use_container_width=True)
                            
                            # View detailed answer
                            st.subheader("View Detailed Answer")
                            answer_idx = st.selectbox(
                                "Select an answer to view:", 
                                range(len(st.session_state.student_answers)),
                                format_func=lambda i: f"{i+1}. {st.session_state.student_answers[i]['student_id']}"
                            )
                            
                            if answer_idx is not None:
                                selected_answer = st.session_state.student_answers[answer_idx]
                                
                                st.markdown("#### Student Information")
                                st.write(f"**Student ID:** {selected_answer['student_id']}")
                                st.write(f"**Submission Time:** {selected_answer['submitted_at']}")
                                
                                st.markdown("#### Answer Content")
                                st.info(selected_answer['answer'])
                                
                                # Print debug info
                                print(f"DEBUG: Suggestions data type: {type(selected_answer['suggestions'])}")
                                print(f"DEBUG: Raw suggestions data: {selected_answer['suggestions']}")
                                
                                # Sanitize potentially problematic suggestions data
                                sanitized_suggestions = debug_sanitize_suggestions(selected_answer['suggestions'])
                                
                                # 分别显示评分、反馈和建议
                                st.markdown("#### AI Assessment")
                                
                                # 显示分数
                                score = int(float(selected_answer['score']) * 100)
                                if score >= 80:
                                    score_color = "green"
                                elif score >= 60:
                                    score_color = "orange" 
                                else:
                                    score_color = "red"
                                    
                                st.markdown(f"**Score:** <span style='color:{score_color}'>{score}%</span>", 
                                          unsafe_allow_html=True)
                                
                                # 显示反馈
                                st.markdown("**Detailed Feedback:**")
                                if selected_answer['feedback']:
                                    st.info(selected_answer['feedback'])
                                else:
                                    st.info("No detailed feedback available")
                                
                                # 显示改进建议
                                st.markdown("**Improvement Suggestions:**")
                                if sanitized_suggestions:
                                    for i, suggestion in enumerate(sanitized_suggestions, 1):
                                        st.write(f"{i}. {suggestion}")
                                else:
                                    st.info("No improvement suggestions available")
                
                else:
                    st.warning("No discussion question set. Please create questions in the 'Question Creation' tab.")
                
                if st.button("End Class", type="primary"):
                    st.session_state.class_code = None
                    st.session_state.current_question = None
                    st.session_state.timer_active = False
                    st.session_state.connected_students = []
                    st.query_params.class_code = ""
            else:
                st.subheader("Create New Class")
                
                if not st.session_state.questions:
                    st.warning("Please create at least one question in the 'Question Creation' tab first.")
                    st.stop()
                
                if st.button("Generate Class Code", type="primary"):
                    new_code = generate_class_code()
                    if db.create_classroom(new_code, "teacher-1", st.session_state.current_question):
                        st.session_state.class_code = new_code
                        st.success(f"Class created successfully! Class code: {new_code}")
                        st.query_params.class_code = new_code
                    else:
                        st.error("Failed to create class, please try again.")
        
        with col2:
            st.subheader("Connected Students")
            if st.session_state.class_code:
                if st.button("Refresh Student List", type="primary", use_container_width=True):
                    st.session_state.connected_students = db.get_classroom_students(st.session_state.class_code)
                    st.success("Student list updated")
                
                student_container = st.empty()
                
                with student_container.container():
                    st.session_state.connected_students = db.get_classroom_students(st.session_state.class_code)
                    st.write(f"Connected students: {len(st.session_state.connected_students)}")
                    if st.session_state.connected_students:
                        st.markdown('<div class="student-list">', unsafe_allow_html=True)
                        for i, student in enumerate(st.session_state.connected_students):
                            st.write(f"{i+1}. {student['id']} (Joined at: {student['joined_at']})")
                        st.markdown('</div>', unsafe_allow_html=True)
                    else:
                        st.info("No students connected")
            else:
                st.info("Connected students will be displayed here after class creation")
    
    # Data Export tab
    with tab3:
        st.header("Data Export")
        
        if st.session_state.class_code:
            st.write(f"Current Class: {st.session_state.class_code}")
            try:
                df = db.get_classroom_data(st.session_state.class_code)
                if not df.empty:
                    st.write("Class data preview:")
                    st.dataframe(df.head())
                    
                    export_format = st.selectbox("Export Format:", ["CSV", "Excel"])
                    if st.button("Export Data", type="primary"):
                        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                        filename = f"classroom_{st.session_state.class_code}_{timestamp}"
                        
                        if export_format == "CSV":
                            file_path = f"{filename}.csv"
                            df.to_csv(file_path, index=False)
                        else:
                            file_path = f"{filename}.xlsx"
                            df.to_excel(file_path, index=False)
                        
                        with open(file_path, "rb") as file:
                            st.download_button(
                                label="Download File",
                                data=file,
                                file_name=os.path.basename(file_path),
                                mime="application/octet-stream"
                            )
                else:
                    st.info("No data available for export")
            except Exception as e:
                st.error(f"Failed to retrieve data: {e}")
        else:
            st.info("Please create or join a class first")
        
        # Add new section for database download
        st.markdown("---")
        st.subheader("Database File Download")
        
        db_col1, db_col2 = st.columns([1, 2])
        
        with db_col1:
            if os.path.exists(db.db_path):
                with open(db.db_path, "rb") as file:
                    st.download_button(
                        label="Download Database File",
                        data=file,
                        file_name="education_tool.db",
                        mime="application/octet-stream",
                        help="Download the complete database file to your local computer"
                    )
            else:
                st.error("Database file does not exist")
        
        with db_col2:
            st.info("""
            **Note**: This function allows you to download the complete database file.
            
            The database contains all classroom, student, and answer data. You can use SQLite tools (such as DB Browser for SQLite) to open this file for advanced data analysis.
            
            **Important**: The downloaded database file only contains data from the current session. A new database is created each time the application restarts.
            """)
        
        # Existing database files viewer
        with st.expander("View System Database Files"):
            db_files = find_database_files()
            if db_files:
                st.write("Database files in the system:")
                for db_file in db_files:
                    st.code(db_file)
                    
                    try:
                        import sqlite3
                        conn = sqlite3.connect(db_file)
                        cursor = conn.cursor()
                        
                        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                        tables = cursor.fetchall()
                        st.write(f"Tables in database: {', '.join([t[0] for t in tables])}")
                        
                        conn.close()
                    except Exception as e:
                        st.error(f"Unable to read database information: {e}")
            else:
                st.info("No database files found")

def main():
    """Main application function"""
    logging.info("Entering main() function")
    
    with st.sidebar:
        st.title("Intelligent Education Tool")
        st.write("AI-powered classroom discussion assistant")
        
        if not st.session_state.user_type:
            st.header("Select User Type")
            
            st.write("### Please select your role:")
            
            if st.button("👨‍🏫 Teacher", key="teacher_btn", use_container_width=True):
                st.session_state.user_type = "teacher"
                st.query_params.user_type = "teacher"
            
            st.write("") 
            
            if st.button("👨‍🎓 Student", key="student_btn", use_container_width=True):
                st.session_state.user_type = "student"
                st.query_params.user_type = "student"
                
            st.write("---")
            st.info("If you don't see the buttons, please refresh the page or clear your browser cache")
        
        if st.session_state.user_type:
            # Only show when student ID exists
            if st.session_state.student_id:
                st.write(f"Student ID: {st.session_state.student_id}")
            
            if st.button("Switch User Type"):
                st.session_state.user_type = None
                st.session_state.class_code = None
                st.session_state.student_id = None
                st.session_state.current_question = None
                st.session_state.answer_submitted = False
                st.session_state.evaluation_result = None
                st.query_params.clear()
        
        st.markdown("---")
        st.write("📚 Intelligent Education Tool v1.0")
        st.write("⚙️ Powered by Python + Streamlit + AI")
        st.write("© 2025 Education Tech")
    
    logging.info("Checking if AI API is available...")
    api_available = AIService.is_api_available()
    logging.info(f"AI API availability check result: {api_available}")
    if not api_available:
        st.error("⚠️ AI service unavailable. Please check:\n"
                 "1. Ensure your network connection is working.\n"
                 "2. Check if your API key is correct.\n"
                 "3. Ensure the AI service endpoint is accessible.")
    else:
        st.success("✅ AI service connected successfully")
        if st.session_state.user_type == "teacher":
            teacher_view()
        elif st.session_state.user_type == "student":
            student_view()
        else:
            st.title("Welcome to Intelligent Education Tool")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Teacher Features")
                st.write("✅ Question creation and management")
                st.write("✅ Real-time classroom monitoring")
                st.write("✅ Student response data analysis")
                st.write("✅ AI-assisted teaching assessment")
            
            with col2:
                st.subheader("Student Features")
                st.write("✅ Simple classroom connection")
                st.write("✅ Markdown-formatted answers")
                st.write("✅ Real-time AI feedback")
                st.write("✅ Personalized learning suggestions")
        
        st.info("Please select your user type in the sidebar")

if __name__ == "__main__":
    main()