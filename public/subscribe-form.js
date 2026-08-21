(function () {
  var MAX_TICKERS = 10;
  var SEARCH_DEBOUNCE_MS = 280;
  var TICKER_PATTERN = /^[A-Za-z][A-Za-z0-9.]{0,9}$/;

  var modal = document.getElementById("subscribe-modal");
  if (!modal) {
    return;
  }

  var modalBody = document.getElementById("subscribe-modal-body");
  var successPanel = document.getElementById("subscribe-success");
  var successTitle = successPanel ? successPanel.querySelector("h3") : null;
  var successText = successPanel ? successPanel.querySelector("p") : null;
  var formMounted = false;
  var selectedTickers = [];
  var searchTimer = null;
  var validateTimer = null;
  var activeSuggestion = -1;
  var currentSuggestions = [];
  var searchRequestId = 0;
  var validateRequestId = 0;

  var els = {};

  function mountForm() {
    if (formMounted || !modalBody) {
      return;
    }
    modalBody.innerHTML =
      '<form class="subscribe-form" id="subscribe-form" novalidate>' +
      '<p class="subscribe-error" id="subscribe-error" hidden></p>' +
      '<label for="subscribe-email">Email</label>' +
      '<input type="email" id="subscribe-email" name="email" required autocomplete="email" placeholder="you@example.com">' +
      '<label for="subscribe-ticker-input">US tickers (up to ' + MAX_TICKERS + ')</label>' +
      '<div class="subscribe-ticker-field">' +
      '<div class="subscribe-ticker-row">' +
      '<input type="text" id="subscribe-ticker-input" class="subscribe-ticker-input" autocomplete="off" placeholder="Search by ticker or company name">' +
      '<button type="button" class="subscribe-add-btn" id="subscribe-add-btn">Add</button>' +
      "</div>" +
      '<p class="subscribe-field-status" id="subscribe-field-status">Search, pick a match, or press Enter to validate.</p>' +
      '<ul class="subscribe-suggestions" id="subscribe-suggestions" hidden></ul>' +
      "</div>" +
      '<div class="subscribe-chips" id="subscribe-chips"></div>' +
      '<p class="subscribe-hint">Each ticker is validated as a US-listed stock or ETF before it is added.</p>' +
      '<button type="submit" class="btn-subscribe" id="subscribe-submit">Get your digest</button>' +
      "</form>";

    els.form = document.getElementById("subscribe-form");
    els.email = document.getElementById("subscribe-email");
    els.tickerInput = document.getElementById("subscribe-ticker-input");
    els.addBtn = document.getElementById("subscribe-add-btn");
    els.fieldStatus = document.getElementById("subscribe-field-status");
    els.suggestions = document.getElementById("subscribe-suggestions");
    els.chips = document.getElementById("subscribe-chips");
    els.error = document.getElementById("subscribe-error");
    els.submit = document.getElementById("subscribe-submit");

    els.form.addEventListener("submit", onSubmit);
    els.tickerInput.addEventListener("input", onSearchInput);
    els.tickerInput.addEventListener("keydown", onTickerKeydown);
    els.tickerInput.addEventListener("blur", onTickerBlur);
    els.addBtn.addEventListener("click", function () {
      validateAndAddInput();
    });
    els.suggestions.addEventListener("click", onSuggestionClick);
    document.addEventListener("click", onDocumentClick);

    formMounted = true;
    syncTickerInputState();
  }

  function showError(message) {
    if (!els.error) {
      return;
    }
    if (!message) {
      els.error.hidden = true;
      els.error.textContent = "";
      return;
    }
    els.error.hidden = false;
    els.error.textContent = message;
  }

  function setFieldStatus(kind, message) {
    if (!els.fieldStatus) {
      return;
    }
    els.fieldStatus.textContent = message || "";
    els.fieldStatus.className = "subscribe-field-status";
    if (kind) {
      els.fieldStatus.classList.add("is-" + kind);
    }
  }

  function syncTickerInputState() {
    if (!els.tickerInput || !els.addBtn) {
      return;
    }
    var full = selectedTickers.length >= MAX_TICKERS;
    els.tickerInput.disabled = full;
    els.addBtn.disabled = full;
    els.tickerInput.placeholder = full
      ? "Maximum tickers reached"
      : "Search by ticker or company name";
  }

  function renderChips() {
    if (!els.chips) {
      return;
    }
    els.chips.innerHTML = selectedTickers
      .map(function (symbol) {
        return (
          '<span class="subscribe-chip">' +
          symbol +
          '<button type="button" class="subscribe-chip-remove" data-symbol="' +
          symbol +
          '" aria-label="Remove ' +
          symbol +
          '">&times;</button>' +
          "</span>"
        );
      })
      .join("");

    els.chips.querySelectorAll(".subscribe-chip-remove").forEach(function (btn) {
      btn.addEventListener("click", function () {
        removeTicker(btn.getAttribute("data-symbol"));
      });
    });
    syncTickerInputState();
  }

  function addTicker(symbol) {
    var upper = (symbol || "").trim().toUpperCase();
    if (!upper) {
      return false;
    }
    if (selectedTickers.indexOf(upper) !== -1) {
      setFieldStatus("error", upper + " is already in your list.");
      return false;
    }
    if (selectedTickers.length >= MAX_TICKERS) {
      showError("Maximum " + MAX_TICKERS + " tickers allowed.");
      return false;
    }
    selectedTickers.push(upper);
    renderChips();
    hideSuggestions();
    if (els.tickerInput) {
      els.tickerInput.value = "";
    }
    showError("");
    setFieldStatus("success", upper + " added. Add another or submit.");
    return true;
  }

  function removeTicker(symbol) {
    var upper = (symbol || "").trim().toUpperCase();
    selectedTickers = selectedTickers.filter(function (item) {
      return item !== upper;
    });
    renderChips();
    showError("");
    setFieldStatus("neutral", "Search, pick a match, or press Enter to validate.");
  }

  function hideSuggestions() {
    if (!els.suggestions) {
      return;
    }
    els.suggestions.hidden = true;
    els.suggestions.innerHTML = "";
    currentSuggestions = [];
    activeSuggestion = -1;
  }

  function renderSuggestions(items) {
    if (!els.suggestions) {
      return;
    }
    currentSuggestions = items;
    activeSuggestion = -1;
    if (!items.length) {
      hideSuggestions();
      return;
    }
    els.suggestions.innerHTML = items
      .map(function (item, index) {
        return (
          '<li class="subscribe-suggestion" data-index="' +
          index +
          '"><strong>' +
          item.symbol +
          "</strong> — " +
          item.name +
          "</li>"
        );
      })
      .join("");
    els.suggestions.hidden = false;
    setFieldStatus("neutral", "Select a match below or press Enter.");
  }

  function parseJsonResponse(response) {
    return response.text().then(function (text) {
      if (!text) {
        return {};
      }
      if (text.charAt(0) === "<") {
        return {
          ok: false,
          error: "API unavailable. Run: python3 scripts/dev_server.py",
        };
      }
      try {
        return JSON.parse(text);
      } catch (e) {
        return { ok: false, error: "Unexpected server response." };
      }
    });
  }

  function rankSuggestion(query, item) {
    var upper = query.trim().toUpperCase();
    var lower = query.trim().toLowerCase();
    var symbol = item.symbol || "";
    var name = (item.name || "").toLowerCase();
    if (symbol === upper) {
      return 100;
    }
    if (symbol.indexOf(upper) === 0) {
      return 80;
    }
    if (name.indexOf(lower) === 0) {
      return 70;
    }
    if (name.indexOf(lower) !== -1) {
      return 50;
    }
    return 0;
  }

  function pickBestSuggestion(query) {
    var best = null;
    var bestScore = 0;
    for (var i = 0; i < currentSuggestions.length; i++) {
      var score = rankSuggestion(query, currentSuggestions[i]);
      if (score > bestScore) {
        bestScore = score;
        best = currentSuggestions[i];
      }
    }
    return bestScore >= 50 ? best : null;
  }

  function onSearchInput() {
    var query = (els.tickerInput.value || "").trim();
    if (searchTimer) {
      window.clearTimeout(searchTimer);
    }
    if (validateTimer) {
      window.clearTimeout(validateTimer);
    }

    if (!query) {
      hideSuggestions();
      setFieldStatus("neutral", "Search, pick a match, or press Enter to validate.");
      return;
    }

    if (query.length < 1) {
      hideSuggestions();
      return;
    }

    setFieldStatus("loading", "Searching...");
    var requestId = ++searchRequestId;
    searchTimer = window.setTimeout(function () {
      fetch("/api/tickers/search?q=" + encodeURIComponent(query))
        .then(function (response) {
          return parseJsonResponse(response).then(function (data) {
            return { status: response.status, data: data };
          });
        })
        .then(function (result) {
          if (requestId !== searchRequestId) {
            return;
          }
          if (!result.data.ok) {
            hideSuggestions();
            setFieldStatus(
              "error",
              result.data.error || "Search failed. Check your connection and try again."
            );
            return;
          }
          var results = result.data.results || [];
          if (!results.length) {
            hideSuggestions();
            setFieldStatus("error", "No US stocks or ETFs found for \"" + query + "\".");
            return;
          }
          renderSuggestions(results);
        })
        .catch(function () {
          if (requestId !== searchRequestId) {
            return;
          }
          hideSuggestions();
          setFieldStatus("error", "Could not search right now. Try again.");
        });
    }, SEARCH_DEBOUNCE_MS);
  }

  function findExactSuggestion(query) {
    var upper = query.trim().toUpperCase();
    for (var i = 0; i < currentSuggestions.length; i++) {
      if (currentSuggestions[i].symbol === upper) {
        return currentSuggestions[i];
      }
    }
    return null;
  }

  function validateSymbol(symbol) {
    var query = (symbol || "").trim();
    if (!query) {
      return Promise.resolve({ ok: false, valid: false, error: "Enter a ticker or company name." });
    }

    setFieldStatus("loading", "Validating " + query + "...");
    var requestId = ++validateRequestId;

    return fetch("/api/tickers/validate?symbol=" + encodeURIComponent(query))
      .then(function (response) {
        return parseJsonResponse(response).then(function (data) {
          return { status: response.status, data: data };
        });
      })
      .then(function (result) {
        if (requestId !== validateRequestId) {
          return null;
        }
        if (!result.data.ok) {
          setFieldStatus("error", result.data.error || "Validation failed.");
          return null;
        }
        if (!result.data.valid) {
          setFieldStatus("error", result.data.error || "Could not validate " + query + ".");
          return null;
        }
        return result.data;
      })
      .catch(function () {
        if (requestId !== validateRequestId) {
          return null;
        }
        setFieldStatus("error", "Could not validate right now. Try again.");
        return null;
      });
  }

  function validateAndAddInput() {
    var query = (els.tickerInput.value || "").trim();
    if (!query) {
      setFieldStatus("error", "Enter a ticker or company name.");
      return;
    }

    if (activeSuggestion >= 0 && currentSuggestions[activeSuggestion]) {
      addTicker(currentSuggestions[activeSuggestion].symbol);
      return;
    }

    var exact = findExactSuggestion(query);
    if (exact) {
      addTicker(exact.symbol);
      return;
    }

    var best = pickBestSuggestion(query);
    if (best) {
      addTicker(best.symbol);
      return;
    }

    if (els.addBtn) {
      els.addBtn.disabled = true;
    }

    validateSymbol(query).then(function (data) {
      if (els.addBtn) {
        els.addBtn.disabled = selectedTickers.length >= MAX_TICKERS;
      }
      if (!data) {
        return;
      }
      if (addTicker(data.symbol)) {
        setFieldStatus("success", data.symbol + " — " + data.name);
      }
    });
  }

  function onSuggestionClick(event) {
    var target = event.target.closest(".subscribe-suggestion");
    if (!target) {
      return;
    }
    var index = parseInt(target.getAttribute("data-index"), 10);
    var item = currentSuggestions[index];
    if (item) {
      addTicker(item.symbol);
    }
  }

  function onTickerKeydown(event) {
    if (event.key === "ArrowDown" && currentSuggestions.length && !els.suggestions.hidden) {
      event.preventDefault();
      activeSuggestion = Math.min(activeSuggestion + 1, currentSuggestions.length - 1);
      highlightSuggestion();
      return;
    }
    if (event.key === "ArrowUp" && currentSuggestions.length && !els.suggestions.hidden) {
      event.preventDefault();
      activeSuggestion = Math.max(activeSuggestion - 1, 0);
      highlightSuggestion();
      return;
    }
    if (event.key === "Enter") {
      event.preventDefault();
      validateAndAddInput();
      return;
    }
    if (event.key === "Escape") {
      hideSuggestions();
    }
  }

  function onTickerBlur() {
    window.setTimeout(function () {
      if (!els.suggestions || els.suggestions.hidden) {
        return;
      }
      hideSuggestions();
    }, 150);
  }

  function highlightSuggestion() {
    var nodes = els.suggestions.querySelectorAll(".subscribe-suggestion");
    nodes.forEach(function (node, index) {
      node.classList.toggle("is-active", index === activeSuggestion);
    });
  }

  function onDocumentClick(event) {
    if (!els.tickerInput || !els.suggestions) {
      return;
    }
    if (
      !els.tickerInput.contains(event.target) &&
      !els.suggestions.contains(event.target) &&
      !(els.addBtn && els.addBtn.contains(event.target))
    ) {
      hideSuggestions();
    }
  }

  function onSubmit(event) {
    event.preventDefault();
    showError("");

    var email = (els.email.value || "").trim();
    if (!email) {
      showError("Enter your email address.");
      return;
    }
    if (!selectedTickers.length) {
      showError("Add at least one validated ticker.");
      return;
    }

    els.submit.disabled = true;
    fetch("/api/subscribe", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email, tickers: selectedTickers }),
    })
      .then(function (response) {
        return parseJsonResponse(response).then(function (data) {
          return { status: response.status, data: data };
        });
      })
      .then(function (result) {
        if (!result.data.ok) {
          showError(result.data.error || "Something went wrong. Try again.");
          return;
        }
        showSuccess(result.data);
      })
      .catch(function () {
        showError("Could not connect. Try again in a moment.");
      })
      .finally(function () {
        els.submit.disabled = false;
      });
  }

  function showSuccess(data) {
    if (modalBody) {
      modalBody.hidden = true;
    }
    if (successPanel) {
      successPanel.hidden = false;
    }
    if (successTitle) {
      successTitle.textContent =
        data.mode === "update" ? "Tickers updated" : "Almost there";
    }
    if (successText) {
      successText.textContent =
        data.mode === "update"
          ? (data.message || "Your tickers update on the next session.")
          : "Confirm your email to subscribe.";
    }
    window.setTimeout(function () {
      closeSubscribeModal();
    }, 2200);
  }

  function resetForm() {
    selectedTickers = [];
    searchRequestId += 1;
    validateRequestId += 1;
    hideSuggestions();
    if (els.email) {
      els.email.value = "";
    }
    if (els.tickerInput) {
      els.tickerInput.value = "";
    }
    renderChips();
    showError("");
    setFieldStatus("neutral", "Search, pick a match, or press Enter to validate.");
    if (modalBody) {
      modalBody.hidden = false;
    }
    if (successPanel) {
      successPanel.hidden = true;
    }
  }

  window.openSubscribeModal = function () {
    mountForm();
    resetForm();
    modal.hidden = false;
    document.body.style.overflow = "hidden";
    if (els.email) {
      window.setTimeout(function () {
        els.email.focus();
      }, 50);
    }
  };

  window.closeSubscribeModal = function () {
    modal.hidden = true;
    document.body.style.overflow = "";
    hideSuggestions();
  };

  window.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && !modal.hidden) {
      closeSubscribeModal();
    }
  });

  function openFromHash() {
    var hash = (window.location.hash || "").toLowerCase();
    if (hash === "#subscribe" || hash === "#update-tickers") {
      openSubscribeModal();
    }
  }

  window.addEventListener("hashchange", openFromHash);
  openFromHash();
})();
