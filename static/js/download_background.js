let lastBlobUrl = null;

form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const file = fileInput.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("image", file);

    originalImg.src = URL.createObjectURL(file);
    originalImg.style.display = "block";

    const res = await fetch("https://wf5528-infinitesoft-tr.hf.space/remove-bg", {
        method: "POST",
        body: formData
    });

    const blob = await res.blob();
    lastBlobUrl = URL.createObjectURL(blob);

    resultImg.src = lastBlobUrl;
    resultImg.style.display = "block";

    downloadBtn.style.display = "inline-flex";
});

// gerçek indirme
downloadBtn.addEventListener("click", () => {
    const a = document.createElement("a");
    a.href = lastBlobUrl;
    a.download = "arka-plan-silindi.png";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
});
