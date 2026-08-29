/* The whole interaction is: post the form, swap in the report, keep the button
   honest about what is happening. No framework, and no network dependency --
   this tool has to work on a laptop with no internet. */
(function () {
  "use strict";

  var form = document.getElementById("analyze-form");
  if (!form) return;

  var out = document.getElementById("out");
  var button = form.querySelector("button.go");
  var spinner = form.querySelector(".spinner");
  var busy = false;

  function setBusy(state, label) {
    busy = state;
    button.disabled = state;
    button.textContent = state ? "Analyzing…" : "Analyze resume";
    spinner.textContent = label || "";
    spinner.style.display = state ? "block" : "none";
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    if (busy) return;

    var file = form.querySelector('input[type="file"]');
    if (!file.files.length) {
      out.innerHTML = '<div class="banner bad">Choose a PDF first.</div>';
      return;
    }

    setBusy(true, "Extracting layout, running checks…");
    out.innerHTML = "";

    fetch(form.action || "/analyze", { method: "POST", body: new FormData(form) })
      .then(function (response) {
        if (!response.ok) throw new Error("server returned " + response.status);
        return response.text();
      })
      .then(function (html) {
        out.innerHTML = html;
        out.scrollIntoView({ behavior: "smooth", block: "start" });
      })
      .catch(function (error) {
        out.innerHTML =
          '<div class="banner bad"><strong>Analysis failed.</strong> ' +
          String(error.message || error) +
          " — check the server log.</div>";
      })
      .finally(function () {
        setBusy(false);
      });
  });
})();
