import pandas as pd
from utils import Utils
from logger import setup_logger
from requester import Requester
from parser import Parser

logger = setup_logger(__name__)

class FacebookScraper():
    def crawl_comment(self, post_url: str, post_id: str, cmt_api_path: str) -> pd.DataFrame:
        try: 
            logger.info(f"Thực hiện lấy comment:")
            logger.info(f"Post URL: {post_url}")
            logger.info(f"Post ID: {post_id}")

            cmt_api = Utils.load_json(cmt_api_path)
            logger.info(f"API Get Comment {cmt_api}") 

            # Lấy api get comment gốc và gửi request
            comment_api = cmt_api['CommentListComponentsRootQuery']
            headers = Requester._get_headers(post_url)

            logger.info(f"Gửi request lần đầu lấy thông tin comment")
            resp = Requester._get_comments(headers, post_id, comment_api)

            if resp.status_code == 200:
                logger.info(f"Lấy thông tin comment thành công")
            else:
                logger.info(f"Lỗi khi gửi request {resp.status_code}")

            logger.info(f"Tiến hành parser response:")
            comment_info = Parser.parse_comments_info(resp)
            page_info = Parser.parse_page_info(resp)

            # Lấy api get thêm comment và gửi request
            more_comment_api = cmt_api['CommentsListComponentsPaginationQuery']
            logger.info(f"Lấy thêm comment API: {more_comment_api}")
            iter = 1
            while page_info['has_next_page']:
                logger.info(f"Lấy thêm comment lần {iter}")

                end_cursor = page_info['end_cursor']
                resp = Requester._get_more_comments(headers, post_id, more_comment_api, end_cursor)

                if resp.status_code == 200:
                    logger.info(f"Lấy thông tin comment thành công")
                else:
                    print(f"Lỗi khi gửi request {resp.status_code}")

                logger.info(f"Tiến hành parser response:")
                comments = Parser.parse_comments(resp.json()) 
                page_info = Parser.parse_page_info(resp)

                comment_info['comments'] += comments

                iter += 1
                
            for idx, comment in enumerate(comment_info["comments"]):
                logger.info(f"Comment {idx}:")
                logger.info(f"Text: {comment['text']}")
                logger.info(f"Image: {comment['image']}")
                logger.info(f"\n")
            
            #Ghi kết quả vào tệp
            comments_path = "./facebook_urls/comments.json" 
            Utils.write_json(comments_path, comment_info)
            logger.info(f"Lấy comment thành công")
        except Exception as e:
            logger.error(f"Lỗi khi lấy comment {e}")
            raise Exception(f"Lỗi khi lấy comment {e}")


    def get_post(self):
        pass
    
if __name__ == "__main__":
    post_url = "https://www.facebook.com/Theanh28/posts/pfbid07nWnrFkUs8LLdnyah9VSwXngRfegP5iGDjzCgkL17dp2H4TboYyM8GRzewXGD6uql"
    post_id = "ZmVlZGJhY2s6MTAyODY4ODQzMjc3OTU5Mg==" 
    comment_api_path = "./api_info/comment_api.json"

    scraper = FacebookScraper()
    scraper.crawl_comment(post_url, post_id, comment_api_path)