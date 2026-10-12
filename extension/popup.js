document.getElementById("go").onclick = () => {
  const email = document.getElementById("email").value.trim();
  const form = document.getElementById("form").value.trim();
  const err = document.getElementById("err");
  if (!/^\S+@\S+\.\S+$/.test(email)) return (err.textContent = "Enter your school email.");
  if (!form.startsWith("https://docs.google.com/forms/")) return (err.textContent = "Paste the Google Form link.");
  const url = chrome.runtime.getURL(`exam.html?email=${encodeURIComponent(email)}&form=${encodeURIComponent(form)}`);
  chrome.tabs.create({ url });
  window.close();
};
