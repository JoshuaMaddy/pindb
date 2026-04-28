(function () {
  function injectThumbStyles() {
    if (document.getElementById("pin-swiper-thumb-css")) {
      return;
    }
    var st = document.createElement("style");
    st.id = "pin-swiper-thumb-css";
    st.textContent =
      ".pin-swiper-thumbs .swiper-slide{opacity:0.55;cursor:pointer;width:4rem;height:4rem;}" +
      ".pin-swiper-thumbs .swiper-slide-thumb-active{opacity:1;}";
    document.head.appendChild(st);
  }
  function boot() {
    var root = document.getElementById("pin-image-carousel");
    if (!root || !window.Swiper) {
      return;
    }
    injectThumbStyles();
    var mainEl = root.querySelector(".pin-swiper-main");
    if (!mainEl) {
      return;
    }
    var n = parseInt(root.getAttribute("data-slide-count") || "1", 10);
    var thumbEl = root.querySelector(".pin-swiper-thumbs");
    var base = {
      spaceBetween: 0,
      loop: n > 1,
      grabCursor: true,
      keyboard: { enabled: true },
      navigation: {
        nextEl: root.querySelector(".pin-swiper-nav-next"),
        prevEl: root.querySelector(".pin-swiper-nav-prev"),
      },
    };
    if (n <= 1) {
      new window.Swiper(mainEl, base);
      return;
    }
    var thumbSwiper = new window.Swiper(thumbEl, {
      spaceBetween: 10,
      slidesPerView: "auto",
      freeMode: true,
      watchSlidesProgress: true,
    });
    base.thumbs = { swiper: thumbSwiper };
    new window.Swiper(mainEl, base);
  }
  function loadSwiper(cb) {
    if (window.Swiper) {
      cb();
      return;
    }
    var s = document.createElement("script");
    s.src = "https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.js";
    s.async = true;
    s.onload = cb;
    document.head.appendChild(s);
  }
  loadSwiper(boot);
})();
