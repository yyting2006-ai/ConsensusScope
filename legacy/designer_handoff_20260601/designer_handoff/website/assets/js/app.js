document.addEventListener("DOMContentLoaded", () => {
  const page = document.body.dataset.page;
  document.querySelectorAll("[data-nav]").forEach((link) => {
    link.classList.toggle("is-active", link.dataset.nav === page);
  });

  const menuButton = document.querySelector("[data-menu]");
  if (menuButton) {
    menuButton.addEventListener("click", () => {
      document.body.classList.toggle("nav-open");
    });
  }

  document.querySelectorAll("[data-tabs]").forEach((tabRoot) => {
    const tabs = Array.from(tabRoot.querySelectorAll("[data-tab]"));
    const panels = Array.from(tabRoot.querySelectorAll("[data-tab-panel]"));
    tabs.forEach((tab) => {
      tab.addEventListener("click", () => {
        const id = tab.dataset.tab;
        tabs.forEach((item) => item.classList.toggle("is-active", item === tab));
        panels.forEach((panel) => panel.classList.toggle("is-active", panel.dataset.tabPanel === id));
      });
    });
  });

  document.querySelectorAll("[data-filter]").forEach((button) => {
    button.addEventListener("click", () => {
      const target = button.dataset.filter;
      document.querySelectorAll("[data-filter]").forEach((item) => item.classList.remove("is-active"));
      button.classList.add("is-active");
      document.querySelectorAll("[data-risk-row]").forEach((row) => {
        row.style.display = target === "all" || row.dataset.riskRow === target ? "" : "none";
      });
    });
  });

  document.querySelectorAll("[data-copy]").forEach((button) => {
    button.addEventListener("click", async () => {
      const text = button.dataset.copy || "";
      try {
        await navigator.clipboard.writeText(text);
        button.textContent = "Copied";
        setTimeout(() => (button.textContent = "Copy path"), 1400);
      } catch {
        button.textContent = "Copy failed";
      }
    });
  });
});
