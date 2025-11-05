// =========================
// CONFIG
// =========================
const API_BASE = "/api/companias"; 
// ajuste se for /api/companies ou outro path

// =========================
// DOM refs
// =========================
const form       = document.getElementById("companie-form");
const toastEl    = document.getElementById("toast");
const imgInput   = document.getElementById("imagem");
const previewImg = document.getElementById("preview-img");
const previewTxt = document.getElementById("preview-empty");

const searchForm = document.getElementById("search-form");
const searchIdEl = document.getElementById("search-id");
const resultBox  = document.getElementById("result-box");

// Vamos segurar o dataURL aqui
let imageDataURL = null;

// =========================
// Helpers visuais
// =========================
function showToast(msg, type = "success") {
  toastEl.textContent = msg;
  toastEl.className = "toast show " + (type === "error" ? "error" : "success");
  // some depois
  setTimeout(() => {
    toastEl.classList.remove("show");
  }, 3000);
}

function clearFieldErrors() {
  document.querySelectorAll(".err").forEach(el => {
    el.textContent = "";
  });
}

function setFieldError(fieldName, message) {
  const el = document.querySelector(`.err[data-err="${fieldName}"]`);
  if (el) {
    el.textContent = message || "";
  }
}

// =========================
// Preview da imagem
// =========================
imgInput.addEventListener("change", () => {
  const file = imgInput.files && imgInput.files[0];
  if (!file) {
    imageDataURL = null;
    previewImg.style.display = "none";
    previewTxt.style.display = "block";
    previewTxt.textContent = "Nenhuma imagem selecionada";
    return;
  }

  // tamanho máximo 10 MB (10 * 1024 * 1024)
  if (file.size > 10 * 1024 * 1024) {
    showToast("Imagem maior que 10 MB.", "error");
    imgInput.value = "";
    imageDataURL = null;
    previewImg.style.display = "none";
    previewTxt.style.display = "block";
    previewTxt.textContent = "Arquivo muito grande";
    return;
  }

  const reader = new FileReader();
  reader.onload = (e) => {
    imageDataURL = e.target.result; // tipo "data:image/png;base64,iVBORw0..."
    previewImg.src = imageDataURL;
    previewImg.style.display = "block";
    previewTxt.style.display = "none";
  };
  reader.readAsDataURL(file);
});

// =========================
// Submit do form (POST criar empresa)
// =========================
form.addEventListener("submit", async (ev) => {
  ev.preventDefault();
  clearFieldErrors();

  const payload = {
    nome:      document.getElementById("nome").value.trim(),
    cnpj:      document.getElementById("cnpj").value.trim() || null,
    endereco:  document.getElementById("endereco").value.trim() || null,
    numero:    document.getElementById("numero").value.trim() || null,
    imagem:    imageDataURL || null, // <- o service espera 'imagem'
  };

  try {
    const resp = await fetch(API_BASE, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    const data = await resp.json().catch(() => ({}));

    if (!resp.ok) {
      // Tratar erro de validação no formato api_error
      if (data && data.details) {
        Object.entries(data.details).forEach(([field, msg]) => {
          // teu service retorna err = {"nome": "Campo 'nome' Obrigatório", ...}
          // aqui field seria "nome", "cnpj", etc.
          setFieldError(field, msg);
        });
      }

      // mensagem principal
      showToast(data.message || "Erro ao salvar", "error");
      return;
    }

    // sucesso -> limpar form?
    showToast("Empresa criada com sucesso! Redirecionando....", "success");
    // Se quiser limpar o form:
    form.reset();
    imageDataURL = null;
    previewImg.style.display = "none";
    previewTxt.style.display = "block";
    previewTxt.textContent = "Nenhuma imagem selecionada";
    setTimeout(() => {
      // use replace para não voltar pro form ao apertar "Voltar"
      window.location.replace("/login");
    }, 1200);

  } catch (err) {
    console.error(err);
    showToast("Falha de rede/conexão.", "error");
  }
});

// =========================
// Buscar empresa por ID (GET /api/companias/:id)
// =========================
searchForm.addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const id = searchIdEl.value.trim();
  if (!id) {
    showToast("Informe um ID para buscar.", "error");
    return;
  }

  try {
    const resp = await fetch(`${API_BASE}/${id}`, {
      method: "GET",
      headers: {
        "Accept": "application/json"
      }
    });

    const data = await resp.json().catch(() => ({}));

    if (!resp.ok) {
      showToast(data.message || "Empresa não encontrada", "error");
      resultBox.textContent = JSON.stringify(data, null, 2);
      return;
    }

    // IMPORTANTE:
    // O backend retorna o objeto SQLAlchemy.
    // Garanta que a sua rota está fazendo jsonify/serialize desse objeto
    // (expondo nome, cnpj, endereco, numero, e talvez flags tipo deleted).
    // Se ainda não faz, você precisa serializar no controller.
    resultBox.textContent = JSON.stringify(data, null, 2);
    showToast("Empresa carregada!", "success");

  } catch (err) {
    console.error(err);
    showToast("Falha de rede/conexão.", "error");
  }
});
