const conversationId = null;
let isProcessing = false;

// Atualiza o status inicial
updateStatus();

async function sendMessage() {
    if (isProcessing) return;

    const input = document.getElementById('userInput');
    const sendButton = document.getElementById('sendButton');
    const message = input.value.trim();
    
    if (!message) return;

    isProcessing = true;
    sendButton.disabled = true;
    sendButton.innerHTML = '<div class="loading"></div>';

    appendMessage(message, 'user-message');
    input.value = '';

    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                conversation_id: conversationId,
                message: message
            })
        });

        const data = await response.json();

        if (data && data.answer) {
            appendMessage(data.answer, 'bot-message');
            updateCoffeeStatus(message);
            updateLastActivity();
            updateStatus();
        }
    } catch (error) {
        console.error('Erro ao enviar mensagem:', error);
        appendMessage('Desculpe, ocorreu um erro ao processar sua mensagem.', 'bot-message');
    } finally {
        isProcessing = false;
        sendButton.disabled = false;
        sendButton.textContent = 'Enviar';
    }
}

function appendMessage(content, className) {
    const messagesContainer = document.getElementById('messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${className}`;
    messageDiv.textContent = content;
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function updateCoffeeStatus(message) {
    const statusIndicator = document.getElementById('coffee-status');
    const statusText = document.getElementById('coffee-status-text');
    
    if (message.toLowerCase().includes('ligar')) {
        statusIndicator.className = 'status-indicator status-online';
        statusText.textContent = 'Cafeteira: Ligada';
    } else if (message.toLowerCase().includes('desligar')) {
        statusIndicator.className = 'status-indicator status-offline';
        statusText.textContent = 'Cafeteira: Desligada';
    }
}

async function updateStatus() {
    try {
        const response = await fetch('/status');
        const data = await response.json();
        if (data) {
            document.getElementById('lastActivity').textContent = 
                `Última Atividade: ${data.last_activity}`;
        }
    } catch (error) {
        console.error('Erro ao atualizar status:', error);
    }
}

// Adiciona listener para enviar mensagem com Enter
document.getElementById('userInput').addEventListener('keypress', function(e) {
    if (e.key === 'Enter' && !isProcessing) {
        sendMessage();
    }
});