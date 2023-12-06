# admin_id 为管理员微信号，用于接收机器人报警信息
# admin_room_id 为管理员群聊id，用于接收机器人报警信息
# gpt_room_list 为gpt-3聊天群聊id列表，即使无权限用户也可在该使用gpt-3聊天
# gpt_sk 为gpt-3的sk，token，用于gpt-3聊天\n# gpt_user_list 为gpt-3聊天用户列表，有权限
# keyword_list 为违规词列表
# keyword_room_list 为违规词捕获群聊列表
# keyword_str 为违规词捕获后的回复
# list_revoke 为防止撤回信息捕获群列表
# menu_str 为机器人菜单
# morning_report_room_list 为早报推送群聊列表
# random_list 为随机回复列表
# room_list 为机器人可聊天的群聊列表
# user_list 为机器人可聊天的用户列表
# weather_appid 为天气查询appid
# weather_appsecret 为天气查询appsecret
# wxid_self 为机器人微信号"


import os
import yaml


class Config(object):
    def __init__(self) -> None:
        self.reload()

    def _load_config(self) -> dict:
        pwd = os.path.dirname(os.path.abspath(__file__))
        # 往回找一级目录

        with open(f"{pwd}/config.yaml", "r", encoding='utf-8') as fp:
            yconfig = yaml.safe_load(fp)

        return yconfig

    def reload(self) -> None:
        yconfig = self._load_config()
        self.wxid_self = yconfig["wxid_self"]
        self.admin_id = yconfig["admin_id"]
        self.admin_room_id = yconfig["admin_room_id"]
        self.morning_report_room_list = yconfig["morning_report_room_list"]

        self.user_list = yconfig["user_list"]
        self.room_list = yconfig["room_list"]
        self.list_revoke = yconfig["list_revoke"]

        self.gpt_room_list = yconfig["gpt_room_list"]
        self.gpt_user_list = yconfig["gpt_user_list"]
        self.gpt_sk = yconfig["gpt_sk"]

        self.keyword_list = yconfig["keyword_list"]
        self.keyword_room_list = yconfig["keyword_room_list"]
        self.random_list = yconfig["random_list"]

        self.gpt_flag = yconfig["gpt_flag"]

    def save_yaml(self, yconfig: dict) -> None:
        pwd = os.path.dirname(os.path.abspath(__file__))
        with open(f"{pwd}/config.yaml", "w", encoding='utf-8') as fp:
            yaml.dump(yconfig, fp, allow_unicode=True)
        print("保存成功！")
