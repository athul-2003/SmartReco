/**
 * Bootstraps the "generating" page in two phases. It used to be that
 * retrieval (a real Mesh embed + Qdrant query) ran synchronously in the
 * request that rendered this page, so the browser showed nothing at all
 * until that network round-trip finished. Now the page renders instantly
 * with a loading placeholder, and this script fetches
 * /recommendations/candidates itself once the page is already visible,
 * renders the product cards when they arrive, then streams the narrative
 * the same way as before via /recommendations/stream.
 */
(function () {
  "use strict";

  var scriptEl = document.currentScript;
  var triggerReason = scriptEl.getAttribute("data-trigger-reason") || "manual";
  var narrativeEl = document.getElementById("narrative-text");
  var gridContainer = document.getElementById("product-grid-container");
  if (!narrativeEl || !gridContainer) return;

  function showFailureMessage() {
    narrativeEl.textContent =
      "We couldn't generate your recommendations just now - refresh to try again.";
    narrativeEl.classList.remove("narrative-loading");
    if (gridContainer && gridContainer.parentNode) gridContainer.remove();
  }

  function buildProductCard(product) {
    var card = document.createElement("a");
    card.href = "/catalog/" + product.id;
    card.className = "product-card";
    card.setAttribute("data-product-id", product.id);

    var cover = document.createElement("div");
    cover.className = "product-cover " + product.cover_class;
    var letter = document.createElement("span");
    letter.textContent = product.cover_letter;
    cover.appendChild(letter);

    var body = document.createElement("div");
    body.className = "product-card-body";

    var chip = document.createElement("span");
    chip.className = "chip";
    chip.textContent = product.category;

    var title = document.createElement("h3");
    title.textContent = product.title;

    var description = document.createElement("p");
    description.className = "product-description";
    description.textContent = product.description;

    var meta = document.createElement("div");
    meta.className = "product-meta";
    var price = document.createElement("span");
    price.textContent =
      product.price === 0 ? "Free" : "₹" + product.price.toFixed(2);
    var arrow = document.createElement("span");
    arrow.textContent = "→";
    meta.appendChild(price);
    meta.appendChild(arrow);

    body.appendChild(chip);
    body.appendChild(title);
    body.appendChild(description);
    body.appendChild(meta);
    card.appendChild(cover);
    card.appendChild(body);
    return card;
  }

  function renderProducts(candidates) {
    if (!candidates.length) return;
    var grid = document.createElement("div");
    grid.className = "product-grid";
    candidates.forEach(function (product) {
      grid.appendChild(buildProductCard(product));
    });
    gridContainer.replaceWith(grid);
  }

  function startStream(candidateIds, reason) {
    var source = new EventSource(
      "/recommendations/stream?candidate_ids=" +
        encodeURIComponent(candidateIds) +
        "&reason=" +
        encodeURIComponent(reason)
    );
    var started = false;

    source.onmessage = function (event) {
      if (!started) {
        narrativeEl.textContent = "";
        narrativeEl.classList.remove("narrative-loading");
        started = true;
      }
      narrativeEl.textContent += event.data;
    };

    source.addEventListener("done", function () {
      source.close();
    });

    // Server-sent "failed" event: the request reached Mesh but generation
    // itself errored out before any text arrived.
    source.addEventListener("failed", function () {
      source.close();
      showFailureMessage();
    });

    // Built-in EventSource "error": a connection-level failure (network
    // drop, non-200 response, etc.), distinct from the server-sent "failed"
    // event above.
    source.onerror = function () {
      source.close();
      if (!started) showFailureMessage();
    };
  }

  fetch("/recommendations/candidates?reason=" + encodeURIComponent(triggerReason))
    .then(function (response) {
      return response.json();
    })
    .then(function (data) {
      if (data.status === "redirect") {
        window.location.href = data.redirect;
        return;
      }
      if (data.status === "failed") {
        showFailureMessage();
        return;
      }
      renderProducts(data.candidates);
      startStream(data.candidate_ids, data.trigger_reason);
    })
    .catch(function () {
      showFailureMessage();
    });
})();
