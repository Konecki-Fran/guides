function showContent(guideId) {
  const el = document.querySelector(".content");
  console.log(`Showing content for ${guideId}`);
  if (el) {
    if (guideId === "DevRunner") {
      el.innerHTML = `<iframe width="100%" height="600" src="dev_runner_tutorial.html"></iframe>`;
    } else if (guideId === "LocalLLM") {
      el.innerHTML = `<iframe width="100%" height="600" src="deepseek-local-setup.html"></iframe>`;
    }
  }
}
