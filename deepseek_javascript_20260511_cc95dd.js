// AETHERIUS EXTENSION - CAPTURA EM TEMPO REAL
(function() {
    console.log("🚀 AETHERIUS EXTENSION INICIADA");
    
    let ultimaRodada = null;
    
    // ALTERE PARA URL DO SEU RENDER
    const API_URL = "https://SEU-APP.onrender.com/api/rodada";
    
    function capturarRodada() {
        try {
            // Número da rodada
            let rodada = null;
            let elementos = document.querySelectorAll('span, div');
            
            for (let el of elementos) {
                let texto = el.innerText || el.textContent;
                if (texto && (texto.match(/Rodada\s+(\d+)/i) || texto.match(/^\d{6,7}$/))) {
                    let match = texto.match(/(\d{6,7})/);
                    if (match) rodada = parseInt(match[0]);
                    break;
                }
            }
            
            // Multiplicador
            let multiplier = null;
            let mulEl = document.querySelector('[class*="bubble-multiplier"]');
            if (mulEl) {
                let texto = mulEl.innerText;
                let match = texto.match(/(\d+\.?\d*)/);
                if (match) multiplier = parseFloat(match[0]);
            }
            
            // Horário
            let horario = new Date().toLocaleTimeString('pt-BR');
            let horEl = document.querySelector('[class*="header__info-time"]');
            if (horEl) horario = horEl.innerText.trim();
            
            // Nova rodada
            if (rodada && rodada !== ultimaRodada && multiplier) {
                ultimaRodada = rodada;
                console.log(`📊 Rodada ${rodada} | ${multiplier}x | ${horario}`);
                
                fetch(API_URL, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        rodada: rodada,
                        multiplier: multiplier,
                        horario: horario,
                        source: 'extension'
                    })
                }).catch(err => console.error("Erro:", err));
            }
        } catch(e) {
            console.error(e);
        }
    }
    
    setInterval(capturarRodada, 1000);
    new MutationObserver(() => capturarRodada()).observe(document.body, { childList: true, subtree: true });
    
    console.log("✅ Extensão ativa!");
})();