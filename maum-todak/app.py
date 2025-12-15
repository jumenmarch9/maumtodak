import os
import os
from flask import Flask, render_template, request, session
import requests # Ollama와 통신하기 위해 requests 라이브러리를 사용합니다.
import json     # JSON 데이터를 다루기 위해 사용합니다.
from dotenv import load_dotenv

load_dotenv()

# Flask 애플리케이션 생성
app = Flask(__name__)
# session을 사용하기 위해 시크릿 키 설정 (실제 배포 시에는 더 복잡한 값으로 변경해야 함)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'maum-todak-secret-key')

# 메인 페이지 라우트: '/' 경로로 접속하면 index.html 파일을 보여줌
@app.route('/')
def index():
    """메인 페이지를 렌더링합니다."""
    return render_template('index.html')

# 대화 라우트: '/chat' 경로로 POST 요청을 처리
@app.route('/generate', methods=['POST'])
def generate():
    """사용자 메시지를 받아 대화 기록을 관리하고 모델의 응답을 반환합니다."""
    user_message = request.form.get('message')
    mbti = request.form.get('mbti')
    zodiac = request.form.get('zodiac')

    # 디버깅: 수신된 메시지 내용 확인
    print(f"--- Received message: '{user_message}' ---")

    # 사용자가 빈 메시지를 보냈는지 확인
    if not user_message or not user_message.strip():
        return "" # 빈 응답을 반환하여 아무 일도 일어나지 않게 함

    # 세션에서 대화 기록 가져오기, 없으면 초기화
    if 'messages' not in session:
        session['messages'] = []

    # 사용자의 새 메시지를 대화 기록에 추가
    session['messages'].append({'role': 'user', 'content': user_message})
    session.modified = True

    # Ollama에 전달할 시스템 프롬프트와 대화 기록을 구성합니다.
    system_prompt = """너는 사용자의 감정에 깊이 공감해주는 다정한 친구 '마음토닥'이야.
임무: 사용자의 말을 잘 듣고, 친구처럼 자연스럽게 대화하며 위로해줘.
규칙:
- 사용자의 말을 무시하거나, "어떻게 도와드릴까요?" 같은 기계적인 질문을 절대 하지 마.
- 따뜻하고 친근한 말투(~했구나, ~같아)를 사용해.
- 해결책을 제시하거나 조언하지 마."""

    # 사용자가 MBTI 또는 별자리 정보를 선택했다면, 시스템 프롬프트에 추가합니다.
    user_info = []
    if mbti and mbti != "모름":
        user_info.append(f"사용자의 MBTI는 {mbti}이야.")
    if zodiac and zodiac != "모름":
        user_info.append(f"사용자의 별자리는 {zodiac}이야.")

    if user_info:
        system_prompt += "\n\n추가 정보: " + " ".join(user_info) + " 이 정보를 대화에 자연스럽게 녹여내면 좋지만, 너무 억지로 언급하지는 마."

    # Ollama는 'assistant' 역할을 사용합니다.
    ollama_history = [{'role': 'system', 'content': system_prompt}]
    # 대화가 길어지면 로컬 모델이 느려질 수 있으므로 최근 10개 메시지만 유지합니다.
    ollama_history.extend(session['messages'][-10:])

    try:
        # Ollama API 서버에 요청을 보냅니다.
        response = requests.post(
            'http://localhost:11434/api/chat', # Ollama 채팅 API 엔드포인트
            json={
                'model': 'gemma3:4b', # 안정적인 모델로 변경
                'messages': ollama_history,
                'stream': False # 스트리밍을 사용하지 않음 (한 번에 전체 응답 받기)
            }
        )
        response.raise_for_status() # 오류가 발생하면 예외를 발생시킴

        # 응답에서 메시지 내용 추출
        message = response.json()['message']['content']

        # 모델의 응답도 대화 기록에 추가
        session['messages'].append({'role': 'assistant', 'content': message})
        session.modified = True

        return message
    
    except Exception as e:
        print(f"An error occurred: {e}")
        if session['messages'] and session['messages'][-1]['role'] == 'user':
            session['messages'].pop()
            session.modified = True
        return "메시지를 생성하는 데 실패했어요. Ollama 서버가 실행 중인지 확인해주세요."

# 서버 실행
if __name__ == '__main__':
    # debug=True 모드는 개발 중에 코드가 변경될 때마다 서버를 자동으로 재시작해 줍니다.
    app.run(debug=True)
