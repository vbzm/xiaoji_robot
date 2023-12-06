import random
import sys

import uvicorn
import xmltodict
from fastapi import Body, FastAPI
from pydantic import BaseModel
from wxrobot_request_func import *
from TencentTranslate import TencentTranslate
from config_class import Config
from gpt import Chatbot

msg_dict = {}
# 语言列表的dict，键为语言代码，值为语言的中文名称 例如：'zh': '中文'，， zh（简体中文）：en（英语）、ja（日语）、ko（韩语）、fr（法语）、es（西班牙语）、it（意大利语）、de（德语）、tr（土耳其语）、ru（俄语）、pt（葡萄牙语）、vi（越南语）、id（印尼语）、th（泰语）、ms（马来语）
language_dict = {'zh': '中文', 'en': '英语', 'ja': '日语', 'ko': '韩语', 'fr': '法语', 'es': '西班牙语',
                 'it': '意大利语', 'de': '德语', 'tr': '土耳其语', 'ru': '俄语', 'pt': '葡萄牙语', 'vi': '越南语',
                 'id': '印尼语', 'th': '泰语', 'ms': '马来语'}

"""
常量文本配置，动态变量请放到config.yaml中
"""
# 违禁词提醒的文本
keyword_str = '抱歉，你发表了不当言论，现将你移出群聊️️️\n欢迎再次进来。\n请大家文明交流，谢谢！[炸弹]'
# 菜单
menu_str = '不知名小机功能菜单：\n\n' \
           '普通功能：\n' \
           '1、发那科机器人报警代码查询，发送报警代码到群内即可\n' \
           '2、违规词捕获，自动警告，超过三次将踢出群聊\n' \
           '3、入群自动欢迎\n' \
           '4、@小机并说摸鱼报，推送摸鱼报\n' \
           '5、@小机并说新闻，推送新闻\n' \
           '6、@小机并说地区+天气，例如张家港天气，即可查询天气信息\n' \
           '7、@小机并说搜:+内容，例如搜:谁是最帅的男人，即可获得结果\n' \
           '8、@小机并说翻译+内容，例如翻译你好，即可获得结果\n' \
           '9、高级翻译，@小机说翻译+内容+为+目标语言，即可翻译多语言，具体请@小机说"支持翻译语言"\n' \
           '10、如果管理员开启了gpt模式，@我我就可以与你ai对话了哦\n' \
           '\n管理员功能：\n' \
           '1、管理快速踢人，只需要发送踢并@\n' \
           '2、早报推送，关心天下事\n' \
           '3、gpt-3聊天，@机器人并发送ai:(内容)即可\n' \
           '4、@小机并说跟屁虫模式+开/关，触发跟屁虫模式，开启后，机器人会复读所有人的话\n' \
           '5、@小机并说跟屁虫模式+开/关+@某人，触发跟屁虫模式，开启后，机器人会复读你@的人的话，单次最多指定一人。\n'
weather_appid = 1
weather_appsecret = ''


class Msg(BaseModel):
    id: int
    ts: int
    sign: str
    type: int
    xml: str
    sender: str
    roomid: str
    content: str
    thumb: str
    extra: str
    is_at: bool
    is_self: bool
    is_group: bool


