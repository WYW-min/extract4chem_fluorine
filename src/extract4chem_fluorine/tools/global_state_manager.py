import orjson
from loguru import logger
from datetime import datetime

def pretty_json(d:dict):
    return orjson.dumps(d).decode('utf-8')
class GlobalStateManager:
    
    def __init__(self):
        # 在这里注册全局状态
        self.gs_dict = {
            "timestamp" : "20260108160000"
        }
        
        logger.info(f"所注册的全局状态如下：{pretty_json(self.gs_dict)}")
        
    def __getitem__(self, key):
        return self.gs_dict.get(key)
    
    def __str__(self):
        return str(self.gs_dict)
    
    
gs_manager = GlobalStateManager()

__all__ = ["gs_manager"]


if __name__ == "__main__":
    print(gs_manager)
        
        