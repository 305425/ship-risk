function esmLogo(className) {
  const logo = document.createElement("img");
  logo.src = "/chat/public/esm-logo.png";
  logo.alt = "Executive Ship Management";
  logo.className = className;
  return logo;
}

function esmMark() {
  const heading = document.querySelector("h1");
  if (heading && /login/i.test(heading.textContent || "") && !heading.parentElement.querySelector(".esm-login-logo")) {
    heading.parentElement.insertBefore(esmLogo("esm-login-logo"), heading);
  }
  const bar = document.querySelector(".h-\\[60px\\]");
  if (bar && !bar.querySelector(".esm-header-logo")) {
    bar.insertBefore(esmLogo("esm-header-logo"), bar.firstChild);
  }
}

esmMark();
new MutationObserver(esmMark).observe(document.documentElement, { childList: true, subtree: true });
