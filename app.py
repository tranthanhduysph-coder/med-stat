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

# --- NỘI DUNG KHÓA HỌC (ĐÃ SỬA LỖI ĐƯỜNG DẪN) ---
COURSE_MODULES = {
    "module1-3": {
        "title": "Module 1-3: Nền tảng NCKH",
        "download_url": "/static/downloads/Chương 1 - 3.pdf",
        "chapters": {
            "1": { "id": "1", "title": "Chương 1: Tổng quan về NCKH", "video_url": "https://www.youtube.com/embed/placeholder", "content_file": "chapter_1.html" },
            "2": { "id": "2", "title": "Chương 2: Đặt vấn đề, Mục tiêu, Giả thuyết", "video_url": "https://www.youtube.com/embed/placeholder", "content_file": "chapter_2.html" },
            "3": { "id": "3", "title": "Chương 3: Thiết kế NCKH & Cỡ mẫu", "video_url": "https://www.youtube.com/embed/placeholder", "content_file": "chapter_3.html" }
        }
    },
    "module4-6": {
        "title": "Module 4-6: Thu thập, Xử lý, Báo cáo",
        "download_url": "/static/downloads/Chương 4-6.pdf",
        "chapters": {
            "4": { "id": "4", "title": "Chương 4: Biến số & Thu thập Số liệu", "video_url": "https://www.youtube.com/embed/placeholder", "content_file": "chapter_4.html" },
            "5": { "id": "5", "title": "Chương 5: Phân tích & Trình bày Số liệu", "video_url": "https://www.youtube.com/embed/placeholder", "content_file": "chapter_5.html" },
            "6": { "id": "6", "title": "Chương 6: Viết Báo cáo NCKH (IMRAD)", "video_url": "https://www.youtube.com/embed/placeholder", "content_file": "chapter_6.html" }
        }
    },
    "module7-11": {
        "title": "Module 7-11: Lab Thực hành SPSS",
        "download_url": "/static/downloads/Chương 7-8.pdf",
        "chapters": {
            "7_8": { "id": "7_8", "title": "Chương 7 & 8: Nhập và Làm sạch Dữ liệu", "video_url": "https://www.youtube.com/embed/placeholder", "content_file": "chapter_7_8.html" },
            "9": { "id": "9", "title": "Chương 9: Tính toán & Xử lý Số liệu", "video_url": "https://www.youtube.com/embed/placeholder", "content_file": "chapter_9.html" },
            "10_11": { "id": "10_11", "title": "Chương 10 & 11: Thống kê & Kiểm định", "video_url": "https://www.youtube.com/embed/placeholder", "content_file": "chapter_10_11.html" }
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
    
    try:
        response = requests.post(request_url, headers=headers, data=json.dumps(payload), timeout=120)
        
        if response.status_code == 200:
            result = response.json()
            if "candidates" not in result or not result["candidates"]:
                if result.get("promptFeedback", {}).get("blockReason"):
                    return {"error": f"Yêu cầu bị chặn: {result['promptFeedback']['blockReason']}"}, 400
                raise Exception("Phản hồi API không hợp lệ: Thiếu 'candidates'.")
            
            candidate = result.get("candidates", [{}])[0]
            
            if "content" not in candidate or "parts" not in candidate["content"]:
                finish_reason = candidate.get("finishReason", "UNKNOWN")
                if finish_reason == "SAFETY":
                    return {"error": "Phản hồi bị chặn vì lý do an toàn. Vui lòng điều chỉnh prompt của bạn."}, 400
                raise Exception("Phản hồi API không hợp lệ: Thiếu 'content' hoặc 'parts'.")

            content_part = candidate.get("content", {}).get("parts", [{}])[0]
            content = content_part.get("text")
            
            if content is None:
                raise Exception("Phản hồi API không hợp lệ: Không có nội dung text.")

            sources = []
            grounding_metadata = candidate.get("groundingMetadata", {})
            if grounding_metadata and "groundingAttributions" in grounding_metadata:
                sources = [
                    {"uri": attr["web"]["uri"], "title": attr["web"]["title"]}
                    for attr in grounding_metadata.get("groundingAttributions", [])
                    if attr.get("web")
                ]
            
            if json_schema:
                return {"data": json.loads(content)}, 200
            else:
                return {"text": content, "sources": sources}, 200
        else:
            return {"error": f"Lỗi API: {response.status_code}. {response.text}"}, response.status_code
    except requests.exceptions.RequestException as e:
        return {"error": f"Lỗi kết nối: {e}"}, 500
    except json.JSONDecodeError as e:
        return {"error": f"Lỗi xử lý JSON: {e}"}, 500
    except Exception as e:
        return {"error": f"Lỗi không mong muốn: {e}"}, 500

# --- CÁC ROUTE (TRANG) ---
@app.route("/")
def home():
    return render_template("index.html", modules=COURSE_MODULES)

@app.route("/chapter/<string:chapter_id>")
def chapter(chapter_id):
    chapter_content = None
    module_download_url = None
    for module_key, module_data in COURSE_MODULES.items():
        if chapter_id in module_data["chapters"]:
            chapter_content = module_data["chapters"][chapter_id]
            module_download_url = module_data.get("download_url")
            break
    if chapter_content:
        return render_template("chapter.html", content=chapter_content, download_url=module_download_url)
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
    return render_template("ethics.html")

# --- CÁC API ENDPOINT (LOGIC AI) ---
@app.route("/api/quiz", methods=["POST"])
def api_quiz():
    data = request.json
    chapter_id = data.get("chapterId", "1") 
    chapter_title = "chung"
    for module in COURSE_MODULES.values():
        if chapter_id in module["chapters"]:
            chapter_title = module["chapters"][chapter_id]["title"]
            break
    system_prompt = f"Bạn là chuyên gia về giáo trình NCKH Y học của ThS. Trần Thanh Duy. Chỉ dựa vào kiến thức trong chương: \"{chapter_title}\". Tạo 20 câu hỏi trắc nghiệm (A, B, C, D) và chỉ 1 đáp án đúng. Cung cấp giải thích ngắn. Tuân thủ JSON schema."
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
            }, "required": ["question", "options", "correct_answer_index", "explanation"]
        }
    }
    response, status_code = _call_gemini_api(user_query, system_prompt, json_schema=QUIZ_SCHEMA)
    return jsonify(response), status_code

