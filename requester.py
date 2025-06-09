import requests
from logger import setup_logger
import re

logger = setup_logger(__name__)

class Requester():
    @staticmethod
    def _get_headers(pageurl):
        '''
        Send a request to get cookieid as headers.
        '''
        pageurl = re.sub('www', 'm', pageurl)
        resp = requests.get(pageurl)
        headers = {'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                'accept-language': 'en'}
        headers['cookie'] = '; '.join(['{}={}'.format(cookieid, resp.cookies.get_dict()[
                                    cookieid]) for cookieid in resp.cookies.get_dict()])
        return headers

    @staticmethod
    def _get_comments(headers: dict, post_id: str, get_post_api: str) -> requests.Response:
        data = {
            "variables": str({
                "commentsIntentToken": "RANKED_UNFILTERED_CHRONOLOGICAL_REPLIES_INTENT_V1",
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
            logger.info(f"Lỗi khi request comment {e}")
            return None 

    @staticmethod
    def _get_more_comments(headers: dict, post_id: str, get_post_api: str, end_cursor: str) -> requests.Response:
        data = {
            "variables": str({"commentsAfterCount": -1,
                              "commentsAfterCursor": end_cursor, 
                              "commentsIntentToken": "RANKED_UNFILTERED_CHRONOLOGICAL_REPLIES_INTENT_V1",
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
            logger.info(f"Lỗi khi request comment {e}")
            return None 
        

        