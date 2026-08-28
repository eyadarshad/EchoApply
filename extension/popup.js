// Popup handler for Session Sync
document.addEventListener("DOMContentLoaded", () => {
  const userIdInput = document.getElementById("userIdInput");
  const syncBtn = document.getElementById("syncBtn");
  const statusBox = document.getElementById("statusBox");

  // Load saved User ID if present
  chrome.storage.local.get(["userId"], (data) => {
    if (data.userId) {
      userIdInput.value = data.userId;
    }
  });

  syncBtn.addEventListener("click", () => {
    const userId = userIdInput.value.trim();
    if (!userId) {
      showStatus("Please enter your User ID first.", "error");
      return;
    }

    // Save User ID for future sessions
    chrome.storage.local.set({ userId });

    syncBtn.disabled = true;
    showStatus("Connecting to browser service worker...", "success");

    chrome.runtime.sendMessage({ action: "sync_sessions", userId }, (response) => {
      syncBtn.disabled = false;
      if (chrome.runtime.lastError) {
        showStatus(`Extension error: ${chrome.runtime.lastError.message}`, "error");
      } else if (response && response.success) {
        showStatus(response.message, "success");
      } else {
        showStatus(response ? response.message : "Sync aborted.", "error");
      }
    });
  });

  function showStatus(text, type) {
    statusBox.innerText = text;
    statusBox.className = `status ${type}`;
  }
});
