const submitBtn = document.querySelector(".submit");
const tickCircle = document.querySelector(".tick-circle");

submitBtn.addEventListener("click", function(e){
  e.preventDefault();

  // Butonu küçült ve kaybol
  submitBtn.style.transform = "scale(0.3)";
  submitBtn.style.opacity = "0";

  // Tik topu büyüt
  setTimeout(() => {
    tickCircle.style.width = "95px";
    tickCircle.style.height = "95px";
    tickCircle.style.transform = "translate(-50%, -50%) scale(1)";
  }, 300);
});