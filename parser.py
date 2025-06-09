from typing import Tuple
import requests
from logger import setup_logger

logger = setup_logger(__name__)

class Parser():
    @staticmethod
    def _get_payload(payload: str) -> dict:
        parser_payload = payload.strip().split('&')

        payload_dict = dict()
        for item in parser_payload:
            key, value = item.split('=')
            payload_dict[key] = value

        return payload_dict
    
    @staticmethod
    def _get_api_value(payload: str) -> Tuple[str, int]:
        payload_dict = Parser._get_payload(payload)
        
        api_name = payload_dict['fb_api_req_friendly_name']
        api_key = payload_dict['doc_id']

        return (api_name, api_key)
    
    @staticmethod
    def parse_total_cmt(resp_json: dict) -> int:
        total_cmt = resp_json['data']['node']['comment_rendering_instance_for_feed_location']['comments']['total_count']
        return total_cmt

    @staticmethod
    def parse_total_parent_cmt(resp_json: dict) -> int:
        total_parent_cmt = resp_json['data']['node']['comment_rendering_instance_for_feed_location']['comments']['count']
        return total_parent_cmt
    
    @staticmethod
    def parse_comments(resp_json: dict) -> list:
        edges = resp_json['data']['node']['comment_rendering_instance_for_feed_location']['comments']['edges']

        comments = list()
        for edge in edges:
            comment = {
                'text': "",
                'image': None
            }
            try:
                comment['text'] = edge['node']['body']['text']
            except Exception as e:
                logger.warning("Không tìm thấy text trong comment") 
            
            try:
                i = len(edge['node']['attachments'])
                comment['image'] = edge['node']['attachments'][i-1]['style_type_renderer']['attachment']['media']['image'] 
            except Exception as e:
                logger.warning("Không tìm thấy ảnh trong comment")

            comments.append(comment)

        return comments

    @staticmethod
    def parse_comments_info(resp: requests.Response) -> dict:
        resp_json = resp.json()
        comments_info = dict()

        comments_info['total_comment'] = Parser.parse_total_cmt(resp_json)
        # comments_info['total_parent_comment'] = Parser.parse_total_parent_cmt(resp_json)
        comments_info['comments'] = Parser.parse_comments(resp_json)

        return comments_info

    @staticmethod
    def parse_page_info(resp: requests.Response) -> str:
        resp_json = resp.json()
        page_info = resp_json['data']['node']['comment_rendering_instance_for_feed_location']['comments']['page_info']
        return page_info



        