def msg_cb(msg: Msg = Body(description="微信消息")):
    try:
        """示例回调方法，简单打印消息"""
        global run_flag
        global gpc_mode
        global gpc_id
        global gpc_id_list

        print(
            f"收到消息：\ntype={msg.type}\nsender={msg.sender}\nroomid={msg.roomid}\ncontent={msg.content}\nis_at={msg.is_at}\n")
        if msg.sender in config.admin_id and msg.content == '启用' and not msg.is_group:
            send_msg(f'启用成功', msg.sender, '')
            run_flag = True
        elif msg.sender in config.admin_id and msg.content == '停用' and not msg.is_group:
            send_msg(f'停用成功', msg.sender, '')
            run_flag = False
        if not run_flag:
            print("未启用")
            return {"status": 0, "message": "成功"}

        if msg.is_group and msg.roomid not in config.room_list:
            send_msg(f"收到不在允许列表中的群聊消息群聊id为:", config.admin_room_id, '')
            send_msg(msg.roomid, config.admin_room_id, '')
            return {"status": 0, "message": "成功"}
        if not msg.is_group and msg.sender not in config.user_list and "wxid_" in msg.sender:
            send_msg(f"收到不在允许列表中的用户消息，用户id为", config.admin_room_id, '')
            send_msg(msg.sender, config.admin_room_id, '')
            return {"status": 0, "message": "成功"}

        # 文字消息
        if msg.type == 1:

            if gpc_mode:
                if gpc_id_list:
                    # 跟单人
                    if msg.sender in gpc_id_list:
                        send_msg(msg.content, msg.roomid, '')
                else:
                    # 跟屁虫模式
                    send_msg(msg.content, msg.roomid, '')

            msg_dict[str(msg.id)] = {
                'msg': msg.content,
                'time': msg.ts,
            }
            # 删除超过2分钟的消息
            for key in list(msg_dict.keys()):
                if msg.ts - msg_dict[key]['time'] > 130:
                    del msg_dict[key]
                    print(f"删除了一条消息，id为{key}")
            print(f"增加了一条消息，id为{msg.id}， 内容为{msg.content}")
            # 群聊消息
            if msg.is_group and msg.roomid in config.room_list:
                # 被@时回复
                if msg.is_at:
                    if "在吗" in msg.content:
                        print("在吗")
                        send_msg("在的", msg.roomid, msg.sender)
                    elif '新闻' in msg.content:
                        # 新闻推送
                        news_data = get_important_news()
                        if news_data != '':
                            send_msg(news_data, msg.roomid, '')
                        else:
                            send_msg('今天没有新闻', msg.roomid, msg.sender)
                    elif '摸鱼报' in msg.content:
                        # 摸鱼报
                        moyu_img_url = requests.get('https://moyu.qqsuu.cn/?type=json').json()['data']
                        # 获取今天的日期，与data中(/20231203.png)比较，如果不是新的就不发
                        today = time.strftime("%Y%m%d", time.localtime())
                        if today in moyu_img_url:
                            send_img(moyu_img_url, msg.roomid)
                            send_msg('摸鱼报已推送，摸的开心摸的愉快', msg.roomid, msg.sender)
                        else:
                            send_msg('摸鱼报没更新', msg.roomid, '')
                    elif '天气' in msg.content:
                        # 匹配\u2005后，天气前的字符
                        city = re.findall(r'\u2005(.*?)天气', msg.content)
                        if city:
                            print(city)
                            if city[0] != '':
                                weather = get_weather(city[0], weather_appid, weather_appsecret)
                                print(weather)
                                send_msg(weather, msg.roomid, msg.sender)
                            else:
                                send_msg('你都不说查哪我查个毛啊？[鄙视]', msg.roomid, msg.sender)
                    elif 'ai:' in msg.content or 'ai：' in msg.content or 'AI:' in msg.content or 'AI：' in msg.content:
                        if msg.sender in config.gpt_user_list or msg.roomid in config.gpt_room_list or config.gpt_flag:
                            if ':' in msg.content:
                                user_msg = msg.content.split(':')[1]
                            else:
                                user_msg = msg.content.split('：')[1]
                            send_msg('正在思考中，请稍等...', msg.roomid, msg.sender)
                            #send_msg(chatgpt(user_msg), msg.roomid, msg.sender)
                            send_msg(gpt_bot.ask_question(f'{msg.roomid}_{msg.sender}', user_msg), msg.roomid, msg.sender)
                        else:
                            send_msg('无权限使用此功能', msg.roomid, msg.sender)
                    elif '搜:' in msg.content or '搜：' in msg.content:
                        if ':' in msg.content:
                            user_msg = msg.content.split(':')[1]
                        else:
                            user_msg = msg.content.split('：')[1]
                        send_msg('正在为您使用百度引擎搜索，请稍等...', msg.roomid, msg.sender)
                        send_msg(get_baidu_result(user_msg), msg.roomid, msg.sender)
                    elif '翻译:' in msg.content or '翻译：' in msg.content or '翻译' in msg.content or '支持翻译语言' in msg.content:
                        if '支持翻译语言' in msg.content:
                            send_msg(
                                'zh（中文）\nen（英语）\nja（日语）\nko（韩语）\nfr（法语）\nes（西班牙语）\nit（意大利语）\nde（德语）\ntr（土耳其语）\nru（俄语）\npt（葡萄牙语）\nvi（越南语）\nid（印尼语）\nth（泰语）\nms（马来语)\n\n请输入对应代号如zh，或目标语言的中文名称，例如英语\n\n例子：@小机 翻译hello为中文',
                                msg.roomid, msg.sender)
                            return {"status": 0, "message": "成功"}
                        # ：后翻译内容，为***为翻译语言
                        if ':' in msg.content:
                            # 匹配:后，为之前的内容
                            user_msg = msg.content.split(':')[1]
                        elif '：' in msg.content:
                            user_msg = msg.content.split('：')[1]
                        elif '翻译' in msg.content:
                            user_msg = msg.content.split('翻译')[1]
                        else:
                            send_msg('翻译格式错误，请输入翻译+内容+为+翻译后语言', msg.roomid, msg.sender)
                            return {"status": 0, "message": "成功"}
                        # 匹配为后面的语言
                        # zh（简体中文）：en（英语）、ja（日语）、ko（韩语）、fr（法语）、es（西班牙语）、it（意大利语）、de（德语）、tr（土耳其语）、ru（俄语）、pt（葡萄牙语）、vi（越南语）、id（印尼语）、th（泰语）、ms（马来语）
                        # 直接匹配为后面的语言
                        if '为' in msg.content:
                            target_language = None
                            user_msg = user_msg.split('为')[0]
                            # 判断是否存在a-z
                            if re.search('[a-z]', msg.content.split('为')[1]):
                                target_language = msg.content.split('为')[1]
                                print(user_msg, target_language)
                            else:
                                for key, value in language_dict.items():
                                    if msg.content.split('为')[1] in value:
                                        target_language = key
                                        break
                            if not target_language:
                                send_msg('翻译语种获取失败，将为翻译为中文', msg.roomid, msg.sender)
                                target_language = 'zh'
                        else:
                            send_msg('未指定翻译语言，默认为翻译为中文', msg.roomid, msg.sender)
                            target_language = 'zh'
                        send_msg(f'将{user_msg}翻译为{target_language}\n正在为您翻译，请稍等...', msg.roomid, msg.sender)
                        send_msg(
                            f'翻译内容：{user_msg}\n\n目标语言：{language_dict[target_language]}\n\n翻译结果：{fy.translate(user_msg, target_language)}',
                            msg.roomid, msg.sender)
                    elif '跟屁虫模式开' in msg.content and msg.sender in config.admin_id:
                        gpc_mode = True
                        # 判断跟屁虫模式开后面是否有@人
                        gpc_id = msg.content.split('跟屁虫模式开')[1]
                        if '@' in gpc_id:
                            # 有指定人
                            gpc_id = gpc_id.split('@')[1]
                            gpc_id = gpc_id.replace(u'\u2005', u'')
                            gpc_name = gpc_id
                            gpc_id = put_name_to_wxid(gpc_id, msg.roomid)
                            if gpc_id:
                                send_msg(f'跟屁虫模式已开启，跟屁虫为:{gpc_name}', msg.roomid, gpc_id)
                                gpc_id_list.append(gpc_id)
                            else:
                                send_msg('跟屁虫模式开启失败，未找到该人', msg.roomid, msg.sender)
                        else:
                            send_msg('跟屁虫模式已开启，未指定用户，将跟所有人', msg.roomid, msg.sender)
                    elif '跟屁虫模式关' in msg.content and msg.sender in config.admin_id:
                        gpc_mode = False
                        gpc_id = ''
                        gpc_id_list = []
                        send_msg('跟屁虫模式已关闭', msg.roomid, msg.sender)
                    else:
                        if config.gpt_flag:
                            # 允许群聊天中使用gpt
                            user_msg = msg.content.split('\u2005')[1]
                            send_msg('GPT-AI马上就到！请等候', msg.roomid, msg.sender)
                            send_msg(gpt_bot.ask_question(f'{msg.roomid}_{msg.sender}', user_msg), msg.roomid, msg.sender)
                        else:
                            send_msg(config.random_list[random.randint(0, len(config.random_list)) - 1], msg.roomid,
                                 msg.sender)
                # 群聊天中收到关键词
                else:
                    # 违规词捕获
                    if msg.roomid in config.keyword_room_list:
                        if find_offending_word(msg.content):
                            if msg.sender not in config.admin_id:
                                offending(msg.roomid, msg.sender, keyword_str)
                            else:
                                print('管理员发的违规词，不处理')
                    # 报警查询
                    if re.match(r"[a-zA-Z]{3,}-\d+", msg.content) \
                            or re.match(r"[a-zA-Z]{2,}-[a-zA-Z]-\d+", msg.content) \
                            or re.match(r"[oO][sS]-\d+", msg.content) \
                            or re.match(r"[pP][nN][tT]1-\d+", msg.content) \
                            or re.match(r"[cC][dD]-\d+", msg.content):
                        data = requests.get(f'https://vbzm.cn/api/fanuc_error?fanuc_error={msg.content}&type=text').text
                        send_msg(
                            f'{data}\n\n-- 数据来源：《不知名小查》微信小程序，使用文章：http://vbzm.cn/a/6LAzH，欢迎使用此工具查询发那科工业机器人报警代码',
                            msg.roomid, msg.sender)
                    # 菜单
                    elif msg.content == "菜单":
                        send_msg(menu_str, msg.roomid, '')
                    # 管理踢人
                    elif '踢@' in msg.content and msg.sender in config.admin_id:
                        # 使用split方法分割字符串
                        name = msg.content.split('@')[1]
                        # 去除 
                        name = name.replace(u'\u2005', u'')
                        # 获取群成员
                        response = requests.get(f'http://localhost:9999/chatroom-member/?roomid={msg.roomid}')
                        wxid_dict = response.json()['data']['members']
                        # 遍历这个字典 键是wxid 值是昵称
                        for wxid, nickname in wxid_dict.items():
                            # 判断是否存在
                            if name in nickname:
                                # 存在则踢出
                                delet_room_user(msg.roomid, wxid)
                                send_msg(f'已踢出 {nickname}', msg.roomid, '')
                    elif '违禁词+' in msg.content and msg.sender in config.admin_id:
                        print('add')
                        keyword = msg.content.split('+')[1]
                        if keyword not in config.keyword_list:
                            config.keyword_list.append(keyword)
                            send_msg(f'已添加 {keyword} 到违禁词库', msg.roomid, msg.sender)
                            config.save_yaml(config.__dict__)
                        else:
                            send_msg(f'{keyword} 已存在于违禁词库中', msg.roomid, msg.sender)
                    elif '违禁词-' in msg.content and msg.sender in config.admin_id:
                        print('违禁词-')
                        keyword = msg.content.split('-')[1]
                        if keyword in config.keyword_list:
                            config.keyword_list.remove(keyword)
                            send_msg(f'已删除 {keyword} 从违禁词库', msg.roomid, msg.sender)
                            config.save_yaml(config.__dict__)
                        else:
                            send_msg(f'{keyword} 不存在于违禁词库中', msg.roomid, msg.sender)
                    elif msg.content == '违禁词列表' and msg.roomid == config.admin_room_id:
                        send_msg(f'违禁词库：{str(config.keyword_list)}', msg.roomid, msg.sender)
            # 好友消息
            else:
                # 聊天机器人
                if msg.content == '在吗':
                    send_msg('在的', msg.sender, '')
                elif msg.content == '状态':
                    send_msg(f'我很好, 当前启停状态为：{str(run_flag)}', msg.sender, '')
                elif 'ai:' in msg.content or 'ai：' in msg.content or 'AI:' in msg.content or 'AI：' in msg.content:
                    if msg.sender in config.gpt_user_list or msg.roomid in config.gpt_room_list or config.gpt_flag:
                        if ':' in msg.content:
                            user_msg = msg.content.split(':')[1]
                        else:
                            user_msg = msg.content.split('：')[1]
                        if msg.sender in config.gpt_user_list:
                            send_msg('GPT结果生成中，请稍后', msg.sender, '')
                            #send_msg(chatgpt(user_msg), msg.sender, '')
                            send_msg(gpt_bot.ask_question(msg.sender, user_msg), msg.sender, '')
                        else:
                            send_msg('无权限使用此功能', msg.roomid, msg.sender)
                elif '天气' in msg.content:
                    try:
                        city = re.findall(r'(.*?)天气', msg.content)[0]
                        print(city)
                        if city != '':
                            weather = get_weather(city, weather_appid, weather_appsecret)
                            print(weather)
                            send_msg(weather, msg.sender, '')
                        else:
                            send_msg('你都不说查哪我查个毛啊？[鄙视]', msg.sender, '')
                    except Exception as e:
                        send_msg('查询出错喽', msg.sender, '')
                elif 'id+' in msg.content and msg.sender in config.admin_id:
                    id = msg.content.split('+')[1]
                    if '@' in msg.content:
                        if id not in config.room_list:
                            config.room_list.append(id)
                            send_msg(f'已允许机器人在 {id} 发言', msg.sender, '')
                            send_msg(f'我大哥让我说话啦', id, '')
                        else:
                            send_msg(f'{id} 已存在于允许列表中', msg.sender, '')
                    elif 'wxid' in msg.content:
                        if id not in config.user_list:
                            config.user_list.append(id)
                            send_msg(f'已允许机器人与 {id} 对话', msg.sender, '')
                            send_msg(f'已允许机器人与你聊天', id, '')
                        else:
                            send_msg(f'{id} 已存在于允许列表中', msg.sender, '')
                    config.save_yaml(config.__dict__)
                elif 'id-' in msg.content and msg.sender in config.admin_id:
                    id = msg.content.split('-')[1]
                    if '@' in msg.content:
                        if id in config.room_list:
                            config.room_list.remove(id)
                            send_msg(f'已禁止机器人在 {id} 发言', msg.sender, '')
                            send_msg(f'我大哥让我闭嘴啦', id, '')
                            config.save_yaml(config.__dict__)
                        else:
                            send_msg(f'{id} 不存在于允许列表中', msg.sender, '')
                    elif 'wxid' in msg.content:
                        if id in config.user_list:
                            config.user_list.remove(id)
                            send_msg(f'已禁止机器人与 {id} 聊天', msg.sender, '')
                            send_msg(f'我大哥让我闭嘴啦', id, '')
                            config.save_yaml(config.__dict__)
                        else:
                            send_msg(f'{id} 不存在于允许列表中', msg.sender, '')
                    config.save_yaml(config.__dict__)
                elif msg.content == 'gpt开' or msg.content == 'gpt开启' or msg.content == '开启gpt' or msg.content == '开gpt':
                    if msg.sender in config.admin_id:
                        config.gpt_flag = True
                        send_msg(f'已开启GPT功能', msg.sender, '')
                        config.save_yaml(config.__dict__)
                    else:
                        send_msg('无权限使用此功能', msg.sender, '')
                elif msg.content == 'gpt关' or msg.content == 'gpt关闭' or msg.content == '关闭gpt' or msg.content == '关gpt':
                    if msg.sender in config.admin_id:
                        config.gpt_flag = False
                        send_msg(f'已关闭GPT功能', msg.sender, '')
                        config.save_yaml(config.__dict__)
                    else:
                        send_msg('无权限使用此功能', msg.sender, '')
                elif msg.content == '违禁词列表':
                    if msg.sender in config.admin_id:
                        send_msg(f'违禁词列表：{config.keyword_list}', msg.sender, '')
                    else:
                        send_msg('无权限使用此功能', msg.sender, '')
                else:
                    if config.gpt_flag:
                        # 允许用户聊天中使用gpt
                        send_msg('GPT结果生成中，请稍后', msg.sender, '')
                        send_msg(gpt_bot.ask_question(msg.sender, msg.content), msg.sender, '')
                    else:
                        send_msg(config.random_list[random.randint(0, len(config.random_list)) - 1], msg.sender, '')
        # 系统消息
        elif msg.type == 10000:
            # 加入群聊欢迎
            if "加入群聊" in msg.content or "加入了群聊" in msg.content:
                pattern = r'"([^"]*)"'
                matches = re.findall(pattern, msg.content)
                if len(matches) > 1:
                    welcome_name = matches[1]
                else:
                    welcome_name = matches[0]
                if msg.roomid == '20588960524@chatroom':
                    send_msg(
                        f'🧨🧨🧨\n欢迎 {welcome_name} 一起搞🤖\n进群请先看群公告，谢谢！', msg.roomid, '')
                else:
                    send_msg(
                        f'🧨🧨🧨\n欢迎 {welcome_name} 一起搞🤖\n进群请先看群公告，谢谢！\n\n发那科开发助手，点击链接了解：https://mp.weixin.qq.com/s/XPTM1tH9Q-rCSHu-KkakDg',
                        msg.roomid, '')
        # 消息撤回
        elif msg.type == 10002 and "撤回" in msg.content:
            # 在阻止撤回的列表中
            if msg.sender in config.list_revoke or msg.roomid in config.list_revoke:
                print('尝试阻止')
                if msg.roomid == '':
                    send_id = msg.sender
                    at_id = ''
                else:
                    send_id = msg.roomid
                    at_id = msg.sender

                # 在content中找到newmsgid
                content = xmltodict.parse(msg.content)
                newmsgid = str(content['sysmsg']['revokemsg']['newmsgid'])
                # 获取撤回消息的内容
                if newmsgid in msg_dict.keys():
                    revoke_msg = msg_dict[newmsgid]['msg']
                    send_msg(f'你撤回了一条消息，内容是：{revoke_msg}\n\n不知名小机真厉害', send_id, at_id)
                    del msg_dict[newmsgid]
                    print(f"字典中的{newmsgid}阻止成功，已自动删除")
                else:
                    print(f"字典中的{newmsgid}不存在，阻止失败")
            else:
                print("阻止失败！")

        return {"status": 0, "message": "成功"}
    except Exception as e:
        # 发送报错原因和报错行数
        send_msg(f'报错原因：{str(e)}\n报错行数：{sys.exc_info()[2].tb_lineno}', config.admin_room_id, '')
        return {"status": 0, "message": "成功"}