# --- API MỚI CHO BÀI TẬP VẬN DỤNG ---
@app.route("/api/practice_exercise", methods=["POST"])
def api_practice_exercise():
    data = request.json
    action = data.get("action")
    chapter_id = data.get("chapterId", "1")
    
    chapter_title = "chung"
    for module in COURSE_MODULES.values():
        if chapter_id in module["chapters"]:
            chapter_title = module["chapters"][chapter_id]["title"]
            break

    if action == "get_problem":
        # AI tạo đề bài (dùng JSON Mode)
        system_prompt = f"Bạn là giảng viên Thống kê Y học (Chương 10, 11). Hãy tạo một bài tập VẬN DỤNG duy nhất về chủ đề '{chapter_title}'. Bài tập phải đa dạng. Cung cấp một tình huống lâm sàng ngắn gọn, một bộ dữ liệu mô phỏng (khoảng 5-10 đối tượng, đủ để chạy kiểm định), và một câu hỏi yêu cầu sinh viên diễn giải kết quả (ví dụ: p-value, kết luận H0/H1, diễn giải lâm sàng). Tuân thủ JSON schema."
        user_query = f"Tạo một bài tập vận dụng SPSS về {chapter_title}."
        
        PROBLEM_SCHEMA = {
            "type": "OBJECT",
            "properties": {
                "tinh_huong": { "type": "STRING" },
                "du_lieu_mo_phong": { "type": "STRING" },
                "cau_hoi": { "type": "STRING" },
                "dap_an_mau": { "type": "STRING" }
            },
            "required": ["tinh_huong", "du_lieu_mo_phong", "cau_hoi", "dap_an_mau"]
        }
        
        response, status_code = _call_gemini_api(user_query, system_prompt, json_schema=PROBLEM_SCHEMA)
        return jsonify(response), status_code

    elif action == "submit_feedback":
        # AI chấm bài và sửa lỗi
        problem = data.get("problem", {})
        user_answer = data.get("user_answer", "")
        
        system_prompt = f"Bạn là giảng viên SPSS (Chương 10, 11). Một sinh viên đang làm bài tập về '{chapter_title}'. Dưới đây là đề bài, đáp án đúng (để bạn tham khảo), và câu trả lời của sinh viên. Hãy nhận xét, sửa lỗi, và hướng dẫn họ. Trả lời trực tiếp, thân thiện, và tập trung vào việc giúp họ hiểu tại sao họ đúng hoặc sai (ví dụ: 'Bạn kết luận đúng rồi, vì p < 0.05...')."
        user_query = f"""
        Đề bài:
        - Tình huống: {problem.get('tinh_huong')}
        - Dữ liệu: {problem.get('du_lieu_mo_phong')}
        - Câu hỏi: {problem.get('cau_hoi')}
        - Đáp án mẫu (để bạn tham khảo): {problem.get('dap_an_mau')}

        Câu trả lời của sinh viên:
        "{user_answer}"
        
        Hãy đưa ra phản hồi của bạn.
        """
        
        response, status_code = _call_gemini_api(user_query, system_prompt)
        return jsonify(response), status_code
    
    return jsonify({"error": "Hành động không hợp lệ"}), 400
