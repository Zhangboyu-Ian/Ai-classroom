import json
import time
import requests
from typing import Dict, List, Any, Optional
import openai  # Import the full module for exceptions
from openai import OpenAI  # Import the OpenAI class for client
import os
import traceback
from database import get_api_key  # Import from database.py
import inspect

class AIService:
    @staticmethod
    def is_api_available() -> bool:
        """检查DeepSeek API是否可用"""
        try:
            print("==== Debug: Starting API availability check with DEEPSEEK ====")
            
            # 获取DeepSeek API密钥
            api_key = get_api_key("DEEPSEEK", "DEEPSEEK_API_KEY")
            print(f"==== Debug: Got DEEPSEEK API key successfully: {api_key[:5]}... ====")
            
            client = OpenAI(
                api_key=api_key, 
                base_url="https://api.deepseek.com/v1"
            )
            
            # 测试API连接
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5
            )
            print("==== Debug: DeepSeek API test successful ====")
            return True
        except Exception as e:
            print(f"==== Debug: DeepSeek API not available: {str(e)} ====")
            traceback.print_exc()
            return False
    
    @staticmethod
    def generate_quiz(topic: str, difficulty: str, num_questions: int = 5) -> List[Dict[str, Any]]:
        """使用DeepSeek API生成测验问题"""
        try:
            # 只使用DeepSeek API
            api_key = get_api_key("DEEPSEEK", "DEEPSEEK_API_KEY")
            
            client = OpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com/v1"
            )
            
            # 构建提示
            prompt = f"""
            Generate {num_questions} multiple-choice questions about {topic} at {difficulty} level.
            Each question should have 4 options with only one correct answer.
            Format the response as a JSON array with the following structure for each question:
            {{
                "question": "Question text",
                "options": ["Option A", "Option B", "Option C", "Option D"],
                "answer": "The correct option letter (A, B, C, or D)",
                "explanation": "Explanation of why this answer is correct"
            }}
            """
            
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=2000
            )
            
            # 提取JSON内容
            content = response.choices[0].message.content
            # 查找JSON部分
            json_str = AIService._extract_json(content)
            questions = json.loads(json_str)
            return questions
            
        except Exception as e:
            print(f"AI问题生成失败: {str(e)}")
            traceback.print_exc()
            return []
    
    @staticmethod
    def generate_question(params: Dict[str, Any]) -> str:
        """使用DeepSeek API生成单个讨论问题
        
        Args:
            params: 包含以下键的字典：
                - subject: 主题/学科
                - difficulty: 难度级别
                - keywords: 关键词列表
                - regenerate: 是否是重新生成请求
                - previous_question: 之前生成的问题
        
        Returns:
            生成的讨论问题
        """
        try:
            # 获取DeepSeek API密钥
            api_key = get_api_key("DEEPSEEK", "DEEPSEEK_API_KEY")
            
            client = OpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com/v1"
            )
            
            # 提取参数
            subject = params.get("subject", "general")
            difficulty = params.get("difficulty", "medium")
            keywords = params.get("keywords", [])
            
            # 构建关键词字符串
            keywords_str = ", ".join(keywords) if keywords else "no specific keywords"
            
            # 构建提示
            prompt = f"""
            Generate a thought-provoking discussion question about {subject} at {difficulty} difficulty level.
            The question should incorporate these keywords or concepts if possible: {keywords_str}.
            The question should be clear, open-ended, and designed to encourage critical thinking and classroom discussion.
            Just respond with the question text only, without any additional explanations or formatting.
            """
            
            # 如果是重新生成请求，修改提示以确保新问题与旧问题不同
            if params.get("regenerate"):
                previous_question = params.get("previous_question", "")
                attempt = params.get("attempt", 1)
                if attempt > 1:
                    prompt = f"""
                    Generate a completely NEW and DIFFERENT thought-provoking discussion question about {subject} at {difficulty} difficulty level.
                    The question should incorporate these keywords or concepts if possible: {keywords_str}.
                    
                    IMPORTANT: Your previous generated question was:
                    "{previous_question}"
                    
                    Please ensure this new question is COMPLETELY DIFFERENT from your previous one.
                    Use a different approach, perspective, or angle on the subject.
                    The question should still be clear, open-ended, and designed to encourage critical thinking.
                    
                    Just respond with the question text only, without any additional explanations or formatting.
                    """
                else:
                    prompt = f"""
                    Generate a NEW thought-provoking discussion question about {subject} at {difficulty} difficulty level.
                    The question should incorporate these keywords or concepts if possible: {keywords_str}.
                    
                    IMPORTANT: Your previous generated question was:
                    "{previous_question}"
                    
                    Please ensure this new question is different from your previous one.
                    The question should be clear, open-ended, and designed to encourage critical thinking and classroom discussion.
                    
                    Just respond with the question text only, without any additional explanations or formatting.
                    """
            
            # 增加温度参数，以生成更多样化的问题
            temperature = 0.9 if params.get("regenerate") else 0.7
            
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=500
            )
            
            # 提取生成的问题
            question = response.choices[0].message.content.strip()
            return question
            
        except Exception as e:
            print(f"生成问题失败: {str(e)}")
            traceback.print_exc()
            raise
    
    @staticmethod
    def evaluate_answer(question: str, answer: str) -> Dict[str, Any]:
        """处理学生答案评估并确保返回干净的数据"""
        try:
            # 获取API密钥
            api_key = get_api_key("DEEPSEEK", "DEEPSEEK_API_KEY")
            
            client = OpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com/v1"
            )
            
            # 使用简化的提示，明确要求只返回英文的简短评价
            prompt = f"""
            Evaluate this student answer to the question:
            
            Question: {question}
            
            Student's answer: {answer}
            
            Evaluate the answer based on its relevance, accuracy, depth, and structure.
            
            Return your evaluation in this JSON format (nothing else):
            {{
                "score": 0.X,  // a number between 0 and 1
                "feedback": "Brief overall assessment in English",
                "suggestions": [
                    "First improvement suggestion in English",
                    "Second improvement suggestion in English",
                    "Third improvement suggestion in English"
                ]
            }}
            
            Keep your suggestions straightforward, action-oriented, and in proper English only.
            NEVER include any comments, instructions, or non-English text in your suggestions.
            """
            
            print("Sending evaluation request to AI...")
            
            # 设置低温度以减少意外输出
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=800
            )
            
            # 处理响应
            evaluation_text = response.choices[0].message.content.strip()
            print(f"Raw AI response: {evaluation_text[:100]}...")
            
            # 尝试提取JSON
            try:
                # 如果包含```json标记，提取里面的内容
                if "```json" in evaluation_text:
                    start = evaluation_text.find("```json") + len("```json")
                    end = evaluation_text.rfind("```")
                    if start != -1 and end != -1:
                        evaluation_text = evaluation_text[start:end].strip()
                
                # 如果包含一般JSON标记，提取中间内容
                elif "```" in evaluation_text:
                    start = evaluation_text.find("```") + len("```")
                    end = evaluation_text.rfind("```")
                    if start != -1 and end != -1:
                        evaluation_text = evaluation_text[start:end].strip()
                
                # 尝试解析JSON
                evaluation = json.loads(evaluation_text)
            except Exception as e:
                print(f"JSON parsing error: {e}")
                # 回退到备选方案：尝试从文本中找到最可能的JSON块
                try:
                    start = evaluation_text.find("{")
                    end = evaluation_text.rfind("}") + 1
                    if start != -1 and end > start:
                        json_chunk = evaluation_text[start:end]
                        evaluation = json.loads(json_chunk)
                    else:
                        raise Exception("Could not identify JSON in response")
                except Exception as e2:
                    print(f"Secondary JSON parsing error: {e2}")
                    # 提供默认评估
                    return {
                        "score": 0.5,
                        "feedback": "Your answer was evaluated, but we couldn't generate detailed feedback.",
                        "suggestions": [
                            "Address the key points in the question",
                            "Provide specific examples to support your answer",
                            "Structure your response with clear organization"
                        ]
                    }
            
            # 确保评估包含所有必要字段并且格式正确
            # 分数处理
            if 'score' not in evaluation or not isinstance(evaluation['score'], (int, float)):
                evaluation['score'] = 0.5
            else:
                # 确保分数在0-1之间
                evaluation['score'] = max(0.0, min(1.0, float(evaluation['score'])))
            
            # 反馈处理
            if 'feedback' not in evaluation or not isinstance(evaluation['feedback'], str):
                evaluation['feedback'] = "The answer could be improved for clarity and relevance."
            
            # 建议处理 - 这是关键部分
            if 'suggestions' not in evaluation or not isinstance(evaluation['suggestions'], list):
                evaluation['suggestions'] = [
                    "Focus on addressing the main points of the question",
                    "Add more specific details and examples",
                    "Improve the overall structure of your answer"
                ]
            else:
                # 过滤和清理建议
                clean_suggestions = []
                for suggestion in evaluation['suggestions']:
                    # 跳过非字符串
                    if not isinstance(suggestion, str):
                        continue
                        
                    # 清理建议文本
                    text = suggestion.strip()
                    
                    # 跳过空字符串
                    if not text:
                        continue
                    
                    # 跳过含有可疑内容的字符串
                    if any(char in text for char in ['，', '。', '学', '生', '《', '》', '请', '你']):
                        continue
                    if any(word in text.lower() for word in ['script', 'refresh', 'student', 'click']):
                        continue
                        
                    clean_suggestions.append(text)
                
                # 如果过滤后没有建议，使用默认建议
                if not clean_suggestions:
                    clean_suggestions = [
                        "Focus on addressing the main points of the question",
                        "Add more specific details and examples",
                        "Improve the overall structure of your answer"
                    ]
                    
                # 限制为最多3个建议
                evaluation['suggestions'] = clean_suggestions[:3]
                
                # 如果少于3个建议，添加默认建议
                default_suggestions = [
                    "Focus on addressing the main points of the question",
                    "Add more specific details and examples",
                    "Improve the overall structure of your answer"
                ]
                
                while len(evaluation['suggestions']) < 3:
                    for suggestion in default_suggestions:
                        if suggestion not in evaluation['suggestions']:
                            evaluation['suggestions'].append(suggestion)
                            break
                    if len(evaluation['suggestions']) >= 3:
                        break
            
            # 最终检查 - 打印处理后的评估
            print(f"Processed suggestions: {evaluation['suggestions']}")
            return evaluation
            
        except Exception as e:
            print(f"Overall evaluation error: {str(e)}")
            traceback.print_exc()
            # 返回简单的默认评估
            return {
                "score": 0.5,
                "feedback": "We encountered a problem evaluating your answer.",
                "suggestions": [
                    "Ensure your answer addresses the question directly",
                    "Include specific examples and details",
                    "Check your answer's organization and clarity"
                ]
            }
    
    @staticmethod
    def get_simple_suggestions(question: str, answer: str) -> list:
        """
        Get only simple improvement suggestions for a student answer.
        Returns a list of 3 straightforward suggestions in English.
        """
        try:
            # Get API key
            api_key = get_api_key("DEEPSEEK", "DEEPSEEK_API_KEY")
            
            # Create client
            client = OpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com/v1"
            )
            
            # Very simple prompt that asks for exactly 3 suggestions in English only
            prompt = f"""
            Read this student's answer to the following question:
            
            QUESTION: {question}
            
            ANSWER: {answer}
            
            Provide EXACTLY THREE clear suggestions to improve this answer.
            Format your response as a simple numbered list with 3 items.
            Each suggestion should be a complete English sentence of 10-20 words.
            
            DO NOT include any scores, introduction, or explanations.
            DO NOT use any special formatting, HTML, or non-English characters.
            DO NOT mention the student directly or refer to clicking buttons.
            
            Just return the three suggestions, one per line, starting with "1. ", "2. ", "3. "
            """
            
            # Use low temperature for consistent output
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=300
            )
            
            # Get the raw text response
            raw_text = response.choices[0].message.content.strip()
            
            # Parse the response into separate suggestions
            suggestions = []
            lines = raw_text.split('\n')
            
            for line in lines:
                line = line.strip()
                
                # Skip empty lines
                if not line:
                    continue
                    
                # Try to match numbered items (1. 2. 3.)
                if len(line) > 2 and line[0].isdigit() and line[1] in ['.', ')', ' ']:
                    # Remove the number prefix and clean up
                    suggestion = line[2:].strip()
                    suggestions.append(suggestion)
                elif line:
                    # If not numbered, just add the line as is
                    suggestions.append(line)
            
            # Only keep up to 3 suggestions
            suggestions = suggestions[:3]
            
            # If we don't have exactly 3 suggestions, add some default ones
            default_suggestions = [
                "Focus on addressing the main question more directly.",
                "Include specific examples to support your key points.",
                "Structure your answer with a clear introduction and conclusion."
            ]
            
            # Fill in missing suggestions with defaults
            while len(suggestions) < 3:
                for default in default_suggestions:
                    if default not in suggestions:
                        suggestions.append(default)
                        break
                
                # Break if we have 3 suggestions
                if len(suggestions) >= 3:
                    break
            
            return suggestions[:3]  # Return exactly 3 suggestions

        except Exception as e:
            print(f"Error getting suggestions: {str(e)}")
            # Return default suggestions on error
            return [
                "Focus on addressing the main question more directly.",
                "Include specific examples to support your key points.",
                "Structure your answer with a clear introduction and conclusion."
            ]
    
    @staticmethod
    def _extract_json(text: str) -> str:
        """从文本中提取JSON部分"""
        start = text.find("[")
        end = text.rfind("]") + 1
        if start != -1 and end != 0:
            return text[start:end]
        return "[]"