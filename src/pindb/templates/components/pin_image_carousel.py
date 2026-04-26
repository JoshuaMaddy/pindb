"""
htpy page and fragment builders: `templates/components/pin_image_carousel.py`.

Front/back pin images as a Swiper carousel with thumbnails. Pairs with
`pin_lightbox` — main slide images get the `pin-zoomable` class so the
shared lightbox script picks them up.
"""

from fastapi import Request
from htpy import Element, Fragment, div, fragment, img, link

from pindb.database.pin import Pin
from pindb.templates.pin_image_alt import pin_back_image_alt, pin_front_image_alt

IMG_CAROUSEL_HEIGHT: str = (
    "w-full max-h-[30vh] sm:max-h-[60vh] object-contain bg-pin-base-500"
)

PIN_SWIPER_INIT: str = """
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
"""


def pin_image_carousel(request: Request, pin: Pin) -> Fragment:
    """Front/back images as a Swiper carousel (thumbnails, drag, arrows, loop)."""
    front_full: str = str(request.url_for("get_image", guid=pin.front_image_guid))
    front_thumb: str = str(
        request.url_for("get_image", guid=pin.front_image_guid).include_query_params(
            thumbnail=True
        )
    )
    slides: list[tuple[str, str, str]] = [
        ("Front", front_full, front_thumb),
    ]
    if pin.back_image_guid:
        slides.append(
            (
                "Back",
                str(request.url_for("get_image", guid=pin.back_image_guid)),
                str(
                    request.url_for(
                        "get_image", guid=pin.back_image_guid
                    ).include_query_params(thumbnail=True)
                ),
            )
        )
    slide_count: int = len(slides)
    nav_hidden: str = " hidden" if slide_count <= 1 else ""

    main_slides: list[Element] = []
    thumb_slides: list[Element] = []
    for idx, (_label, full_url, thumb_url) in enumerate(slides):
        slide_alt: str = (
            pin_front_image_alt(pin) if idx == 0 else pin_back_image_alt(pin)
        )
        main_slides.append(
            div(class_="swiper-slide flex items-center justify-center bg-pin-base-500")[
                img(
                    alt=slide_alt,
                    class_=IMG_CAROUSEL_HEIGHT + " pin-zoomable cursor-zoom-in",
                    loading="eager" if idx == 0 else "lazy",
                    src=full_url,
                    role="button",
                    tabindex="0",
                    aria_label=f"View {slide_alt} full size",
                )
            ]
        )
        thumb_slides.append(
            div(
                class_="swiper-slide box-border! overflow-hidden rounded border border-pin-base-400"
            )[
                img(
                    alt=slide_alt,
                    class_="h-full w-full object-cover",
                    loading="lazy",
                    src=thumb_url,
                )
            ]
        )

    nav_btn: str = (
        "pointer-events-auto !h-10 !w-10 shrink-0 text-accent after:!text-xl "
        "after:!text-accent"
    )
    main_swiper: Element = div(class_="swiper pin-swiper-main w-full min-w-0")[
        div(class_="swiper-wrapper")[*main_slides],
    ]
    nav_prev: Element = div(
        class_="pin-swiper-nav-prev swiper-button-prev absolute left-auto! right-full! top-1/2 z-10 m-0! -translate-y-1/2! "
        + nav_btn
        + nav_hidden,
        **{"aria-label": "Previous image"},
    )
    nav_next: Element = div(
        class_="pin-swiper-nav-next swiper-button-next absolute left-full! right-auto! top-1/2 z-10 m-0! -translate-y-1/2! "
        + nav_btn
        + nav_hidden,
        **{"aria-label": "Next image"},
    )
    main_row: Element = div(class_="relative w-full overflow-visible")[
        main_swiper,
        nav_prev,
        nav_next,
    ]
    carousel_children: list[Element] = [main_row]
    if slide_count > 1:
        carousel_children.append(
            div(class_="swiper pin-swiper-thumbs w-full overflow-hidden")[
                div(
                    class_="swiper-wrapper flex! w-full! items-center! justify-center!",
                )[*thumb_slides],
            ],
        )

    return fragment[
        link(
            rel="stylesheet",
            href="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.css",
        ),
        div(
            class_="relative flex w-full flex-col gap-3 md:gap-5 overflow-x-visible",
            id="pin-image-carousel",
            **{"data-slide-count": str(slide_count)},
        )[*carousel_children],
    ]
