// content.tsx
import React, { useEffect, useState } from "react";
import OverlayGuide from "./overlayGuide";
import type { PlasmoCSConfig } from "plasmo";

// Export Plasmo config to ensure proper injection
export const config: PlasmoCSConfig = {
  matches: ["<all_urls>"],
  all_frames: false
};

// Debug logging
console.log("Content script loaded at:", new Date().toISOString());

/**
 * Utility: given a raw HTML string, try multiple strategies to find a live element:
 *  1) If parsed element has an id and a live element with that id exists -> use it
 *  2) If href exists -> querySelector by href
 *  3) If data-title exists -> querySelector by data-title
 *  4) If exact innerText matches -> use the first matching visible element
 *  5) Otherwise inject the parsed element into a test container and return that injected element
 */
function resolveHtmlStringsToElements(htmlList: string[]) {
  const results: HTMLElement[] = [];
  console.log("🔍 Resolving", htmlList.length, "HTML elements...");
  
  let needsFallback = false;

  htmlList.forEach((html, idx) => {
    console.log(`🔎 Processing element ${idx + 1}:`, html.substring(0, 100) + "...");
    
    // parse into element
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, "text/html");
    const parsed = doc.body.firstElementChild as HTMLElement | null;
    if (!parsed) {
      console.log(`❌ Failed to parse element ${idx + 1}`);
      return;
    }

    // 1) match by id
    const id = parsed.getAttribute("id");
    if (id) {
      const byId = document.getElementById(id);
      if (byId) {
        console.log(`✅ Found element ${idx + 1} by ID: ${id}`);
        results.push(byId);
        return;
      }
    }

    // 2) match by href (or anchor inside)
    const href = parsed.getAttribute("href") ?? parsed.querySelector("a")?.getAttribute("href");
    if (href) {
      try {
        const found = document.querySelector<HTMLElement>(`[href="${CSS.escape ? CSS.escape(href) : href}"]`) || document.querySelector<HTMLElement>(`a[href="${href}"]`);
        if (found) {
          console.log(`✅ Found element ${idx + 1} by href: ${href}`);
          results.push(found);
          return;
        }
      } catch (e) {
        // CSS.escape may not be available in some environments; fall back later
        const fallback = Array.from(document.querySelectorAll("a")).find(a => (a as HTMLAnchorElement).getAttribute("href") === href) as HTMLElement | undefined;
        if (fallback) {
          results.push(fallback);
          return;
        }
      }
    }

    // 3) match by data-title
    const dataTitle = parsed.getAttribute("data-title") ?? parsed.querySelector("[data-title]")?.getAttribute("data-title");
    if (dataTitle) {
      const found = document.querySelector<HTMLElement>(`[data-title="${dataTitle}"]`);
      if (found) {
        results.push(found);
        return;
      }
    }

    // 4) match by partial text content for complex elements
    const elementText = parsed.textContent?.trim();
    if (elementText) {
      // For complex elements, try to find by key text phrases
      const keyPhrases = [
        "Log In",
        "small or personal project", 
        "Start for free"
      ];
      
      for (const phrase of keyPhrases) {
        if (elementText.includes(phrase)) {
          const elements = Array.from(document.querySelectorAll<HTMLElement>("*")).filter(el => {
            const elText = el.textContent?.trim();
            return elText && elText.includes(phrase) && el.offsetParent !== null;
          });
          
          if (elements.length > 0) {
            // For "small or personal project", look for the actual radio button container
            if (phrase === "small or personal project") {
              // Try multiple selectors to find the exact radio button container
              const selectors = [
                'button.MuiBox-root.css-zjvir',  // Exact class from your HTML
                'button[class*="MuiBox-root"]',  // Any button with MuiBox class
                '.css-zjvir',                    // The specific CSS class
                'button:has(.MuiRadio-root)',    // Button containing radio
              ];
              
              for (const selector of selectors) {
                try {
                  const containers = document.querySelectorAll<HTMLElement>(selector);
                  for (const container of containers) {
                    const containerText = container.textContent?.trim();
                    if (containerText && containerText.includes(phrase)) {
                      console.log(`✅ Found element ${idx + 1} by selector "${selector}":`, container.tagName, container.className);
                      results.push(container);
                      return;
                    }
                  }
                } catch (e) {
                  // :has selector might not be supported
                  continue;
                }
              }
              
              // Final fallback
              const bestMatch = elements.find(el => el.tagName === 'BUTTON') || elements[0];
              if (bestMatch) {
                console.log(`✅ Found element ${idx + 1} by phrase "${phrase}" (fallback):`, bestMatch.tagName);
                results.push(bestMatch);
                return;
              }
            }
            
            // Find the most specific element (smallest one that contains the text)
            const bestMatch = elements.reduce((best, current) => {
              const bestText = best.textContent?.trim() || "";
              const currentText = current.textContent?.trim() || "";
              return currentText.length < bestText.length ? current : best;
            });
            console.log(`✅ Found element ${idx + 1} by phrase "${phrase}":`, bestMatch.tagName);
            results.push(bestMatch);
            return;
          }
        }
      }
      
      // Fallback: exact text match
      const all = Array.from(document.querySelectorAll<HTMLElement>("*")).filter(el => {
        const t = el.textContent?.trim();
        return t === elementText && el.offsetParent !== null;
      });
      if (all.length > 0) {
        results.push(all[0]);
        return;
      }
    }

    // 5) Don't create fallback elements - just skip if not found
    console.log(`⚠️ Element ${idx + 1} not found on page, skipping`);
    needsFallback = true;
  });

  return results;
}

