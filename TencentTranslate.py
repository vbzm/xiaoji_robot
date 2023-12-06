from tencentcloud.common import credential  # 这里需要安装腾讯翻译sdk
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.tmt.v20180321 import tmt_client, models
import json

class TencentTranslate:
    def __init__(self):
        self.cred = credential.Credential("",
                                     "")
        self.httpProfile = HttpProfile()
        self.httpProfile.endpoint = "tmt.tencentcloudapi.com"
        self.clientProfile = ClientProfile()
        self.clientProfile.httpProfile = self.httpProfile
        self.client = tmt_client.TmtClient(self.cred, "ap-beijing", self.clientProfile)

    def translate(self, source_text, target):
        req = models.TextTranslateRequest()
        req.SourceText = source_text
        req.Source = 'auto'
        req.Target = target
        req.ProjectId = 0
        resp = self.client.TextTranslate(req)
        data = json.loads(resp.to_json_string())
        print(data)
        return data['TargetText']