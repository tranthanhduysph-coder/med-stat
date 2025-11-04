import os
import json
import requests
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv 

load_dotenv() 

app = Flask(__name__)

# --- CẤU HÌNH API ---
API_KEY = os.environ.get("GEMINI_API_KEY", "") 
GEMINI_API_URL_BASE = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent"

# --- CẤU TRÚC KHÓA HỌC (ĐÃ TỐI GIẢN) ---
# Toàn bộ nội dung chi tiết đã được chuyển sang thư mục /templates/content/
# File app.py này chỉ quản lý cấu trúc, tên, và các liên kết.
COURSE_MODULES = {
    "module1-3": {
        "title": "Module 1-3: Nền tảng Nghiên cứu Khoa học",
        "download_url": "/static/downloads/Chương 1 - 3.pdf",
        "chapters": {
            "1": { "id": "1", "title": "Chương 1: Tổng quan về NCKH trong Y học", "video_url": "https://www.youtube.com/embed/placeholder" },
            "2": { "id": "2", "title": "Chương 2: Đặt vấn đề, Mục tiêu và Giả thuyết", "video_url": "https://www.youtube.com/embed/placeholder" },
            "3": { "id": "3", "title": "Chương 3: Các thiết kế NCKH và Cỡ mẫu", "video_url": "https://www.youtube.com/embed/placeholder" }
        }
    },
    "module4-6": {
        "title": "Module 4-6: Thu thập, Xử lý và Báo cáo",
        "download_url": "/static/downloads/Chương 4-6.pdf",
        "chapters": {
            "4": { "id": "4", "title": "Chương 4: Biến số và Kỹ thuật Thu thập Số liệu", "video_url": "https://www.youtube.com/embed/placeholder" },
            "5": { "id": "5", "title": "Chương 5: Tổng hợp, Phân tích và Trình bày Số liệu", "video_url": "https://www.youtube.com/embed/placeholder" },
            "6": { "id": "6", "title": "Chương 6: Viết và Trình bày Báo cáo NCKH", "video_url": "https://www.youtube.com/embed/placeholder" }
        }
    },
    "module7-11": {
        "title": "Module 7-11: Lab Thực hành SPSS",
        # Lưu ý: File PDF Chương 7-8.pdf chứa nội dung cho cả 3 chương này
        "download_url": "/static/downloads/Chương 7-8.pdf", 
        "chapters": {
            "7": { "id": "7", "title": "Chương 7 & 8: Nhập và Làm sạch Dữ liệu", "video_url": "https://www.youtube.com/embed/placeholder" },
            "9": { "id": "9", "title": "Chương 9: Tính toán và Xử lý Số liệu", "video_url": "https://www.youtube.com/embed/placeholder" },
            "10": { "id": "10", "title": "Chương 10 & 11: Thống kê Mô tả và Kiểm định", "video_url": "https://www.youtube.com/embed/placeholder" }
        }
    }
}


# --- HÀM GỌI GEMINI (TRUNG TÂM) ---
def _call_gemini_api(user_query, system_instruction, use_grounding=False, json_schema=None):
    if not API_KEY:
        return {"error": "GEMINI_API_KEY chưa được thiết lập trên server."}, 500

    request_url = f"{GEMINI_API_URL_BASE}?key={API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": user_query}]}],
        "systemInstruction": {"parts": [{"text": system_instruction}]},
    }
    if use_grounding:
        payload["tools"] = [{"google_search": {}}]
    if json_schema:
        payload["generationConfig"] = {
            "responseMimeType": "application/json",
            "responseSchema": json_schema
        }
    headers = {"Content-Type": "application/json"}
    
    for _ in range(3): 
        try:
            response = requests.post(request_url, headers=headers, data=json.dumps(payload), timeout=120)
            
            if response.status_code == 200:
                result = response.json()
                candidate = result.get("candidates", [{}])[0]
                content_part = candidate.get("content", {}).get("parts", [{}])[0]
                content = content_part.get("text")
                
                if content is None:
                    if json_schema and "error" in content_part:
                         raise Exception(f"API Error in JSON Mode: {content_part['error']}")
                    else:
                         raise Exception("Invalid API response structure: No content text.")

                sources = []
                grounding_metadata = candidate.get("groundingMetadata", {})
                if grounding_metadata and "groundingAttributions" in grounding_metadata:
                    sources = [
                        {"uri": attr["web"]["uri"], "title": attr["web"]["title"]}
                        for attr in grounding_metadata["groundingAttributions"]
                        if attr.get("web")
                    ]
                
                if json_schema:
                    return {"data": json.loads(content)}, 200
                else:
                    return {"text": content, "sources": sources}, 200
            else:
                print(f"API Error: {response.status_code}, {response.text}")
                if response.status_code >= 500:
                    continue 
                else:
                    return {"error": f"API Error: {response.status_code}. {response.text}"}, response.status_code
        except requests.exceptions.RequestException as e:
            print(f"Request Error: {e}")
            continue 
        except json.JSONDecodeError as e:
            print(f"JSON Parse Error: {e}. Content was: {content}")
            return {"error": "Lỗi xử lý dữ liệu JSON từ AI."}, 500
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return {"error": f"Lỗi không mong muốn: {e}"}, 500
    return {"error": "Không thể kết nối đến AI sau nhiều lần thử."}, 500

