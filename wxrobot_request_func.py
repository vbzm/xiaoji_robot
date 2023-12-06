import requests
import json
from config_class import Config

import re
import time
from datetime import datetime
from lxml import etree

config = Config()

def get_important_news():
    week = {0: "周一", 1: "周二", 2: "周三", 3: "周四", 4: "周五", 5: "周六", 6: "周日"}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/110.0"}

    url = "https://www.cls.cn/api/sw?app=CailianpressWeb&os=web&sv=7.7.5"
    data = {"type": "telegram", "keyword": "你需要知道的隔夜全球要闻", "page": 0,
            "rn": 1, "os": "web", "sv": "7.7.5", "app": "CailianpressWeb"}
    try:
        rsp = requests.post(url=url, headers=headers, data=data)
        # print(rsp.text)
        data = json.loads(rsp.text)["data"]["telegram"]["data"][0]
        news = data["descr"]
        timestamp = data["time"]
        ts = time.localtime(timestamp)
        weekday_news = datetime(*ts[:6]).weekday()
    except Exception as e:
        print(str(e))
        return ""

    weekday_now = datetime.now().weekday()
    if weekday_news != weekday_now:
        return ""  # 旧闻，观察发现周二～周六早晨6点半左右发布

    fmt_time = time.strftime("%Y年%m月%d日", ts)

    news = re.sub(r"(\d{1,2}、)", r"\n\1", news)
    fmt_news = "".join(etree.HTML(news).xpath(" // text()"))
    fmt_news = re.sub(r"周[一|二|三|四|五|六|日]你需要知道的", r"", fmt_news)

    return f"{fmt_time} {week[weekday_news]}\n{fmt_news}"


headers = {
    'accept': 'application/json',
    'Content-Type': 'application/json',
}


# 反算name
def put_wxid_to_name(aters, receiver):
    # 以wxid反推昵称
    response = requests.get(f'http://localhost:9999/chatroom-member/?roomid={receiver}')
    wxid_dict = response.json()['data']['members']
    at_name = wxid_dict[aters]
    print('反查成功：' + at_name)
    config.reload()
    if find_offending_word(at_name):
        send_msg(f'群聊:{receiver}\nID违规:{at_name}\nwxid:{aters}', config.admin_room_id, '')
        return '你的名称中存在违规词汇，无法被我@'
    return at_name

# 反算name
def put_name_to_wxid(aters, receiver):
    # 以wxid反推昵称
    response = requests.get(f'http://localhost:9999/chatroom-member/?roomid={receiver}')
    wxid_dict = response.json()['data']['members']

    for key, value in wxid_dict.items():
        if value == aters:
            return key


# 踢人
def delet_room_user(roomid, user):
    # 踢出群聊
    json_data = {
        'roomid': roomid,
        'wxids': user,
    }
    response = requests.delete('http://localhost:9999/chatroom-member', headers=headers, json=json_data)
    print("踢：", response.text)

# 发送消息
def send_msg(msg, receiver, aters):
    # 判断是否为权限内的群聊或者好友
    # if receiver not in config.room_list and receiver not in config.user_list:
    #     return print(f"{receiver}无权限执行发送任务")

    if aters != '':
        # 以wxid反推昵称
        at_name = put_wxid_to_name(aters, receiver)
        print(at_name)
        msg = f'@{at_name}\n\n{msg}'
    json_data = {
        'msg': msg,
        'receiver': receiver,
        'aters': aters,
    }
    print(f"正在发送信息给：{receiver}，内容：{msg}")
    # 判断是否为权限内的群聊或者好友
    response = requests.post('http://127.0.0.1:9999/text', headers=headers, json=json_data)
    if response.status_code == 200:
        print("发送文字成功")
    else:
        print("发送文字失败")

def send_img(path, receiver):
    # 判断是否为权限内的群聊或者好友
    if receiver not in config.room_list and receiver not in config.user_list:
        return print(f"{receiver}无权限执行发送任务")

    json_data = {
        'path': path,
        'receiver': receiver,
    }
    response = requests.post('http://117.72.37.154:9999/image', headers=headers, json=json_data)
    if response.status_code == 200:
        print("发送图片成功")
    else:
        print("发送图片失败")


# 违规记忆
def offending(roomid, sender, keyword_str):
    # 获取data.json中的数据
    with open('data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    # 判断是否存在sender
    if sender in data['offending_user']:
        # 存在则+1
        data['offending_user'][sender] = data['offending_user'][sender] + 1
    else:
        # 不存在则创建
        data['offending_user'][sender] = 1
    # 判断是否超过三次
    if data['offending_user'][sender] >= 3:
        # 超过三次则踢出群聊
        send_msg(f'{put_wxid_to_name(sender, roomid)}\n{keyword_str}', roomid, '')
        delet_room_user(roomid, sender)
        # 删除data.json中的数据
        del data['offending_user'][sender]
    else:
        send_msg(f'您因不正当言论已违规{data["offending_user"][sender]}次，如有疑问请联系管理员！', roomid, sender)
    # 保存data.json中的数据
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)

