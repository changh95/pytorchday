/**
 * <section data-manim="SceneName"> 를 manim section 개수만큼의 슬라이드로 펼친다.
 *
 *  - 각 section 영상은 슬라이드 배경 영상(data-background-video)으로 재생된다.
 *  - section 사이에는 전환 효과가 없어서, 클릭할 때마다 애니메이션이 이어서 재생되는 것처럼 보인다.
 *  - section_type="loop" 로 렌더한 구간은 다음 클릭 전까지 반복 재생된다.
 *  - placeholder 안의 <aside class="notes"> 는 순서대로 각 section 슬라이드의 발표자 노트가 된다.
 *  - placeholder 안의 그 밖의 HTML(예: 캡션)은 첫 번째 section 슬라이드 위에 겹쳐진다.
 *
 * Reveal.initialize() 보다 먼저 실행되어야 한다. (manifest.js → manim.js → initialize 순서)
 */
(function () {
  const scenes = window.MANIM_SCENES || {};

  document.querySelectorAll("section[data-manim]").forEach((placeholder) => {
    const name = placeholder.dataset.manim;
    const scene = scenes[name];

    if (!scene || !scene.sections.length) {
      placeholder.classList.add("manim-missing");
      placeholder.innerHTML =
        `<p>⚠ manim scene <code>${name}</code> 이(가) 아직 렌더되지 않았습니다.</p>` +
        `<p><code>make anim</code> 을 실행하세요.</p>`;
      return;
    }

    const notes = [...placeholder.querySelectorAll("aside.notes")];
    notes.forEach((n) => n.remove());
    const overlay = placeholder.innerHTML.trim();
    const bg = getComputedStyle(document.documentElement).getPropertyValue("--bg").trim() || "#000";

    const slides = scene.sections.map((sec, i) => {
      const s = document.createElement("section");
      s.className = "manim-slide";
      s.dataset.manimScene = name;
      s.dataset.manimSection = sec.name;
      s.dataset.backgroundVideo = sec.src;
      s.dataset.backgroundVideoMuted = "";
      s.dataset.backgroundColor = bg;
      if (sec.type === "loop") s.dataset.backgroundVideoLoop = "";

      // 첫 section 은 덱 기본 전환으로 들어오고, 이후 section 은 끊김 없이 이어진다.
      if (i > 0) {
        s.dataset.transition = "none";
        s.dataset.backgroundTransition = "none";
      } else {
        // placeholder 의 나머지 data-* 속성(예: data-transition="none")은 첫 슬라이드에 적용
        for (const [k, v] of Object.entries(placeholder.dataset)) {
          if (k !== "manim") s.dataset[k] = v;
        }
        if (overlay) s.innerHTML = overlay;
      }
      if (notes[i]) s.appendChild(notes[i]);
      return s;
    });

    placeholder.replaceWith(...slides);
  });
})();
