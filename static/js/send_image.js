const form = document.getElementById("bgForm");
const fileInput = document.getElementById("fileInput");
const resultImg = document.getElementById("result");
const originalImg = document.getElementById("original");
const downloadBtn = document.getElementById("downloadBtn");

form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const file = fileInput.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("image", file);

    // solda orijinal
    originalImg.src = URL.createObjectURL(file);
    originalImg.style.display = "block";

    const res = await fetch("https://wf5528-infinitesoft-tr.hf.space/remove-bg", {
        method: "POST",
        body: formData
    });

    const blob = await res.blob();
    const url = URL.createObjectURL(blob);

    // sağda sonuç
    resultImg.src = url;
    resultImg.style.display = "block";

    downloadBtn.href = url;
    downloadBtn.style.display = "inline-block";
});