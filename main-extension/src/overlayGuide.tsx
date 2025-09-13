// overlayGuide.tsx
import React, { useEffect, useState } from "react";

type OverlayGuideProps = {
  target: HTMLElement | null;
  onComplete?: () => void;
  offsetY?: number; // how far above the element to place arrow
};

const OverlayGuide: React.FC<OverlayGuideProps> = ({ target, onComplete, offsetY = 40 }) => {
  const [rect, setRect] = useState<DOMRect | null>(null);

  useEffect(() => {
    if (!target) {
      setRect(null);
      return;
    }

    const update = () => {
      if (!document.contains(target)) {
        setRect(null);
        return;
      }
      // Force a reflow to ensure accurate measurements
      target.offsetHeight;
      const newRect = target.getBoundingClientRect();
      console.log("Target element rect:", newRect, "Element:", target.tagName, target.className);
      setRect(newRect);
    };

    // scroll target into view (center) so highlight shows up nicely
    try {
      target.scrollIntoView({ behavior: "smooth", block: "center", inline: "center" });
      
      // Wait for scroll to complete before calculating position
      setTimeout(() => {
        requestAnimationFrame(() => {
          requestAnimationFrame(() => {
            update();
          });
        });
      }, 100);
    } catch (e) {
      // If scrollIntoView fails, just update position immediately
      update();
    }

    // update on scroll/resize
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);

    // when the user clicks the target, notify parent to advance
    const onClick = () => {
      console.log("Target element clicked, advancing guide");
      onComplete?.();
    };

    target.addEventListener("click", onClick);

    return () => {
      window.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
      target.removeEventListener("click", onClick);
    };
  }, [target, onComplete, offsetY]);

  if (!rect) return null;

  // Create a highlighting overlay that covers the target element
  return (
    <>
      {/* Backdrop overlay to dim the rest of the page */}
      <div
        aria-hidden
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          width: "100vw",
          height: "100vh",
          backgroundColor: "rgba(0, 0, 0, 0.05)",
          zIndex: 2147483646,
          pointerEvents: "none",
          userSelect: "none",
        }}
      />
      
      {/* Highlight box around the target element */}
      <div
        aria-hidden
        style={{
          position: "fixed",
          top: rect.top - 2,
          left: rect.left - 2,
          width: rect.width + 4,
          height: rect.height + 4,
          border: "2px solid #111827",
          borderRadius: "12px",
          backgroundColor: "transparent",
          boxShadow: "0 0 0 1px rgba(17, 24, 39, 0.1)",
          animation: "minimal-pulse 2s infinite",
          zIndex: 2147483647,
          pointerEvents: "none",
          userSelect: "none",
        }}
      />

      {/* Click instruction */}
      <div
        aria-hidden
        style={{
          position: "fixed",
          top: rect.bottom + 12,
          left: rect.left,
          backgroundColor: "rgba(255, 255, 255, 0.95)",
          color: "#374151",
          padding: "8px 12px",
          borderRadius: "8px",
          fontSize: "12px",
          fontFamily: "system-ui, -apple-system, sans-serif",
          fontWeight: 500,
          zIndex: 2147483647,
          pointerEvents: "none",
          userSelect: "none",
          boxShadow: "0 4px 12px rgba(0, 0, 0, 0.08)",
          border: "1px solid rgba(0, 0, 0, 0.06)",
          backdropFilter: "blur(20px)",
        }}
      >
        Click to continue
      </div>

      <style>{`
        @keyframes minimal-pulse {
          0% { 
            border-color: #111827;
            opacity: 1;
          }
          50% { 
            border-color: #374151;
            opacity: 0.8;
          }
          100% { 
            border-color: #111827;
            opacity: 1;
          }
        }
      `}</style>
    </>
  );
};

export default OverlayGuide;
