(function () {
  // Leaves a little breathing room below the carousel (nav buttons, page margin)
  // instead of pinning the bottom edge exactly to the viewport edge.
  var BOTTOM_MARGIN_PX = 16;
  var MIN_HEIGHT_PX = 320;

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
    var swiper = new window.Swiper(mainEl, {
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

    function fillRemainingHeight() {
      var top = mainEl.getBoundingClientRect().top;
      var available = window.innerHeight - top - BOTTOM_MARGIN_PX;
      mainEl.style.height = Math.max(available, MIN_HEIGHT_PX) + "px";
      swiper.update();
    }

    fillRemainingHeight();
    window.addEventListener("resize", fillRemainingHeight);
  }
  // Vendored swiper.min.js loads (deferred, in document order) before this
  // script — see templates/user/display_page.py head_content.
  boot();
})();
