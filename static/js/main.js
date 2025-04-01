document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Quiz timer functionality
    const quizTimerElement = document.getElementById('quiz-timer');
    if (quizTimerElement) {
        let timeLeft = parseInt(quizTimerElement.dataset.timeLimit) * 60; // Convert to seconds
        const quizId = quizTimerElement.dataset.quizId;
        const attemptId = quizTimerElement.dataset.attemptId;

        const timerInterval = setInterval(function() {
            timeLeft--;
            const minutes = Math.floor(timeLeft / 60);
            const seconds = timeLeft % 60;
            
            quizTimerElement.textContent = `${minutes}:${seconds < 10 ? '0' : ''}${seconds}`;
            
            if (timeLeft <= 300) { // 5 minutes left
                quizTimerElement.classList.add('text-danger');
                quizTimerElement.classList.add('fw-bold');
            }
            
            if (timeLeft <= 0) {
                clearInterval(timerInterval);
                document.getElementById('quiz-form').submit();
                alert('Time is up! Your quiz has been submitted.');
            }
        }, 1000);
    }

    // Confirmation modals
    const confirmActionButtons = document.querySelectorAll('[data-confirm]');
    confirmActionButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm(this.dataset.confirm)) {
                e.preventDefault();
            }
        });
    });

    // Dynamic form fields for quiz questions
    const questionTypeSelect = document.getElementById('question_type');
    if (questionTypeSelect) {
        const optionsContainer = document.getElementById('options-container');
        
        questionTypeSelect.addEventListener('change', function() {
            if (this.value === 'multiple_choice') {
                optionsContainer.classList.remove('d-none');
            } else if (this.value === 'true_false') {
                optionsContainer.classList.add('d-none');
                // Create true/false options automatically
            }
        });
        
        // Initialize based on current selection
        if (questionTypeSelect.value === 'multiple_choice') {
            optionsContainer.classList.remove('d-none');
        } else {
            optionsContainer.classList.add('d-none');
        }
    }

    // Add option button for quiz questions
    const addOptionBtn = document.getElementById('add-option-btn');
    if (addOptionBtn) {
        const optionsContainer = document.getElementById('options-container');
        let optionCount = document.querySelectorAll('.option-row').length;
        
        addOptionBtn.addEventListener('click', function(e) {
            e.preventDefault();
            optionCount++;
            
            const optionRow = document.createElement('div');
            optionRow.className = 'option-row mb-3 row';
            
            optionRow.innerHTML = `
                <div class="col-md-8">
                    <input type="text" name="option_text_${optionCount}" class="form-control" placeholder="Option ${optionCount}" required>
                </div>
                <div class="col-md-3">
                    <div class="form-check mt-2">
                        <input class="form-check-input" type="radio" name="correct_option" value="${optionCount}" id="option${optionCount}">
                        <label class="form-check-label" for="option${optionCount}">Correct</label>
                    </div>
                </div>
                <div class="col-md-1">
                    <button type="button" class="btn btn-danger btn-sm remove-option"><i class="fas fa-times"></i></button>
                </div>
            `;
            
            optionsContainer.appendChild(optionRow);
            
            // Add event listener to the new remove button
            optionRow.querySelector('.remove-option').addEventListener('click', function() {
                optionRow.remove();
            });
        });
    }

    // Handle file uploads with progress indication
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(input => {
        input.addEventListener('change', function() {
            const fileName = this.files[0]?.name;
            if (fileName) {
                const fileNameDisplay = this.nextElementSibling;
                if (fileNameDisplay) {
                    fileNameDisplay.textContent = fileName;
                }
            }
        });
    });

    // Toggle password visibility
    const togglePasswordButtons = document.querySelectorAll('.toggle-password');
    togglePasswordButtons.forEach(button => {
        button.addEventListener('click', function() {
            const passwordField = document.querySelector(this.dataset.target);
            const type = passwordField.getAttribute('type') === 'password' ? 'text' : 'password';
            passwordField.setAttribute('type', type);
            
            // Toggle icon
            const icon = this.querySelector('i');
            if (type === 'text') {
                icon.classList.remove('fa-eye');
                icon.classList.add('fa-eye-slash');
            } else {
                icon.classList.remove('fa-eye-slash');
                icon.classList.add('fa-eye');
            }
        });
    });

    // Search functionality
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.addEventListener('keyup', function() {
            const searchTerm = this.value.toLowerCase();
            const searchableItems = document.querySelectorAll('[data-searchable]');
            
            searchableItems.forEach(item => {
                const searchableText = item.dataset.searchable.toLowerCase();
                if (searchableText.includes(searchTerm)) {
                    item.style.display = '';
                } else {
                    item.style.display = 'none';
                }
            });
        });
    }
});
