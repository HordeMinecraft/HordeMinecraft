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
  const authCabinet = document.querySelector("[data-auth-cabinet]");
  const authResult = document.querySelector("[data-auth-demo-result]");
  const authApiStatus = document.querySelector("[data-auth-api-status]");
  const cabinetStatus = document.querySelector("[data-cabinet-status]");
  const cabinetNick = document.querySelector("[data-cabinet-nick]");
  const cabinetDonate = document.querySelector("[data-cabinet-donate]");
  const cabinetSubscription = document.querySelector("[data-cabinet-subscription]");
  const subscriptionTier = document.querySelector("[data-subscription-tier]");
  const subscriptionExpires = document.querySelector("[data-subscription-expires]");
  const skinPreview = document.querySelector("[data-skin-preview]");
  const skinModel = document.querySelector("[data-skin-model]");
  const skinFile = document.querySelector("[data-skin-file]");
  const skinResult = document.querySelector("[data-skin-result]");
  const saveSkin = document.querySelector("[data-save-skin]");
  const refreshProfile = document.querySelector("[data-refresh-profile]");
  const authLogout = document.querySelector("[data-auth-logout]");
  const resetRequest = document.querySelector("[data-reset-request]");
  const resetConfirm = document.querySelector("[data-reset-confirm]");
  const inventoryStatus = document.querySelector("[data-inventory-status]");
  const inventoryGrid = document.querySelector("[data-inventory-grid]");
  const authApiBase = window.HORDE_AUTH_API_BASE || "";
  const getSessionToken = () => localStorage.getItem("horde_session_token") || "";
  const friendlyError = (error) => {
    const text = String(error?.message || error || "");
    if (text.includes("Неверный ник") || text.includes("зарегистрирован") || text.includes("Код") || text.includes("Сессия")) return text;
    if (text.includes("Failed to fetch")) return "нет связи с кабинетом, попробуйте позже.";
    if (text.includes("422") || text.includes("validation") || text.includes("loc") || text.includes("string_")) return "проверьте ник, пароль и заполненные поля.";
    return text || "попробуйте ещё раз.";
  };
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
  const setCabinetStatus = (text, state = "info") => {
    if (!cabinetStatus) return;
    cabinetStatus.textContent = text;
    cabinetStatus.dataset.state = state;
  };
  const setSkinResult = (text, state = "info") => {
    if (!skinResult) return;
    skinResult.textContent = text;
    skinResult.dataset.state = state;
  };
  const showCabinet = (show) => {
    if (authDemo) authDemo.hidden = show;
    if (authCabinet) authCabinet.hidden = !show;
  };
  const authRequest = async (path, payload, options = {}) => {
    const response = await fetch(`${authApiBase}${path}`, {
      method: options.method || "POST",
      headers: {
        "Content-Type": "application/json",
        ...(options.token ? {"Authorization": `Bearer ${options.token}`} : {}),
      },
      body: payload ? JSON.stringify(payload) : undefined,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = typeof data.detail === "string" ? data.detail : "";
      throw new Error(detail || `Ошибка ${response.status}`);
    }
    return data;
  };
  const formatDonate = (subscription) => {
    if (!subscription?.active) return "Активной донат-подписки сейчас нет.";
    const expires = subscription.expires_at ? new Date(subscription.expires_at).toLocaleString("ru-RU") : "дата уточняется";
    return `Активна подписка ${subscription.tier} до ${expires}.`;
  };
  const renderSubscription = (subscription) => {
    const active = Boolean(subscription?.active);
    cabinetSubscription?.classList.toggle("active", active);
    if (subscriptionTier) subscriptionTier.textContent = active ? subscription.tier : "Нет активной";
    if (subscriptionExpires) {
      if (active) {
        const expires = subscription.expires_at ? new Date(subscription.expires_at).toLocaleString("ru-RU") : "дата уточняется";
        subscriptionExpires.textContent = `Действует до ${expires}. Префикс и защита донат-вещей активны до окончания подписки.`;
      } else {
        subscriptionExpires.textContent = "После покупки PRO/ELITE/PRIME/EMPEROR статус появится здесь.";
      }
    }
  };
  const renderInventory = (snapshot) => {
    if (!inventoryStatus || !inventoryGrid) return;
    inventoryGrid.innerHTML = "";
    const items = Array.isArray(snapshot?.inventory) ? snapshot.inventory : [];
    if (!snapshot?.synced) {
      inventoryStatus.textContent = "Инвентарь появится здесь после привязки и синхронизации с сервера.";
      inventoryGrid.hidden = true;
      return;
    }
    const updated = snapshot.updated_at ? new Date(snapshot.updated_at).toLocaleString("ru-RU") : "только что";
    inventoryStatus.textContent = `Последняя синхронизация: ${updated}.`;
    inventoryGrid.hidden = false;
    const visibleItems = items.slice(0, 36);
    for (let i = 0; i < 36; i += 1) {
      const item = visibleItems[i];
      const slot = document.createElement("span");
      slot.className = "inventory-slot";
      if (item) {
        const count = item.count || item.Count || "";
        const name = item.name || item.id || item.item || "Предмет";
        slot.textContent = count && Number(count) > 1 ? String(count) : "•";
        slot.title = `${name}${count ? ` ×${count}` : ""}`;
        slot.dataset.filled = "true";
      }
      inventoryGrid.appendChild(slot);
    }
  };
  const loadInventory = async () => {
    const token = getSessionToken();
    if (!authApiBase || !token) return;
    try {
      const snapshot = await authRequest("/auth/inventory", null, {method: "GET", token});
      renderInventory(snapshot);
    } catch {
      if (inventoryStatus) inventoryStatus.textContent = "Инвентарь сейчас не удалось обновить.";
    }
  };
  const renderProfile = async (user) => {
    const nick = user?.minecraft_nick || "Игрок";
    if (cabinetNick) cabinetNick.textContent = nick;
    if (skinModel) skinModel.value = user?.skin_model || "classic";
    if (skinPreview) {
      skinPreview.style.backgroundImage = user?.skin_data_url ? `url("${user.skin_data_url}")` : "";
      skinPreview.classList.toggle("has-skin", Boolean(user?.skin_data_url));
    }
    if (cabinetDonate) cabinetDonate.textContent = "Проверяем донат-подписку...";
    try {
      const sub = await fetch(`${authApiBase}/donate/subscription/${encodeURIComponent(nick)}`).then((r) => r.json());
      if (cabinetDonate) cabinetDonate.textContent = formatDonate(sub);
      renderSubscription(sub);
    } catch {
      if (cabinetDonate) cabinetDonate.textContent = "Донат-подписку сейчас не удалось проверить.";
      renderSubscription(null);
    }
    await loadInventory();
  };
  const loadProfile = async () => {
    const token = getSessionToken();
    if (!authApiBase || !token) return false;
    const data = await authRequest("/auth/me", null, {method: "GET", token});
    await renderProfile(data.user);
    showCabinet(true);
    setAuthStatus("ГОТОВО", "good");
    setCabinetStatus("ONLINE", "good");
    return true;
  };
  if (authDemo) {
    if (!authApiBase) {
      setAuthStatus("НЕТ СВЯЗИ", "bad");
      setAuthResult("Кабинет временно недоступен. Попробуйте позже.", "bad");
    } else {
      fetch(`${authApiBase}/health`, {method: "GET"})
        .then((response) => {
          if (!response.ok) throw new Error(`HTTP ${response.status}`);
          setAuthStatus("ГОТОВО", "good");
          setAuthResult("Введите ник и пароль, чтобы войти в кабинет.", "good");
          if (getSessionToken()) {
            loadProfile().catch(() => {
              localStorage.removeItem("horde_session_token");
              localStorage.removeItem("horde_launcher_token");
              showCabinet(false);
            });
          }
        })
        .catch(() => {
          setAuthStatus("ОЖИДАНИЕ", "warn");
          setAuthResult("Кабинет просыпается или временно недоступен. Попробуйте ещё раз через минуту.", "warn");
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
    const email = form.get("email")?.toString().trim();
    const code = form.get("code")?.toString().trim();
    if (!minecraft_nick || minecraft_nick.length < 3) return setAuthResult("Введите ник от 3 символов.", "bad");
    if (!password || password.length < 6) return setAuthResult("Пароль должен быть минимум 6 символов.", "bad");
    if (!authApiBase) return setAuthResult("Кабинет временно недоступен.", "bad");
    const path = action === "register" ? "/auth/register" : action === "link" ? "/auth/link" : "/auth/login";
    const payload = action === "link" ? {minecraft_nick, password, code, email} : {minecraft_nick, password, email};
    if (action === "link" && (!code || code.length < 4)) return setAuthResult("Для привязки нужен код из игры.", "bad");
    if ((action === "register" || action === "link") && email && !email.includes("@")) {
      return setAuthResult("Проверьте почту для восстановления.", "bad");
    }
    setAuthResult("Проверяем данные входа...", "info");
    try {
      const data = await authRequest(path, payload);
      if (data.session_token) localStorage.setItem("horde_session_token", data.session_token);
      if (data.launcher_token) localStorage.setItem("horde_launcher_token", data.launcher_token);
      setAuthStatus("ГОТОВО", "good");
      setAuthResult(`Вход выполнен: ${data.user?.minecraft_nick || minecraft_nick}.`, "good");
      await renderProfile(data.user);
      showCabinet(true);
    } catch (error) {
      setAuthStatus("ОШИБКА", "bad");
      setAuthResult(`Не удалось войти: ${friendlyError(error)}`, "bad");
    }
  });
  refreshProfile?.addEventListener("click", async () => {
    setCabinetStatus("SYNC", "warn");
    try {
      await loadProfile();
    } catch (error) {
      setCabinetStatus("ERROR", "bad");
      setSkinResult(`Не удалось обновить профиль: ${friendlyError(error)}`, "bad");
    }
  });
  authLogout?.addEventListener("click", () => {
    localStorage.removeItem("horde_session_token");
    localStorage.removeItem("horde_launcher_token");
    showCabinet(false);
    setAuthResult("Вы вышли из кабинета на этом устройстве.", "warn");
  });
  saveSkin?.addEventListener("click", async () => {
    const file = skinFile?.files?.[0];
    if (!file) return setSkinResult("Выберите PNG-файл скина.", "bad");
    if (file.type !== "image/png" && !file.name.toLowerCase().endsWith(".png")) {
      return setSkinResult("Нужен именно PNG-скин Minecraft.", "bad");
    }
    if (file.size > 650 * 1024) return setSkinResult("Файл слишком большой. Для скина Minecraft хватит PNG до 650 КБ.", "bad");
    const token = getSessionToken();
    if (!token) return setSkinResult("Сначала войдите в кабинет.", "bad");
    const reader = new FileReader();
    reader.onload = async () => {
      try {
        setSkinResult("Сохраняю скин...", "info");
        const data = await authRequest("/auth/skin", {
          skin_data_url: reader.result,
          skin_model: skinModel?.value || "classic",
        }, {token});
        await renderProfile(data.user);
        setSkinResult("Скин сохранён. Он будет применён после синхронизации лаунчера.", "good");
      } catch (error) {
        setSkinResult(`Ошибка сохранения скина: ${friendlyError(error)}`, "bad");
      }
    };
    reader.onerror = () => setSkinResult("Не удалось прочитать файл скина.", "bad");
    reader.readAsDataURL(file);
  });

  resetRequest?.addEventListener("click", async () => {
    const form = new FormData(authDemo);
    const minecraft_nick = form.get("nick")?.toString().trim();
    const email = form.get("reset_email")?.toString().trim();
    if (!minecraft_nick || minecraft_nick.length < 3) return setAuthResult("Введите ник аккаунта.", "bad");
    if (!email || !email.includes("@")) return setAuthResult("Введите почту аккаунта.", "bad");
    try {
      const data = await authRequest("/auth/password-reset/request", {minecraft_nick, email});
      setAuthResult(data.message || "Если почта совпала с аккаунтом, код восстановления будет отправлен.", "warn");
    } catch (error) {
      setAuthResult(`Не удалось запросить восстановление: ${friendlyError(error)}`, "bad");
    }
  });

  resetConfirm?.addEventListener("click", async () => {
    const form = new FormData(authDemo);
    const minecraft_nick = form.get("nick")?.toString().trim();
    const code = form.get("reset_code")?.toString().trim();
    const new_password = form.get("reset_password")?.toString();
    if (!minecraft_nick || minecraft_nick.length < 3) return setAuthResult("Введите ник аккаунта.", "bad");
    if (!code || code.length < 6) return setAuthResult("Введите код восстановления.", "bad");
    if (!new_password || new_password.length < 6) return setAuthResult("Новый пароль должен быть минимум 6 символов.", "bad");
    try {
      const data = await authRequest("/auth/password-reset/confirm", {minecraft_nick, code, new_password});
      if (data.session_token) localStorage.setItem("horde_session_token", data.session_token);
      if (data.launcher_token) localStorage.setItem("horde_launcher_token", data.launcher_token);
      setAuthResult("Пароль изменён. Вход выполнен.", "good");
      await renderProfile(data.user);
      showCabinet(true);
    } catch (error) {
      setAuthResult(`Не удалось сменить пароль: ${friendlyError(error)}`, "bad");
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
