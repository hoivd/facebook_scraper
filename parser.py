from typing import Tuple
import requests
from logger import setup_logger
import os
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime
from requester import Requester
from typing import Optional, Tuple
from utils import Utils
import logging

logger = setup_logger(__name__, logging.DEBUG)

VALID_IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}

def is_valid_image(filename):
    ext = os.path.splitext(filename)[1].lower()
    return ext in VALID_IMAGE_EXTS and ext != ''

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
    def download_images_from_attachments(attachments, save_dir="./data/image"):
        image_paths = []
        for att in attachments:
            try:
                styles = att.get('styles', {})
                attachment = styles.get('attachment', {})
                if attachment.get('media', {}).get('__typename') == "Video":
                    continue
                if 'all_subattachments' in attachment:
                    nodes = attachment['all_subattachments'].get('nodes', [])
                    for node in nodes:
                        media = node.get('media', {})
                        if media.get('__typename') == "Video":
                            continue
                        viewer_image = media.get('viewer_image', {})
                        uri = viewer_image.get('uri')
                        if uri:
                            filename = os.path.join(save_dir, os.path.basename(uri.split("?")[0]))
                            if is_valid_image(filename):
                                img = requests.get(uri)
                                with open(filename, "wb") as f:
                                    f.write(img.content)
                                image_paths.append(filename)
                elif 'media' in attachment:
                    media = attachment['media']
                    if media.get('__typename') == "Video":
                        continue
                    uri = media.get('photo_image', {}).get('uri')
                    if uri:
                        filename = os.path.join(save_dir, os.path.basename(uri.split("?")[0]))
                        if is_valid_image(filename):
                            img = requests.get(uri)
                            with open(filename, "wb") as f:
                                f.write(img.content)
                            image_paths.append(filename)
            except Exception as e:
                print("Không lấy được ảnh:", e)
        return image_paths

    @staticmethod
    def _get_reaction_id(page_url: str) -> dict:
            headers = Requester._get_headers(page_url)
            homepage_response = Requester._get_homepage(page_url, headers)

            entryPoint = Parser._parse_entryPoint(homepage_response)
            identifier = Parser._parse_identifier(entryPoint, homepage_response)
            post_api = Parser._parse_docid(entryPoint, homepage_response)           
            
            logger.debug(f"EntryPoint: {entryPoint}")
            logger.debug(f"PageID: {identifier}")
            logger.debug(f"PostAPI: {post_api}")

            time_range, _ = Utils.init_requests_variables()
            logger.debug(f"TimeRange: {time_range}")

            resp = Requester._get_posts(headers, time_range, identifier, entryPoint, post_api)
            jsons = Parser.parse_jsons(resp)

            reaction_ids = {}

            for json in jsons:
                try:
                    resources = json['extensions']['sr_payload']['ddd']['jsmods']['define']  
                    for define in resources:
                        if define[0] == 'DynamicUFIReactionTypes':
                            reaction_ids = define[2]
                except Exception as e:
                    pass

            if reaction_ids:
                logger.debug("Lấy reaction_ids thành công")  
            else:
                logger.warning("Lấy reaction_ids thất bại")

            save_path = './api_info/reaction_ids.json'
            Utils.write_json(save_path, reaction_ids)

            return reaction_ids
    
    @staticmethod
    def parse_total_reactions(comment_edge: dict) -> int:
        try: 
            total_reactions = comment_edge['node']['feedback']['reactors']['count_reduced']
            logger.debug("Lấy total reactions thành công")
            return int(total_reactions)
        except Exception as e:
            logger.warning("Lấy total reactions thất bại")
            return None

    @staticmethod
    def parse_detail_reactions(comment_edge: dict, reaction_id_info: dict) -> int:
        try:
            reaction_detail = dict()
            reaction_edges = comment_edge['node']['feedback']['top_reactions']['edges']

            for edge in reaction_edges:
                logger.debug(edge)
                id_reaction = edge.get('node', {}) \
                                    .get('id', None)
                count_reaction = edge.get('reaction_count', None)
                
                logger.debug(f"ID reaction và count reaction --{id_reaction}:{count_reaction}--")
                if id_reaction and count_reaction:
                    logger.debug(f"Tìm thấy id reaction và count reaction {id_reaction}:{count_reaction}")
                else:
                    logger.warning("Không tìm thấy id reaction và count reaction")
            
                name_reaction = reaction_id_info.get("reactions") \
                                                    .get(str(id_reaction)) \
                                                    .get("name", None)
                if name_reaction:
                    logger.debug(f"Tìm thấy tên reaction --{name_reaction}--")
                    reaction_detail[name_reaction] = count_reaction
                else:
                    logger.warning("Không tìm thấy tên reaction")
            
            logger.debug("Lấy detail reactions thành công")
            return reaction_detail
        except Exception as e:
            logger.warning("Lấy detail reactions thất bại")
            return {}

    @staticmethod
    def parse_reaction_comments_info(comment_edge: dict, reaction_id_info: dict) -> dict:
        logger.debug("Tiến hành lấy thông tin comment")
        reactions_info = dict()
        reactions_info['total'] = Parser.parse_total_reactions(comment_edge)
        reactions_info['detail'] = Parser.parse_detail_reactions(comment_edge, reaction_id_info)
        return reactions_info

    @staticmethod
    def scraper_depth1_comments(headers: dict, feedback_id: str, expansion_token: str,
                    reaction_id_info: dict, cmt_api_path: str = "./api_info/comment_api.json",
                    max_comment: int = 50) -> None:
        try: 
            logger.debug(f"{"-" * 10} Thực hiện lấy DEPTH01 COMMENT: {"-" * 10}")
            logger.debug(f"Post ID: {feedback_id}")
            logger.debug(f"Expansion Token {expansion_token}")

            cmt_api = Utils.load_json(cmt_api_path)
            logger.debug(f"API Get Comment {cmt_api}") 

            # Lấy api get comment gốc và gửi request
            depth1_comment_api = cmt_api['Depth1CommentsListPaginationQuery']

            comment_info = list()

            page_info = {
                'has_next_page': True,
                'end_cursor': ""
            }
            iter = 0
            max_iter = Utils.n_comment2n_iter(max_comment)
            while page_info['has_next_page'] and iter < max_iter:
                logger.debug(f"{'-' * 20} DEPTH01 COMMENT ITER {iter} {'-' * 20}")
                end_cursor = page_info['end_cursor']
                resp = Requester._get_comments_depth1(headers, comment_id=feedback_id, expansion_token=expansion_token, get_comment_api=depth1_comment_api, end_cursor=end_cursor)
                resp_jsons = Parser.parse_jsons(resp)
                data_json = resp_jsons[0]
                comments = Parser.parse_depth1_comments(data_json, reaction_id_info=reaction_id_info)
                page_info = Parser.parse_depth1_comment_page_info(resp)

                comment_info += list(comments)

                iter += 1
                
            for idx, comment in enumerate(comment_info):
                logger.debug(f"Comment {idx}:")
                logger.debug(f"Text: {comment['text']}")
                logger.debug(f"Image: {comment['image']}")
                logger.debug(f"\n")

            logger.debug(f"{"-" * 10} Lấy DEPTH01 COMMENT thành công {"-" * 10}")                
            return comment_info
        except Exception as e:
            logger.error(f"Lỗi khi lấy comment {e}")
            raise Exception(f"Lỗi khi lấy comment {e}")


    @staticmethod
    def parse_comments(resp_json: dict, headers: dict, reaction_id_info: dict, save_dir: str = "data\\image") -> list:
        edges = resp_json['data']['node']['comment_rendering_instance_for_feed_location']['comments']['edges']

        comments = []
        for edge in edges:
            comment = {
                'text': "",
                'image': None,
                'reactions': {}
            }
            try:
                comment['text'] = edge['node']['body']['text']
            except Exception as e:
                logger.warning("Không tìm thấy text trong comment") 
            
            try:
                attachments = edge['node'].get('attachments', [])
                if attachments:
                    att = attachments[-1]
                    img_info = att['style_type_renderer']['attachment']['media']['image']
                    uri = img_info.get('uri')
                    if uri:
                        filename = os.path.join(save_dir, os.path.basename(uri.split("?")[0]))
                        if is_valid_image(filename):
                            img = requests.get(uri)
                            with open(filename, "wb") as f:
                                f.write(img.content)
                            comment['image'] = filename
            except Exception as e:
                logger.warning("Không lấy được ảnh trong comment")

            try:
                comment['reactions'] = Parser.parse_reaction_comments_info(edge, reaction_id_info)
            except Exception as e:
                logger.warning("Không lấy được reactions trong comment")
            
            feedback_info = dict()
        # try:
            feedback_info['total_count'] = edge['node']['feedback']['replies_fields']['total_count']
            feedback_info['id'] = edge['node']['feedback']['id']
            feedback_info['expansion_token'] = edge['node']['feedback']['expansion_info']['expansion_token']
            feedback_info['comments'] = Parser.scraper_depth1_comments(headers=headers, feedback_id=feedback_info['id'], expansion_token=feedback_info['expansion_token'], \
                                                                        reaction_id_info=reaction_id_info)
            logger.debug(f"Lấy FEEDBACK_INFO cho parent comment thành công")
        # except Exception as e:
            # logger.warning(f"Không lấy được FEEDBACK_INFO cho parent comment {e}")
        # finally:
            comment['feedback_info'] = feedback_info

            comments.append(comment)

        return comments

    @staticmethod
    def parse_comments_info(resp: requests.Response, headers: dict, reaction_id_info: dict, save_dir="data\\image") -> dict:
        resp_json = resp.json()
        comments_info = dict()
        comments_info['total_comment'] = Parser.parse_total_cmt(resp_json)
        comments_info['total_parent_comment'] = Parser.parse_total_parent_cmt(resp_json)
        comments_info['comments'] = Parser.parse_comments(resp_json, headers, reaction_id_info, save_dir=save_dir)
        return comments_info

    @staticmethod
    def parse_page_info(resp: requests.Response) -> str:
        resp_json = resp.json()
        page_info = resp_json['data']['node']['comment_rendering_instance_for_feed_location']['comments']['page_info']

        return page_info
    @staticmethod
    def parse_depth1_comment_page_info(resp: requests.Response) -> str:
        resp_json = Parser.parse_jsons(resp)[0]
        page_info = resp_json['data']['node']['replies_connection']['page_info']
        return page_info
    
    @staticmethod
    def parse_depth1_comments(resp_json: dict, reaction_id_info: dict, save_dir: str = "data\\image") -> list:
        logger.debug(f"Tiến hành parse DEPTH1 COMMENT")
        edges = resp_json['data']['node']['replies_connection']['edges']

        comments = []
        for idx, edge in enumerate(edges):
            logger.debug(f"Tiến hành parse edge thứ {idx+1}")
            comment = {
                'text': "",
                'image': None,
                'reactions': {}
            }
            try:
                comment['text'] = edge['node']['body']['text']
            except Exception as e:
                logger.warning("Không tìm thấy text trong comment") 
            
            try:
                attachments = edge['node'].get('attachments', [])
                if attachments:
                    att = attachments[-1]
                    img_info = att['style_type_renderer']['attachment']['media']['image']
                    uri = img_info.get('uri')
                    if uri:
                        filename = os.path.join(save_dir, os.path.basename(uri.split("?")[0]))
                        if is_valid_image(filename):
                            img = requests.get(uri)
                            with open(filename, "wb") as f:
                                f.write(img.content)
                            comment['image'] = filename
            except Exception as e:
                logger.warning("Không lấy được ảnh trong comment")

            try:
                comment['reactions'] = Parser.parse_reaction_comments_info(edge, reaction_id_info)
            except Exception as e:
                logger.warning("Không lấy được reactions trong comment")
            
            feedback_info = dict()
            try:
                feedback_info['total_count'] = edge['node']['feedback']['replies_fields']['total_count']
                feedback_info['id'] = edge['node']['feedback']['id']
                feedback_info['expansion_token'] = edge['node']['feedback']['expansion_info']['expansion_token']
                comment['feedback_info'] = feedback_info
                logger.debug(f"Lấy FEEDBACK_INFO cho parent comment thành công")
            except Exception as e:
                logger.warning(f"Không lấy được FEEDBACK_INFO cho parent comment {e}")

            comments.append(comment)

        return comments
    
    
    @staticmethod
    def extract_message_and_attachments(obj):
        message = ""
        attachments = []
        try:
            if 'label' not in obj:
                node = obj['data']['node']['timeline_list_feed_units']['edges'][0]['node']
                # print(node)
            else:
                node = obj['data']['node']
                # print(node)
            if 'label' not in obj:
                message = node['comet_sections']['content']['story']['comet_sections']['message']['story']['message']['text'].strip()
                attachments = node['comet_sections']['content']['story'].get('attachments', [])
            else:
                message = node['comet_sections']['content']['story']['comet_sections']['message']['story']['message']['text'].strip()
                attachments = node['comet_sections']['content']['story'].get('attachments', [])
        except Exception as e:
            logger.warning(f"Không lấy được text: {e}")
            attachments = []
        message = message.replace('\n', ' ').replace('\r', ' ')
        message = message.split('Theo:')[0].split('Nguồn:')[0].split('Cre:')[0].strip()
        return message, attachments
    
    @staticmethod
    def extract_post_url(obj):
        try:
            if 'label' not in obj:
                node = obj['data']['node']['timeline_list_feed_units']['edges'][0]['node']
            else:
                node = obj['data']['node']
            story = node['comet_sections']['content']['story']
            post_url = story.get("wwwURL", None)
            return post_url
        except Exception as e:
            logger.warning(f"Không lấy được post url: {e}")
            return None

    @staticmethod
    def extract_comment_count(obj):
        try:
            if 'label' not in obj:
                node = obj['data']['node']['timeline_list_feed_units']['edges'][0]['node']
            else:
                node = obj['data']['node']
            comment_count = node.get('comet_sections', {}) \
                .get('feedback', {}) \
                .get('story', {}) \
                .get('story_ufi_container', {}) \
                .get('story', {}) \
                .get('feedback_context', {}) \
                .get('feedback_target_with_context', {}) \
                .get('comment_list_renderer', {}) \
                .get('feedback', {}) \
                .get('comment_rendering_instance', {}) \
                .get('comments', {}) \
                .get('total_count', 0)
            return comment_count
        except Exception as e:
            logger.warning(f"Không lấy được comment count: {e}")
            return 0

    @staticmethod
    def extract_share_count(obj):
        try:
            if 'label' not in obj:
                node = obj['data']['node']['timeline_list_feed_units']['edges'][0]['node']
            else:
                node = obj['data']['node']
            feedback_ctx = node.get('comet_sections', {}) \
                .get('feedback', {}) \
                .get('story', {}) \
                .get('story_ufi_container', {}) \
                .get('story', {}) \
                .get('feedback_context', {}) \
                .get('feedback_target_with_context', {})
            
            summary = feedback_ctx.get('comet_ufi_summary_and_actions_renderer', {})
            feedback = summary.get('feedback', {})
            share_count = feedback.get('i18n_share_count', None)
            return share_count
        except Exception as e:
            logger.warning(f"Không lấy được share count: {e}")
            return None

    @staticmethod
    def extract_reactions(obj):
        total_reactions = 0
        reactions_detail = {}

        try:
            if 'label' not in obj:
                node = obj['data']['node']['timeline_list_feed_units']['edges'][0]['node']
            else:
                node = obj['data']['node']

            feedback_ctx = node.get('comet_sections', {}) \
                .get('feedback', {}) \
                .get('story', {}) \
                .get('story_ufi_container', {}) \
                .get('story', {}) \
                .get('feedback_context', {}) \
                .get('feedback_target_with_context', {})
            
            summary = feedback_ctx.get('comet_ufi_summary_and_actions_renderer', {})
            feedback = summary.get('feedback', {})
            total_reactions = feedback.get('reaction_count', {}).get('count', 0)
            top_reactions = feedback.get('top_reactions', {}).get('edges', [])
            
            for react in top_reactions:
                node_react = react.get('node', {})
                name = node_react.get('localized_name', 'Unknown')
                count = react.get('reaction_count', 0)
                reactions_detail[name] = count
                
        except Exception as e:
            logger.warning(f"Không lấy được reactions: {e}")
        return total_reactions, reactions_detail

    @staticmethod
    def extract_feedback_id(obj):
        try:
            if 'label' not in obj:
                node = obj['data']['node']['timeline_list_feed_units']['edges'][0]['node']
            else:
                node = obj['data']['node']
            feedback = node.get('feedback', {})
            feedback_id = feedback.get('id', None)
            return feedback_id
        except Exception as e:
            logger.warning(f"Không lấy được feedback id: {e}")
            return None

    @staticmethod
    def extract_creation_time(obj):
        try:
            if 'label' not in obj:
                node = obj['data']['node']['timeline_list_feed_units']['edges'][0]['node']['comet_sections']
            else:
                node = obj['data']['node']['comet_sections']
            timestamp = node.get('timestamp', {})
            story = timestamp.get('story', {})
            creation_time = story.get('creation_time', None)
            return creation_time
        except Exception as e:
            logger.warning(f"Không lấy được creation_time: {e}")
            return None

    @staticmethod
    def parse_post_obj(obj, save_dir="data\\image"):
        post_url = Parser.extract_post_url(obj)

        if post_url == None:
            logger.warning("Không tìm thấy Post")
            return {}
        
        logger.debug(f"Tìm Post thành công {post_url}")

        message, attachments = Parser.extract_message_and_attachments(obj)
        total_reactions, reactions_detail = Parser.extract_reactions(obj)
        page_info_found = True
        feedback_id = Parser.extract_feedback_id(obj)
        creation_time = Parser.extract_creation_time(obj)
        share_count = Parser.extract_share_count(obj)
        comment_count = Parser.extract_comment_count(obj)
        image_paths = Parser.download_images_from_attachments(attachments, save_dir)

        return {
            "post_content": message,
            "image_paths": image_paths,
            "feedback_id": feedback_id,
            "creation_time": creation_time,
            "total_reactions": total_reactions,
            "reactions_detail": reactions_detail,
            "share_count": share_count,
            "comment_count": comment_count,
            "post_url": post_url
        }
    
    @staticmethod 
    def parse_post_page_info(jsons: list[dict]) -> dict:
        page_info = {}
        for idx, json in enumerate(jsons):
            announce = f"Tìm kiếm PageInfo ở json thứ {idx + 1}"
            try:
                new_page_info = json['data']['page_info']
                page_info = new_page_info
                logger.warning(announce + " - " + "Tìm thấy PageInfo")
            except Exception as e:
                logger.warning(announce + " - " + "Không tìm thấy PageInfo") 

        if page_info == {}:
            logger.warning("Lấy PageInfo không thành công")
        else:
            logger.debug("Lấy PageInfo thành công")
        
        return page_info


    @staticmethod
    def parse_jsons(resp: requests.Response) -> dict:
        return [json.loads(d) for d in resp.text.split('\r\n', -1) if d.strip()]        

    @staticmethod
    def _parse_docid(entryPoint: str, homepage_response: requests.Response):
        soup = BeautifulSoup(homepage_response.text, 'lxml')
        if entryPoint == 'nojs':
            docid = 'NoDocid'
        else:
            for link in soup.findAll('link', {'rel': 'preload'}):
                resp = requests.get(link['href'])
                for line in resp.text.split('\n', -1):
                    if 'ProfileCometTimelineFeedRefetchQuery_' in line:
                        docid = re.findall('e.exports="([0-9]{1,})"', line)[0]
                        break

                    if 'CometModernPageFeedPaginationQuery_' in line:
                        docid = re.findall('e.exports="([0-9]{1,})"', line)[0]
                        break

                    if 'CometUFICommentsProviderQuery_' in line:
                        docid = re.findall('e.exports="([0-9]{1,})"', line)[0]
                        break

                    if 'GroupsCometFeedRegularStoriesPaginationQuery' in line:
                        docid = re.findall('e.exports="([0-9]{1,})"', line)[0]
                        break
                if 'docid' in locals():
                    break
        return docid
    
    @staticmethod
    def _parse_entryPoint(homepage_response: requests.Response):
        try:
            entryPoint = re.findall(
                '"entryPoint":{"__dr":"(.*?)"}}', homepage_response.text)[0]
        except:
            entryPoint = 'nojs'
        
        logger.debug(f"Lấy entryPoint thành công")
        return entryPoint

    @staticmethod
    def _parse_identifier(entryPoint: str, homepage_response: requests.Response):
        identifier = None
        if entryPoint in ['ProfilePlusCometLoggedOutRouteRoot.entrypoint', 'CometGroupDiscussionRoot.entrypoint']:
            # pattern 1
            if len(re.findall('"identifier":"{0,1}([0-9]{5,})"{0,1},', homepage_response.text)) >= 1:
                identifier = re.findall(
                    '"identifier":"{0,1}([0-9]{5,})"{0,1},', homepage_response.text)[0]

            # pattern 2
            elif len(re.findall('fb://profile/(.*?)"', homepage_response.text)) >= 1:
                identifier = re.findall(
                    'fb://profile/(.*?)"', homepage_response.text)[0]

            # pattern 3
            elif len(re.findall('content="fb://group/([0-9]{1,})" />', homepage_response.text)) >= 1:
                identifier = re.findall(
                    'content="fb://group/([0-9]{1,})" />', homepage_response.text)[0]

        elif entryPoint in ['CometSinglePageHomeRoot.entrypoint', 'nojs']:
            # pattern 1
            if len(re.findall('"pageID":"{0,1}([0-9]{5,})"{0,1},', homepage_response.text)) >= 1:
                identifier = re.findall(
                    '"pageID":"{0,1}([0-9]{5,})"{0,1},', homepage_response.text)[0]

        if identifier:
            logger.debug(f"Lấy PageID thành công")
        else:
            logger.warning(f"Lấy PageId thất bại")
        
        return identifier

        