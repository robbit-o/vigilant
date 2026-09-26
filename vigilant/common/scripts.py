from typing import Final

MOUSE_POINTER_SCRIPT: Final[str] = """
(() => {
  if (window.__vigilantMousePointer) return;

  const SVG_NS = "http://www.w3.org/2000/svg";
  const CURSOR_ID = "vigilant-mouse-pointer";
  const ARROW_PATH = "M4 1 L4 20 L9.5 14.5 L12.7 22 L16 20.7 L12.9 13.5 L20 13.5 Z";

  let cursor = null;
  let x = 0;
  let y = 0;
  let pressed = false;

  const render = () => {
    if (!cursor) return;

    cursor.style.opacity = "1";
    cursor.style.transform = `translate(${x}px, ${y}px) scale(${pressed ? 0.7 : 1})`;
  };

  const attach = () => {
    if (cursor || !document.body) return;

    const style = document.createElement("style");
    style.textContent = "*, *::before, *::after { cursor: none !important; }";
    (document.head || document.documentElement).appendChild(style);

    cursor = document.createElementNS(SVG_NS, "svg");
    cursor.id = CURSOR_ID;
    cursor.setAttribute("width", "24");
    cursor.setAttribute("height", "24");
    cursor.setAttribute("viewBox", "0 0 24 24");
    cursor.style.cssText = [
      "position:fixed",
      "top:0",
      "left:0",
      "z-index:2147483647",
      "pointer-events:none",
      "opacity:0",
      "will-change:transform,opacity",
      "transition:transform .08s ease-out,opacity .2s ease-out",
    ].join(";");

    const arrow = document.createElementNS(SVG_NS, "path");
    arrow.setAttribute("d", ARROW_PATH);
    arrow.setAttribute("fill", "#ffffff");
    arrow.setAttribute("stroke", "#1c2331");
    arrow.setAttribute("stroke-width", "1.6");
    arrow.setAttribute("stroke-linejoin", "round");
    cursor.appendChild(arrow);

    document.body.appendChild(cursor);
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", attach);
  } else {
    attach();
  }

  document.addEventListener(
    "mousemove",
    (event) => {
      x = event.clientX;
      y = event.clientY;
      render();
    },
    true
  );
  document.addEventListener("mousedown", () => (pressed = (render(), true)), true);
  document.addEventListener("mouseup", () => (pressed = (render(), false)), true);

  window.__vigilantMousePointer = true;
})();
"""
