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

  const community = document.querySelector(".nav-community");
  const communityButton = document.querySelector(".nav-community-button");
  communityButton?.addEventListener("click", () => {
    const opened = community?.classList.toggle("open");
    communityButton.setAttribute("aria-expanded", opened ? "true" : "false");
  });
  document.addEventListener("click", (event) => {
    if (!community || community.contains(event.target)) return;
    community.classList.remove("open");
    communityButton?.setAttribute("aria-expanded", "false");
  });

  const year = document.querySelector("[data-year]");
  if (year) year.textContent = String(new Date().getFullYear());

  const donateNick = document.querySelector("[data-donate-nick]");
  const donateMessage = document.querySelector("[data-donate-message]");
  const donateCopyButton = document.querySelector("[data-copy-donate-message]");
  const donateHint = document.querySelector("[data-donate-hint]");
  const donateLink = document.querySelector("[data-donate-link]");
  const donateSummary = document.querySelector("[data-donate-summary]");
  const donateTierButtons = Array.from(document.querySelectorAll("[data-donate-tier]"));
  let selectedDonateTier = "PRO";
  let selectedDonateAmount = "150";

  const setDonateTier = (tier, amount) => {
    selectedDonateTier = tier || "PRO";
    selectedDonateAmount = amount || "150";
    donateTierButtons.forEach((button) => {
      button.classList.toggle("active", button.dataset.donateTier === selectedDonateTier);
    });
    buildDonateMessage();
    donateNick?.focus();
  };

  const buildDonateMessage = () => {
    if (!donateNick || !donateMessage) return "";
    const cleanNick = donateNick.value.replace(/[^A-Za-z0-9_]/g, "").slice(0, 16);
    if (donateNick.value !== cleanNick) donateNick.value = cleanNick;
    const message = cleanNick.length >= 3 ? `HORDE ${cleanNick} ${selectedDonateTier}` : `HORDE Ник ${selectedDonateTier}`;
    donateMessage.textContent = message;
    if (donateHint) {
      donateHint.innerHTML = cleanNick.length >= 3
        ? `В DonationAlerts укажи сумму <code>${selectedDonateAmount} ₽</code> и вставь сообщение <code>${message}</code>.`
        : "Введите ник от 3 до 16 символов: латиница, цифры и _.";
    }
    if (donateSummary) donateSummary.textContent = `${selectedDonateTier} · ${selectedDonateAmount} ₽ · 30 дней`;
    donateLink?.classList.toggle("disabled", cleanNick.length < 3);
    donateLink?.setAttribute("aria-disabled", cleanNick.length < 3 ? "true" : "false");
    return message;
  };
  donateTierButtons.forEach((button) => {
    button.addEventListener("click", () => setDonateTier(button.dataset.donateTier, button.dataset.donateAmount));
  });
  donateNick?.addEventListener("input", buildDonateMessage);
  donateCopyButton?.addEventListener("click", async () => {
    const message = buildDonateMessage();
    if (!message || message.includes("Ник")) return;
    try {
      if (navigator.clipboard?.writeText) await navigator.clipboard.writeText(message);
      else fallbackCopy(message);
      if (donateHint) donateHint.innerHTML = `Скопировано: <code>${message}</code>. Теперь вставь это в сообщение DonationAlerts.`;
    } catch {
      fallbackCopy(message);
      if (donateHint) donateHint.innerHTML = `Скопировано: <code>${message}</code>. Теперь вставь это в сообщение DonationAlerts.`;
    }
  });
  donateLink?.addEventListener("click", (event) => {
    const message = buildDonateMessage();
    if (!message || message.includes("Ник")) {
      event.preventDefault();
      donateNick?.focus();
    }
  });
  buildDonateMessage();
});
