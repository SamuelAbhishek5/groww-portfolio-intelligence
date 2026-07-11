import { postUpload } from './api.js';

const uploadForm = document.getElementById('upload-form');
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const feedback = document.getElementById('upload-feedback');

let selectedFile = null;

function clearPollingIntervals() {
  const controller = window.__portfolioPollingController || (window.__portfolioPollingController = {
    intervalId: null,
    timeoutId: null,
    activeReportId: null,
    token: 0,
  });
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
}

function getErrorFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const errorValue = params.get('error');
  return errorValue ? decodeURIComponent(errorValue) : '';
}

function setFeedback(message, isError = false) {
  feedback.textContent = message;
  feedback.style.color = isError ? '#f16c6c' : 'var(--muted)';
}

window.addEventListener('beforeunload', clearPollingIntervals);
window.addEventListener('pagehide', clearPollingIntervals);

const initialError = getErrorFromUrl();
if (initialError) {
  window.alert(initialError);
  setFeedback(initialError, true);
}

function isValidFile(file) {
  const acceptedTypes = ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/vnd.ms-excel', 'text/csv'];
  const allowedExtensions = ['.xlsx', '.xls', '.csv'];
  const fileName = file.name.toLowerCase();
  return acceptedTypes.includes(file.type) || allowedExtensions.some(ext => fileName.endsWith(ext));
}

function updateSelectedFile(file) {
  if (!file) {
    selectedFile = null;
    setFeedback('Pick an Excel or CSV file to upload.');
    return;
  }

  if (!isValidFile(file)) {
    selectedFile = null;
    setFeedback('Please select a valid Excel or CSV file.', true);
    return;
  }

  selectedFile = file;
  setFeedback(`Ready to upload ${file.name}`);
}

fileInput.addEventListener('change', (event) => {
  clearPollingIntervals();
  const file = event.target.files[0];
  updateSelectedFile(file);
});

['dragenter', 'dragover'].forEach((eventName) => {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    event.stopPropagation();
    dropZone.classList.add('drag-over');
  });
});

['dragleave', 'drop'].forEach((eventName) => {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    event.stopPropagation();
    if (eventName === 'drop') {
      clearPollingIntervals();
      const file = event.dataTransfer.files[0];
      updateSelectedFile(file);
      fileInput.files = event.dataTransfer.files;
    }
    dropZone.classList.remove('drag-over');
  });
});

uploadForm.addEventListener('submit', async (event) => {
  event.preventDefault();

  clearPollingIntervals();

  if (!selectedFile) {
    setFeedback('No file selected. Please choose a file first.', true);
    return;
  }
  sessionStorage.removeItem('report_id');
  
  setFeedback('Uploading and analyzing your portfolio...');

  const formData = new FormData();
  formData.append('file', selectedFile);

  try {
    const response = await postUpload(formData);
    if (!response.report_id) {
      throw new Error('Upload succeeded but no report ID was returned.');
    }

    sessionStorage.setItem('report_id', response.report_id);
    window.location.href = 'processing.html';
  } catch (error) {
    setFeedback(error.message || 'Upload failed. Try again.', true);
  }
});
