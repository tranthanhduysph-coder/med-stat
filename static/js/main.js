// Chờ cho toàn bộ nội dung trang web được tải xong
document.addEventListener('DOMContentLoaded', () => {

    // --- LOGIC CHO PHẦN TỰ LƯỢNG GIÁ (QUIZ) ---
    
    // 1. Lấy các phần tử (element) trong trang chapter.html
    const quizModal = document.getElementById('quiz-modal');
    const quizBody = document.getElementById('quiz-body');
    const startBtn = document.getElementById('start-quiz-btn');
    const closeBtn = document.getElementById('close-quiz-btn');
    const submitBtn = document.getElementById('submit-quiz-btn');
    const retakeBtn = document.getElementById('retake-quiz-btn');
    
    const quizLoading = document.getElementById('quiz-loading');
    const quizForm = document.getElementById('quiz-form');
    const quizResults = document.getElementById('quiz-results');
    const quizScore = document.getElementById('quiz-score');
    const quizSummary = document.getElementById('quiz-summary');
    const quizReview = document.getElementById('quiz-review');
    
    let quizData = []; // Biến để lưu trữ 20 câu hỏi AI trả về

    // 2. Hàm reset modal về trạng thái ban đầu
    function resetQuizModal() {
        quizLoading.classList.add('hidden');
        quizForm.classList.add('hidden');
        quizResults.classList.add('hidden');
        submitBtn.classList.add('hidden');
        retakeBtn.classList.add('hidden');
        
        quizForm.innerHTML = ''; // Xóa câu hỏi cũ
        quizReview.innerHTML = ''; // Xóa phần review cũ
        quizData = [];
    }

    // 3. Hàm xây dựng form quiz từ dữ liệu AI
    function buildQuizForm(questions) {
        quizData = questions; // Lưu lại data để chấm điểm
        let formHtml = '';
        
        questions.forEach((q, index) => {
            // Tạo các lựa chọn (radio button)
            const optionsHtml = q.options.map((option, i) => `
                <div class="flex items-center ps-4 border border-gray-200 rounded-lg hover:bg-gray-50">
                    <input id="q${index}_option${i}" type="radio" value="${i}" name="q${index}" class="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 focus:ring-blue-500">
                    <label for="q${index}_option${i}" class="w-full py-3 ms-2 text-sm font-medium text-gray-700">${escapeHTML(option)}</label>
                </div>
            `).join('');
            
            // Tạo câu hỏi
            formHtml += `
                <fieldset class="border-t pt-4">
                    <legend class="text-md font-semibold text-gray-800 mb-3">(Câu ${index + 1}) ${escapeHTML(q.question)}</legend>
                    <div class="space-y-2">
                        ${optionsHtml}
                    </div>
                </fieldset>
            `;
        });
        
        quizForm.innerHTML = formHtml;
    }
    
    // 4. Hàm chấm điểm
    function gradeQuiz() {
        const formData = new FormData(quizForm);
        let score = 0;
        let reviewHtml = '';

        quizData.forEach((question, index) => {
            const userAnswer = formData.get(`q${index}`); // Lấy câu trả lời của user (dưới dạng index: "0", "1", "2", "3")
            const correctAnswerIndex = question.correct_answer_index;
            const correctAnswerText = question.options[correctAnswerIndex];

            if (userAnswer !== null && parseInt(userAnswer, 10) === correctAnswerIndex) {
                // Nếu trả lời đúng
                score++;
            } else {
                // Nếu trả lời sai hoặc bỏ qua
                const userAnswerText = (userAnswer === null) ? "Bạn đã bỏ qua câu này." : `Lựa chọn của bạn: "${escapeHTML(question.options[userAnswer])}"`;
                
                reviewHtml += `
                    <div class="p-3 bg-red-50 border border-red-200 rounded-lg">
                        <p class="font-semibold text-red-800">Câu ${index + 1}: ${escapeHTML(question.question)}</p>
                        <p class="text-sm text-gray-700 mt-1">${userAnswerText}</p>
                        <p class="text-sm text-green-700 font-medium mt-1">Đáp án đúng: "${escapeHTML(correctAnswerText)}"</p>
                        <p class="text-sm text-gray-600 mt-1"><em>Giải thích: ${escapeHTML(question.explanation)}</em></p>
                    </div>
                `;
            }
        });

        // Hiển thị kết quả
        quizScore.textContent = `Kết quả của bạn: ${score} / ${quizData.length}`;
        quizSummary.textContent = (score === quizData.length) ? "Tuyệt vời! Bạn đã trả lời đúng tất cả!" : "Hãy xem lại các câu trả lời sai bên dưới.";
        quizReview.innerHTML = reviewHtml || '<p class="text-center text-green-600">Xin chúc mừng, bạn không sai câu nào!</p>';
        
        quizForm.classList.add('hidden');
        submitBtn.classList.add('hidden');
        quizResults.classList.remove('hidden');
        retakeBtn.classList.remove('hidden');
    }

    // 5. Gắn sự kiện "click" cho nút "Bắt đầu Tự lượng giá"
    // (Kiểm tra xem nút này có tồn tại không, vì nó chỉ có ở trang chapter.html)
    if (startBtn) {
        startBtn.addEventListener('click', async (e) => {
            e.preventDefault(); // Ngăn hành vi mặc định của nút
            
            const chapterId = startBtn.dataset.chapterId;
            
            // Reset modal về trạng thái sạch
            resetQuizModal();
            // Hiển thị modal và icon loading
            quizModal.classList.remove('hidden');
            quizLoading.classList.remove('hidden');
            
            try {
                // --- ĐÂY LÀ PHẦN GỌI AI (PYTHON) ---
                const response = await fetch('/api/quiz', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ chapterId: chapterId }),
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.error || 'Lỗi khi tạo câu hỏi.');
                }

                const data = await response.json();
                
                if (data.data && data.data.length > 0) {
                    // 6. Xây dựng form quiz
                    buildQuizForm(data.data);
                    
                    // 7. Ẩn loading, hiện form và nút Nộp bài
                    quizLoading.classList.add('hidden');
                    quizForm.classList.remove('hidden');
                    submitBtn.classList.remove('hidden');
                } else {
                    throw new Error('Không nhận được dữ liệu câu hỏi từ AI.');
                }

            } catch (error) {
                console.error('Lỗi khi gọi API Tự lượng giá:', error);
                quizLoading.innerHTML = `<p class="text-red-600">Lỗi: ${error.message}</p>`;
            }
        });
    }

    // 6. Gắn sự kiện cho các nút trong modal
    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            quizModal.classList.add('hidden');
        });
    }
    
    if (submitBtn) {
        submitBtn.addEventListener('click', gradeQuiz);
    }
    
    if (retakeBtn) {
        retakeBtn.addEventListener('click', () => {
            resetQuizModal();
            // Tải lại câu hỏi mới
            startBtn.click();
        });
    }

    // Hàm tiện ích để tránh lỗi XSS (Cross-site scripting)
    function escapeHTML(str) {
        return str.replace(/[&<>"']/g, function(m) {
            return {
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#39;'
            }[m];
        });
    }

    // --- CÁC LOGIC KHÁC CỦA TRANG WEB (VÍ DỤ: PROPOSAL, TOOLS...) ---
    // (Bạn có thể thêm code cho các trang khác vào đây sau)
});

