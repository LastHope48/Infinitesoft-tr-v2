const menuBtn = document.getElementById("menuBtn");
const sideMenu = document.getElementById("sideMenu");
const overlay = document.getElementById("overlay");
const closeMenu = document.getElementById("closeMenu");

menuBtn.onclick = () => {
  sideMenu.classList.add("active");
  overlay.classList.add("active");
};

overlay.onclick = closeMenu.onclick = () => {
  sideMenu.classList.remove("active");
  overlay.classList.remove("active");
};