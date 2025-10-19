document.getElementById("loginForm").addEventListener("submit", async (e) => {
      e.preventDefault();
      const username = document.getElementById("username").value;
      const password = document.getElementById("password").value;

      try {
        const resp = await fetch("/login", {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: new URLSearchParams({ username, password })
        });

        if (resp.redirected) {
          window.location.href = resp.url; // Flask redireciona se sucesso
        } else {
          const msg = document.getElementById("msg");
          msg.textContent = "E-mail ou senha inválidos.";
        }
      } catch (err) {
        console.error(err);
        document.getElementById("msg").textContent = "Erro ao tentar login.";
      }
    });