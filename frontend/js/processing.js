import { getReport } from './api.js';

const feedback = document.getElementById('processing-feedback');
const steps = Array.from(document.querySelectorAll('.checklist-item'));
const failureOverlay = document.getElementById('failure-overlay');
const failureMessage = document.getElementById('failure-message');
const homeButton = document.getElementById('failure-home-btn');

function getPollingController() {
  if (!window.__portfolioPollingController) {
    window.__portfolioPollingController = {
      intervalId: null,
      timeoutId: null,
      activeReportId: null,
      token: 0,
    };
  }
  return window.__portfolioPollingController;
}

function clearPollingHandles() {
  const controller = getPollingController();
  if (controller.intervalId !== null && controller.intervalId !== undefined) {
    clearInterval(controller.intervalId);
  }
  if (controller.timeoutId !== null && controller.timeoutId !== undefined) {
    clearTimeout(controller.timeoutId);
  }
  controller.intervalId = null;
  controller.timeoutId = null;
  controller.activeReportId = null;
  controller.token += 1;
  window.__portfolioPollingIntervalId = null;
  return controller.token;
}

function setFeedback(message, isError = false) {
  feedback.textContent = message;
  feedback.style.color = isError ? '#f16c6c' : 'var(--muted)';
}

function stopPolling() {
  clearPollingHandles();
}

function updateSteps(status) {
  steps.forEach((step, index) => {
    step.classList.remove('active', 'done');
    if (status === 'completed') {
      step.classList.add('done');
    } else if (index === 0) {
      step.classList.add('active');
    }
  });
}

function showFailureModal(errorMessage) {
  console.trace("showFailureModal was called from here:");
  clearPollingHandles();
  const message = errorMessage || 'Processing failed. Please try again.';
  setFeedback(`Processing failed: ${message}`, true);
  if (failureMessage) {
    failureMessage.textContent = message;
  }
  if (failureOverlay) {
    failureOverlay.removeAttribute('hidden');
    failureOverlay.style.display = 'grid';
  }
  sessionStorage.removeItem('report_id');
  if (homeButton) {
    homeButton.addEventListener('click', redirectToHome);
  }
}

function redirectToHome() {
  clearPollingHandles();
  sessionStorage.removeItem('report_id');
  window.location.href = 'index.html';
}

window.addEventListener('beforeunload', clearPollingHandles);
window.addEventListener('pagehide', clearPollingHandles);

async function pollStatus(reportId, sessionToken) {
  const controller = getPollingController();

  // Guard clause: stop instantly if this polling session is outdated
  if (controller.token !== sessionToken) {
    return null;
  }

  try {
    const report = await getReport(reportId);
    
    // Safety check again after the network request finishes
    if (controller.token !== sessionToken) {
      return null;
    }

    // Handle missing or broken response structures safely
    if (!report || typeof report.status !== 'string') {
      setFeedback('Waiting for report generation...');
      return { status: 'pending' }; 
    }

    // Evaluate the live status from the server
    switch (report.status) {
      case 'completed':
        clearPollingHandles();
        window.location.href = 'report.html';
        return report;

      case 'failed':
        // The moment it transitions to failed, trigger the modal and stop the loop
        //clearPollingHandles(); 
        showFailureModal(report.error || 'Portfolio processing failed.');
        return report;

      case 'processing':
      case 'pending':
      default:
        // Keep updating the UI progress bar/steps while it processes
        updateSteps(report.status);
        setFeedback('Still analyzing your portfolio. This may take a moment.');
        return report;
    }
  } catch (error) {
    console.error('Polling error:', error);
    setFeedback('Unable to reach the server. Retrying...', true);
    // Return a temporary state so a single network hiccup doesn't crash the script
    return { status: 'processing' }; 
  }
}

function startPolling(reportId) {
  const controller = getPollingController();
  
  // 1. Reset everything, increment token, and ensure overlay is hidden initially
  const sessionToken = clearPollingHandles();
  controller.activeReportId = reportId;
  
  if (failureOverlay) {
    failureOverlay.hidden = true;
  }
  
  setFeedback('Connecting to the portfolio report service...');
  updateSteps('processing');

  // 2. Fire the absolute first check immediately
  pollStatus(reportId, sessionToken).then((initialReport) => {
    const activeController = getPollingController();
    
    // Guard against race conditions
    if (activeController.token !== sessionToken) return;

    // If it immediately ended on step 1 (completed/failed), don't start a timer
    if (initialReport && (initialReport.status === 'completed' || initialReport.status === 'failed')) {
      return;
    }

    // 3. Setup the continuous background loop every 3 seconds
    activeController.intervalId = window.setInterval(async () => {
      const liveController = getPollingController();
      if (liveController.token !== sessionToken) return;

      const currentReport = await pollStatus(reportId, sessionToken);
      
      // If the background check returns a terminal state, destroy the interval timer
      if (currentReport && (currentReport.status === 'completed' || currentReport.status === 'failed')) {
        clearInterval(activeController.intervalId);
      }
    }, 3000);

    window.__portfolioPollingIntervalId = activeController.intervalId;
  });
}

if (homeButton) {
  homeButton.addEventListener('click', (event) => {
    event.preventDefault();
    redirectToHome();
  });
}

(function initializePolling() {
  if (failureOverlay) {
  failureOverlay.style.setProperty('display', 'none', 'important');
}
  const reportId = sessionStorage.getItem('report_id');
  if (!reportId) {
    setFeedback('Report ID is missing. Please upload again.', true);
    return;
  }
  startPolling(reportId);
})();
