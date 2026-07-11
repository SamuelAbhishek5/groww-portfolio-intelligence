import { getReport, postChatMessage } from './api.js';

const portfolioValueNode = document.getElementById('portfolio-value');
const healthScoreNode = document.getElementById('health-score');
const viewButton = document.getElementById('view-report');
const downloadButton = document.getElementById('download-report');
const feedback = document.getElementById('report-feedback');

const chatForm = document.getElementById('chat-form');
const chatInput = document.getElementById('chat-input');
const chatSendButton = document.getElementById('chat-send');
const chatMessages = document.getElementById('chat-messages');
const chatFeedback = document.getElementById('chat-feedback');

function formatCurrency(value) {
  if (typeof value !== 'number') return '—';
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(value);
}

function setFeedback(message, isError = false) {
  feedback.textContent = message;
  feedback.style.color = isError ? '#f16c6c' : 'var(--muted)';
}

function enableReportActions(pdfUrl) {
  if (!pdfUrl) return;
  viewButton.disabled = false;
  downloadButton.disabled = false;

  viewButton.addEventListener('click', () => {
    window.open(pdfUrl, '_blank');
  });

  downloadButton.addEventListener('click', () => {
    const anchor = document.createElement('a');
    anchor.href = pdfUrl;
    anchor.download = 'Groww-Portfolio-Report.pdf';
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
  });
}

function setChatFeedback(message, isError = false) {
  chatFeedback.textContent = message;
  chatFeedback.style.color = isError ? '#f16c6c' : 'var(--muted)';
}

function appendChatMessage(role, text) {
  const bubble = document.createElement('div');
  bubble.className = `chat-message chat-message-${role}`;

  const paragraph = document.createElement('p');
  paragraph.textContent = text;

  bubble.appendChild(paragraph);
  chatMessages.appendChild(bubble);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function setChatBusy(isBusy) {
  chatInput.disabled = isBusy;
  chatSendButton.disabled = isBusy;
}

function initChat(reportId) {
  chatForm.addEventListener('submit', async (event) => {
    event.preventDefault();

    const query = chatInput.value.trim();
    if (!query) {
      setChatFeedback('Type a question first.', true);
      return;
    }

    if (!reportId) {
      setChatFeedback('No report found. Upload your portfolio again.', true);
      return;
    }

    appendChatMessage('user', query);
    chatInput.value = '';
    setChatBusy(true);
    setChatFeedback('Thinking…');

    try {
      const response = await postChatMessage(reportId, query);
      const answer = response  || 'Sorry, I could not generate a response.';
      console.log("Response:", response);
      appendChatMessage('bot', answer);
      setChatFeedback('');
    } catch (error) {
      setChatFeedback(error.message || 'Unable to get a response. Please try again.', true);
    } finally {
      setChatBusy(false);
      chatInput.focus();
    }
  });
}

(async function loadReport() {
  const reportId = sessionStorage.getItem('report_id');
  initChat(reportId);

  if (!reportId) {
    setFeedback('No report found. Upload your portfolio again.', true);
    return;
  }

  try {
    const report = await getReport(reportId);
    portfolioValueNode.textContent = formatCurrency(report.portfolio_value);
    healthScoreNode.textContent = report.health_score != null ? `${report.health_score}%` : '—';
    enableReportActions(report.pdf_url);
    setFeedback('Your portfolio report is ready. Use the buttons above to view or download.');

  } catch (error) {
    setFeedback(error.message || 'Could not load report details.', true);
  }
})();