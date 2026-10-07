(function () {
  "use strict";
  const token = document.querySelector('meta[name="admin-csrf-token"]')?.content;
  const baseValue = document.querySelector('meta[name="admin-base-url"]')?.content;
  if (!token || !baseValue) return;
  const base = new URL(baseValue, window.location.href);
  const prefix = base.pathname.replace(/\/+$/, "");
  const safe = new Set(["GET", "HEAD", "OPTIONS"]);
  function protectedRequest(urlValue, method) {
    const url = new URL(urlValue, window.location.href);
    return !safe.has(String(method || "GET").toUpperCase()) &&
      url.origin === window.location.origin &&
      (url.pathname === prefix || url.pathname.startsWith(prefix + "/"));
  }
  function protectForm(form) {
    if (!protectedRequest(form.action, form.method)) return;
    let field = form.querySelector('input[name="csrf_token"]');
    if (!field) {
      field = document.createElement("input");
      field.type = "hidden";
      field.name = "csrf_token";
      form.append(field);
    }
    field.value = token;
  }
  document.querySelectorAll("form").forEach(protectForm);
  document.addEventListener("submit", function (event) {
    if (event.target instanceof HTMLFormElement) protectForm(event.target);
  }, true);
  if (window.jQuery) {
    window.jQuery.ajaxPrefilter(function (options, original, xhr) {
      if (protectedRequest(options.url, options.type || options.method)) {
        xhr.setRequestHeader("X-CSRF-Token", token);
      }
    });
  }
  const originalFetch = window.fetch;
  window.fetch = function (input, init) {
    const options = init ? {...init} : {};
    const isRequest = input instanceof Request;
    const method = options.method || (isRequest ? input.method : "GET");
    const url = isRequest ? input.url : input;
    if (protectedRequest(url, method)) {
      const headers = new Headers(options.headers || (isRequest ? input.headers : undefined));
      headers.set("X-CSRF-Token", token);
      options.headers = headers;
    }
    return originalFetch.call(this, input, options);
  };
})();