# --- CÁC ROUTE (ĐIỀU HƯỚNG TRANG WEB) ---

@app.route("/")
def home():
    return render_template("index.html", modules=COURSE_MODULES)

# === ROUTE ĐÃ NÂNG CẤP ===
@app.route("/chapter/<string:chapter_id>")
def chapter(chapter_id):
    """Trang chi tiết bài học (động)."""
    chapter_data = None
    module_download_url = None
    
    # Logic để xử lý các chương ghép (7, 10)
    content_id = chapter_id
    if chapter_id == "7":
        content_id = "7_8" # Chương 7 dùng chung nội dung file 7_8
    elif chapter_id == "10":
        content_id = "10_11" # Chương 10 dùng chung nội dung file 10_11
    
    # 1. Tìm dữ liệu của chương (tiêu đề, video...)
    for module_key, module_data in COURSE_MODULES.items():
        if chapter_id in module_data["chapters"]:
            chapter_data = module_data["chapters"][chapter_id]
            module_download_url = module_data.get("download_url")
            break
            
    if chapter_data:
        # 2. Tạo đường dẫn đến file nội dung chi tiết
        content_template_path = f"content/chapter_{content_id}.html"
        
        # 3. Render file chapter.html và truyền 2 biến vào nó
        return render_template(
            "chapter.html", 
            chapter_data=chapter_data, 
            download_url=module_download_url,
            content_template_path=content_template_path # Đường dẫn file nội dung
        )
    else:
        return "Không tìm thấy chương", 404

@app.route("/proposal-builder")
def proposal_builder():
    return render_template("proposal.html")

@app.route("/ai-tools")
def ai_tools():
    return render_template("tools.html")

@app.route("/ai-assistant")
def ai_assistant():
    return render_template("assistant.html")

@app.route("/ethics")
def ethics():
    """Trang Đạo đức Nghiên cứu."""
    return render_template("ethics.html")

# --- CÁC API ENDPOINT (ĐỂ JAVASCRIPT GỌI) ---

@app.route("/api/quiz", methods=["POST"])
def api_quiz():
    data = request.json
    chapter_id = data.get("chapterId", "1") 
    
    chapter_title = "chung"
    for module in COURSE_MODULES.values():
        if chapter_id in module["chapters"]:
            chapter_title = module["chapters"][chapter_id]["title"]
            break

    system_prompt = f"""Bạn là một chuyên gia về giáo trình NCKH Y học của ThS.BS. Trần Thanh Duy.
Chỉ dựa vào kiến thức trong chương: "{chapter_title}".
Hãy tạo ra 20 câu hỏi trắc nghiệm ngẫu nhiên, mỗi câu có 4 đáp án (A, B, C, D) và chỉ 1 đáp án đúng.
Cung cấp một giải thích ngắn gọn cho đáp án đúng.
Tuyệt đối tuân thủ JSON schema được cung cấp."""
    user_query = f"Tạo 20 câu hỏi trắc nghiệm cho \"{chapter_title}\"."
    
    QUIZ_SCHEMA = {
        "type": "ARRAY",
        "items": {
            "type": "OBJECT",
            "properties": {
                "question": { "type": "STRING" },
                "options": { "type": "ARRAY", "items": { "type": "STRING" }, "minItems": 4, "maxItems": 4 },
                "correct_answer_index": { "type": "NUMBER" },
                "explanation": { "type": "STRING" }
            },
            "required": ["question", "options", "correct_answer_index", "explanation"]
        }
    }
    
    response, status_code = _call_gemini_api(user_query, system_prompt, json_schema=QUIZ_SCHEMA)
    return jsonify(response), status_code

