/**
 * 이미지 파일이 아직 없으면, 넣어야 할 경로가 적힌 점선 박스로 대신 보여준다.
 * 파일을 그 경로에 넣으면 자동으로 사진이 보인다.
 */
(function () {
  function swap(img) {
    const box = document.createElement("div");
    box.className = ["img-placeholder", ...img.classList].join(" ");
    const label = document.createElement("span");
    label.textContent = img.alt || "image";
    const path = document.createElement("code");
    path.textContent = img.getAttribute("src");
    box.append(label, path);
    img.replaceWith(box);
  }

  document.querySelectorAll(".reveal img").forEach((img) => {
    // 이미 실패한 경우 (SVG 는 intrinsic size 가 0 일 수 있어 제외)
    const isSvg = /\.svg($|\?)/.test(img.getAttribute("src") || "");
    if (img.complete && img.naturalWidth === 0 && !isSvg) swap(img);
    else img.addEventListener("error", () => swap(img), { once: true });
  });
})();
