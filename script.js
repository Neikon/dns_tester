// Copy helper for landing page buttons
// Comments in English as per project conventions

function copy(btn, text) {
  // Copy text to clipboard and show temporary feedback
  navigator.clipboard.writeText(text).then(() => {
    const original = btn.innerHTML;
    btn.innerHTML = "✓";
    setTimeout(() => { btn.innerHTML = original; }, 1500);
  });
}
