from requests import JSONDecodeError
import requests
import json

class Chatbot:
    def __init__(self, config, max_history_length=5, max_total_length=1000):
        self.url = config['url']
        self.key = config['key']
        self.max_history_length = max_history_length
        self.max_total_length = max_total_length

    def ask_question(self, user_id, question):
        user_history = self.get_user_history(user_id)
        if not user_history or user_history == '':
            # 新用户，预设关键词
            user_history = ['Q: 从现在开始你叫做不知名小机，你应尽可能的回答我提出的问题！\nA: 好的，从现在开始你可以称呼我为"不知名小机"。有什么我可以帮助你的吗？']
        full_question = '\n'.join(user_history + [question])
        data = {
            'key': self.key,
            'question': full_question,
        }
        try:
            response = requests.post(self.url, data=data)
            if response.json()['msg'] != 'ok':
                return f"哦豁，玩坏啦，报错啦，出错原因：{response.json()['msg']},[委屈][委屈]"
            answer = response.json()['data']
            if answer[:2] == 'A:':
                answer = answer.split('A: ')[1]
            user_history.append(f'Q: {question}\nA: {answer}')
            self.update_user_history(user_id, user_history)
            self.trim_history(user_id)
            return answer
        except JSONDecodeError as e:
            return f"哦豁，玩坏啦，报错啦，出错原因：{str(e)},[委屈][委屈]"

    def trim_history(self, user_id):
        user_history = self.get_user_history(user_id)
        while len(user_history) > self.max_history_length or self.get_total_length(user_history) > self.max_total_length:
            user_history.pop(0)
        self.update_user_history(user_id, user_history)

    def get_user_history(self, user_id):
        user_msg_data = self.load_user_msg_data()
        return user_msg_data.get(user_id, [])

    def update_user_history(self, user_id, history):
        user_msg_data = self.load_user_msg_data()
        user_msg_data[user_id] = history
        self.save_user_msg_data(user_msg_data)

    def load_user_msg_data(self):
        try:
            with open('gpt_user_msg_data.json', 'r') as file:
                user_msg_data = json.load(file)
        except FileNotFoundError:
            user_msg_data = {}
        return user_msg_data

    def save_user_msg_data(self, user_msg_data):
        with open('gpt_user_msg_data.json', 'w') as file:
            json.dump(user_msg_data, file)

    def get_total_length(self, history):
        return sum(len(item) for item in history)
