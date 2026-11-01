document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll('input[type="date"]').forEach(el => {
    if (!el.value && el.dataset.defaultToday === "true") el.value = new Date().toISOString().slice(0,10);
  });
  document.querySelectorAll("form").forEach(form => {
    form.addEventListener("submit", () => {
      const button = form.querySelector('button[type="submit"],button:not([type])');
      if (button && !button.disabled) {
        button.dataset.originalText = button.innerHTML;
        button.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Обработка...';
      }
    });
  });
});