@app.route("/api/proposal", methods=["POST"])
def api_proposal():
    data = request.json
    step = data.get("step")
    context = data.get("context", {})

    system_prompt = "Bạn là một cố vấn NCKH, chuyên sâu về giáo trình 11 chương của ThS.BS. Trần Thanh Duy. Hãy giúp sinh viên phát triển đề cương."
    user_query = ""
    use_grounding = False 

    if step == 'proposal-title':
        user_query = f"Tôi có ý tưởng về một đề tài (có thể trong phần Đặt vấn đề). Hãy gợi ý 3 tên đề tài (Title) thật chuẩn khoa học (dựa trên Chương 2). \nNgữ cảnh: {context.get('problem', '')}"
    elif step == 'proposal-problem':
        user_query = f"Dựa trên 'Đặt vấn đề' sau: \"{context.get('problem', '')}\", hãy giúp tôi tinh chỉnh lại theo cấu trúc 3 đoạn (Bối cảnh, Khoảng trống, Tính cấp thiết) (dựa trên Chương 2)."
    elif step == 'proposal-lit-review':
        user_query = f"Cho đề tài: \"{context.get('title', 'chưa có')}\", hãy dùng Google Search để tìm và tóm tắt ngắn 3-5 nghiên cứu liên quan (Tổng quan tài liệu), tập trung vào các phát hiện chính và khoảng trống tri thức."
        use_grounding = True 
    elif step == 'proposal-general':
         user_query = f"Từ 'Đặt vấn đề' sau: \"{context.get('problem', '')}\", hãy gợi ý 1 'Mục tiêu tổng quát' (dựa trên Chương 2)."
    elif step == 'proposal-specific':
         user_query = f"Từ 'Mục tiêu tổng quát' sau: \"{context.get('general', '')}\", hãy gợi ý 2-3 'Mục tiêu cụ thể' theo tiêu chí SMART (dựa trên Chương 2)."
    elif step == 'proposal-methods':
         user_query = f"Cho mục tiêu: \"{context.get('general', '')}\", hãy gợi ý chi tiết 'Đối tượng và Phương pháp Nghiên cứu' (dựa trên Chương 3 và 4), bao gồm: \n1. Thiết kế nghiên cứu. \n2. Đối tượng nghiên cứu. \n3. Tiêu chuẩn chọn và loại trừ."
    elif step == 'proposal-sample':
        user_query = f"Cho thiết kế nghiên cứu sau: \"{context.get('methods', '')}\", hãy gợi ý 'Công thức tính cỡ mẫu' phù hợp và 'Phương pháp chọn mẫu' (dựa trên Chương 3)."
    elif step == 'proposal-analysis':
        user_query = f"Dựa trên các 'Mục tiêu cụ thể' sau: \"{context.get('specific', '')}\", hãy gợi ý các 'Phép phân tích thống kê' tương ứng (dựa trên Chương 5 và 11)."
    elif step == 'proposal-ethics':
        user_query = "Hãy gợi ý các nội dung cơ bản cần có trong phần 'Đạo đức Nghiên cứu' cho một đề tài y sinh học (dựa trên Chương 6)."
    elif step == 'proposal-references':
        user_query = f"Cho đề tài: \"{context.get('title', 'chưa có')}\", hãy dùng Google Search để tìm 3 tài liệu tham khảo quan trọng và định dạng chúng theo chuẩn Vancouver."
        use_grounding = True 
    else:
        return jsonify({"error": "Bước không hợp lệ"}), 400
        
    response, status_code = _call_gemini_api(user_query, system_prompt, use_grounding=use_grounding)
    return jsonify(response), status_code

