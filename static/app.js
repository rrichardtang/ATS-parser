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

  // Rewrite generation is a separate, explicit step -- the button lives inside
  // the report HTML that just got swapped in, so listen on the stable container
  // instead of the button itself.
  var generating = false;

  out.addEventListener("click", function (event) {
    var button2 = event.target.closest("#generate-rewrites");
    if (!button2 || generating) return;

    var spinner2 = document.getElementById("generate-spinner");
    var token = button2.getAttribute("data-token");
    var body = new FormData();
    body.append("anthropic_key", (form.querySelector("#anthropic_key") || {}).value || "");
    body.append("openai_key", (form.querySelector("#openai_key") || {}).value || "");
    body.append("mode", (form.querySelector("#mode") || {}).value || "default");

    generating = true;
    button2.disabled = true;
    button2.textContent = "Generating…";
    if (spinner2) {
      spinner2.textContent = "Rewriting the worst bullets…";
      spinner2.style.display = "block";
    }

    fetch("/generate/" + encodeURIComponent(token), { method: "POST", body: body })
      .then(function (response) {
        if (!response.ok) throw new Error("server returned " + response.status);
        return response.text();
      })
      .then(function (html) {
        out.innerHTML = html;
        // Scroll to the rewrites themselves, not the top of #out -- that button
        // sits near the bottom of a long report, and scrolling the container's
        // top into view yanks the page back up past everything the click just
        // produced, which reads as "nothing happened."
        var target = out.querySelector(".rewrites") || out;
        target.scrollIntoView({ behavior: "smooth", block: "start" });
      })
      .catch(function (error) {
        out.innerHTML =
          '<div class="banner bad"><strong>Generating rewrites failed.</strong> ' +
          String(error.message || error) +
          " — check the server log.</div>";
      })
      .finally(function () {
        generating = false;
      });
  });
})();
