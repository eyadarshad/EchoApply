// Secure sync background script
// Backend URL is configurable — defaults to localhost for development
const DEFAULT_BACKEND_URL = "http://localhost:8000";
let BACKEND_URL = `${DEFAULT_BACKEND_URL}/api/auth/extension-sync`;

// List of target platforms and their specific session identifiers
const TARGET_DOMAINS = [
  { domain: "linkedin.com", name: "li_at", platform: "linkedin" },
  { domain: "indeed.com", name: "JSESSIONID", platform: "indeed" },
  { domain: "glassdoor.com", name: "GD_SESSION", platform: "glassdoor" }
];

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "sync_sessions") {
    syncActiveSessions(request.userId).then(result => {
      sendResponse(result);
    });
    return true; // Keep message channel open for async response
  }
});

async function syncActiveSessions(userId) {
  const cookiesList = [];

  for (const target of TARGET_DOMAINS) {
    try {
      const cookies = await chrome.cookies.getAll({ domain: target.domain });
      // Find the session identifying cookies
      const sessionCookies = cookies.filter(c => c.name === target.name || c.name.toLowerCase().includes("session") || c.name.toLowerCase().includes("token"));
      
      sessionCookies.forEach(cookie => {
        cookiesList.push({
          platform: target.platform,
          name: cookie.name,
          value: cookie.value,
          domain: cookie.domain,
          path: cookie.path,
          secure: cookie.secure,
          httpOnly: cookie.httpOnly,
          expirationDate: cookie.expirationDate
        });
      });
    } catch (err) {
      console.error(`Error fetching cookies for ${target.domain}:`, err);
    }
  }

  if (cookiesList.length === 0) {
    return { success: false, message: "No active session cookies found. Please log in to the platforms first." };
  }

  try {
    const response = await fetch(BACKEND_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        user_id: userId,
        cookies: cookiesList
      })
    });
    
    const data = await response.json();
    return { success: response.ok, message: data.message || "Sync completed successfully!" };
  } catch (err) {
    return { success: false, message: `Connection error: ${err.message}` };
  }
}