@app.route("/api/advisor", methods=["POST"])
def api_advisor():
    data = request.json
    user_query = f"Tôi muốn {data.get('goal')}, so sánh {data.get('groups')}. Biến kết quả của tôi là {data.get('varType')} và có phân phối {data.get('dist')}. Tôi nên dùng phép kiểm định nào?"
    system_prompt = "Bạn là chuyên gia Thống kê Y học, chỉ dựa vào kiến thức trong Chương 11 (đặc biệt là Bảng 11.1) từ giáo trình. Đưa ra tên phép kiểm định (ví dụ: Independent t-test, Chi-square), giải thích ngắn gọn tại sao, và nêu đường dẫn menu SPSS (ví dụ: Analyze > Compare Means > ...)."
    
    response, status_code = _call_gemini_api(user_query, system_prompt)
    return jsonify(response), status_code

@app.route("/api/grader", methods=["POST"])
def api_grader():
    data = request.json
    user_query = f"Đây là phần \"{data.get('section')}\" trong bài viết của tôi. Hãy góp ý:\n\n\"{data.get('text')}\""
    system_prompt = "Bạn là một nhà phản biện khoa học, chỉ dựa vào kiến thức trong Chương 6 (Viết Báo cáo NCKH) từ giáo trình. Đọc đoạn văn của sinh viên và đưa ra 3 Góp ý Xây dựng: (1) Điểm tốt, (2) Điểm cần cải thiện, và (3) Các mục còn thiếu theo cấu trúc IMRAD chuẩn của Chương 6."
    
    response, status_code = _call_gemini_api(user_query, system_prompt)
    return jsonify(response), status_code

@app.route("/api/scenario", methods=["POST"])
def api_scenario():
    user_query = "Tạo một tình huống (scenario) nghiên cứu y học thực tế, ngắn gọn (khoảng 2-3 câu) dành cho sinh viên. Tình huống này cần có một vấn đề chưa rõ ràng để sinh viên phải xác định thiết kế nghiên cứu (Chương 3) hoặc phương pháp thu thập số liệu (Chương 4)."
    system_prompt = "Bạn là một giảng viên thống kê y học. Hãy tạo ra các tình huống NCKH thú vị và đầy thách thức dựa trên kiến thức trong giáo trình 11 chương."
    
    response, status_code = _call_gemini_api(user_query, system_prompt)
    return jsonify(response), status_code

@app.route("/api/assistant", methods=["POST"])
def api_assistant():
    data = request.json
    user_query = data.get("query")
    system_prompt = "Bạn là Trợ lý AI, được đào tạo dựa trên giáo trình 11 chương về Thống kê Y học và NCKH do ThS.BS. Trần Thanh Duy biên soạn. Chỉ trả lời các câu hỏi dựa trên kiến thức từ giáo trình này. Sử dụng công cụ tìm kiếm (Google Search) để tra cứu các khái niệm trong giáo trình và trả lời một cách chính xác. Luôn cố gắng trích dẫn nguồn (nếu có)."
    
    response, status_code = _call_gemini_api(user_query, system_prompt, use_grounding=True)
    return jsonify(response), status_code

@app.route("/api/ethics_chat", methods=["POST"])
def api_ethics_chat():
    """API Chatbot chuyên biệt về Đạo đức Nghiên cứu."""
    data = request.json
    user_query = data.get("query")
    
    # Prompt này rất quan trọng: nó giới hạn AI chỉ nói về đạo đức
    system_prompt = """Bạn là một chuyên gia về Đạo đức Nghiên cứu Y học. Nhiệm vụ của bạn là chỉ trả lời các câu hỏi liên quan đến các nguyên tắc đạo đức, Tuyên ngôn Helsinki, Báo cáo Belmont, và các hướng dẫn của CIOMS.
    
    Nội dung Tuyên ngôn Helsinki đã được cung cấp trên trang. Bạn có thể sử dụng Google Search để tra cứu thêm thông tin chi tiết về các nguyên tắc đạo đức khác.
    
    Nếu người dùng hỏi về thống kê (p-value, t-test), SPSS, hay cách viết đề cương, hãy lịch sự từ chối và gợi ý họ dùng các trang 'Công cụ AI' hoặc 'Trợ lý AI' chung.
    """
    
    response, status_code = _call_gemini_api(user_query, system_prompt, use_grounding=True)
    return jsonify(response), status_code

# --- KHỞI CHẠY SERVER ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

