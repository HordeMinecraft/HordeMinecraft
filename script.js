const SERVER_IP = "213.152.43.80:25855";

function fallbackCopy(text) {
  const input = document.createElement("textarea");
  input.value = text;
  input.setAttribute("readonly", "");
  input.style.position = "fixed";
  input.style.opacity = "0";
  document.body.appendChild(input);
  input.select();
  document.execCommand("copy");
  input.remove();
}

function showCopyToast() {
  const toast = document.querySelector("[data-copy-toast]");
  if (!toast) return;
  toast.classList.add("visible");
  window.clearTimeout(showCopyToast.timer);
  showCopyToast.timer = window.setTimeout(() => toast.classList.remove("visible"), 1800);
}

document.addEventListener("DOMContentLoaded", () => {
  if (window.lucide) window.lucide.createIcons();

  const copyButton = document.querySelector("[data-copy-ip]");
  copyButton?.addEventListener("click", async () => {
    try {
      if (navigator.clipboard?.writeText) await navigator.clipboard.writeText(SERVER_IP);
      else fallbackCopy(SERVER_IP);
      showCopyToast();
    } catch {
      fallbackCopy(SERVER_IP);
      showCopyToast();
    }
  });

  const year = document.querySelector("[data-year]");
  if (year) year.textContent = String(new Date().getFullYear());
});
