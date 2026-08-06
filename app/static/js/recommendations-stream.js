/**
 * Streams the recommendation narrative via Server-Sent Events instead of
 * making the user wait on a blank page for the full Mesh generation to
 * finish. The product cards are already server-rendered (retrieval, the
 * fast part, already ran); this only streams the slower narrative text.
 */
(function () {
  "use strict";

  var scriptEl = document.currentScript;
  var candidateIds = scriptEl.getAttribute("data-candidate-ids") || "";
  var narrativeEl = document.getElementById("narrative-text");
  if (!narrativeEl || !candidateIds) return;

  var source = new EventSource(
    "/recommendations/stream?candidate_ids=" + encodeURIComponent(candidateIds)
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

  source.onerror = function () {
    source.close();
    if (!started) {
      narrativeEl.textContent = "We couldn't generate your recommendations just now - refresh to try again.";
      narrativeEl.classList.remove("narrative-loading");
    }
  };
})();
