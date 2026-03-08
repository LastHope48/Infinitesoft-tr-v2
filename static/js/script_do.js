document.addEventListener("DOMContentLoaded", function() {
    const modeSelect = document.getElementById("mode-select");
    const storyMode = document.getElementById("story-mode");
    const gameMode = document.getElementById("game-mode");
    const storyText = document.getElementById("story-text");

    const storyLines = [
        "Ali: Kulem neden yıkıldı?",
        "Ayşe: Benimki neden sağlam kaldı?",
        "Ali: Belki kullandığımız şekiller farklıdır...",
        "Ayşe: Evet! Üçgenler daha dayanıklıymış!",
    ];

    let currentLine = 0;

    function showStoryLine() {
        if (currentLine < storyLines.length) {
            storyText.innerText = storyLines[currentLine];
            currentLine++;
            setTimeout(showStoryLine, 2000);
        }
    }

    // Butonları seç
    const storyBtn = document.getElementById("story-btn");
    const gameBtn = document.getElementById("game-btn");
    const startGameBtn = document.getElementById("start-game-btn");
    const restartBtn = document.getElementById("restart-btn");

    const dikdortgen = document.getElementById("dikdortgen");
    const ucbgen = document.getElementById("ucbgen");

    // Moda geçiş
    storyBtn.addEventListener("click", () => {
        modeSelect.style.display = "none";
        storyMode.style.display = "block";
        showStoryLine();
    });

    gameBtn.addEventListener("click", () => {
        modeSelect.style.display = "none";
        gameMode.style.display = "block";
    });

    startGameBtn.addEventListener("click", () => {
        storyMode.style.display = "none";
        gameMode.style.display = "block";
    });

    // Oyun modu tıklama animasyonları
    dikdortgen.addEventListener("click", () => {
        dikdortgen.style.transform = "rotate(20deg) translateY(50px)";
        alert("Dikdörtgen kule yıkıldı!"); 
    });

    ucbgen.addEventListener("click", () => {
        ucbgen.style.transform = "translateY(0px)";
        alert("Üçgen kule sağlam kaldı!"); 
    });

    // Tekrar oynama
    restartBtn.addEventListener("click", () => {
        dikdortgen.style.transform = "rotate(0deg) translateY(0px)";
        ucbgen.style.transform = "rotate(0deg) translateY(0px)";
        // Gerekirse mod tekrar seçme ekranına dön
        gameMode.style.display = "none";
        modeSelect.style.display = "block";
        currentLine = 0;
    });
});
// MOD AYRIMI
document.addEventListener("DOMContentLoaded", function() {
    const gameArea = document.getElementById("game-area");
    const ROWS = 3;
    const COLS = 2;
    const BLOCK_SIZE = 60;

    let board = Array.from({length: ROWS}, () => Array(COLS).fill(null));
    let placedPieces = 0;

    function makeDraggable(piece) {
        let offsetX, offsetY;

        piece.addEventListener("mousedown", (e) => {
            if (placedPieces >= 6) return; // 2x3 dolduysa hareket yok

            offsetX = e.offsetX;
            offsetY = e.offsetY;

            function move(eMove) {
                piece.style.left = eMove.clientX - offsetX - gameArea.getBoundingClientRect().left + "px";
                piece.style.top = eMove.clientY - offsetY - gameArea.getBoundingClientRect().top + "px";
            }

            function up(eUp) {
                document.removeEventListener("mousemove", move);
                document.removeEventListener("mouseup", up);

                let left = parseInt(piece.style.left);
                let top = parseInt(piece.style.top);

                let col = Math.round(left / BLOCK_SIZE);
                let row = Math.round(top / BLOCK_SIZE);

                // Sınır kontrolü
                if (row < 0 || row >= ROWS || col < 0 || col >= COLS) {
                    alert("Burası geçersiz!");
                    piece.style.left = "0px";
                    piece.style.top = "0px";
                    return;
                }

                // Eğer o hücre doluysa izin verme
                if (board[row][col] !== null) {
                    alert("Bu hücre dolu!");
                    piece.style.left = "0px";
                    piece.style.top = "0px";
                    return;
                }

                // İlk parça her yere konabilir
                if (placedPieces > 0) {
                    // Sonraki parçalar sadece komşulara
                    const dirs = [
                        [0,1],[1,0],[0,-1],[-1,0]
                    ];
                    let canPlace = false;
                    for (const [dr, dc] of dirs) {
                        const r = row + dr;
                        const c = col + dc;
                        if (r>=0 && r<ROWS && c>=0 && c<COLS) {
                            if (board[r][c] !== null) {
                                canPlace = true;
                                break;
                            }
                        }
                    }
                    if (!canPlace) {
                        alert("Parça buraya eklenemez!");
                        piece.style.left = "0px";
                        piece.style.top = "0px";
                        return;
                    }
                }

                // Hücreyi işaretle
                board[row][col] = piece.dataset.type;

                // Yeni parça oluştur
                const newPiece = piece.cloneNode(true);
                newPiece.style.position = "absolute";
                newPiece.style.left = (col * BLOCK_SIZE) + "px";
                newPiece.style.top = (row * BLOCK_SIZE) + "px";
                gameArea.appendChild(newPiece);
                makeDraggable(newPiece);

                placedPieces++;

                // Sonsuz parça için orijinalini sıfırla
                piece.style.left = "0px";
                piece.style.top = "0px";

                // 2x3 tamamlandıysa
                if (placedPieces === 6) {
                    setTimeout(() => alert("Tebrikler! 2x3 kule tamamlandı!"), 100);
                }
            }

            document.addEventListener("mousemove", move);
            document.addEventListener("mouseup", up);
        });
    }

    const initialPieces = document.querySelectorAll(".piece");
    initialPieces.forEach(piece => {
        piece.style.position = "relative";
        piece.style.left = "0px";
        piece.style.top = "0px";
        makeDraggable(piece);
    });

    document.getElementById("restart-btn").addEventListener("click", () => {
        gameArea.innerHTML = "";
        board = Array.from({length: ROWS}, () => Array(COLS).fill(null));
        placedPieces = 0;
    });
});
document.addEventListener("DOMContentLoaded", function() {
    const gameArea = document.getElementById("game-area");
    const BLOCK_SIZE = 60;
    const ROWS = 3;
    const COLS = 2;
    
    let placedPieces = 0;
    const MAX_PIECES = 6; // 2x3 blok (her blok = 2 üçgen)

    // Üçgene tıklama
    document.querySelectorAll(".piece[data-type='ucgen']").forEach(piece => {
        piece.addEventListener("click", () => {
            if (placedPieces >= MAX_PIECES) {
                alert("Kule zaten tamamlandı!");
                return;
            }

            const rect = piece.getBoundingClientRect();
            const gameRect = gameArea.getBoundingClientRect();
            const startLeft = rect.left - gameRect.left;
            const startTop = rect.top - gameRect.top;

            for (let r = 0; r < ROWS; r++) {
                for (let c = 0; c < COLS; c++) {
                    // Kare başına 2 üçgen
                    const leftTriangle = piece.cloneNode(true);
                    leftTriangle.classList.add("triangle-left");
                    leftTriangle.style.left = startLeft + c * BLOCK_SIZE + "px"; 
                    leftTriangle.style.top = startTop + r * BLOCK_SIZE + "px";
                    gameArea.appendChild(leftTriangle);

                    const rightTriangle = piece.cloneNode(true);
                    rightTriangle.classList.add("triangle-right");
                    // **Sağa kaydırıyoruz**: left += BLOCK_SIZE / 2
                    rightTriangle.style.left = startLeft + c * BLOCK_SIZE + BLOCK_SIZE/2 + "px"; 
                    rightTriangle.style.top = startTop + r * BLOCK_SIZE + "px";
                    gameArea.appendChild(rightTriangle);

                    placedPieces++;
                    if (placedPieces >= MAX_PIECES) break;
                }
                if (placedPieces >= MAX_PIECES) break;
            }

            alert("Kule tamamlandı! 12 üçgen yerleştirildi.");
        });
    });
});
document.getElementById("start-kule").addEventListener("click", () => {
    const gameArea = document.getElementById("game-area");
    const ROWS = 3;
    const COLS = 2;
    const BLOCK_SIZE = 60;

    for (let r = 0; r < ROWS; r++) {
        for (let c = 0; c < COLS; c++) {
            const square = document.createElement("div");
            square.classList.add("square");
            square.style.left = c * BLOCK_SIZE + "px";
            square.style.top = r * BLOCK_SIZE + "px";

            const leftTriangle = document.createElement("div");
            leftTriangle.classList.add("triangle-left");

            const rightTriangle = document.createElement("div");
            rightTriangle.classList.add("triangle-right");

            square.appendChild(leftTriangle);
            square.appendChild(rightTriangle);

            gameArea.appendChild(square);
        }
    }
});