document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".toast").forEach(t => setTimeout(() => t.remove(), 4200));
  const file = document.querySelector('input[type="file"]');
  if (file) file.addEventListener("change", () => {
    if (file.files[0] && file.files[0].size > 5 * 1024 * 1024) {
      alert("Please choose a file smaller than 5 MB.");
      file.value = "";
    }
  });
});