// Guide state interface
interface GuideState {
  htmlList: string[];
  currentIndex: number;
  isActive: boolean;
  timestamp: number;
}

// Storage key for guide state
const GUIDE_STATE_KEY = 'clueless_guide_state';

// Check if chrome.storage is available, otherwise use localStorage
const hasChrome = typeof chrome !== 'undefined' && chrome?.storage?.local;

// Log storage method being used
console.log("Storage method:", hasChrome ? "chrome.storage.local" : "localStorage");

// Save guide state to storage
const saveGuideState = async (htmlList: string[], index: number, isActive: boolean) => {
  const state: GuideState = {
    htmlList,
    currentIndex: index,
    isActive,
    timestamp: Date.now()
  };
  
  try {
    if (hasChrome) {
      await chrome.storage.local.set({ [GUIDE_STATE_KEY]: state });
    } else {
      // Fallback to localStorage
      localStorage.setItem(GUIDE_STATE_KEY, JSON.stringify(state));
    }
    console.log("Guide state saved:", state);
  } catch (error) {
    console.error("Failed to save guide state:", error);
  }
};

// Load guide state from storage
const loadGuideState = async (): Promise<GuideState | null> => {
  try {
    let state: GuideState | undefined;
    
    if (hasChrome) {
      const result = await chrome.storage.local.get(GUIDE_STATE_KEY);
      state = result[GUIDE_STATE_KEY] as GuideState | undefined;
    } else {
      // Fallback to localStorage
      const stored = localStorage.getItem(GUIDE_STATE_KEY);
      if (stored) {
        state = JSON.parse(stored) as GuideState;
      }
    }
    
    if (state) {
      // Check if state is not too old (24 hours)
      const isExpired = Date.now() - state.timestamp > 24 * 60 * 60 * 1000;
      if (isExpired) {
        if (hasChrome) {
          await chrome.storage.local.remove(GUIDE_STATE_KEY);
        } else {
          localStorage.removeItem(GUIDE_STATE_KEY);
        }
        return null;
      }
      console.log("Guide state loaded:", state);
      return state;
    }
    return null;
  } catch (error) {
    console.error("Failed to load guide state:", error);
    return null;
  }
};

// Clear guide state from storage
const clearGuideState = async () => {
  try {
    if (hasChrome) {
      await chrome.storage.local.remove(GUIDE_STATE_KEY);
    } else {
      localStorage.removeItem(GUIDE_STATE_KEY);
    }
    console.log("Guide state cleared");
  } catch (error) {
    console.error("Failed to clear guide state:", error);
  }
};

