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

  const authDemo = document.querySelector("[data-auth-demo]");
  const authResult = document.querySelector("[data-auth-demo-result]");
  const authApiStatus = document.querySelector("[data-auth-api-status]");
  const authApiBase = window.HORDE_AUTH_API_BASE || "";
  const setAuthResult = (text, state = "info") => {
    if (!authResult) return;
    authResult.textContent = text;
    authResult.dataset.state = state;
  };
  const setAuthStatus = (text, state = "info") => {
    if (!authApiStatus) return;
    authApiStatus.textContent = text;
    authApiStatus.dataset.state = state;
  };
  const authRequest = async (path, payload) => {
    const response = await fetch(`${authApiBase}${path}`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || `API HTTP ${response.status}`);
    return data;
  };
  if (authDemo) {
    if (!authApiBase) {
      setAuthStatus("API OFF", "bad");
      setAuthResult("API-адрес не задан. Форма работает только как макет.", "bad");
    } else {
      fetch(`${authApiBase}/health`, {method: "GET"})
        .then((response) => {
          if (!response.ok) throw new Error(`HTTP ${response.status}`);
          setAuthStatus("API ONLINE", "good");
          setAuthResult("API доступен. Можно проверять регистрацию и вход.", "good");
        })
        .catch(() => {
          setAuthStatus("API WAIT", "warn");
          setAuthResult("Backend ещё не запущен на публичном адресе. Сайт уже готов к подключению API.", "warn");
        });
    }
  }
  authDemo?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const submitter = event.submitter;
    const action = submitter?.dataset?.authAction || "login";
    const form = new FormData(authDemo);
    const minecraft_nick = form.get("nick")?.toString().trim();
    const password = form.get("password")?.toString();
    const code = form.get("code")?.toString().trim();
    if (!minecraft_nick || minecraft_nick.length < 3) return setAuthResult("Введите ник от 3 символов.", "bad");
    if (!password || password.length < 6) return setAuthResult("Пароль должен быть минимум 6 символов.", "bad");
    if (!authApiBase) return setAuthResult("API-адрес не задан.", "bad");
    const path = action === "register" ? "/auth/register" : action === "link" ? "/auth/link" : "/auth/login";
    const payload = action === "link" ? {minecraft_nick, password, code} : {minecraft_nick, password};
    if (action === "link" && (!code || code.length < 4)) return setAuthResult("Для привязки нужен код из игры.", "bad");
    setAuthResult("Отправляю запрос в HORDE API...", "info");
    try {
      const data = await authRequest(path, payload);
      if (data.session_token) localStorage.setItem("horde_session_token", data.session_token);
      if (data.launcher_token) localStorage.setItem("horde_launcher_token", data.launcher_token);
      setAuthStatus("API OK", "good");
      setAuthResult(`Готово: ${data.user?.minecraft_nick || minecraft_nick}. Токен сохранён локально в браузере.`, "good");
    } catch (error) {
      setAuthStatus("API ERROR", "bad");
      setAuthResult(`Ошибка API: ${error.message}`, "bad");
    }
  });

  const donateNick = document.querySelector("[data-donate-nick]");
  const donateMessage = document.querySelector("[data-donate-message]");
  const donateCopyButton = document.querySelector("[data-copy-donate-message]");
  const donateHint = document.querySelector("[data-donate-hint]");
  const donateLink = document.querySelector("[data-donate-link]");
  const donateSummary = document.querySelector("[data-donate-summary]");
  const donateTierButtons = Array.from(document.querySelectorAll("[data-donate-tier]"));
  const donateConsole = document.querySelector(".donate-console");
  let selectedDonateTier = "PRO";
  let selectedDonateAmount = "150";

  const setDonateTier = (tier, amount) => {
    selectedDonateTier = tier || "PRO";
    selectedDonateAmount = amount || "150";
    donateTierButtons.forEach((button) => {
      button.classList.toggle("active", button.dataset.donateTier === selectedDonateTier);
    });
    buildDonateMessage();
    if (donateConsole && window.matchMedia("(max-width: 700px)").matches) {
      donateConsole.scrollIntoView({ behavior: "smooth", block: "start" });
      window.setTimeout(() => donateNick?.focus(), 260);
    } else {
      donateNick?.focus();
    }
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
