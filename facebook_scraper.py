from logger import setup_logger
from requester import Requester, Ranking
from parser import Parser
import os
import time
import json
from utils import Utils
from typing import Union, Optional, Tuple
from datetime import datetime
import logging

logger = setup_logger(__name__, logging.DEBUG)
class FacebookScraper():
    def crawl_comment(self, post_url: str, feedback_id: str,
                       ranking: Ranking,
                       reaction_id_info: dict,
                        cmt_api_path: str,
                       has_return: bool = False,
                        has_write: bool = True, max_comment: int = 50, max_depth1_comment: int = 50,
                        max_retry: int = 3, break_time: int = 2) -> None:
        try: 
            logger.debug(f"{'-' * 20} Thực hiện lấy COMMENT: {'-' * 20}")
            logger.debug(f"Post URL: {post_url}")
            logger.debug(f"Post ID: {feedback_id}")
            logger.debug(f"Ranking Filter: {ranking.name}")

            cmt_api = Utils.load_json(cmt_api_path)
            logger.debug(f"API Get Comment {cmt_api}") 

            # Lấy api get comment gốc và gửi request
            comment_api = cmt_api['CommentListComponentsRootQuery']
            headers = Requester._get_headers(post_url)

            logger.debug(f"Gửi request lần đầu lấy thông tin comment")
            resp = Requester._get_comments(headers, feedback_id, ranking, comment_api)

            logger.debug(f"Tiến hành parser response:")
            comment_info = Parser.parse_comments_info(resp, headers,  reaction_id_info=reaction_id_info)
            page_info = Parser.parse_page_info(resp)

            # Lấy api get thêm comment và gửi request
            more_comment_api = cmt_api['CommentsListComponentsPaginationQuery']
            logger.debug(f"Lấy thêm comment API: {more_comment_api}")
            max_iter = Utils.n_comment2n_iter(max_comment) - 1
            iter = 0
            retry_count = 0
            while page_info['has_next_page'] and len(comment_info['comments']) < max_comment:
                logger.debug(f"{'-' * 20} PARENT COMMENT ITER {iter} {'-' * 20}")
                try:
                    end_cursor = page_info['end_cursor']
                    resp = Requester._get_more_comments(headers, feedback_id, ranking,  more_comment_api, end_cursor)

                    logger.debug(f"Tiến hành parser response:")
                    resp_jsons = Parser.parse_jsons(resp)
                    data_json = resp_jsons[0]
                    comments = Parser.parse_comments(data_json, headers, reaction_id_info) 
                    cur_page_info = Parser.parse_page_info(resp)

                    logger.debug(f"{'-' * 20}Lấy PARENT COMMENT ITER {iter} thành công{'-' * 20}")
                    comment_info['comments'] += comments
                    page_info = cur_page_info
                    retry_count = 0
                except:
                    logger.debug(f"{'-' * 20} Lỗi khi lấy PARENT COMMENT ITER {iter} {'-' * 20}")
                    retry_count += 1
                    if retry_count >= max_retry:
                        logger.warning(f"Thất bại khi lấy PARENT COMMENT --- Thử lại lần {retry_count+1} ---")
                        break
                iter += 1
                time.sleep(break_time)
                
            for idx, comment in enumerate(comment_info["comments"]):
                logger.debug(f"Comment {idx}:")
                logger.debug(f"Text: {comment['text']}")
                logger.debug(f"Image: {comment['image']}")
                logger.debug(f"\n")
            
            #Ghi kết quả vào tệp
            # if has_write:
            #     comments_path = "./data/jsonl/comments.jsonl" 
            #     os.makedirs(os.path.dirname(comments_path), exist_ok=True)
            #     Utils.write_jsonl(comments_path, comment_info)

            path = "./facebook_urls/comments.json"
            Utils.write_json(path, comment_info)            

            if has_return:
                return comment_info
            logger.debug(f"Lấy PARENT COMMENT thành công")
        except Exception as e:
            logger.error(f"Lỗi khi lấy PARENT COMMENT {e}")

    def crawl_post(self, page_url: str, after_time: int = None, before_time: int = None, 
                   ranking_comment: Ranking = Ranking.MOST_RELEVANT, include_comment: bool = True, 
                   save_dir: str = "data\\image", max_post: int = 10, 
                   comment_api_path: str = "./api_info/comment_api.json", 
                   return_posts: bool = False,
                    max_parent_comment: int = 50, max_depth1_comment: int = 50):
        try:
            logger.debug(f"----------------Chương trình lấy post---------------")
            headers = Requester._get_headers(page_url)
            homepage_response = Requester._get_homepage(page_url, headers)

            entryPoint = Parser._parse_entryPoint(homepage_response)
            identifier = Parser._parse_identifier(entryPoint, homepage_response)
            post_api = Parser._parse_docid(entryPoint, homepage_response)           
            
            logger.debug(f"EntryPoint: {entryPoint}")
            logger.debug(f"PageID: {identifier}")
            logger.debug(f"PostAPI: {post_api}")
            logger.debug(f"Lấy thông tin api thành công")

            time_range, page_info = Utils.init_requests_variables(after_time, before_time)
            logger.debug(f"TimeRange: {time_range}")
            logger.debug(f"PageInfo: {page_info}")
            logger.debug(f"Lấy thông tin Variable Request thành công")

            reaction_id= Parser._get_reaction_id(page_url) 
                    
            all_posts = []
            post_ids = set()
            os.makedirs(save_dir, exist_ok=True)
            
            max_retry = 3
            retry_count = 0
            page_info_found = True
            n_iter = Utils.n_post2n_iter(max_post)  
            logger.debug(f"NUM ITERATIONS: {n_iter}")

            fanpage_name = page_url.rstrip('/').split('/')[-1] or "unknown"
            file_jsonl_path = f"data/json/posts_{fanpage_name}_{before_time}.jsonl"
            Utils.remove_file(file_jsonl_path)

            for round_idx in range(n_iter):
                logger.debug(f"--- ITER {round_idx+1} ---")

                if page_info_found == False:
                    retry_count += 1
                    if retry_count >= max_retry:
                        logger.warning(f"Thất bại khi lấy PageInfo --- Thử lại lần {retry_count+1} ---")
                        break
                    
                if page_info['has_next_page'] == True:
                    cursor = page_info['end_cursor']
                    resp = Requester._get_posts(headers, time_range, identifier, entryPoint, post_api, cursor)

                    if not resp or resp.status_code != 200:
                        logger.warning(f"Lỗi khi gửi request lấy post {resp.status_code if resp else 'No response'}")
                        break

                    resp_jsons = Parser.parse_jsons(resp)

                    for idx, json in enumerate(resp_jsons):
                        logger.debug(f"Parse Json thứ {idx+1}")
                        try:
                            post_info = Parser.parse_post_obj(json, save_dir=save_dir)

                            if post_info != {}:
                                if include_comment:
                                    post_url = post_info['post_url']
                                    feedback_id = post_info['feedback_id']
                                    post_info['comments'] = self.crawl_comment(post_url, feedback_id, ranking_comment,
                                                                                reaction_id, comment_api_path, has_return=True,
                                                                                 max_comment=max_parent_comment, max_depth1_comment=max_depth1_comment)

                                Utils.write_jsonl(file_jsonl_path, post_info)      
                                all_posts.append(post_info)
                            
                        except Exception as e:
                            logger.warning(f"Lỗi dòng: {e}")
                    
                    new_page_info = Parser.parse_post_page_info(resp_jsons)

                    if new_page_info == {}:
                        page_info_found = False
                    else:
                        retry_count = 0
                        page_info = new_page_info
                        page_info_found = True

                    time.sleep(3)
            
            os.makedirs("data/json", exist_ok=True)
            fanpage_name = page_url.rstrip('/').split('/')[-1] or "unknown"
            file_path = f"data/json/posts_{fanpage_name}.json"
            Utils.write_json(file_path, all_posts)

            for post in all_posts:
                logger.debug(f"Post content: {post['post_content']}")

            logger.debug(f"Đã lưu thông tin các post vào {file_path}")
            if return_posts:
                return all_posts
        except Exception as e:
            logger.error(f"Lỗi khi lấy post {e}")
            raise Exception(f"Lỗi khi lấy post {e}")
    
if __name__ == "__main__":
    scraper = FacebookScraper()

    post_url = "https://www.facebook.com/Theanh28/posts/pfbid02s6nYu5teN3M5KyLuBZVrHGPyZrbxWSzSisV382h7bC7SdcKP4giHydTWKy63fhLLl"
    post_id = "ZmVlZGJhY2s6MTAxMzkzNDcwMDkyMTYzMg==" 
    comment_api_path = "./api_info/comment_api.json"
    ranking = Ranking.MOST_RELEVANT
    logger.debug(f"Ranking Filter: {ranking.value}")
    reaction_id  = Utils.load_json("./api_info/reaction_ids.json")
    max_parent_comment = 10
    max_depth_comment = 10
    scraper.crawl_comment(post_url, post_id, ranking, reaction_id, comment_api_path, max_comment=max_parent_comment, max_depth1_comment=max_depth_comment)
    
    # fanpage_url = "https://www.facebook.com/Theanh28"
    # before_time = "2025-5-31"
    # ranking = Ranking.MOST_RELEVANT
    # scraper.crawl_post(fanpage_url, max_post=200, ranking_comment=ranking, before_time=before_time )


    # Parser._get_reaction_id(fanpage_url)
 