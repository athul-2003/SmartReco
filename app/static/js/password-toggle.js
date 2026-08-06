/**
 * Show/hide toggle for password fields on the login/register forms - pure
 * UI convenience, no data ever leaves the page differently either way.
 */
(function () {
  "use strict";

  var eyeOpen =
    '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/><circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="1.6"/>';
  var eyeOff =
    '<path d="M3 3l18 18M10.6 10.6a3 3 0 0 0 4.24 4.24M6.6 6.7C4.5 8.1 3 10 2 12c0 0 3.5 7 10 7 1.8 0 3.36-.42 4.68-1.06M17.4 17.3C19.3 15.9 20.7 14.1 22 12c0 0-1.44-2.88-4.24-4.9M14.1 5.3A10.7 10.7 0 0 0 12 5c-.7 0-1.36.06-2 .17" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>';

  document.querySelectorAll(".password-toggle").forEach(function (btn) {
    var input = document.getElementById(btn.getAttribute("data-toggle-for"));
    if (!input) return;
    btn.addEventListener("click", function () {
      var showing = input.type === "text";
      input.type = showing ? "password" : "text";
      btn.querySelector("svg").innerHTML = showing ? eyeOpen : eyeOff;
      btn.setAttribute("aria-label", showing ? "Show password" : "Hide password");
    });
  });
})();
