const tabButtons = document.querySelectorAll(".tab");

tabButtons.forEach((button) => {
  button.addEventListener("click", () => {
    tabButtons.forEach((other) => other.classList.toggle("active", other === button));
    document.querySelectorAll(".panel").forEach((panel) => {
      panel.classList.toggle("active", panel.id === `tab-${button.dataset.tab}`);
    });
    document.dispatchEvent(new CustomEvent("tabchange", { detail: button.dataset.tab }));
  });
});