# --- KẾT THÚC API MỚI ---

@app.route("/api/proposal", methods=["POST"])
def api_proposal():
    data = request.json
    step = data.get("step")
    context = data.get("context", {})
    system_prompt = "Bạn là cố vấn NCKH, chuyên sâu về giáo trình 11 chương của ThS. Trần Thanh Duy. Giúp sinh viên phát triển đề cương."
    user_query = ""
    use_grounding = False 
    if step == 'proposal-title':
        user_query = f"Gợi ý 3 tên đề tài (Title) chuẩn khoa học (Chương 2). \nNgữ cảnh: {context.get('problem', '')}"
    elif step == 'proposal-problem':
        user_query = f"Tinh chỉnh 'Đặt vấn đề' sau theo cấu trúc 3 đoạn (Bối cảnh, Khoảng trống, Tính cấp thiết) (Chương 2): \"{context.get('problem', '')}\""
    elif step == 'proposal-lit-review':
        user_query = f"Cho đề tài: \"{context.get('title', 'chưa có')}\", dùng Google Search tìm và tóm tắt 3-5 nghiên cứu liên quan (Tổng quan tài liệu)."
        use_grounding = True 
    elif step == 'proposal-general':
         user_query = f"Từ 'Đặt vấn đề' sau: \"{context.get('problem', '')}\", gợi ý 1 'Mục tiêu tổng quát' (Chương 2)."
    elif step == 'proposal-specific':
         user_query = f"Từ 'Mục tiêu tổng quát' sau: \"{context.get('general', '')}\", gợi ý 2-3 'Mục tiêu cụ thể' (SMART, Chương 2)."
    elif step == 'proposal-methods':
         user_query = f"Cho mục tiêu: \"{context.get('general', '')}\", gợi ý 'Đối tượng và Phương pháp Nghiên cứu' (Chương 3, 4): Thiết kế, Đối tượng, Tiêu chuẩn chọn/loại trừ."
    elif step == 'proposal-variables':
         user_query = f"Dựa trên các mục tiêu: \"{context.get('general', '')}\" và \"{context.get('specific', '')}\", hãy giúp tôi xác định các 'Biến số nghiên cứu' chính (dựa trên Chương 4). Phân loại rõ biến độc lập, biến phụ thuộc, và các biến số thông tin chung."
    elif step == 'proposal-sample':
        user_query = f"Cho thiết kế nghiên cứu: \"{context.get('methods', '')}\", gợi ý 'Công thức tính cỡ mẫu' và 'Phương pháp chọn mẫu' (Chương 3)."
    elif step == 'proposal-analysis':
        user_query = f"Dựa trên 'Mục tiêu cụ thể': \"{context.get('specific', '')}\", gợi ý các 'Phép phân tích thống kê' tương ứng (Chương 5, 11)."
    elif step == 'proposal-ethics':
        user_query = "Gợi ý các nội dung cơ bản cho phần 'Đạo đức Nghiên cứu' (Chương 6)."
    elif step == 'proposal-references':
        user_query = f"Cho đề tài: \"{context.get('title', 'chưa có')}\", dùng Google Search tìm 3 tài liệu tham khảo và định dạng theo chuẩn Vancouver."
        use_grounding = True 
    else:
        return jsonify({"error": "Bước không hợp lệ"}), 400
    response, status_code = _call_gemini_api(user_query, system_prompt, use_grounding=use_grounding)
    return jsonify(response), status_code

