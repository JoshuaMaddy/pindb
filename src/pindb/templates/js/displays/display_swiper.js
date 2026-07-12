(function () {
  function boot() {
    var root = document.getElementById("display-carousel");
    if (!root || !window.Swiper) {
      return;
    }
    var mainEl = root.querySelector(".display-swiper-main");
    if (!mainEl) {
      return;
    }
    var slideCount = root.querySelectorAll(".swiper-slide").length;
    new window.Swiper(mainEl, {
      spaceBetween: 0,
      loop: slideCount > 1,
      grabCursor: true,
      keyboard: { enabled: true },
      navigation: {
        nextEl: root.querySelector(".swiper-button-next"),
        prevEl: root.querySelector(".swiper-button-prev"),
      },
      pagination: {
        el: root.querySelector(".swiper-pagination"),
        clickable: true,
      },
    });
  }
  // Vendored swiper.min.js loads (deferred, in document order) before this
  // script — see templates/user/display_page.py head_content.
  boot();
})();