const Content: React.FC = () => {
  const [steps, setSteps] = useState<HTMLElement[]>([]);
  const [index, setIndex] = useState<number>(0);
  const [isActive, setIsActive] = useState<boolean>(false);

  // Store original HTML list for persistence
  const [originalHtmlList, setOriginalHtmlList] = useState<string[]>([]);

  // Chat interface states
  const [chatInput, setChatInput] = useState<string>("");
  const [chatMessages, setChatMessages] = useState<Array<{role: 'user' | 'assistant', content: string}>>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isMinimized, setIsMinimized] = useState<boolean>(false);

  // Load guide state on mount
  useEffect(() => {
    console.log("Content component mounted, DOM ready state:", document.readyState);
    
    // Wait for DOM to be fully loaded
    const initializeGuide = async () => {
      console.log("Checking for saved guide state...");
      const loadedState = await loadGuideState();
      
      if (loadedState && loadedState.isActive) {
        const htmlList = loadedState.htmlList;
        const currentIndex = loadedState.currentIndex;
        
        console.log("✅ Found active guide state - resuming at step", currentIndex, "of", htmlList.length);
        setOriginalHtmlList(htmlList);
        
        // Resolve elements for current page
        console.log("Resolving HTML elements for current page...");
        const resolved = resolveHtmlStringsToElements(htmlList);
        console.log("Resolved", resolved.length, "elements, looking for element at index", currentIndex);
        
        // Check if current element exists on this page
        if (resolved[currentIndex]) {
          console.log("✅ Found element for step", currentIndex, "on this page");
        } else {
          console.log("⚠️ Element for step", currentIndex, "not found on this page");
        }
        
        setSteps(resolved);
        setIndex(currentIndex);
        setIsActive(true);
      } else {
        console.log("No active guide state found");
      }
    };

    // Run initialization immediately and after a delay
    initializeGuide();
    
    // Also run after a delay to handle slow-loading pages
    const timeoutId = setTimeout(initializeGuide, 1000);

    // Clean up
    return () => {
      clearTimeout(timeoutId);
    };
  }, []);

  // Move to next step when handler called
  const advance = async () => {
    const newIndex = index + 1;
    
    if (newIndex >= originalHtmlList.length) {
      // Guide completed
      console.log("Guide completed!");
      setIsActive(false);
      await clearGuideState();
    } else {
      console.log("Advancing to step", newIndex, "of", originalHtmlList.length);
      // Save state BEFORE navigation happens
      await saveGuideState(originalHtmlList, newIndex, true);
      // Then update local index
      setIndex(newIndex);
    }
  };

  // Start a new guide
  const startGuide = async (htmlList: string[]) => {
    console.log("Starting guide with", htmlList.length, "steps");
    setOriginalHtmlList(htmlList);
    
    const resolved = resolveHtmlStringsToElements(htmlList);
    console.log("Resolved elements:", resolved.length);
    
    setSteps(resolved);
    setIndex(0);
    setIsActive(true);
    
    // Save initial state
    await saveGuideState(htmlList, 0, true);
  };

  // Stop the guide
  const stopGuide = async () => {
    console.log("Stopping guide");
    setIsActive(false);
    setSteps([]);
    setIndex(0);
    setOriginalHtmlList([]);
    await clearGuideState();
  };

  // // Mock backend function - replace this with actual API call later
  // const mockBackendResponse = async (prompt: string): Promise<string[]> => {
  //   // Simulate API delay
  //   await new Promise(resolve => setTimeout(resolve, 1000));

  //   // Return mock HTML elements based on prompt keywords
  //   if (prompt.toLowerCase().includes('login') || prompt.toLowerCase().includes('sign in')) {
  //     return [
  //       `<a href="https://app.pinecone.io/?sessionType=login" class="flex items-center gap-1.5 whitespace-nowrap font-medium text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-300" target="_blank">Log In</a>`,
  //       `<input type="email" placeholder="Enter your email" class="form-input" />`,
  //       `<button type="submit" class="btn-primary">Continue</button>`
  //     ];
  //   } else if (prompt.toLowerCase().includes('project')) {
  //     return [
  //       `<button class="MuiBox-root css-zjvir"><span class="MuiButtonBase-root MuiRadio-root MuiRadio-colorPrimary PrivateSwitchBase-root MuiRadio-root MuiRadio-colorPrimary MuiRadio-root MuiRadio-colorPrimary css-1pv1b0u"><input type="radio" class="PrivateSwitchBase-input css-j8yymo" value=""><span class="css-1qiat4j"><svg class="MuiSvgIcon-root MuiSvgIcon-fontSizeMedium css-1nyspg7" focusable="false" aria-hidden="true" viewBox="0 0 24 24" data-testid="RadioButtonUncheckedIcon"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8z"></path></svg><svg class="MuiSvgIcon-root MuiSvgIcon-fontSizeMedium css-1hq0fuf" focusable="false" aria-hidden="true" viewBox="0 0 24 24" data-testid="RadioButtonCheckedIcon"><path d="M8.465 8.465C9.37 7.56 10.62 7 12 7C14.76 7 17 9.24 17 12C17 13.38 16.44 14.63 15.535 15.535C14.63 16.44 13.38 17 12 17C9.24 17 7 14.76 7 12C7 10.62 7.56 9.37 8.465 8.465Z"></path></svg></span></span><div class="MuiBox-root css-1svqped"><p class="MuiTypography-root MuiTypography-body1 css-7kft6t">I'm building a <span class="MuiTypography-root MuiTypography-body1 css-1ci3xvh">small or personal project</span></p></div></button>`,
  //       `<button class="MuiButtonBase-root MuiButton-root MuiButton-contained MuiButton-containedPrimary MuiButton-sizeMedium MuiButton-containedSizeMedium MuiButton-colorPrimary MuiButton-disableElevation MuiButton-fullWidth MuiButton-root MuiButton-contained MuiButton-containedPrimary MuiButton-sizeMedium MuiButton-containedSizeMedium MuiButton-colorPrimary MuiButton-disableElevation MuiButton-fullWidth css-64xooo" tabindex="0" type="button">Start for free<span class="MuiTouchRipple-root css-4mb1j7"></span></button>`
  //     ];
  //   } else {
  //     // Default response
  //     return [
  //       `<button id="default-btn-1" class="btn">Click here to start</button>`,
  //       `<input type="text" id="default-input" placeholder="Enter value" />`,
  //       `<button id="default-submit" class="btn-submit">Submit</button>`
  //     ];
  //   }
  // };

  // Handle chat submission
  const handleChatSubmit = async () => {
    if (!chatInput.trim()) return;

    const userMessage = chatInput.trim();
    setChatInput("");

    // Add user message
    setChatMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsLoading(true);

    try {
      // Call the Flask backend API
      const response = await fetch('http://localhost:5001/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userMessage,
          use_retrieval: true,
        }),
      });
      
      if (!response.ok) {
        throw new Error(`API request failed: ${response.status} ${response.statusText}`);
      }
      
      const data = await response.json();
      
      if (data.status === 'error') {
        throw new Error(data.error || 'Unknown error from backend');
      }
      
      // Add assistant response to chat
      setChatMessages(prev => [...prev, {
        role: 'assistant',
        content: data.response
      }]);
      
      // For now, we'll parse the response to extract HTML elements or guide steps
      // This is a placeholder - you might want to enhance this based on your specific needs
      // const htmlList = extractHtmlFromResponse(data.response);
      // if (htmlList.length > 0) {
      //   await startGuide(htmlList);
      // }

    } catch (error) {
      console.error('Guide generation error:', error);
      setChatMessages(prev => [...prev, {
        role: 'assistant',
        content: `Sorry, I encountered an error: ${error.message}. Please make sure the backend server is running on localhost:5001.`
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      {/* Minimalist Guide Assistant */}
      <div
        style={{
          position: "fixed",
          bottom: 32,
          right: 32,
          width: isMinimized ? 64 : 360,
          height: isMinimized ? 64 : 480,
          background: "rgba(255, 255, 255, 0.95)",
          boxShadow: "0 8px 32px rgba(0, 0, 0, 0.08)",
          borderRadius: isMinimized ? "50%" : 24,
          zIndex: 999999,
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          backdropFilter: "blur(20px)",
          border: "1px solid rgba(0, 0, 0, 0.06)",
          transition: "all 0.3s ease",
          cursor: isMinimized ? "pointer" : "default",
        }}
        onClick={isMinimized ? () => setIsMinimized(false) : undefined}
      >
        {isMinimized ? (
          /* Minimized State */
          <div style={{
            width: "100%",
            height: "100%",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: "24px",
            position: "relative",
          }}>
            ✨
            {isActive && (
              <div style={{
                position: "absolute",
                top: 8,
                right: 8,
                width: 12,
                height: 12,
                borderRadius: "50%",
                background: "#10b981",
                border: "2px solid white",
              }} />
            )}
          </div>
        ) : (
          /* Full Header */
          <div style={{
            padding: "24px 24px 20px",
            borderBottom: "1px solid rgba(0, 0, 0, 0.04)",
          }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div>
                <div style={{
                  fontSize: "16px",
                  fontWeight: 600,
                  color: "#111827",
                  letterSpacing: "-0.01em",
                }}>Cluelessly</div>
                <div style={{
                  fontSize: "12px",
                  color: "#6b7280",
                  marginTop: 2,
                }}>
                  {isActive ? `${index + 1}/${originalHtmlList.length}` : "Ready"}
                </div>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <div style={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  background: isActive ? "#10b981" : "#d1d5db",
                }} />
                <button
                  onClick={() => setIsMinimized(true)}
                  style={{
                    background: "none",
                    border: "none",
                    cursor: "pointer",
                    padding: 4,
                    borderRadius: 4,
                    color: "#6b7280",
                    fontSize: "14px",
                  }}
                >
                  −
                </button>
              </div>
            </div>
          </div>
        )}

        {!isMinimized && (
          /* Messages */
          <div style={{
            flex: 1,
            overflow: "auto",
            padding: "16px 24px",
            display: "flex",
            flexDirection: "column",
            gap: 16,
          }}>
          {chatMessages.length === 0 && (
            <div style={{
              textAlign: "center",
              padding: "40px 20px",
            }}>
              <div style={{
                width: 48,
                height: 48,
                borderRadius: "50%",
                background: "#f3f4f6",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                margin: "0 auto 16px",
                fontSize: "20px",
              }}>✨</div>
              <div style={{
                color: "#111827",
                fontSize: "14px",
                fontWeight: 500,
                marginBottom: 8,
              }}>
                What can I help you with?
              </div>
              <div style={{
                color: "#9ca3af",
                fontSize: "12px",
                lineHeight: 1.4,
              }}>
                "Help me login" or "Create a project"
              </div>
            </div>
          )}

          {chatMessages.map((msg, idx) => (
            <div
              key={idx}
              style={{
                display: 'flex',
                flexDirection: msg.role === 'user' ? 'row-reverse' : 'row',
                gap: 8,
                opacity: 0,
                animation: `fadeIn 0.4s ease-out ${idx * 0.1}s forwards`,
              }}
            >
              <div style={{
                width: 24,
                height: 24,
                borderRadius: '50%',
                background: msg.role === 'user' ? '#111827' : '#f3f4f6',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '10px',
                flexShrink: 0,
              }}>
                {msg.role === 'user' ? '👤' : '✨'}
              </div>
              <div style={{
                flex: 1,
                padding: '12px 16px',
                borderRadius: 16,
                background: msg.role === 'user' ? '#f9fafb' : '#ffffff',
                border: '1px solid rgba(0, 0, 0, 0.04)',
                color: '#374151',
                fontSize: '13px',
                lineHeight: 1.5,
                maxWidth: '80%',
              }}>
                {msg.content}
              </div>
            </div>
          ))}

          {isLoading && (
            <div style={{
              display: 'flex',
              gap: 8,
            }}>
              <div style={{
                width: 24,
                height: 24,
                borderRadius: '50%',
                background: '#f3f4f6',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '10px',
              }}>✨</div>
              <div style={{
                flex: 1,
                padding: '12px 16px',
                borderRadius: 16,
                background: '#ffffff',
                border: '1px solid rgba(0, 0, 0, 0.04)',
                color: '#9ca3af',
                fontSize: '13px',
                display: 'flex',
                alignItems: 'center',
                gap: 8,
              }}>
                <div style={{
                  display: 'flex',
                  gap: 3,
                }}>
                  <div style={{
                    width: 4,
                    height: 4,
                    borderRadius: '50%',
                    background: '#d1d5db',
                    animation: 'pulse 1.4s ease-in-out infinite',
                  }} />
                  <div style={{
                    width: 4,
                    height: 4,
                    borderRadius: '50%',
                    background: '#d1d5db',
                    animation: 'pulse 1.4s ease-in-out 0.2s infinite',
                  }} />
                  <div style={{
                    width: 4,
                    height: 4,
                    borderRadius: '50%',
                    background: '#d1d5db',
                    animation: 'pulse 1.4s ease-in-out 0.4s infinite',
                  }} />
                </div>
              </div>
            </div>
          )}

          {isActive && !steps[index] && (
            <div style={{
              padding: '12px 16px',
              borderRadius: 12,
              background: '#fef3c7',
              border: '1px solid #fbbf24',
              color: '#92400e',
              fontSize: '12px',
              textAlign: 'center',
            }}>
              Element not found. Navigate to the correct page.
            </div>
          )}
          </div>
        )}

        {!isMinimized && (
          /* Input */
          <div style={{
            padding: "16px 24px 24px",
            borderTop: "1px solid rgba(0, 0, 0, 0.04)",
          }}>
          <div style={{ display: "flex", gap: 8, marginBottom: isActive ? 12 : 0 }}>
            <input
              type="text"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleChatSubmit()}
              placeholder="Ask me anything..."
              disabled={isLoading}
              style={{
                flex: 1,
                padding: "12px 16px",
                borderRadius: 12,
                border: "1px solid rgba(0, 0, 0, 0.08)",
                fontSize: "13px",
                outline: "none",
                background: '#fafafa',
                color: '#374151',
              }}
            />
            <button
              onClick={handleChatSubmit}
              disabled={isLoading || !chatInput.trim()}
              style={{
                padding: "12px 16px",
                borderRadius: 12,
                background: isLoading || !chatInput.trim() ? '#f3f4f6' : '#111827',
                color: isLoading || !chatInput.trim() ? '#9ca3af' : 'white',
                border: "none",
                cursor: isLoading || !chatInput.trim() ? "not-allowed" : "pointer",
                fontSize: "13px",
                fontWeight: 500,
              }}
            >
              →
            </button>
          </div>

          {isActive && (
            <div style={{ display: "flex", gap: 6 }}>
              <button
                onClick={stopGuide}
                style={{
                  flex: 1,
                  padding: "8px 12px",
                  borderRadius: 8,
                  background: "#f3f4f6",
                  color: "#6b7280",
                  border: "none",
                  fontSize: "12px",
                  cursor: "pointer",
                }}
              >
                Stop
              </button>
              <button
                onClick={() => setIndex(0)}
                style={{
                  flex: 1,
                  padding: "8px 12px",
                  borderRadius: 8,
                  background: "#f3f4f6",
                  color: "#6b7280",
                  border: "none",
                  fontSize: "12px",
                  cursor: "pointer",
                }}
              >
                Restart
              </button>
              <button
                onClick={advance}
                style={{
                  flex: 1,
                  padding: "8px 12px",
                  borderRadius: 8,
                  background: "#111827",
                  color: "white",
                  border: "none",
                  fontSize: "12px",
                  cursor: "pointer",
                }}
              >
                Next
              </button>
            </div>
          )}
          </div>
        )}
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 0.3; }
          50% { opacity: 0.8; }
        }
        
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        
        button:hover:not(:disabled) {
          opacity: 0.8;
        }
        
        input:focus {
          border-color: rgba(0, 0, 0, 0.12) !important;
        }
      `}</style>

      {/* Render overlay for current step */}
      {isActive && steps.length > 0 && index >= 0 && index < steps.length && steps[index] && (
        <OverlayGuide target={steps[index]} onComplete={advance} />
      )}
    </>
  );
};

export default Content;
