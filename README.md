# Facebook Scraper
Facebook Scraper là một công cụ mạnh mẽ được phát triển để thu thập các dữ liệu quan trọng từ các bài đăng trên Facebook. Với công cụ này, bạn có thể dễ dàng thu thập các thông tin như bình luận, hình ảnh, số lượng tương tác và nội dung của bài đăng từ các trang Facebook công khai.

## Tính năng
Thu thập Bình luận: Tự động thu thập tất cả các bình luận từ một bài đăng Facebook.

Thu thập Hình ảnh: Lấy tất cả hình ảnh có trong bài đăng hoặc trong phần bình luận (nếu có).

Số lượng Tương tác: Trích xuất số lượng lượt thích, chia sẻ và bình luận của bài đăng.

Nội dung Bài đăng: Lấy toàn bộ nội dung bài viết, bao gồm văn bản, liên kết và các thông tin bổ sung.

## Cài đặt
Clone repository:


```bash
git clone https://github.com/hoivd/facebook_scraper.git
cd facebook_scraper
```
Yêu Cầu
Python 3.13.5

Các thư viện Python cần thiết: requests, beautifulsoup4, pandas, v.v.

Cài đặt các thư viện cần thiết:

```bash
python -m venv venv 
./venv/Scripts/activate
pip install -r requirements.txt
```

## Sử dụng
1. Cấu hình API thông qua api_info.json
Trước khi chạy, bạn cần cấu hình thông tin API (cookie hoặc token) để truy cập vào dữ liệu của Facebook.

Tạo file api_info/comment_api.json với nội dung bằng cách (liên hệ Vĩnh Hội):

```json
{
    "CommentListComponentsRootQuery": "24269275729371154",
    "CommentsListComponentsPaginationQuery": "9994312660685367",
    "Depth1CommentsListPaginationQuery": "30292744670339145"
}
```

Tạo file api_info/post_api.json với nội dung bằng cách (liên hệ Vĩnh Hội):

```json
{
    "ProfileCometTimelineFeedRefetchQuery": "10043084549111090"
}
```

2. Chạy Scraper
Chạy script chính để thu thập các bài post trên trang facebook:

```bash
python app.py
```

Code mẫu:
```python
scraper = FacebookScraper()

fanpage_url = "https://www.facebook.com/groups/1605994656091242/"
before_time = "2025-8-20"
ranking = Ranking.MOST_RELEVANT
scraper.crawl_post(fanpage_url, max_post=200, ranking_comment=ranking, before_time=before_time)
```

Các tính năng của hàm:
- ranking_comment: Lựa chọn comment theo tất cả, liên quan nhất hoặc mới nhất
- before_time: crawl post trước mốc thời gian này
- after_time: crawl post sau thời gian này
- max_post: số lượng post thu thập max

Dữ liệu thu thập sẽ được lưu trong thư mục data/ dưới dạng các file JSONL và hình ảnh.

## Cấu trúc Thư mục
```text
facebook_scraper/
├── api_info/
│   ├── api_info.json          # Thông tin cấu hình API
├── data/
│   ├── images/                # Lưu hình ảnh thu thập được
│   ├── comments.json          # Dữ liệu bình luận
│   ├── post_data.json         # Dữ liệu bài đăng
├── app.py                     # Script chính thực hiện việc thu thập dữ liệu
├── parser.py                  # Parser response sau khi request được (parser post và comment response)    
├── requester.py               # Request dữ liệu post comment từ API
├── requirements.txt           # Danh sách các thư viện cần thiết
└── README.md                  # Tài liệu hướng dẫn sử dụng
```

Cảnh Báo
Việc thu thập dữ liệu từ Facebook phải tuân thủ các quy định và chính sách của Facebook.

Hãy đảm bảo rằng bạn chỉ sử dụng công cụ này cho mục đích hợp pháp và không vi phạm quyền riêng tư của người khác.