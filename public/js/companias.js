// =========================
// Tela de primeiro acesso — cadastro de empresa
// =========================

const API_BASE = "/api/companias";
const MAX_FILE_BYTES = 10 * 1024 * 1024;

// =========================
// DOM refs
// =========================
const form        = document.getElementById("companie-form");
const toastEl     = document.getElementById("toast");
const cnpjInput   = document.getElementById("cnpj");

const dropzone    = document.getElementById("dropzone");
const imgInput    = document.getElementById("imagem");
const previewImg  = document.getElementById("preview-img");
const previewEmpty = document.getElementById("preview-empty");

const btnTrocar   = document.getElementById("btnTrocarLogo");
const btnRemover  = document.getElementById("btnRemoverLogo");

const btnSalvar   = document.getElementById("btnSalvar");
const btnLbl      = btnSalvar.querySelector(".lbl");
const btnSpinner  = btnSalvar.querySelector(".spinner");

let imageDataURL = null;

// =========================
// Helpers visuais
// =========================
function showToast(msg, type = "success") {
  toastEl.textContent = msg;
  toastEl.className = "toast show " + (type === "error" ? "error" : "success");
  setTimeout(() => toastEl.classList.remove("show"), 3000);
}

function clearFieldErrors() {
  document.querySelectorAll(".err").forEach(el => (el.textContent = ""));
  document.querySelectorAll(".input-with-icon.has-error").forEach(el => el.classList.remove("has-error"));
}

function setFieldError(field, message) {
  const el = document.querySelector(`.err[data-err="${field}"]`);
  if (el) el.textContent = message || "";
  const input = document.getElementById(field);
  if (input) input.closest(".input-with-icon")?.classList.add("has-error");
}

function setLoading(loading) {
  btnSalvar.disabled = loading;
  btnLbl.hidden = loading;
  btnSpinner.hidden = !loading;
}

// =========================
// Máscara de CNPJ (00.000.000/0000-00)
// =========================
function maskCNPJ(value) {
  const d = (value || "").replace(/\D/g, "").slice(0, 14);
  if (!d) return "";
  if (d.length <= 2) return d;
  if (d.length <= 5) return `${d.slice(0, 2)}.${d.slice(2)}`;
  if (d.length <= 8) return `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5)}`;
  if (d.length <= 12) return `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5, 8)}/${d.slice(8)}`;
  return `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5, 8)}/${d.slice(8, 12)}-${d.slice(12)}`;
}
cnpjInput.addEventListener("input", (e) => {
  const pos = e.target.selectionStart;
  const before = e.target.value.length;
  e.target.value = maskCNPJ(e.target.value);
  // tenta manter o cursor
  const after = e.target.value.length;
  e.target.setSelectionRange(pos + (after - before), pos + (after - before));
});

// =========================
// Logo: drag & drop + click
// =========================
function applyImage(file) {
  if (!file) return;
  if (!file.type.startsWith("image/")) {
    showToast("Arquivo precisa ser imagem.", "error");
    return;
  }
  if (file.size > MAX_FILE_BYTES) {
    showToast("Imagem maior que 10 MB.", "error");
    return;
  }
  const reader = new FileReader();
  reader.onload = (e) => {
    imageDataURL = e.target.result;
    previewImg.src = imageDataURL;
    previewImg.style.display = "block";
    previewEmpty.style.display = "none";
    btnTrocar.hidden = false;
    btnRemover.hidden = false;
  };
  reader.readAsDataURL(file);
}

function clearImage() {
  imageDataURL = null;
  imgInput.value = "";
  previewImg.removeAttribute("src");
  previewImg.style.display = "none";
  previewEmpty.style.display = "flex";
  btnTrocar.hidden = true;
  btnRemover.hidden = true;
}

imgInput.addEventListener("change", () => {
  applyImage(imgInput.files?.[0]);
});

["dragenter", "dragover"].forEach(evt => {
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    e.stopPropagation();
    dropzone.classList.add("dragover");
  });
});
["dragleave", "drop"].forEach(evt => {
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    e.stopPropagation();
    dropzone.classList.remove("dragover");
  });
});
dropzone.addEventListener("drop", (e) => {
  applyImage(e.dataTransfer.files?.[0]);
});

btnTrocar.addEventListener("click", (e) => {
  e.preventDefault();
  imgInput.click();
});
btnRemover.addEventListener("click", (e) => {
  e.preventDefault();
  clearImage();
});

// =========================
// Submit
// =========================
form.addEventListener("submit", async (ev) => {
  ev.preventDefault();
  clearFieldErrors();

  const payload = {
    nome:     document.getElementById("nome").value.trim(),
    cnpj:     cnpjInput.value.trim() || null,
    endereco: document.getElementById("endereco").value.trim() || null,
    numero:   document.getElementById("numero").value.trim() || null,
    imagem:   imageDataURL || null,
  };

  if (!payload.nome) {
    setFieldError("nome", "Nome obrigatório");
    return;
  }

  setLoading(true);
  try {
    const resp = await fetch(API_BASE, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await resp.json().catch(() => ({}));

    if (!resp.ok) {
      if (data?.details && typeof data.details === "object") {
        Object.entries(data.details).forEach(([f, m]) => setFieldError(f, m));
      }
      showToast(data?.error || data?.message || "Erro ao salvar", "error");
      return;
    }

    showToast("Empresa cadastrada! Redirecionando para o login…", "success");
    setTimeout(() => window.location.replace("/login"), 1200);
  } catch (err) {
    console.error(err);
    showToast("Falha de conexão.", "error");
  } finally {
    setLoading(false);
  }
});
