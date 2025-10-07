import toml
from pathlib import Path

CONFIG_PATH = (Path(__file__).parent / "config.toml").resolve()
CONFIG = toml.load(CONFIG_PATH)
token = CONFIG.get("qiniu_oss_token", "")

res_list = [
    f"http://t3ra9pvqh.hd-bkt.clouddn.com/MaaStarResonance/python-3.13.7-embed-amd64.zip?e=1759834164&token={token}:1CDJcwBizi8yKAcsm0FouNUYdj0=",
    f"http://t3ra9pvqh.hd-bkt.clouddn.com/MaaStarResonance/MAACopilot_%E4%BF%9D%E5%85%A8%E6%B4%BE%E9%A9%BB-%E9%98%BF%E5%8D%A1%E8%83%A1%E6%8B%89%E4%B8%9B%E6%9E%97-EW%2B%E9%80%BB%E5%90%84%E6%96%AF-%E4%B8%9B%E6%9E%97%E7%94%A8%E7%A4%BA%E8%B8%AA%E4%BF%A1%E6%A0%87.json?e=1759834583&token={token}:6u47kDvliWdFDdgeu-driT4FwoA="
]