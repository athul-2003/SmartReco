/**
 * Non-blocking behavioral event tracker. Batches view/search/click/dwell
 * events and flushes on whichever comes first: 10s elapsed, 20 events
 * queued, or the page unloading. Never throws into the page - a failed
 * or blocked network call must not affect the UI.
 */
(function () {
  "use strict";

  var ENDPOINT = "/events";
  var FLUSH_INTERVAL_MS = 10000;
  var FLUSH_MAX_EVENTS = 20;

  var queue = [];
  var flushTimer = null;

  function enqueue(eventType, productId, metadata) {
    queue.push({
      event_type: eventType,
      product_id: productId || null,
      metadata: metadata || null,
    });
    if (queue.length >= FLUSH_MAX_EVENTS) {
      flush(false);
    } else {
      scheduleFlush();
    }
  }

  function scheduleFlush() {
    if (flushTimer) return;
    flushTimer = setTimeout(function () {
      flush(false);
    }, FLUSH_INTERVAL_MS);
  }

  function flush(useBeacon) {
    if (flushTimer) {
      clearTimeout(flushTimer);
      flushTimer = null;
    }
    if (queue.length === 0) return;
    var batch = queue;
    queue = [];
    var body = JSON.stringify({ events: batch });

    if (useBeacon && navigator.sendBeacon) {
      var blob = new Blob([body], { type: "application/json" });
      navigator.sendBeacon(ENDPOINT, blob);
      return;
    }

    fetch(ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body,
      keepalive: true,
    }).catch(function () {
      // Tracking must never surface an error to the user.
    });
  }

  function trackView() {
    var el = document.querySelector("[data-track-view]");
    if (el) {
      enqueue("view", Number(el.getAttribute("data-track-view")));
    }
    return el;
  }

  function trackClicks() {
    document.addEventListener("click", function (evt) {
      var card = evt.target.closest("[data-product-id]");
      if (card) {
        enqueue("click", Number(card.getAttribute("data-product-id")));
      }
    });
  }

  function trackSearch() {
    var form = document.querySelector("[data-track-search]");
    if (!form) return;
    form.addEventListener("submit", function () {
      var input = form.querySelector('input[name="q"]');
      var q = input ? input.value.trim() : "";
      if (q) {
        enqueue("search", null, { query: q });
      }
    });
  }

  function trackDwell(viewEl) {
    if (!viewEl) return;
    var productId = Number(viewEl.getAttribute("data-track-view"));
    var start = Date.now();
    var sent = false;

    function sendDwell() {
      if (sent) return;
      var seconds = Math.round((Date.now() - start) / 1000);
      if (seconds < 1) return;
      sent = true;
      enqueue("dwell", productId, { seconds: seconds });
      flush(true);
    }

    document.addEventListener("visibilitychange", function () {
      if (document.visibilityState === "hidden") sendDwell();
    });
    window.addEventListener("pagehide", sendDwell);
  }

  function init() {
    var viewEl = trackView();
    trackClicks();
    trackSearch();
    trackDwell(viewEl);

    window.addEventListener("pagehide", function () {
      flush(true);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
