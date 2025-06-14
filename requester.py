import requests
from logger import setup_logger
import re
import time
from enum import Enum
import logging

logger = setup_logger(__name__, logging.DEBUG)
class Ranking(Enum):
    ALL_COMMENTS = "RANKED_UNFILTERED_CHRONOLOGICAL_REPLIES_INTENT_V1"
    MOST_RELEVANT = "RANKED_FILTERED_INTENT_V1"
    NEWEST = "REVERSE_CHRONOLOGICAL_UNFILTERED_INTENT_V1"
class Requester():
    @staticmethod
    def _get_headers(pageurl: str):
        '''
        Send a request to get cookieid as headers.
        '''
        pageurl = re.sub('www', 'm', pageurl)
        resp = requests.get(pageurl)
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-language': 'en'
        }
        cookies = resp.cookies.get_dict()
        headers['cookie'] = '; '.join([f'{k}={v}' for k, v in cookies.items()])

        logger.debug("Lấy headers thành công")
        return headers

    @staticmethod
    def _get_homepage(pageurl: str, headers: dict):
        '''
        Send a request to get the homepage response
        '''
        pageurl = re.sub('/$', '', pageurl)
        timeout_cnt = 0
        while True:
            try:
                homepage_response = requests.get(pageurl, headers=headers, timeout=3)
                return homepage_response
            except:
                time.sleep(5)
                timeout_cnt += 1
                if timeout_cnt > 20:
                    class homepage_response:
                        text = 'Sorry, something went wrong.'
                    return homepage_response

    @staticmethod
    def _get_comments(headers: dict, post_id: str, ranking: Ranking, get_post_api: str) -> requests.Response:
        data = {
            "variables": str({
                "commentsIntentToken": ranking.value,
                "scale": 1,
                "id": post_id,
                "__relay_internal__pv__IsWorkUserrelayprovider": "false"
            }),
            "doc_id": get_post_api
        }

        url = "https://www.facebook.com/api/graphql/"
        try:
            resp = requests.post(url, data=data, headers=headers)

            if resp.status_code != 200:
                logger.warning(f"Lỗi khi request comment {resp.status_code}")
            else:
                logger.debug(f"Lấy comment thành công")
            return resp
        except Exception as e:
            logger.debug(f"Lỗi khi request comment {e}")
            return None 

    @staticmethod
    def _get_more_comments(headers: dict, post_id: str, ranking: Ranking, get_post_api: str, end_cursor: str) -> requests.Response:
        data = {
            "variables": str({"commentsAfterCount": -1,
                              "commentsAfterCursor": end_cursor, 
                              "commentsIntentToken": ranking.value,
                              "scale": 1,
                              "id": post_id,
                              "__relay_internal__pv__IsWorkUserrelayprovider": "false"
            }),
            "doc_id": get_post_api
        }

        url = "https://www.facebook.com/api/graphql/"

        try:
            resp = requests.post(url, data=data, headers=headers)
            return resp
        except Exception as e:
            logger.debug(f"Lỗi khi request comment {e}")
            return None 

    @staticmethod
    def _get_comments_depth1(headers: dict, comment_id: str, expansion_token: str,  get_comment_api: str, end_cursor: str = "") -> requests.Response:
        variables = {
            "expansionToken": expansion_token,
            "scale": 1,
            "id": comment_id,
            "__relay_internal__pv__IsWorkUserrelayprovider": "false"
        }

        if end_cursor:
            variables['repliesAfterCursor'] = end_cursor
        
        data = {
            "variables": str(variables),
            "doc_id": get_comment_api
        }

        url = "https://www.facebook.com/api/graphql/"
        try:
            resp = requests.post(url, data=data, headers=headers)

            if resp.status_code != 200:
                logger.warning(f"Lỗi khi request comment {resp.status_code}")
            else:
                logger.debug(f"Lấy comment thành công")
            return resp
        except Exception as e:
            logger.debug(f"Lỗi khi request comment {e}")
            return None 


    @staticmethod
    def _get_posts(headers: dict, time_range: dict, identifier: str, entryPoint: str, docid: str, cursor: str = "") -> requests.Response:
        data = {
            'variables': str({
                'aftertime': time_range['after_time'],
                "beforeTime": time_range['before_time'],
                'cursor': cursor,
                'id': identifier,
                'count': 3
            }), 
            'doc_id': docid
        }
        try:
            resp = requests.post(
                url='https://www.facebook.com/api/graphql/',
                data=data,
                headers=headers
            )
            return resp
        except Exception as e:
            logger.debug(f"Lỗi khi request post {e}")
            return None