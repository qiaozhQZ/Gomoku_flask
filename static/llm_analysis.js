// LLM Analysis Sidebar JavaScript
let conversationHistory = [];

$(document).ready(function() {
    // Initialize sidebar functionality
    initializeSidebar();
});

function initializeSidebar() {
    // Explain move button click handler
    $('#explain-move-btn').click(function() {
        // Disable button to prevent multiple clicks
        $(this).prop('disabled', true);
        
        // Show loading state
        $(this).text('Analyzing...');
        
        // Get current move data
        $.ajax({
            type: "POST",
            url: '/analyze_move',
            data: JSON.stringify({}),
            contentType: 'application/json',
            success: function(response) {
                showSidebar(response.analysis, response.score);
                conversationHistory = []; // Reset conversation
            },
            error: function(xhr, status, error) {
                console.error('Error analyzing move:', error);
                alert('Error analyzing move. Please try again.');
            },
            complete: function() {
                // Re-enable button
                $('#explain-move-btn').prop('disabled', false).text('Explain This Move');
            }
        });
    });

    // Close sidebar button
    $('#close-sidebar').click(function() {
        closeSidebar();
    });

    // Send message button
    $('#send-message').click(function() {
        sendMessage();
    });

    // Enter key in input field
    $('#user-input').keypress(function(e) {
        if (e.which === 13) { // Enter key
            sendMessage();
        }
    });
}

function showSidebar(analysis, score) {
    // Update score display
    $('#current-score').text(score.toFixed(2));
    
    // Show sidebar
    $('#analysis-sidebar').removeClass('hidden').addClass('open');
    
    // Clear previous messages
    $('#chat-messages').empty();
    
    // Add initial analysis message
    addMessage('assistant', analysis);
}

function closeSidebar() {
    $('#analysis-sidebar').removeClass('open').addClass('hidden');
    conversationHistory = [];
}

function sendMessage() {
    const message = $('#user-input').val().trim();
    if (message === '') return;
    
    // Add user message to chat
    addMessage('user', message);
    
    // Clear input
    $('#user-input').val('');
    
    // Disable send button and show loading
    $('#send-message').prop('disabled', true).text('Sending...');
    
    // Send to LLM
    $.ajax({
        type: "POST",
        url: '/chat_with_llm',
        data: JSON.stringify({
            message: message,
            conversation: conversationHistory
        }),
        contentType: 'application/json',
        success: function(response) {
            addMessage('assistant', response.response);
        },
        error: function(xhr, status, error) {
            console.error('Error chatting with LLM:', error);
            addMessage('assistant', 'Sorry, I encountered an error. Please try again.');
        },
        complete: function() {
            // Re-enable send button
            $('#send-message').prop('disabled', false).text('Send');
        }
    });
}

function addMessage(sender, message) {
    const formattedMessage = formatLLMResponse(message);
    const messageDiv = $('<div class="chat-message ' + sender + '-message">' + 
                        formattedMessage + '</div>');
    $('#chat-messages').append(messageDiv);
    
    // Scroll to bottom
    $('#chat-messages').scrollTop($('#chat-messages')[0].scrollHeight);
    
    // Store in conversation history
    if (sender === 'user') {
        conversationHistory.push({user: message, assistant: ''});
    } else {
        if (conversationHistory.length > 0) {
            conversationHistory[conversationHistory.length - 1].assistant = message;
        }
    }
}

function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, function(m) { return map[m]; });
}

function formatLLMResponse(text) {
    // First escape HTML to prevent XSS
    let formatted = escapeHtml(text);
    
    // Convert markdown headings (### Heading -> <h3>Heading</h3>)
    // Handle H1-H6 (1-6 hash symbols)
    formatted = formatted.replace(/^######\s+(.+)$/gm, '<h6>$1</h6>');
    formatted = formatted.replace(/^#####\s+(.+)$/gm, '<h5>$1</h5>');
    formatted = formatted.replace(/^####\s+(.+)$/gm, '<h4>$1</h4>');
    formatted = formatted.replace(/^###\s+(.+)$/gm, '<h3>$1</h3>');
    formatted = formatted.replace(/^##\s+(.+)$/gm, '<h2>$1</h2>');
    formatted = formatted.replace(/^#\s+(.+)$/gm, '<h1>$1</h1>');
    
    // Convert line breaks to <br> tags (but not after headings)
    formatted = formatted.replace(/\n/g, '<br>');
    
    // Convert **bold** to <strong>bold</strong> (do this first)
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Convert *italic* to <em>italic</em> (single asterisks, avoiding conflicts with bold)
    // This matches single asterisks that have non-asterisk content between them
    formatted = formatted.replace(/\*([^*\n]+?)\*/g, '<em>$1</em>');
    
    // Convert numbered lists (1. item)
    formatted = formatted.replace(/^(\d+)\.\s+(.+)$/gm, '<li><strong>$1.</strong> $2</li>');
    
    // Wrap consecutive list items in <ol>
    formatted = formatted.replace(/(<li>.*<\/li>)(\s*<li>.*<\/li>)*/g, function(match) {
        return '<ol>' + match + '</ol>';
    });
    
    // Convert bullet points (- item or • item)
    formatted = formatted.replace(/^[-•]\s+(.+)$/gm, '<li>$1</li>');
    
    // Wrap consecutive bullet points in <ul>
    formatted = formatted.replace(/(<li>.*<\/li>)(\s*<li>.*<\/li>)*/g, function(match) {
        return '<ul>' + match + '</ul>';
    });
    
    return formatted;
}
