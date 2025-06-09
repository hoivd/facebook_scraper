import os
from typing import Tuple
import json
from logger import setup_logger
import random

logger = setup_logger(__name__)

class Utils():
    @staticmethod
    def load_cookies(path):
        logger.info("Tiến hành load cookies")
        try:
            with open(path, "r", encoding="utf-8") as file:
                return json.load(file)
            logger.info(f"Load cookies thành công {path}")
        except Exception as e:
            logger.error(f"Lỗi khi load cookies {path} {e}")
            raise Exception("Lỗi khi load cookies", e)

    @staticmethod
    def check_and_add_api(json_path: str, data: Tuple[str, int]) -> None:
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as file:
                    json_data = json.load(file)
            except json.JSONDecodeError:
                json_data = {}
        else:
            json_data = {}

        key, value = data

        if key not in json_data.keys():
            json_data[key] = value
        else:
            if json_data[key] != value:
                json_data[key] = value
        try:
            with open(json_path, "w", encoding="utf-8") as file:
                json.dump(json_data, file, ensure_ascii=False, indent=4)
            
            logger.info(f"Ghi facebook api vào log thành công {data}")
        except Exception as e:
            logger.error(f"Lỗi khi ghi facebook api vào log {data}")

    def write_json(json_path: str, data: dict) -> None:
        try: 
            with open(json_path, "w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=4)
            logger.info(f"Ghi json thành công {json_path}")
        except Exception as e:
            logger.error(f"Lỗi khi ghi json {json_path} {e}")
    
    @staticmethod
    def load_json(json_path: str) -> dict:
        try:
            with open(json_path, "r", encoding="utf-8") as file:
                return json.load(file)
        except Exception as e:
            logger.error(f"Lỗi khi load json {json_path} {e}")
            raise Exception("Lỗi khi load json", e)

    @staticmethod
    def del_json(json_path: str) -> None:
        try:
            os.remove(json_path)
        except Exception as e:
            logger.error(f"Lỗi khi xóa json {json_path} {e}")

    @staticmethod
    def file_exists(file_path: str) -> bool:
        return os.path.exists(file_path)

    @staticmethod
    def get_random_url(file_path: str) -> str:
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                urls = file.readlines()

            url = random.choice(urls).strip()
            return url
        except Exception as e:
            logger.error(f"Lỗi khi lấy url ngẫu nhiên {file_path} {e}")
            raise Exception("Lỗi khi lấy url ngẫu nhiên", e)

    def is_apis_in_source(json_path: str, api_names: list[str]) -> bool:
        try:
            if not os.path.exists(json_path):
                logger.warning(f"File {json_path} không tồn tại")
                return False

            api_sources = Utils.load_json(json_path)
            for api_name in api_names:
                if api_name not in api_sources.keys():
                    logger.warning(f"API {api_name} không tồn tại")
                    return False
                else:
                    logger.info(f"API {api_name} tồn tại")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra api {json_path} {e}")

    @staticmethod
    def export_api2json(api_path: str, json_path: str, api_names: list[str]) -> None:
        try:
            if not os.path.exists(api_path):
                logger.warning(f"File {api_path} không tồn tại")
                return

            if not Utils.is_apis_in_source(api_path, api_names):
                logger.warning(f"Có API không tồn tại trong API SOURCE")
                return

            api_sources = Utils.load_json(api_path)
            api_json = dict()
            for api_name in api_names:
                api_json[api_name] = api_sources[api_name]
            
            Utils.write_json(json_path, api_json)
        except Exception as e:
            logger.error(f"Lỗi khi export api {api_path} {e}")


        
        
