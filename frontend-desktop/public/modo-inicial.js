(function () {
  try {
    var modo = window.localStorage.getItem("silice-modo");
    var raiz = document.documentElement;
    var meta = document.querySelector('meta[name="color-scheme"]');
    if (modo === "claro" || modo === "oscuro") {
      raiz.dataset.modo = modo;
      if (meta) meta.setAttribute("content", modo === "claro" ? "light" : "dark");
    } else {
      delete raiz.dataset.modo;
      if (meta) meta.setAttribute("content", "light dark");
    }
  } catch (_) {
    // Sin almacenamiento o con acceso bloqueado rige el modo del sistema.
  }
})();