# 违禁词寻找函数
def find_offending_word(msg):
    keyword_suspected_list = []
    up_find_list = []
    config.reload()
    for one_content in msg:
        # 如果任意一个字在敏感词列表中，则取疑似的列表，进行二次判断
        for one_keyword in config.keyword_list:
            # 将msg转为小写
            one_content = one_content.lower()
            if one_content in one_keyword and one_keyword not in keyword_suspected_list:
                keyword_suspected_list.append(one_keyword)
    # 如果疑似列表中有字，则进行二次判断
    if len(keyword_suspected_list) > 0:
        for one_suspected in keyword_suspected_list:
            keyword_nums = 0
            up_find_list.clear()
            # 如果消息中的字在疑似列表中，则计数加一 并且将此字加入已判断列表
            for one_content in msg:
                one_content = one_content.lower()
                if one_content in one_suspected and one_content not in up_find_list:
                    keyword_nums += 1
                    up_find_list.append(one_content)
                # 如果疑似列表中的字数大于等于敏感词字数，则判断为敏感词
                if keyword_nums >= len(one_suspected):
                    print(f'违规词：{one_suspected}\n消息中存在的字数：{keyword_nums}\n违规词长度{len(one_suspected)}')
                    return True
    else:
        return False


def save_keyword_str(key_word):
    # 追加保存
    with open('keyword.txt', 'a', encoding='utf-8') as f:
        f.write(key_word + '\n\n')

# 获取天气
def get_weather(city, appid, appsecret):
    try:
        url = 'http://v1.yiketianqi.com/free/day'
        # get请求参数
        params = {
            'appid': appid,
            'appsecret': appsecret,
            'city': city,
            'unescape': 1,
        }
        response = requests.get(url, params=params)
        print(response.json())
        """
        {
        "nums":226, //今日实时请求次数
        "cityid":"101120101", //城市ID
        "city":"济南",
        "date":"2022-05-05",
        "week":"星期四",
        "update_time":"22:38", //更新时间
        "wea":"多云", //天气情况
        "wea_img":"yun", //天气标识
        "tem":"25", //实况温度
        "tem_day":"30", //白天温度(高温)
        "tem_night":"23", //夜间温度(低温)
        "win":"南风", //风向
        "win_speed":"3级", //风力
        "win_meter":"19km\/h", //风速
        "air":"53", //空气质量
        "pressure":"987", //气压
        "humidity":"27%" //湿度
        }
        """
        if response.status_code == 200:
            return f'{response.json()["city"]}今日天气：{response.json()["wea"]}\n' \
                      f'温度：{response.json()["tem"]}℃\n' \
                        f'白天温度：{response.json()["tem_day"]}℃\n' \
                        f'夜间温度：{response.json()["tem_night"]}℃\n' \
                        f'风向：{response.json()["win"]}\n' \
                        f'风力：{response.json()["win_speed"]}\n' \
                        f'空气质量：{response.json()["air"]}\n' \
                        f'湿度：{response.json()["humidity"]}\n' \
                        f'天气信息更新时间：{response.json()["update_time"]}\n\n'\
                        f'不知名小查今日已帮助查询次数：{response.json()["nums"]}'
        else:
            return "获取天气失败"
    except Exception as e:
        return '获取天气信息失败喽，可能是city找不到，不要带市和区, 支持市区县, 不支持乡镇级别\n\n只需要@我并说出地区+天气，例如济南天气就好啦'

def get_baidu_result(keyword):
    url = 'https://zhidao.baidu.com/search'

    params = {
        'lm': 0,
        'rn': 10,
        'pn': 0,
        'fr': 'search',
        'dyTabStr': 'null',
        'word': keyword
    }

    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Accept-Encoding': 'gzip, deflate', 'Accept-Language': 'zh-CN,zh;q=0.9', 'Cache-Control': 'max-age=0',
        'Connection': 'keep-alive',
        'Host': 'zhidao.baidu.com', 'Referer': 'https://zhidao.baidu.com/',
        'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="102"', 'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"', 'Sec-Fetch-Dest': 'document', 'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin', 'Sec-Fetch-User': '?1', 'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36'}

    response = requests.get(url, params=params, headers=headers)
    response.encoding = 'utf-8'
    # 使用正则匹配list-inner至<a href，然后得到<a href中的内容
    zhidao_url = re.findall(r'list-inner.*?<a href="(.*?)"', response.text, re.S)
    # 使用正则匹配list-inner至<i class="i-answer-text">，然后得到<i class="i-answer-text">中的内容
    str_data = re.findall(r'list-inner.*?<i class="i-answer-text">(.*?)</dd>', response.text, re.S)
    # 去除str_data中的html标签和&middot;等特殊字符
    str_data = re.sub(r'<.*?>', '', str_data[0])
    str_data = re.sub(r'&.*?;', '', str_data)
    #print(response.text)

    #print(zhidao_url, str_data)
    return f'{str_data}\n\n' \
           f'详情转至链接：{zhidao_url[0]}\n'\
           f'内容来源：百度知道'

def get_my_wxid():
    # 获取自己的微信id
    url = 'http://localhost:9999/wxid'
    response = requests.get(url, headers=headers).json()
    print('自己的微信id获取成功：', response['data']['wxid'])
    return response['data']['wxid']