def test():
    print(config.random_list)
    return {"status": 0, "message": "成功"}


def moyu_send_room():
    moyu_img_url = requests.get('https://moyu.qqsuu.cn/?type=json').json()['data']
    # 获取今天的日期，与data中(/20231203.png)比较，如果不是新的就不发
    today = time.strftime("%Y%m%d", time.localtime())
    if today not in moyu_img_url:
        send_msg('摸鱼报未更新', config.admin_room_id, '')
    else:
        for room_id in config.morning_report_room_list:
            send_img(moyu_img_url, room_id)
    return {"status": 0, "message": "成功"}


def morning_send_room():
    # 新闻推送
    news_data = get_important_news()
    if news_data == '':
        send_msg('今天新闻没更新', config.admin_room_id, '')
        return {"status": 0, "message": "成功"}
    for room_id in config.morning_report_room_list:
        send_msg(news_data, room_id, '')
    return {"status": 0, "message": "成功"}


def first_run():
    send_msg(f'不知名小机已上线', config.admin_room_id, '')


if __name__ == "__main__":
    run_flag = True
    gpc_mode = False
    gpc_id = ''
    gpc_id_list = []

    # 初始化yaml配置
    config = Config()
    fy = TencentTranslate()

    gpt_config = {
        'url': '',
        'key': config.gpt_sk
    }

    gpt_bot = Chatbot(gpt_config)
    # config.wxid_self = get_my_wxid()
    # config.save_yaml(config.__dict__)
    app = FastAPI()
    first_run()
    app.add_api_route('/', test, methods=["GET"])
    app.add_api_route("/t", msg_cb, methods=["POST"])
    app.add_api_route("/morning_send_room", morning_send_room, methods=["GET"])
    app.add_api_route("/moyu_send_room", moyu_send_room, methods=["GET"])
    uvicorn.run(app, host="0.0.0.0", port=7888)


    # 500行代码 不知名网友真滴猛