@app.route("/api/advisor", methods=["POST"])
def api_advisor():
    data = request.json
    user_query = f"Tôi muốn {data.get('goal')}, so sánh {data.get('groups')}. Biến kết quả là {data.get('varType')} và có phân phối {data.get('dist')}. Tôi nên dùng phép kiểm định nào?"
    system_prompt = "Bạn là chuyên gia Thống kê Y học (Chương 11, Bảng 11.1). Đưa ra tên phép kiểm định (ví dụ: Independent t-test, Chi-square), giải thích tại sao, và nêu đường dẫn menu SPSS."
    response, status_code = _call_gemini_api(user_query, system_prompt)
    return jsonify(response), status_code

@app.route("/api/grader", methods=["POST"])
def api_grader():
    data = request.json
    user_query = f"Đây là phần \"{data.get('section')}\" của tôi. Hãy góp ý:\n\n\"{data.get('text')}\""
    system_prompt = "Bạn là nhà phản biện khoa học (Chương 6, IMRAD). Đọc đoạn văn và đưa ra 3 Góp ý Xây dựng: (1) Điểm tốt, (2) Điểm cần cải thiện, và (3) Các mục còn thiếu."
    response, status_code = _call_gemini_api(user_query, system_prompt)
    return jsonify(response), status_code

@app.route("/api/scenario", methods=["POST"])
def api_scenario():
    user_query = "Tạo một tình huống (scenario) nghiên cứu y học thực tế, ngắn gọn (2-3 câu). Tình huống này cần có một vấn đề chưa rõ ràng để sinh viên xác định thiết kế nghiên cứu (Chương 3) hoặc phương pháp thu thập (Chương 4)."
    system_prompt = "Bạn là giảng viên thống kê y học. Hãy tạo ra các tình huống NCKH thú vị dựa trên giáo trình 11 chương."
    response, status_code = _call_gemini_api(user_query, system_prompt)
    return jsonify(response), status_code

@app.route("/api/assistant", methods=["POST"])
def api_assistant():
    data = request.json
    user_query = data.get("query")
    system_prompt = "Bạn là Trợ lý AI, đào tạo dựa trên giáo trình 11 chương NCKH & Thống kê Y học của ThS. Trần Thanh Duy. Chỉ trả lời dựa trên kiến thức từ giáo trình này. Dùng Google Search để tra cứu các khái niệm trong giáo trình và trả lời chính xác, trích dẫn nguồn (nếu có)."
    response, status_code = _call_gemini_api(user_query, system_prompt, use_grounding=True)
    return jsonify(response), status_code

@app.route("/api/ethics_chat", methods=["POST"])
def api_ethics_chat():
    data = request.json
    user_query = data.get("query")
    system_prompt = "Bạn là chuyên gia về Đạo đức Nghiên cứu Y học. Chỉ trả lời câu hỏi liên quan đến Tuyên ngôn Helsinki, Báo cáo Belmont, và CIOMS. Dùng Google Search để tra cứu thêm. Nếu người dùng hỏi về thống kê (p-value, t-test) hay SPSS, hãy lịch sự từ chối và gợi ý họ dùng trang 'Công cụ AI' hoặc 'Trợ lý AI'."
    response, status_code = _call_gemini_api(user_query, system_prompt, use_grounding=True)
    return jsonify(response), status_code

# --- KHỞI CHẠY SERVER ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # TẮT debug=False khi deploy chính thức
    app.run(host="0.0.0.0", port=port, debug=True)