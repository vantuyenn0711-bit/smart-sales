(() => {
  "use strict";
  const loading = document.getElementById("page-loading");
  const connectionError = document.getElementById("connection-error");
  document.querySelectorAll("[data-password-toggle]").forEach((button) => {
    const input = document.getElementById(button.getAttribute("aria-controls"));
    if (!input) return;
    button.hidden = false;
    button.addEventListener("click", () => {
      const reveal = input.type === "password";
      input.type = reveal ? "text" : "password";
      button.setAttribute("aria-pressed", String(reveal));
      button.setAttribute("aria-label", reveal ? "Ẩn mật khẩu" : "Hiện mật khẩu");
      button.textContent = reveal ? "Ẩn" : "Hiện";
    });
  });
  const sidebar = document.getElementById("sidebar");
  const mobileViewport = window.matchMedia("(max-width: 800px)");
  const setMenu = (open) => {
    document.body.classList.toggle("menu-open", open);
    document.querySelector("[data-toggle-menu]")?.setAttribute("aria-expanded", String(open));
    if (sidebar) {
      sidebar.inert = mobileViewport.matches && !open;
      sidebar.setAttribute("aria-hidden", String(sidebar.inert));
    }
  };
  setMenu(false);
  mobileViewport.addEventListener("change", () => setMenu(false));
  document.querySelector("[data-toggle-menu]")?.addEventListener("click", () => setMenu(!document.body.classList.contains("menu-open")));
  document.querySelector("[data-close-menu]")?.addEventListener("click", () => setMenu(false));
  document.addEventListener("keydown", (event) => { if (event.key === "Escape") setMenu(false); });
  document.querySelectorAll("[data-dismiss]").forEach((button) => button.addEventListener("click", () => button.parentElement.remove()));
  document.querySelectorAll("[data-print]").forEach((button) => button.addEventListener("click", () => window.print()));
  document.addEventListener("submit", (event) => {
    const form = event.target;
    if (form.dataset.confirm && !window.confirm(form.dataset.confirm)) { event.preventDefault(); return; }
    if ((form.dataset.loading !== undefined || form.classList.contains("filter-bar")) && !event.defaultPrevented) {
      if (form.classList.contains("is-submitting")) { event.preventDefault(); return; }
      form.classList.add("is-submitting");
      form.setAttribute("aria-busy", "true");
      loading?.classList.add("active");
    }
  });
  window.addEventListener("pageshow", () => {
    loading?.classList.remove("active");
    document.querySelectorAll(".is-submitting").forEach((form) => { form.classList.remove("is-submitting"); form.removeAttribute("aria-busy"); });
  });
  const showConnectionError = () => { if (connectionError) { connectionError.hidden = false; connectionError.scrollIntoView({ block: "nearest" }); } };
  window.addEventListener("offline", showConnectionError);
  window.addEventListener("online", () => { if (connectionError) connectionError.hidden = true; });
  document.body.addEventListener("htmx:sendError", showConnectionError);
  document.body.addEventListener("htmx:responseError", showConnectionError);
  document.body.addEventListener("htmx:beforeRequest", () => loading?.classList.add("active"));
  document.body.addEventListener("htmx:afterRequest", (event) => {
    loading?.classList.remove("active");
    event.detail.elt?.classList.remove("is-submitting");
    event.detail.elt?.removeAttribute("aria-busy");
  });

  const orderItems = document.getElementById("order-items");
  if (!orderItems) return;
  const totalForms = document.getElementById("id_items-TOTAL_FORMS");
  const emptyRow = document.getElementById("empty-row");
  const products = new Map(JSON.parse(document.getElementById("product-data")?.textContent || "[]").map((product) => [String(product.id), product]));
  const formatMoney = (value) => new Intl.NumberFormat("vi-VN", { style: "currency", currency: "VND", maximumFractionDigits: 0 }).format(value);
  const refresh = () => {
    let subtotal = 0;
    orderItems.querySelectorAll(".order-row").forEach((row) => {
      if (row.hidden) return;
      const product = products.get(row.querySelector('[name$="-product"]')?.value);
      const quantity = Number(row.querySelector('[name$="-quantity"]')?.value || 0);
      const info = row.querySelector(".line-product-info");
      if (info) info.textContent = product ? `${formatMoney(Number(product.price))} / sản phẩm · Tồn ${product.stock}` : "";
      subtotal += product ? Number(product.price) * Math.max(0, quantity) : 0;
    });
    const discount = Number(document.getElementById("id_discount")?.value || 0);
    document.getElementById("order-estimate").textContent = formatMoney(Math.max(0, subtotal - discount));
  };
  orderItems.addEventListener("click", (event) => {
    const button = event.target.closest("[data-remove-item]");
    if (!button) return;
    const row = button.closest(".order-row");
    row.querySelector('[name$="-DELETE"]').checked = true;
    row.hidden = true;
    row.querySelectorAll("input, select").forEach((input) => input.removeAttribute("required"));
    refresh();
  });
  document.querySelector("[data-add-item]")?.addEventListener("click", () => {
    const count = Number(totalForms.value);
    if (count >= 50) { window.alert("Mỗi đơn có tối đa 50 dòng sản phẩm."); return; }
    const container = document.createElement("div");
    container.innerHTML = emptyRow.innerHTML.replaceAll("__prefix__", String(count));
    orderItems.append(container.firstElementChild);
    totalForms.value = String(count + 1);
    orderItems.lastElementChild.querySelector("select")?.focus();
    refresh();
  });
  orderItems.addEventListener("input", refresh);
  orderItems.addEventListener("change", refresh);
  document.getElementById("id_discount")?.addEventListener("input", refresh);
  refresh();
})();
