document.addEventListener('DOMContentLoaded', () => {

    const loadingSpinner = document.getElementById('loading-spinner');

    async function fetchFromBackend(endpoint, body) {
        loadingSpinner.style.display = 'block';
        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(body)
            });

            const responseData = await response.json();
            if (!response.ok) {
                throw new Error(responseData.error || `Lỗi Server: ${response.status}`);
            }
            return responseData;

        } catch (error) {
            console.error(`Lỗi khi gọi ${endpoint}:`, error);
            alert(`Lỗi: ${error.message}`);
            return { error: error.message };
        } finally {
            loadingSpinner.style.display = 'none';
        }
    }

    function formatAIResponse(text) {
        if (!text) return "";
        let safeText = text.replace(/[&<>"']/g, function(m) {
            return {
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#39;'
            }[m];
        });

        return safeText
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/^### (.*$)/gm, '<h3 class="text-xl font-semibold mt-4 mb-2">$1</h3>')
            .replace(/^## (.*$)/gm, '<h2 class="text-2xl font-bold mt-6 mb-3">$1</h2>')
            .replace(/^- (.*$)/gm, '<ul class="list-disc list-inside mb-4"><li>$1</li></ul>')
            .replace(/^(\d+)\. (.*$)/gm, '<ol class="list-decimal list-inside mb-4"><li>$2</li></ol>')
            .replace(/\n/g, '<br>')
            .replace(/<\/ul><br><ul>/g, '')
            .replace(/<\/ol><br><ol>/g, '');
    }

    function displayAIResponse(targetElement, text, sources = []) {
        if (!targetElement) return;
        let html = formatAIResponse(text);

        if (sources && sources.length > 0) {
            html += '<div class="citation">';
            html += '<strong>Nguồn tham khảo (từ Google Search):</strong><ul>';
            sources.forEach(source => {
                html += `<li><a href="${source.uri}" target="_blank" rel="noopener noreferrer">${source.title}</a></li>`;
            });
            html += '</ul></div>';
        }
        
        targetElement.innerHTML = html;
        targetElement.style.display = 'block';
    }

    function escapeHTML(str) {
        if (!str) return "";
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

    const disclaimerModal = document.getElementById('disclaimer-modal');
    const openBtn = document.getElementById('open-disclaimer-btn');
    const closeBtn = document.getElementById('close-disclaimer-btn');

    if (disclaimerModal && openBtn && closeBtn) {
        openBtn.addEventListener('click', () => disclaimerModal.classList.remove('hidden'));
        closeBtn.addEventListener('click', () => disclaimerModal.classList.add('hidden'));
        disclaimerModal.addEventListener('click', (e) => {
            if (e.target === disclaimerModal) {
                disclaimerModal.classList.add('hidden');
            }
        });
    }

    const quizModal = document.getElementById('quiz-modal');
    if (quizModal) {
        const quizBody = document.getElementById('quiz-body');
        const startBtn = document.getElementById('start-quiz-btn');
        const startBtnBottom = document.getElementById('start-quiz-btn-bottom'); // SỬA LỖI ID TRÙNG
        const closeQuizBtn = document.getElementById('close-quiz-btn');
        const submitBtn = document.getElementById('submit-quiz-btn');
        const retakeBtn = document.getElementById('retake-quiz-btn');
        
        const quizLoading = document.getElementById('quiz-loading');
        const quizForm = document.getElementById('quiz-form');
        const quizResults = document.getElementById('quiz-results');
        const quizScore = document.getElementById('quiz-score');
        const quizSummary = document.getElementById('quiz-summary');
        const quizReview = document.getElementById('quiz-review');
        
        let quizData = []; 

        function resetQuizModal() {
            if (quizLoading) quizLoading.classList.add('hidden');
            if (quizForm) quizForm.classList.add('hidden');
            if (quizResults) quizResults.classList.add('hidden');
            if (submitBtn) submitBtn.classList.add('hidden');
            if (retakeBtn) retakeBtn.classList.add('hidden');
            
            if (quizForm) quizForm.innerHTML = ''; 
            if (quizReview) quizReview.innerHTML = ''; 
            quizData = [];
        }

        function buildQuizForm(questions) {
            quizData = questions; 
            let formHtml = '';
            
            questions.forEach((q, index) => {
                const optionsHtml = q.options.map((option, i) => `
                    <div class="flex items-center ps-4 border border-gray-200 rounded-lg hover:bg-gray-50">
                        <input id="q${index}_option${i}" type="radio" value="${i}" name="q${index}" class="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 focus:ring-blue-500">
                        <label for="q${index}_option${i}" class="w-full py-3 ms-2 text-sm font-medium text-gray-700">${escapeHTML(option)}</label>
                    </div>
                `).join('');
                
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
        
        function gradeQuiz() {
            const formData = new FormData(quizForm);
            let score = 0;
            let reviewHtml = '';
            let hasWrongAnswers = false;

            quizData.forEach((question, index) => {
                const userAnswer = formData.get(`q${index}`); 
                const correctAnswerIndex = question.correct_answer_index;
                const correctAnswerText = question.options[correctAnswerIndex];

                if (userAnswer !== null && parseInt(userAnswer, 10) === correctAnswerIndex) {
                    score++;
                } else {
                    hasWrongAnswers = true;
                    const userAnswerText = (userAnswer === null) ? "Bạn đã bỏ qua câu này." : `Lựa chọn của bạn: "${escapeHTML(question.options[userAnswer])}"`;
                    
                    reviewHtml += `
                        <div class="p-3 bg-red-50 border border-red-200 rounded-lg">
                            <p class="font-semibold text-red-800">Câu ${index + 1}: ${escapeHTML(q.question)}</p>
                            <p class="text-sm text-gray-700 mt-1">${userAnswerText}</p>
                            <p class="text-sm text-green-700 font-medium mt-1">Đáp án đúng: "${escapeHTML(correctAnswerText)}"</p>
                            <p class="text-sm text-gray-600 mt-1"><em>Giải thích: ${escapeHTML(q.explanation)}</em></p>
                        </div>
                    `;
                }
            });

            if (quizScore) quizScore.textContent = `Kết quả của bạn: ${score} / ${quizData.length}`;
            if (quizSummary) quizSummary.textContent = (score === quizData.length) ? "Tuyệt vời! Bạn đã trả lời đúng tất cả!" : "Hãy xem lại các câu trả lời sai bên dưới.";
            if (quizReview) quizReview.innerHTML = reviewHtml || '<p class="text-center text-green-600">Xin chúc mừng, bạn không sai câu nào!</p>';
            
            if (quizForm) quizForm.classList.add('hidden');
            if (submitBtn) submitBtn.classList.add('hidden');
            if (quizResults) quizResults.classList.remove('hidden');
            if (retakeBtn) retakeBtn.classList.remove('hidden');
            if (quizBody) quizBody.scrollTop = 0;
        }

        // HÀM SỰ KIỆN CHÍNH (ĐÃ SỬA)
        const handleStartQuiz = async (e) => {
            e.preventDefault(); 
            const chapterId = e.currentTarget.dataset.chapterId;
            
            resetQuizModal();
            quizModal.classList.remove('hidden');
            quizLoading.classList.remove('hidden');
            
            try {
                const response = await fetchFromBackend('/api/quiz', { chapterId: chapterId });

                if (response.data && response.data.length > 0) {
                    buildQuizForm(response.data);
                    quizLoading.classList.add('hidden');
                    quizForm.classList.remove('hidden');
                    submitBtn.classList.remove('hidden');
                } else {
                    throw new Error(response.error || 'Không nhận được dữ liệu câu hỏi từ AI.');
                }

            } catch (error) {
                console.error('Lỗi khi gọi API Tự lượng giá:', error);
                quizLoading.innerHTML = `<p class="text-red-600 text-center">Lỗi: ${error.message}</p>`;
            }
        };

        if (startBtn) {
            startBtn.addEventListener('click', handleStartQuiz); // Gắn sự kiện cho nút đầu
        }
        if (startBtnBottom) {
            startBtnBottom.addEventListener('click', handleStartQuiz); // Gắn sự kiện cho nút cuối
        }

        if (closeQuizBtn) {
            closeQuizBtn.addEventListener('click', () => {
                quizModal.classList.add('hidden');
            });
        }
        
        if (submitBtn) {
            submitBtn.addEventListener('click', gradeQuiz);
        }
        
        if (retakeBtn) {
            retakeBtn.addEventListener('click', () => {
                resetQuizModal();
                if (startBtn) startBtn.click();
            });
        }
    }

    const proposalResponseEl = document.getElementById('proposal-ai-response');
    if (proposalResponseEl) {
        document.querySelectorAll('.btn-proposal-ai').forEach(button => {
            button.addEventListener('click', async () => {
                const step = button.dataset.step;
                
                const context = {
                    title: document.getElementById('proposal-title').value,
                    problem: document.getElementById('proposal-problem').value,
                    litReview: document.getElementById('proposal-lit-review').value,
                    general: document.getElementById('proposal-general').value,
                    specific: document.getElementById('proposal-specific').value,
                    methods: document.getElementById('proposal-methods').value,
                    variables: document.getElementById('proposal-variables').value, 
                    sample: document.getElementById('proposal-sample').value,
                    analysis: document.getElementById('proposal-analysis').value,
                    ethics: document.getElementById('proposal-ethics').value,
                    references: document.getElementById('proposal-references').value,
                };

                proposalResponseEl.innerHTML = '<p class="text-gray-500">AI đang suy nghĩ...</p>';
                proposalResponseEl.style.display = 'block';

                const response = await fetchFromBackend('/api/proposal', { step: step, context: context });

                if (response.text) {
                    displayAIResponse(proposalResponseEl, response.text, response.sources);
                } else {
                    displayAIResponse(proposalResponseEl, `<p class="text-red-600">Lỗi: ${response.error}</p>`);
                }
            });
        });

        const printBtn = document.getElementById('print-proposal-btn');
        if (printBtn) {
            printBtn.addEventListener('click', () => {
                window.print();
            });
        }
    }

    const toolTabs = document.querySelectorAll('.tool-tab-button');
    const toolTabContents = document.querySelectorAll('.tool-tab-content');

    if (toolTabs.length > 0) {
        toolTabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const targetTab = tab.dataset.tab;
                toolTabs.forEach(t => { t.classList.remove('tab-active'); t.classList.add('tab-inactive'); });
                tab.classList.add('tab-active'); tab.classList.remove('tab-inactive');
                
                toolTabContents.forEach(content => {
                    content.classList.toggle('active', content.id === targetTab);
                    content.classList.toggle('hidden', content.id !== targetTab);
                });
            });
        });
        
        const firstTabContent = document.querySelector('.tool-tab-content');
        if (firstTabContent) {
            firstTabContent.classList.remove('hidden');
            firstTabContent.classList.add('active');
        }
    
        const btnAdvisor = document.getElementById('btn-run-advisor');
        if (btnAdvisor) {
            btnAdvisor.addEventListener('click', async () => {
                const payload = {
                    goal: document.getElementById('advisor-goal').value,
                    groups: document.getElementById('advisor-groups').value,
                    varType: document.getElementById('advisor-var').value,
                    dist: document.getElementById('advisor-dist').value,
                };
                const responseEl = document.getElementById('advisor-ai-response');

                if (!payload.goal) {
                    responseEl.innerHTML = '<p class="text-red-600">Vui lòng chọn mục tiêu phân tích.</p>';
                    return;
                }
                responseEl.innerHTML = '<p class="text-gray-500">AI đang tra cứu Chương 11...</p>';
                
                const response = await fetchFromBackend('/api/advisor', payload);
                displayAIResponse(responseEl, response.text, response.sources);
            });
        }

        const btnGrader = document.getElementById('btn-run-grader');
        if (btnGrader) {
            btnGrader.addEventListener('click', async () => {
                const payload = {
                    section: document.getElementById('grader-section').value,
                    text: document.getElementById('grader-text').value,
                };
                const responseEl = document.getElementById('grader-ai-response');
                
                if (payload.text.length < 50) {
                    responseEl.innerHTML = '<p class="text-red-600">Vui lòng nhập ít nhất 50 ký tự để AI có thể góp ý.</p>';
                    responseEl.style.display = 'block';
                    return;
                }
                responseEl.innerHTML = '<p class="text-gray-500">AI đang đọc và phản biện...</p>';
                responseEl.style.display = 'block';

                const response = await fetchFromBackend('/api/grader', payload);
                displayAIResponse(responseEl, response.text, response.sources);
            });
        }

        const btnScenario = document.getElementById('btn-run-scenario');
        if (btnScenario) {
            btnScenario.addEventListener('click', async () => {
                const responseEl = document.getElementById('scenario-ai-response');
                responseEl.innerHTML = '<p class="text-gray-500">AI đang xây dựng tình huống...</p>';
                responseEl.style.display = 'block';

                const response = await fetchFromBackend('/api/scenario', {});
                displayAIResponse(responseEl, response.text, response.sources);
            });
        }
    }

    const chatWindow = document.getElementById('chat-window');
    const chatInput = document.getElementById('chat-input');
    const chatSendBtn = document.getElementById('btn-send-chat');

    if (chatWindow) {
        chatSendBtn.addEventListener('click', handleChatSend);
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleChatSend();
            }
        });

        async function handleChatSend() {
            const userQuery = chatInput.value.trim();
            if (userQuery === "") return;

            chatWindow.innerHTML += `
                <div class="flex justify-end">
                    <div class="bg-blue-100 p-4 rounded-lg rounded-br-none shadow-sm max-w-[80%]">
                        <p class="text-sm text-gray-800">${escapeHTML(userQuery)}</p>
                    </div>
                </div>`;
            
            chatInput.value = "";
            chatWindow.scrollTop = chatWindow.scrollHeight;

            chatWindow.innerHTML += `
                <div id="ai-typing" class="flex items-start space-x-3">
                    <div class="flex-shrink-0 w-10 h-10 bg-blue-600 rounded-full flex items-center justify-center">
                        <i class='bx bxs-brain text-2xl text-white'></i>
                    </div>
                    <div class="bg-gray-200 p-4 rounded-lg rounded-tl-none shadow-sm">
                        <p class="text-sm text-gray-500 italic">AI đang suy nghĩ...</p>
                    </div>
                </div>`;
            chatWindow.scrollTop = chatWindow.scrollHeight;

            const response = await fetchFromBackend('/api/assistant', { query: userQuery });

            const typingIndicator = document.getElementById('ai-typing');
            if (typingIndicator) typingIndicator.remove();

            let aiResponseHTML = `
                <div class="flex items-start space-x-3">
                    <div class="flex-shrink-0 w-10 h-10 bg-blue-600 rounded-full flex items-center justify-center">
                        <i class='bx bxs-brain text-2xl text-white'></i>
                    </div>
                    <div class="bg-gray-200 p-4 rounded-lg rounded-tl-none shadow-sm max-w-[80%]">
                        <div class="ai-response text-sm text-gray-800">
                            ${formatAIResponse(response.text || response.error)}
                        </div>`;

            if (response.sources && response.sources.length > 0) {
                aiResponseHTML += '<div class="citation mt-3 pt-2 border-t border-gray-300">';
                aiResponseHTML += '<strong class="text-xs text-gray-600">Nguồn tham khảo (từ Google Search):</strong><ul class="text-xs list-disc pl-4">';
                response.sources.forEach(source => {
                    aiResponseHTML += `<li><a href="${source.uri}" target="_blank" rel="noopener noreferrer" class="text-blue-600 hover:underline">${escapeHTML(source.title)}</a></li>`;
                });
                aiResponseHTML += '</ul></div>';
            }
            
            aiResponseHTML += `</div></div>`;
            chatWindow.innerHTML += aiResponseHTML;
            chatWindow.scrollTop = chatWindow.scrollHeight;
        }
    }
    
    const ethicsChatWindow = document.getElementById('ethics-chat-window');
    const ethicsChatInput = document.getElementById('ethics-chat-input');
    const ethicsChatSendBtn = document.getElementById('btn-send-ethics-chat');
    const ethicsChatForm = document.getElementById('ethics-chat-form');

    if (ethicsChatWindow && ethicsChatForm) {
        
        ethicsChatForm.addEventListener('submit', (e) => {
             e.preventDefault();
             handleEthicsChatSend();
        });

        async function handleEthicsChatSend() {
            const userQuery = ethicsChatInput.value.trim();
            if (userQuery === "") return;

            ethicsChatWindow.innerHTML += `
                <div class="flex justify-end">
                    <div class="bg-blue-100 p-3 rounded-lg rounded-br-none shadow-sm max-w-[80%]">
                        <p class="text-sm text-gray-800">${escapeHTML(userQuery)}</p>
                    </div>
                </div>`;
            
            ethicsChatInput.value = "";
            ethicsChatWindow.scrollTop = ethicsChatWindow.scrollHeight;

            ethicsChatWindow.innerHTML += `
                <div id="ai-ethics-typing" class="flex items-start space-x-3">
                    <div class="flex-shrink-0 w-10 h-10 bg-blue-600 rounded-full flex items-center justify-center">
                        <i class='bx bxs-shield-check text-2xl text-white'></i>
                    </div>
                    <div class="bg-gray-200 p-3 rounded-lg rounded-tl-none shadow-sm">
                        <p class="text-sm text-gray-500 italic">AI đang suy nghĩ...</p>
                    </div>
                </div>`;
            ethicsChatWindow.scrollTop = ethicsChatWindow.scrollHeight;

            const response = await fetchFromBackend('/api/ethics_chat', { query: userQuery });

            const typingIndicator = document.getElementById('ai-ethics-typing');
            if (typingIndicator) typingIndicator.remove();

            let aiResponseHTML = `
                <div class="flex items-start space-x-3">
                    <div class="flex-shrink-0 w-10 h-10 bg-blue-600 rounded-full flex items-center justify-center">
                        <i class='bx bxs-shield-check text-2xl text-white'></i>
                    </div>
                    <div class="bg-gray-200 p-3 rounded-lg rounded-tl-none shadow-sm max-w-[80%]">
                        <div class="ai-response text-sm text-gray-800">
                            ${formatAIResponse(response.text || response.error)}
                        </div>`;

            if (response.sources && response.sources.length > 0) {
                aiResponseHTML += '<div class="citation mt-3 pt-2 border-t border-gray-300">';
                aiResponseHTML += '<strong class="text-xs text-gray-600">Nguồn tham khảo (từ Google Search):</strong><ul class="text-xs list-disc pl-4">';
                response.sources.forEach(source => {
                    aiResponseHTML += `<li><a href="${source.uri}" target="_blank" rel="noopener noreferrer" class="text-blue-600 hover:underline">${escapeHTML(source.title)}</a></li>`;
                });
                aiResponseHTML += '</ul></div>';
            }
            
            aiResponseHTML += `</div></div>`;
            ethicsChatWindow.innerHTML += aiResponseHTML;
            ethicsChatWindow.scrollTop = ethicsChatWindow.scrollHeight;
        }
    }

});